# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
# Version: $Id: DCacheAggregator.py,v 1.29 2009/10/21 20:24:46 greenc Exp $
#
# This is a first attempt at a python program that reads the dCache billing
# database, aggregates any new content, and posts it to Gratia.

import os
import sys
import logging
import time
import sqlalchemy
import Gratia
import traceback
import pwd
import locale
import datetime
import re

from Checkpoint import Checkpoint
from Alarm import Alarm

import TimeBinRange
import Collapse

DCACHE_AGG_FIELDS = ['initiator', 'client', 'protocol', 'errorcode', 'isnew']
DCACHE_SUM_FIELDS = ['njobs','transfersize','connectiontime']

# If the DB query takes more than this amount of time, something is very wrong!
MAX_QUERY_TIME_SECS = 180

re_parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB' )

def _Meminfo():
    """-> dict of data from meminfo (str:int).
    Values are in kilobytes.
    """
    result = dict()
    for line in open('/proc/meminfo'):
        match = re_parser.match(line)
        if not match:
            continue # skip lines that don't parse
        key, value = match.groups(['key', 'value'])
        result[key] = int(value)
    return result

def _CalcMaxSelect():
    """
    Returns the maximum number of sql results so that
    we do not use more than half of the install RAM on
    the current machine.
    """
    try:
        mem = _Meminfo()["MemTotal"]
        if ( mem < 2048000 ) : mem = 2048000
        return int(mem / 4)
    except:
        return 512000
    
STARTING_MAX_SELECT = 32000
MAX_SELECT = _CalcMaxSelect()
STARTING_RANGE = 60
MIN_RANGE = 1


BILLINGDB_SELECT_CMD = """
    SELECT
        b.datestamp AS datestamp,
        b.transaction AS transaction,
        b.cellname AS cellname,
        b.action AS action,
        b.transfersize AS transfersize,
        b.connectiontime AS connectiontime,
        b.isnew AS isnew,
        b.client AS client,
        b.errorcode AS errorcode,
        b.protocol AS protocol,
        b.initiator AS doorlink,
        COALESCE(d.owner, 'unknown') AS initiator,
        COALESCE(d.client, 'Unknown') AS initiatorHost,
        d.mappeduid as mappeduid
    FROM
        (
            SELECT *
            FROM billinginfo b
            WHERE b.datestamp >= '%s' AND b.datestamp < '%s'
            ORDER BY datestamp
            LIMIT %i
        ) as b
    LEFT JOIN doorinfo d ON b.initiator = d.transaction;
"""

import warnings
warnings.simplefilter('ignore', FutureWarning)

class DCacheAggregator:
    """
    This class reads the dCache billing database on the specified host
    and pulls out the next set of data to be sent to gratia. It remembers
    what it has already sent by looking at the last successful checkpoint.
    Note that we limit the select to _maxSelect items to moderate memory
    usage when a lot of records have arrived since the probe was last run.
    """

    _connection = None
    _maxSelect = STARTING_MAX_SELECT
    _range = STARTING_RANGE
    
    # Do not send in records older than 30 days
    _maxAge = 30

    def __init__( self, configuration, chkptdir=None ):
        # Pick up the logger
        self._log = logging.getLogger( 'DCacheAggregator' )
        DBurl = 'postgres://' + configuration.get_DBLoginName() + ':' + \
                configuration.get_DBPassword() + '@' + \
                configuration.get_DBHostName() + ':5432/billing'

        self._skipIntraSite = configuration.get_OnlySendInterSiteTransfers()
        self._stopFileName = configuration.get_StopFileName()
        self._dCacheSvrHost = configuration.get_DCacheServerHost()
        # Create the billinginfo database checkpoint.
        self._maxAge = configuration.get_MaxBillingHistoryDays()
        billinginfoChkpt = 'chkpt_dcache_xfer_DoNotDelete'
        if chkptdir != None:
            billinginfoChkpt = os.path.join(chkptdir, billinginfoChkpt)
        self._BIcheckpoint = Checkpoint(billinginfoChkpt, self._maxAge)

        self._sendAlarm = Alarm(
                configuration.get_EmailServerHost(),
                configuration.get_EmailFromAddress(),
                configuration.get_EmailToList(),
                'dCacheTransfer probe aggregator alarm',
                'The dCache Transfer Probe was not able to send to Gratia.',
                2,    # If more than two errors have occurred
                1800, # Max of once per half hour complaining
                True )

        self._summarize = configuration.get_Summarize();

        # Connect to the dCache postgres database.
        try:
            self._db = sqlalchemy.create_engine( DBurl )
            self._connection = self._db.connect()
        except:
            tblist = traceback.format_exception( sys.exc_type,
                                                 sys.exc_value,
                                                 sys.exc_traceback)
            errmsg = 'Failed to connect to ' + DBurl + \
                     '\n\n' + "".join( tblist )
            self._log.error( errmsg )
            raise

        self._grid = configuration.get_Grid()

    def _skipIntraSiteXfer( self, row ) :
        """
        Boolean method that returns true if the specified row is for an
        intra-site transfer and we the configuration file said to skip
        such records.
        """
        return self._skipIntraSite and row['protocol'].startswith("DCap")

    def _execute(self, starttime, endtime, maxSelect):
        """
        Execute the select command against the Billing DB return the results
        (possibly summarized)

        It is guaranteed this function will return an endtime greater than the
        starttime, but not guaranteed by how much.
        
        Note on the time returned as the first part of the tuple:
        This is time that is guaranted to be after all the record included in 
        select and it thus suitable to use as the start time of the next select
        query.   In the current implementation, it is the upper limit of the 
        actual query.  We reduce the range until it reaches 1 second or the
        query return less than maxSelect results.   If the interval is one 
        second and it still returns maxSelect results then we extend the limit 
        of the query until all records fit and in consequence:

           Let's say endtime = the parameter, endtime2 = max of starttimes in 
               the results of the select query
           if endtime2 < endtime and len(result) < maxSelect, then we know that 
               there are no records between (endtime2, endtime].  Hence, we can
               return endtime.
           if endtime2 < endtime and len(result) == maxSelect, then we don't 
               know if we got all the records at time value endtime2, so we
               increase maxSelect and try again.
           Assuming a finite number of records, you eventually increase
           maxSelect until you return endtime or throw an exception.
           Finally, if endtime2 == endtime, you can just return endtime.

        @param starttime: Datetime object for the start of the query interval.
        @param endtime: Datetime object for the end of the query interval.
        @param maxSelect: The maximum number of rows to select
        @return: Tuple containing the a time that is greater than all the 
           records and the results
        """
        assert starttime < endtime
        if (maxSelect > MAX_SELECT) and ((endtime-starttime).seconds <= MIN_RANGE):
            raise Exception("Fatal error - more than %i transfers in %i" \
                " second(s)." % (MAX_SELECT,(endtime-starttime).seconds)
        datestr = str(starttime)
        datestr_end = str(endtime)
       
        dictRecordAgg = TimeBinRange.DictRecordAggregator(DCACHE_AGG_FIELDS,
            DCACHE_SUM_FIELDS)
 
        # Query the database.  If it takes more than MAX_QUERY_TIME_SECS, then
        # have the probe self-destruct.
        #self._log.debug('_sendToGratia: will execute ' + BILLINGDB_SELECT_CMD \
        #    % (datestr, datestr_end, maxSelect))
        select_time = -time.time()
        result = self._connection.execute(BILLINGDB_SELECT_CMD % (datestr,
            datestr_end, maxSelect)).fetchall()
        select_time += time.time()
        if select_time > MAX_QUERY_TIME_SECS:
            raise Exception("Postgres query took %i seconds, more than " \
                "the maximum allowable of %i; this is a sign the DB is " \
                "not properly optimized!" % (int(select_time),
                MAX_QUERY_TIME_SECS))
        self._log.debug("BillingDB query finished in %.02f seconds and " \
            "returned %i records." % (select_time, len(result)))

        if not result:
            self._log.debug("No results from %s to %s." % (starttime, endtime))
            return endtime, result

        # If we hit our limit, there's no telling how many identical records
        # there are on the final millisecond; we must re-query with higher
        # limits.
        if len(result) == maxSelect:
            interval = (endtime - starttime).seconds
            new_interval = int(interval / 2)
            if (interval == new_interval or new_interval == 0):
               self._log.warning("Limit hit; increasing from %i to %i." % \
                  (maxSelect, maxSelect*2))
               endtime, result = self._execute(starttime, endtime, maxSelect*2)
               assert endtime > starttime
               return endtime, result
            else:
               self._log.warning("Limit hit; decreasing time interval from %i to %i." % \
                  (interval, new_interval)
               self._range = new_interval 
               endtime = starttime + datetime.timedelta(0, new_interval)
               endtime, result = self._execute(starttime, endtime, maxSelect*2)
               assert endtime > starttime
               return endtime, result

        return endtime, result

    def _processResults(self, results):
        """
        Process all of the results
        """
        numDone = 0
        for row in results:
            row = dict(row)
            row.setdefault("njobs", 1)
            try:
                numDone += self._processDBRow(row)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, e:
                self._log.warning("Unable to make a record out of the " \
                    "following SQL row: %s." % str(row))
                self._log.exception(e)
                # Increment numDone, otherwise we will exit early.
                numDone += row['njobs']
        return numDone

    def _processDBRow(self, row):
        """
        Completely process a single DB row.  Take the row, convert it to a 
        UsageRecord, and send it up to Gratia.  Process any errors which
        occurred during the process.

        @return: The number of jobs in this row, regardless of whether we sent
           them successfully or not.
        """
        # Skip intra-site transfers if required
        if self._skipIntraSiteXfer(row):
            return row['njobs']

        usageRecord = self._convertBillingInfoToGratiaUsageRecord(\
                        row)

        # Send to gratia, and see what it says.
        response = Gratia.Send(usageRecord)
        baseMsg = "Record: %s, %s, njobs %i" % (str(row['datestamp']),
            row['transaction'], row['njobs'])
        if response == "Fatal Error: too many pending files":
            # The server is currently not accepting record and
            # Gratia.py was not able to store the record, we will
            # need to resend it.
            # For now take a long nap and then by 'break' we
            # force a retry for this record.
            self._log.error("Error sending : too many pending files")
            longsleep = 15*60
            self._log.warn("sleeping for = %i seconds." % longsleep)
            time.sleep(longsleep)
        elif response.startswith('Fatal Error') or \
            response.startswith('Internal Error'):
            self._log.critical( 'error sending ' + baseMsg + \
                '\ngot response ' + response )
            sys.exit(2)
            self._log.debug( 'sent ' + baseMsg )
        # If we got a non-fatal error, slow down since the server
        # might be overloaded.
        if response[:2] != 'OK':
                        self._log.error( 'error sending ' + baseMsg + \
                                        '\ngot response ' + response )

        return row['njobs']

    def _convertBillingInfoToGratiaUsageRecord(self, row):
        """
        Take a record returned from the database and convert it to a Gratia
        UsageRecord

        @param row: A dictionary-like object describing the Billing DB entry.
        @return: UsageRecord equivalent to the input row
        """
        # Convert date to utc. This can't be done perfectly, alas, since we
        # don't have the original timezone. We assume localtime.
        # This code is horrible, but it should work. row['datestamp'] should
        # be a datetime.datetime object.
        # make the time into a float
        fltTime = time.mktime(row['datestamp'].timetuple())
        startTime = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(fltTime))
        # NOTE WELL: we need the time accurate to milliseconds. So we
        # add it back to the UTC time.
        startTime = startTime + "." + \
                    locale.format("%06d", row['datestamp'].microsecond) + "Z"

        # convert the connection time in milliseconds to a decimal in seconds
        connectTime = float(row['connectiontime']) / 1000.0
        connectionTimeStr = 'PT' + str(connectTime) + 'S'

        # Check for the link to the doorinfo table being bad and log a
        # warning in the hope that somebody notices a bug has crept in.
        if row['doorlink'] == '<undefined>' and \
                   not row['protocol'].startswith('DCap'):
            self._log.warn( 'billinginfo record with datestamp ' + \
                        startTime + ' contained undefined initiator field' );

        # Work out the end points of the data transfer.
        thisHost = str(row['cellname']) + '@' + self._dCacheSvrHost
        if row['isnew']:
            srcHost = row['client']
            dstHost = thisHost
            isNew = 1
        else:
            srcHost = thisHost
            dstHost = row['client']
            isNew = 0

        r = Gratia.UsageRecord('Storage')
        r.Njobs(row['njobs'])
        r.AdditionalInfo('Source', srcHost)
        r.AdditionalInfo('Destination', dstHost)
        r.AdditionalInfo('Protocol', row['protocol'])
        r.AdditionalInfo('IsNew', isNew)
        r.LocalJobId(row['transaction'])
        if row['protocol'].startswith("DCap"):
            r.Grid("Local")
        else:
            r.Grid("OSG")
        r.StartTime( startTime )
        r.Network(row['transfersize'], 'b', connectionTimeStr, 'total',
            row['action'])
        r.WallDuration(connectionTimeStr)

        # only send the initiator if it is known.
        if row['initiator'] != 'unknown':
            r.DN( row['initiator'] )
        # if the initiator host is "unknown", make it "Unknown".
        initiatorHost = row['initiatorhost']
        if initiatorHost == 'unknown':
            initiatorHost = 'Unknown'
        r.SubmitHost(initiatorHost)
        r.Status(row['errorcode'])
        # If we included the mapped uid as the local user id, then
        # Gratia will make a best effort to map this to the VO name.
        mappedUID = row['mappeduid']
        try:
            if mappedUID != None and int(mappedUID) > 0:
                try:
                    info = pwd.getpwuid(int(mappedUID))
                except:
                    self._log.warn("UID %s not found locally; make sure " \
                        "/etc/passwd on this host and your dCache are using " \
                        "the same UIDs!" % str(int(mappedUID)))
                    raise
                r.LocalUserId( info[0] )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            self._log.info("Failed to map UID %s to VO." % mappedUID)
        return r


    def sendBillingInfoRecordsToGratia(self):
        self._log.debug( "sendBillingInfoRecordsToGratia" )

        # Query no more than a set number of days in the past
        minTime = datetime.datetime.now() - datetime.timedelta(self._maxAge, 0)
        minTime = datetime.datetime(minTime.year, minTime.month, minTime.day,
            minTime.hour, 0, 0)

        # The latest allowed record is 75 minutes in the past, in order to make
        # sure we only query complete intervals
        latestAllowed = datetime.datetime.now() - datetime.timedelta(0, 75*60)

        starttime = max(self._BIcheckpoint.lastDateStamp(), minTime)
        self._log.info("Starting queries at time %s." % starttime)

        dictRecordAgg = TimeBinRange.DictRecordAggregator(DCACHE_AGG_FIELDS,
            DCACHE_SUM_FIELDS)

        nextSummary = self._determineNextEndtime(starttime, summary=True)
        if self._summarize:
            self._log.debug("Next summary send time: %s." % nextSummary)

        results = []
        endtime = self._determineNextEndtime(starttime)
        totalRecords = 0
        # Loop until we have caught up to latestAllowed.
        while starttime < latestAllowed:
            assert starttime < endtime
            self._log.debug('sendBillingInfoRecordsToGratia: Processing ' \
                'starting at %s.' % starttime)
            # We are guaranteed that starttime will move forward to the value of
            # endtime every time we call execute.
            next_starttime, rows = self._execute(starttime, endtime,
                self._maxSelect)
            results += rows
            totalRecords += len(rows)
            if self._summarize:
                # Summarize the partial results
                results = Collapse.collapse(results, dictRecordAgg)
            assert next_starttime > starttime
            next_endtime = self._determineNextEndtime(next_starttime)

            # If we're not summarizing, we send up records each loop.
            if not self._summarize and results:
                totalRecords = 0
                # We now have all the rows we want; process them
                self._BIcheckpoint.createPending(endtime, '')
                self._processResults(results)
                self._BIcheckpoint.commit()
                if (self._range < STARTING_RANGE and len(results)*4 < self._maxSelect):
                   self._range = STARTING_RANGE
                results = []
            # If we are summarizing, send records only per hour of data
            elif (next_endtime > nextSummary) and results:
                num_agg = totalRecords - len(results)
                if num_agg:
                    self._log.info("Aggregated %i of %i records for time " \
                        "interval ending in %s" % (num_agg, totalRecords,
                        nextSummary))
                else:
                    self._log.debug("Unable to aggregate any of %i records" \
                        % totalRecords)
                totalRecords = 0
                self._BIcheckpoint.createPending(nextSummary, '')
                self._processResults(results)
                self._BIcheckpoint.commit()
                nextSummary = self._determineNextEndtime(next_starttime,
                    summary=True)
                results = []
                self._range = STARTING_RANGE

            endtime = next_endtime
            starttime = next_starttime

            # Check to see if the stop file has been created.  If so, break
            if os.path.exists(self._stopFileName):
                break


    def _determineNextEndtime(self, starttime, summary=False):
        """
        Given a starttime, determine the next full minute.
        Examples:
           - 01:06:00 -> 01:07:00
           - 01:00:40 -> 01:01:00
           - 01:59:59 -> 02:00:00

        If summary=True, determine the next full hour instead.
        """
        assert isinstance(starttime, datetime.datetime)
        if summary:
            endtime = datetime.datetime(starttime.year, starttime.month,
                starttime.day, starttime.hour, 0, 0)
            endtime += datetime.timedelta(0, 3600)
        else:
            endtime = datetime.datetime(starttime.year, starttime.month,
                starttime.day, starttime.hour, starttime.minute, 0)
            endtime += datetime.timedelta(0, self._range)
        # Watch out for DST issues
        if endtime == starttime:
            endtime += datetime.timedelta(0, 7200)
        return endtime

# end class dCacheRecordAggregator

