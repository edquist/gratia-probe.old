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

from Checkpoint import Checkpoint
from Alarm import Alarm

import TimeBinRange
import Collapse

DCACHE_AGG_FIELDS = ['initiator', 'client', 'protocol', 'errorcode', 'isnew']
DCACHE_SUM_FIELDS = ['njobs','transfersize','connectiontime']

# If the DB query takes more than this amount of time, something is very wrong!
MAX_QUERY_TIME_SECS = 180

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
            WHERE '%%s' <= b.datestamp AND b.datestamp <= '%%s'
            AND b.datestamp >= '%s'
            ORDER BY datestamp
            LIMIT %i
        ) as b
    LEFT JOIN doorinfo d ON b.initiator = d.transaction;
"""

import warnings
warnings.simplefilter( 'ignore', FutureWarning )

class DCacheAggregator:
    """
    This class reads the dCache billing database on the specified host
    and pulls out the next set of data to be sent to gratia. It remembers
    what it has already sent by looking at the last successful checkpoint.
    Note that we limit the select to _maxSelect items to moderate memory
    usage when a lot of records have arrived since the probe was last run.
    """

    _connection = None
    # Don't select more than 10000 records at a time.
    # If you change this value, duplicate record detection will break for
    # summarized records.
    _maxSelect = 10000
    
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

        try:
          self._summarize = configuration.get_Summarize();
        except:
          self._summarize = False

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


    def _isIntraSiteTransfer( self, row ) :
        """
        This static method encapsulates the mysterious definition of an
        intra-site transfer. Once we know what that definition should be,
        it should be defined here...
        Returns true if this record appears to be for an intra-site transfer
        and false if it appears to be for an inter-site transfer.
        """
        return str(row['protocol']).startswith( 'DCap' )


    def _skipIntraSiteXfer( self, row ) :
        """
        Boolean method that returns true if the specified row is for an
        intra-site transfer and we the configuration file said to skip
        such records.
        """
        return self._skipIntraSite and self._isIntraSiteTransfer( row )


    def _sendToGratia( self, tableName, checkpt, selectCMD, makeRecord ):
        # Pull up the _maxSelect records that are newer than the last checkpoint
        txn = checkpt.lastTransaction()

        # For each record we found, try to send it to Gratia.
        numDone = 0
        initDate = checkpt.lastDateStamp()
        start = initDate
        now = datetime.datetime.now() - datetime.timedelta(1, 75*60)
        dictRecordAgg = TimeBinRange.DictRecordAggregator(DCACHE_AGG_FIELDS,
            DCACHE_SUM_FIELDS)

        # Iterate by one hour time intervals.  Stop when there are either
        # _maxSelect records (we will increase maxSelect next round) or we
        # have completely caught up.
        while (numDone < self._maxSelect) and (start < now):

            # Regardless of where the start happens within the hour, try to
            # make the end align with the beginning of the next hour.
            datestr = str(start)
            start = start + datetime.timedelta(hours=1)
            start = datetime.datetime(start.year, start.month, start.hour, 0, 0)
            datestr_end = str(start)
            # start is already aligned with the hour.
            if datestr == datestr_end:
                start += datetime.timedelta(0, 3600)
                datestr_end = str(start)
         
            # Run the sql query with last checkpointed date stamp
            self._log.debug('_sendToGratia: will execute ' + selectCMD % \
                (datestr, datestr_end))
            select_time = -time.time()
            result = self._connection.execute(selectCMD % (datestr,
                datestr_end)).fetchall()
            select_time += time.time()
            if select_time > MAX_QUERY_TIME_SECS:
                raise Exception("Postgres query took %i seconds, more than " \
                    "the maximum allowable of %i; this is a sign the DB is " \
                    "not properly optimized!" % (int(select_time),
                    MAX_QUERY_TIME_SECS))
            self._log.debug('_sendToGratia: returned from sql')
            if not result:
                self._log.debug("No results from %s to %s." % (datestr,
                    datestr_end))
                continue
            # 'DN','VO','Probe/Source','Destination' (i.e. RemoteSite), 
            # 'Protocol','Status','Grid','IsNew' 
            # add njobs field , set it to 1
            if self._summarize:
                self._log.debug("Summarizing records.  Started with %i " \
                    "records." % len(result))
                result = Collapse.collapse(result, dictRecordAgg)

            self._log.info("dCache BillingDB query returned %i results." % \
                len(result))

            for row in result:
                try:
                    newDate = row['datestamp']
                    newTxn = row['transaction']

                    try:
                        njobs = row['njobs']
                    except:
                        njobs = 1

                    # We checkpoint everything, just in case...
                    checkpt.createPending(newDate, newTxn)
                    # Skip intra-site transfers if required, or if this is the
                    # same record as the last checkpoint.
                    if self._skipIntraSiteXfer(row) or (txn == newTxn):
                        # We have to count this because of the way the return
                        # value will be used.
                        checkpt.commit()
                        numDone += njobs
                        continue

                    usageRecord = makeRecord(row)

                    # Send to gratia, and see what it says.
                    response = Gratia.Send(usageRecord)
                    baseMsg = tableName + ' record: ' + \
                              str( newDate ) + ', ' + newTxn + ", njobs " + \
                              str(njobs)
                    if response ==  "Fatal Error: too many pending files":
                        # The server is currently not accepting record and
                        # Gratia.py was not able to store the record, we will
                        # need to resend it.
                        # For now take a long nap and then by 'break' we
                        # force a retry for this record.
                        self._log.error('Error sending : too many pending ' \
                            'files')
                        longsleep = 15*60
                        self._log.warn("sleeping for = "  + str( longsleep ) + \
                            " seconds")
                        time.sleep(longsleep)
                        break
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
                    numDone += njobs
                    # Check to see if the stop file has been created.
                    if os.path.exists( self._stopFileName ):
                        break
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception, e:
                    self._log.warning("Unable to make a record out of the " \
                        "following SQL row: %s." % str(row))
                    self._log.exception(e)
                    # Increment numDone, otherwise we will exit early.
                    numDone += njobs
                    continue

        # We only commit the checkpoint if the entire interval is done;
        # otherwise, we don't know where to start up from.
        checkpt.commit()
        self._log.debug( '_sendToGratia: numDone = %d' % numDone )
        return numDone


    def _convertBillingInfoToGratiaUsageRecord( self, row ):
        # Convert date to utc. This can't be done perfectly, alas, since we
        # don't have the original timezone. We assume localtime.
        # This code is horrible, but it should work. row['datestamp'] should
        # be a datetime.datetime object.
        # make the time into a float
        fltTime = time.mktime( row['datestamp'].timetuple() )
        startTime = time.strftime( '%Y-%m-%dT%H:%M:%S', time.gmtime(fltTime) )
        # NOTE WELL: we need the time accurate to milliseconds. So we
        # add it back to the UTC time.
        startTime = startTime + "." + \
                    locale.format( "%06d", row['datestamp'].microsecond ) + \
                    "Z"

        # convert the connection time in milliseconds to a decimal in seconds
        connectTime = float( row['connectiontime'] ) / 1000.0
        connectionTimeStr = 'PT' + str(connectTime) + 'S'

        # Check for the link to the doorinfo table being bad and log a
        # warning in the hope that somebody notices a bug has crept in.
        if row['doorlink'] == '<undefined>' and \
                   not row['protocol'].startswith( 'DCap' ):
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

        r = Gratia.UsageRecord( 'Storage' )
        njobs = 1
        try:
            njobs = row['njobs']
        except:
            pass
        r.Njobs(njobs)
        r.AdditionalInfo( 'Source', srcHost )
        r.AdditionalInfo( 'Destination', dstHost )
        r.AdditionalInfo( 'Protocol', row['protocol'] )
        r.AdditionalInfo( 'IsNew', isNew )
        r.LocalJobId( row['transaction'] )
        if self._isIntraSiteTransfer( row ):
            r.Grid( "Local" )
        else:
            r.Grid( "OSG" )
        r.StartTime( startTime )
        r.Network( row['transfersize'], 'b',
                   connectionTimeStr, 'total',
                   row['action'] )
        r.WallDuration( connectionTimeStr )

        # only send the initiator if it is known.
        if row['initiator'] != 'unknown':
            r.DN( row['initiator'] )
        # if the initiator host is "unknown", make it "Unknown".
        initiatorHost = row['initiatorhost']
        if initiatorHost == 'unknown':
            initiatorHost = 'Unknown'
        r.SubmitHost( initiatorHost )
        r.Status( row['errorcode'] )
        # If we included the mapped uid as the local user id, then
        # Gratia will make a best effort to map this to the VO name.
        mappedUID = row['mappeduid']
        try:
            if mappedUID != None and int( mappedUID ) > 0:
                try:
                    info = pwd.getpwuid(int(mappedUID))
                except:
                    self._log.warn("UID %s not found locally; make sure " \
                        "/etc/passwd on this host and your dCache are using " \
                        "the same UIDs!" % str(int(mappedUID)))
                    raise
                r.LocalUserId( info[0] )
        except Exception, e:
            self._log.info("Failed to map UID %s to VO." % mappedUID)
        return r


    def sendBillingInfoRecordsToGratia(self):
        # _sendToGratia will embed the latest datestamp and transaction value
        # from the checkpoint where %s is embedded in the command.
        self._log.debug( "sendBillingInfoRecordsToGratia" )

        numDone = self._maxSelect
        minTime = datetime.datetime.now() - datetime.timedelta(self._maxAge, 0)
        minTime = datetime.datetime(minTime.year, minTime.month, minTime.day,
            minTime.hour, 0, 0)
        selectCMD = BILLINGDB_SELECT_CMD % (minTime, self._maxSelect)

        while numDone == self._maxSelect:
            numDone = self._sendToGratia('billinginfo', self._BIcheckpoint,
                selectCMD, self._convertBillingInfoToGratiaUsageRecord)
            self._log.debug('sendBillingInfoRecordsToGratia: looping')

# end class dCacheRecordAggregator

