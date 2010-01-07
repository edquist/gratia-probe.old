# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
# Version: $Id: DCacheAggregator.py,v 1.29 2009/10/21 20:24:46 greenc Exp $
#
# This is a first attempt at a python program that reads the dCache billing
# database, aggregates any new content, and posts it to Gratia.

import os.path
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

#import pkg_resources
#pkg_resources.require( 'sqlalchemy >= 0.3.8' )
#pkg_resources.require( 'psycopg2   >= 2.0.5.1' )

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
    # Don't select more than 1000 records at a time.
    _maxSelect = 1000
    
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
        billinginfoChkpt = 'chkpt_dcache_xfer_DoNotDelete'
        if chkptdir != None:
            billinginfoChkpt = os.path.join( chkptdir, billinginfoChkpt )
        self._BIcheckpoint = Checkpoint( billinginfoChkpt )

        self._sendAlarm = Alarm(
                configuration.get_EmailServerHost(),
                configuration.get_EmailFromAddress(),
                configuration.get_EmailToList(),
                'dCacheTransfer probe aggregator alarm',
                'The dCache Transfer Probe was not able to send to Gratia.',
                2,    # If more than two errors have occurred
                1800, # Max of once per half hour complaining
                True )

        self._maxAge = configuration.get_MaxBillingHistoryDays()

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
        start = checkpt.lastDateStamp()
        now = datetime.datetime.now()
        
        while(numDone == 0 and start<now) :

            datestr = str( start )
            start = start + datetime.timedelta(hours=12) # For next iteration
            datestr_end = str( start )
         
            # Run the sql query with last checkpointed date stamp
            self._log.debug( '_sendToGratia: will execute ' + selectCMD % (datestr,datestr_end) )
            result = self._connection.execute( selectCMD % (datestr,datestr_end) )
            self._log.debug( '_sendToGratia: returned from sql' )
            for row in result:
                try:
                    newDate = row['datestamp']
                    newTxn = row['transaction']

                    # We checkpoint everything, just in case...
                    checkpt.createPending( newDate, newTxn )
                    # Skip intra-site transfers if required, or if this is the same
                    # record as the last checkpoint.
                    if self._skipIntraSiteXfer(row) or txn == newTxn :
                        # We have to count this because of the way the return value
                        # will be used.
                        checkpt.commit()
                        numDone = numDone + 1
                        continue

                    usageRecord = makeRecord( row )

                    # Send to gratia, and see what it says.
                    response = Gratia.Send( usageRecord )
                    baseMsg = tableName + ' record: ' + \
                              str( newDate ) + ', ' + newTxn
                    if response ==  "Fatal Error: too many pending files":
                        # The server is currently not accepting record and
                        # Gratia.py was not able to store the record, we will
                        # need to resend it.
                        # For now take a long nap and then by 'break' we
                        # force a retry for this record.
                        self._log.error( 'Error sending : too many pending files' )
                        longsleep = 15*60
                        self._log.warn( "sleeping for = "  + str( longsleep ) + " seconds" )
                        time.sleep( longsleep )
                        break
                    elif response.startswith( 'Fatal Error' ) or \
                       response.startswith( 'Internal Error' ):
                        self._log.critical( 'error sending ' + baseMsg + \
                                            '\ngot response ' + response )
                        sys.exit( 2 )
                    self._log.debug( 'sent ' + baseMsg )
                    checkpt.commit()
                    # If we got a non-fatal error, slow down since the server
                    # might be overloaded.
                    if response[0:2] != 'OK':
                        self._log.error( 'error sending ' + baseMsg + \
                                        '\ngot response ' + response )
                    numDone = numDone + 1
                    # Check to see if the stop file has been created.
                    if os.path.exists( self._stopFileName ):
                        break
                except:
                    self._log.warning("Unable to make a record out of the following SQL row: %s." % str(row))
                    numDone += 1 # Increment numDone, otherwise we will exit early.
                    continue
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
        initiatorHost = row['initiatorHost']
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


    def sendBillingInfoRecordsToGratia( self ):
        # _sendToGratia will embed the latest datestamp and transaction value
        # from the checkpoint where %s is embedded in the command.
        self._log.debug( "sendBillingInfoRecordsToGratia" )
        selectCMD = """
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
 (SELECT *
 FROM billinginfo b
 WHERE '%%s' <= b.datestamp AND b.datestamp <= '%%s'
 AND b.datestamp >= '%s'
 ORDER BY datestamp
 LIMIT %i
 ) as b
LEFT JOIN doorinfo d ON b.initiator = d.transaction;
        """ \
            % (datetime.datetime.now()- datetime.timedelta(self._maxAge, 0),
               self._maxSelect)

        while self._sendToGratia(
               'billinginfo', self._BIcheckpoint, selectCMD,
               self._convertBillingInfoToGratiaUsageRecord ) == self._maxSelect:
            self._log.debug( 'sendBillingInfoRecordsToGratia: looping' )

# end class dCacheRecordAggregator

