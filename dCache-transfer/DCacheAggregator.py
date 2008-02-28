# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
# Version: $Id: DCacheAggregator.py,v 1.3 2008-02-28 22:31:51 greenc Exp $
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
import time
import pwd

from datetime import timedelta
from Checkpoint import Checkpoint
from Alarm import Alarm

#import pkg_resources
#pkg_resources.require( 'sqlalchemy >= 0.3.8' )
#pkg_resources.require( 'psycopg2   >= 2.0.5.1' )


class DCacheAggregator:
    """
    This class reads the dCache billing database on the specified host
    and pulls out the next set of data to be sent to gratia. It remembers
    what it has already sent by looking at the last successful checkpoint.
    Note that we limit the select to _maxSelect items to moderate memory
    usage when a lot of records have arrived since the probe was last run.
    """

    _connection = None
    # Don't select more than 500 records at a time.
    _maxSelect = 1000

    def __init__( self, configuration, logdir=None ):
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
        if logdir != None:
	    billinginfoChkpt = os.path.join( logdir, billinginfoChkpt )
	self._BIcheckpoint = Checkpoint( billinginfoChkpt )
	# Create the storageinfo database checkpoint.
	storageInfoChkpt = 'chkpt_storageinfo'
        if logdir != None:
	    storageInfoChkpt = os.path.join( logdir, storageInfoChkpt )

	self._sendAlarm = Alarm(
		configuration.get_EmailServerHost(),
		configuration.get_EmailFromAddress(),
		configuration.get_EmailToList(),
		'dCacheTransfer probe aggregator alarm',
		'The dCache Transfer Probe was not able to send to Gratia.',
		2,    # If more than two errors have occurred
		1800, # Max of once per half hour complaining
		True )

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
        return row['protocol'].startswith( 'DCap' )


    def _skipIntraSiteXfer( self, row ) :
        """
        Boolean method that returns true if the specified row is for an
        intra-site transfer and we the configuration file said to skip
        such records.
        """
        return self._skipIntraSite and self._isIntraSiteTransfer( row )


    def _sendToGratia( self, tableName, checkpt, selectCMD, makeRecord ):
        # Pull up the _maxSelect records that are newer than the last checkpoint
        datestr = str( checkpt.lastDateStamp() )
        txn = checkpt.lastTransaction()

        # Run the sql query with datestr and txn suitably embedded...
        result = self._connection.execute( selectCMD % ( datestr, datestr, txn ) )
        # For each record we found, try to send it to Gratia.
	numDone = 0
        for row in result:
            newDate = row['datestamp']
            newTxn = row['transaction']

	    # Skip intra-site transfers if required, and skip txns already sent
	    if self._skipIntraSiteXfer(row) or newTxn <= txn :
		# We have to count it here because of the way the return value
		# will be used. (This is an hysterical raisin and will go away)
		numDone = numDone + 1
		continue

            usageRecord = makeRecord( row )
            checkpt.createPending( newDate, newTxn )

	    # Send to gratia, and see what it says.
	    response = Gratia.Send( usageRecord )
	    baseMsg = tableName + ' record: ' + \
		      str( newDate ) + ', ' + newTxn
	    if response.startswith( 'Fatal Error' ) or \
	       response.startswith( 'Internal Error' ):
		self._log.critical( 'error sending ' + baseMsg + \
				    '\ngot response ' + response )
		sys.exit( 2 )
	    self._log.debug( 'sent ' + baseMsg )
	    checkpt.commit()
	    # If we got a non-fatal error, slow down since the server
	    # might be overloaded.
	    if response != 'OK':
		self._log.error( 'error sending ' + baseMsg + \
				'\ngot response ' + response )
		time.sleep( 15 )
            numDone = numDone + 1
	    # Check to see if the stop file has been created.
	    if os.path.exists( self._stopFileName ):
	        break
	self._log.debug( '_sendToGratia: numDone = %d' % numDone )
	return numDone


    def _convertBillingInfoToGratiaUsageRecord( self, row ):
	# Convert date to utc. This can't be done perfectly, alas, since we
	# don't have the original timezone. but we can get it mostly right
	# by assuming localtime.
	# It might be off by an hour around daylight saving time changes...
	utcTime = row['datestamp'] + timedelta( seconds = time.timezone )
	startTime = utcTime.strftime( '%Y-%m-%dT%H:%M:%SZ' )
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
	thisHost = row['cellname'] + '@' + self._dCacheSvrHost
	if row['isnew']:
	    srcHost = row['client']
	    dstHost = thisHost
	else:
	    srcHost = thisHost
	    dstHost = row['client']

	r = Gratia.UsageRecord( 'Storage' )
	r.AdditionalInfo( 'Source', srcHost )
	r.AdditionalInfo( 'Destination', dstHost )
	r.AdditionalInfo( 'Protocol', row['protocol'] )
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
	    r.UserKeyInfo( row['initiator'] )
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
	selectCMD = "SELECT b.datestamp AS datestamp" + \
		    ", b.transaction AS transaction" + \
		    ", b.cellname AS cellname" + \
       		    ", b.action AS action" + \
       		    ", b.transfersize AS transfersize" + \
       		    ", b.connectiontime AS connectiontime" + \
       		    ", b.isnew AS isnew" + \
       		    ", b.client AS client" + \
       		    ", b.errorcode AS errorcode" + \
		    ", b.protocol AS protocol" + \
		    ", b.initiator AS doorlink" + \
       		    ", COALESCE(d.owner, 'unknown') AS initiator" + \
       		    ", COALESCE(d.client, 'Unknown') AS initiatorHost" + \
		    ", d.mappeduid as mappeduid" + \
		    " FROM billinginfo b" + \
		    " LEFT JOIN doorinfo d ON b.initiator = d.transaction" + \
		    " WHERE b.datestamp > '%s' OR" + \
      		    " ( b.datestamp = '%s' AND" + " b.transaction > '%s' )" + \
		    " ORDER BY datestamp" + \
                    " LIMIT " + str( self._maxSelect )

	while self._sendToGratia(
               'billinginfo', self._BIcheckpoint, selectCMD,
               self._convertBillingInfoToGratiaUsageRecord ) == self._maxSelect:
            self._log.debug( 'sendBillingInfoRecordsToGratia: looping' )

# end class dCacheRecordAggregator

