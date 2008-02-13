#!/usr/bin/env python
#
# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
# Version: $Id: dcacheStorageMeter.py,v 1.2 2008-02-13 22:49:58 greenc Exp $
#
# This program is the dCache storage usage and capacity probe for Gratia.
# It collects data from the Admin server and the SRM postgres database.
#
# Note:
# The dCacheAdminSvr class is adapted from code written by Brian Bockelman.
# All bugs are my responsibility.

import traceback
import sys
import os
import time
import string
import logging
import re
import resource
import pty
from stat import ST_CTIME, S_IWRITE, S_IREAD

import sqlalchemy
import Gratia


def convertLongToKB( valueString ) :
    return ( valueString + 1023 ) / 1024

def convertToKB( valueString ) :
    """
    This function translates file sizes from the units specified to kilobytes.
    The unit specifiers can be in uppercase or lowercase. Acceptable unit
    specifiers are g m k b. If no specifier is provided, bytes is assumed.
    E.g., 10G is translated to 10485760.
          1048576 is assumed to be in bytes and is translated to 1024.
    """
    result = re.split( '(\d+)', string.lower( valueString ), 1 )
    val = long( result[1] )
    if len( result ) == 2 :
	# Convert bytes to kilobytes
	return (val + 1023 )/ 1024
    if len( result ) == 3 :
        result[2] = result[2].strip()
	if result[2] == 'g' : # Convert gigabytes to kilobytes
	    return val * 1024 * 1024
	if result[2] == 'm' : # Convert megabytes to kilobytes
	    return val * 1024
	if result[2] == 'k' : # No conversion needed
	    return val
	if result[2] == 'b' or result[2] == '' :
	    # Convert bytes to kilobytes
	    return ( val + 1023 ) / 1024
    raise Exception( 'unknown size qualifier "' + str( result[2] ) + '"' )


class dCacheProbeConfig( Gratia.ProbeConfiguration ) :
    """
    This class extends the gratia ProbeConfiguration class so that we can
    add our own configuration parameters to the ProbeConfig file.
    The additional variables each have their own get_ function below.
    """
    def __init__( self ) :
        # Call the parent class to read in the file.
	# We add some extra name/value readouts.
	Gratia.ProbeConfiguration.__init__( self )

    def _getAttr( self, name ) :
	return Gratia.ProbeConfiguration._ProbeConfiguration__getConfigAttribute( self, name )

    def get_DCacheServerHost( self ) :
        return self._getAttr( 'DCacheServerHost' )

    # The next 3 get information about the dCache admin server
    def get_AdminSvrLogin( self ) :
        return self._getAttr( 'AdminSvrLogin' )

    def get_AdminSvrPassword( self ) :
        return self._getAttr( 'AdminSvrPassword' )

    def get_AdminSvrPort( self ) :
        return self._getAttr( 'AdminSvrPort' )

    # The next 3 get the access info for the Postgres database
    def get_DBHostName( self ):
        return self._getAttr( 'DBHostName' )

    def get_DBLoginName( self ):
        return self._getAttr( 'DBLoginName' )

    def get_DBPassword( self ):
        return self._getAttr( 'DBPassword' )

    # The logging level for this program is distinct from the logging
    # level for Gratia. We default to DEBUG if we don't recognize the
    # log level as "error", "warn" or "info"
    def get_DcacheLogLevel( self ) :
        level = self.getConfigAttribute( 'DCacheLogLevel' )
        if level == 'error' :
            return logging.ERROR
        elif level == 'warn' :
            return logging.WARN
        elif level == 'info' :
            return logging.INFO
	else :
	    return logging.DEBUG

# end of class dCacheProbeConfig


class CheckPointTime :
    def __init__( self, dirname ) :
        pathname = os.path.join( dirname, 'checkpt_dcacheSt_DoNotDelete' )
	try :
	    if os.path.exists( pathname ) :
		# Read the timestamp of the file into self._lastUpdateTime
		self._lastUpdateTime = os.stat( pathname )[ST_CTIME] * 1000
		# unlink the file
		os.chmod( pathname, S_IWRITE )
		os.unlink( pathname )
	    else :
	        self._lastUpdateTime = 0
	    # create fileagain to update the ctime.
	    newFile = open( pathname, 'w' )
	    newFile.close()
	    os.chmod( pathname, S_IREAD )
	except IOError, (errno, strerror) :
	    log.error( 'Got error accessing ' + pathname + ': ' + strerror )
	    raise

    def last( self ) :
	return self._lastUpdateTime

# end of class CheckPointTime


class dCacheAdminSvr :
    """
    This class manages the ssh connection to the admin server.
    It is particularly inflexible, tailored to work only with the dCache
    admin server. It was originally written by Brian Bockelman but heavily
    modified and stripped down.
    """
    def __init__( self, log, adminHost, port, username, password ) :
	self._log = log
	self.delay = 0.001
	ssh_args = [ '-c', 'blowfish', '-l', username, '-p', port, adminHost ]
	self._log.debug( 'connecting to admin server' )
	self._make_connection( ssh_args, password )
	self.location = None

    def _fork_ssh( self, args ) :
	log.debug( 'forking for ssh ' + str( args ) )
	self.pid, self.child = pty.fork()
	if self.pid == 0 :
	    # In the child...
	    str_args = ''
	    for arg in args :
		str_args += ' ' + str( arg )
	    max_fd = resource.getrlimit( resource.RLIMIT_NOFILE )[0]
	    for i in range( 3, max_fd ) :
		try :
		    os.close( i )
		except OSError :
		    pass
	    try :
		os.execvp( '/usr/bin/ssh', ['ssh'] + args )
	    except Exception, e :
		log.debug( '_fork_ssh: child unable to execute ssh\n' + str( e ) )

    def read( self, max_read ) :
	time.sleep( self.delay )
	return os.read( self.child, max_read )

    def readlines( self, matches=[] ) :
	time.sleep( self.delay )
	read_line = None
	re_matches = [ re.compile( i ) for i in matches ]
	while read_line != '' :
	    read_line = ''
	    read_char = None
	    stop_flag = False
	    while read_char != '' and read_char != '\n' and ( not stop_flag ) :
	        for regexp in re_matches :
	    	    if regexp.search( read_line ) :
		        stop_flag = True
	        read_char = os.read( self.child, 1 )
	        read_line += read_char
	    yield str( read_line )
	return

    def write( self, text ) :
	time.sleep( self.delay )
	assert os.write( self.child, text )  == len( text )

    def _make_connection( self, ssh_args, password ) :
	self._fork_ssh( ssh_args )
	# Make sure the child has a chance to start.
	time.sleep( 1 )

	for line in self.readlines( matches=['password:', '\(yes/no\)\?', '>'] ) :
	    if re.search( 'password:', line ) :
	        break
	    if re.search( '\(yes/no\)\?', line ) :
	        self.write( 'yes\n' )
	    if re.search( '>', line ) :
	        return
	    if re.search( '@@@@@@@', line ) :
	        raise Exception( 'Got an error message from SSH.' )
	self._log.debug( 'Sending password to server.' )
	self.write( password + '\n' )
	for line in self.readlines( matches=['>'] ) :
	    if re.search( '>', line ) :
		return
	raise Exception( 'Reached the end of input and no new prompt!' )

    def logoff( self ) :
	# Terminate the connection to the admin server.
	self.cd( None )
	self.write( 'logoff\n' )

    def cd( self, cell ) :
	# Change directory to the specified cell.
        if self.location == None :
	    location = 'HOME'
	else :
	    location = self.location
	self._log.debug( 'Current directory is ' + location )
	if self.location == str( cell ) :
	    return
	self._log.debug( 'Changing directory to ' + str( cell ) )
	self.write( '..\n' )
	for line in self.readlines( matches=['>'] ) :
	    self._log.debug( '# ' + line.strip() )
	    if re.search( '>', line ) :
	        break
	self.location = None
	if cell != None :
	    cmd = 'cd ' + str( cell ) + '\n'
	    self._log.debug( cmd )
	    self.write( cmd )
	    for line in self.readlines( matches=['\\(%s\\) [\\w]* >' % cell, '\\([\\w]*\\) /*%s >' % cell] ) :
	        if re.search( '>', line ) :
	            break
	    self.location = str( cell )

    def execute( self, cell, command, args=[] ) :
	assert type( args ) == type( [] )
	self.cd( cell )
	arglist = ''
	for arg in args :
	    arg = str( arg )
	    if arg.find( '\n' ) >=0 :
	        raise Exception( 'Newline not allowed in arguments!' )
	    if not re.match( '^[\-_\w]+$[\-_\w]*','-a_rg\n' ) :
	        raise Exception( 'Malformed argument %s' % arg )
	    arglist += ' ' + str( arg )
	dc_command = str( command ) + arglist
	self.write( dc_command + '\n' )
	ret_str = ''
	count = 0
	should_raise_exception = False
	no_cell_exception = False
	r1 = re.compile( 'java.lang.Exception' )
	r2 = re.compile( 'No Route to cell for packet' )
	r3 = re.compile( '\(%s\) [\w]* >' % self.location )
	r4 = re.compile( '\([\w]*\) /*%s >' % cell )
	for line in self.readlines( matches=['\(%s\) [\w]* >' % cell, '\([\w]*\) /*%s >' % cell] ) :
	    count += 1
	    if r1.search( line ) :
	        should_raise_exception = True
	    if r2.search( line ) :
	        no_cell_exception = True
	    if r3.search( line ) or r4.search( line ) :
	        break
	    if count > 1 :
	        ret_str += line.strip() + '\n'
	if no_cell_exception :
	    raise Exception( 'No route to cell %s.' % cell )
	if should_raise_exception :
	    raise Exception( 'Timeout or other exception from cell %s.' % str( self.location ) )
	return ret_str

#end of class dCacheAdminSvr


class Pool :
    """
    This is a container class that parses a pool info object and caches
    the information about a dCache Pool that is required by Gratia,
    until we are ready to send it.
    """
    def __init__( self, poolName, poolInfo ) :

        data = {}
        for line in string.split( poolInfo, '\n' ) :
            y = string.split( line, ':' )
            if len( y ) > 1 :
                data[ y[0].strip() ] = y[1].strip()
        self.poolName = poolName
	# The total is frequently given as [0-9]+G to signify gigabytes
        self.totalSpaceKB = convertToKB( data[ 'Total' ] )
        self.usedSpaceKB = convertToKB( ( data[ 'Used' ].split() )[0] )
        self.freeSpaceKB = convertToKB( ( data[ 'Free' ].split() )[0] )
        self.type = string.lower( data[ 'LargeFileStore' ] )
        self.pnfsRoot = data[ 'Base directory' ]

    def __repr__( self ) :
	# Make a string representation of the pool data.
        return self.poolName + \
               ', totalKB = ' + str( self.totalSpaceKB ) + \
               ', usedKB = ' + str( self.usedSpaceKB ) + \
               ', freeKB = ' + str( self.freeSpaceKB ) + \
               ', type = ' + self.type + \
               ', pnfs root = ' + self.pnfsRoot

# end of class Pool


class SRM_record :
    """
    This is a container for the data we need to make an SRM record.
    """
    def __init__( self, row, usedSpaceInBytes, retention, accessLatency ) :
	self.vogroup = row.vogroup
        self.capacityKB = convertLongToKB( row.capacityInBytes )
	self.usedSpaceKB = convertLongToKB( usedSpaceInBytes )
        self.retentionPolicy = retention
	self.accessLatency = accessLatency
	if row.hsmType == None:
	    self.hsmType = 'None'
	else :
	    self.hsmType = row.hsmType
	self.lastUpdateTime = row.lastUpdateTime

    def __repr__( self ) :
	# Make a string representation of the pool data.
        return self.vogroup + \
	       ', totalKB = ' + str( self.capacityKB ) + \
	       ', usedKB = ' + str( self.usedSpaceKB ) + \
	       ', retention policy = ' + str( self.retentionPolicy ) + \
	       ', access latency = ' + str( self.accessLatency ) + \
	       ', hsm type = ' + str( self.hsmType ) + \
	       ', last updated = ' + str( self.lastUpdateTime )

#end of class SRM_record


class SRM_collector :
    """
    This class encapsulates the connection to the SRM database.
    """
    _selectSpaceCmd = \
    	'SELECT ' + \
	    'srmspace.id AS spaceId,' + \
	    'srmspace.vogroup AS vogroup,' + \
	    'srmspace.retentionpolicy AS retentionPolicy,' + \
	    'srmspace.accesslatency AS accessLatency,' + \
	    'srmspace.sizeinbytes AS capacityInBytes, ' + \
	    'srmlinkgroup.hsmtype AS hsmType, ' + \
	    'srmlinkgroup.lastupdatetime AS lastupdatetime ' + \
	'FROM ' + \
	    'srmspace INNER JOIN srmlinkgroup ' + \
	    'ON srmlinkgroup.id=srmspace.linkgroupid ' + \
	    'AND srmlinkgroup.lastupdatetime >= %d'

    _selectSpaceUsageCmd = \
	'SELECT ' + \
	    'SUM(sizeInBytes) AS usedspace FROM srmspacefile ' + \
	'WHERE ' + \
	    'spaceReservationId = %d AND state != 3'

    def __init__( self, dbHost, dbLogin, dbPasswd, lastUpdateTimer, logger ) :
	self._log = logger
	# Connect to the database
	DBurl = 'postgres://' + dbLogin + ':' + dbPasswd + '@' + \
		 dbHost + ':5432/dcache'

	# We use the creation time of a time-stamp file to track
	# when this function last ran.
	# We can then avoid sending SRM space reservation records that have
	# not been modified during that time.
	self._updateTimer = lastUpdateTimer

	self._accesslatency_dict = {}
	self._retentionpolicy_dict = {}

	# Connect to the dCache postgres database.
	try :
	    self._log.debug( 'Connecting to SRM database: ' + DBurl )
	    self._db = sqlalchemy.create_engine( DBurl )
	    self._connection = self._db.connect()
	    self._log.debug( 'Connected to SRM database' )

	    # We will need the retention policy and access latency types.
	    retpolicy = self._execute( 'SELECT id,name FROM srmretentionpolicy' )
	    for row in retpolicy :
		self._retentionpolicy_dict.update( {row[0]:row[1]} )
	    log.debug( 'loaded retentionpolicy data' )

	    accLatency = self._execute( 'SELECT id,name FROM srmaccesslatency' )
	    for row in accLatency :
		self._accesslatency_dict.update( {row[0]:row[1]} )
	    log.debug( 'loaded access latency data' )

	except :
	    tblist = traceback.format_exception( sys.exc_type,
						 sys.exc_value,
						 sys.exc_traceback)
	    errmsg = 'Failed to connect to ' + DBurl + \
		     '\n\n' + "".join( tblist )
	    self._log.error( errmsg )
	    raise

    def _execute( self, cmd ) :
	self._log.debug( 'Sending cmd to SRM database: "' + cmd + '"' )
        return self._connection.execute( cmd )

    def lookupSRMStorageInfo( self ) :
	try :
	    results = self._execute( self._selectSpaceCmd % self._updateTimer.last())
	except :
	    # If there is no SRM v2.2 implementation or if postgres is down
	    # we proceed as if there were no new records.
	    self._log.error( 'Could not connect to SRM database' )
	    results = None

	if results == None or results.rowcount == 0 :
	    self._log.warn( 'Found no new SRM space records' )

	recordList = []
	for row in results :
	    self._log.debug( 'Processing SRM record for ' + str( row.spaceId ) )
	    spaceUsageCmd = self._selectSpaceUsageCmd % row.spaceId
	    spaceUsedResult = self._execute( spaceUsageCmd )
	    if spaceUsedResult.rowcount != 1 :
	        self._log.warning( 'no space usage result' )
	    else :
		for spacerow in spaceUsedResult :
		    if spacerow.usedspace == None :
		        usedSpace = 0L
		    else :
		    	usedSpace = long( spacerow.usedSpace )
		    record = SRM_record( row, usedSpace,
			      self._retentionpolicy_dict[ row.retentionPolicy ],
			      self._accesslatency_dict[ row.accessLatency ]
			     )
		    assert record.lastUpdateTime >= self._updateTimer.last()
		    recordList.append( record )
	return recordList

    def dispose( self ) :
	self._log.debug( 'Closing connection to SRM database' )
        self._connection.close()
	self._db.dispose()

# end class SRM_collector


def setupLogging( logDir, logLevel ) :
    # Get the name of the directory where we are to store the log files.
    logFileName = os.path.join( logDir, 'dcacheStorage.log' )
    # Make sure that the logging directory is present
    if not os.path.isdir( logDir ) :
	os.mkdir( logDir, 0755 )
    if os.path.exists( logFileName ) :
	backupName = logFileName + time.strftime( '_%Y%m%d_%H%M%S' )
	os.rename( logFileName, backupName )
    # Set up the logger with a suitable format.
    # This is more complex than you'd expect because we have to work with
    # python 2.3
    logger = logging.getLogger( 'DCacheStorage' )
    hdlr = logging.FileHandler( logFileName, 'w' )
    formatter = logging.Formatter( '%(asctime)s %(levelname)s %(message)s' )
    hdlr.setFormatter( formatter )
    logger.addHandler( hdlr )
    logger.setLevel( logLevel )
    logger.info( 'starting logger with log level ' + str( logLevel ) )
    return logger


def lookupPoolStorageInfo( connection, log ) :
    listOfPools = []
    # get a list of pools
    # If this raises an exception, it will be caught in main.
    # It is a fatal error...
    pooldata = connection.execute( 'PoolManager', 'cm ls' )

    # for each pool get the vital statistics about capacity and usage
    defPoolList = pooldata.splitlines()
    for poolStr in defPoolList :
        poolName = poolStr.split( '={', 1 )[0]
	if string.strip( poolName ) == '' :
	    continue # Skip empty lines.
	log.debug( 'found pool:' + str( poolName ) )
	try :
	    poolinfo = connection.execute( poolName, 'info -l' )
	    if poolinfo != None :
		listOfPools.append( Pool( poolName, poolinfo ) )
	    else :
		log.error( 'Error doing info -l on pool ' + str( poolName ) )
        except :
	    tblist = traceback.format_exception( sys.exc_type,
						 sys.exc_value,
					         sys.exc_traceback )
	    log.warning( 'Got exception:\n\n' + "".join( tblist ) + \
			 '\nwhile doing "info -l" for pool ' + \
			 str( poolName ) + '.\nIgnoring this pool.' )

    return listOfPools


def sendGratiaPoolRecord( log,
			  dCacheSiteName,
			  poolName,
			  spaceKB,
			  spaceType,
			  retentionPolicy ) :
    log.debug( 'sendGratiaPoolRecord: ' + dCacheSiteName + \
	       ', ' + poolName + \
               ', ' + str( spaceKB ) + \
	       ', ' + str( spaceType ) + \
	       ', ' + retentionPolicy )
    record = Gratia.UsageRecord( 'Storage' )
    record.MachineName( value = dCacheSiteName )
    record.Disk( spaceKB,
		 storageUnit = 'kb',
		 phaseUnit = 1,
		 metric = 'total',
		 description = spaceType )
    record.Host( value = poolName, description='dCache pool name' )
    record.AdditionalInfo( 'Type ', retentionPolicy )
    record.AdditionalInfo( 'srmType', 'dcache' )
    Gratia.Send( record )


def sendGratiaSRMRecord( log,
			 dCacheSiteName,
			 voname,
		   	 spaceKB,
			 spaceType,
			 retentionPolicy,
			 hsmType ) :
    if voname == None :
	voname = ''

    log.debug( 'sendGratiaSRMRecord: ' + dCacheSiteName + \
	       ', ' + voname + \
               ', ' + str( spaceKB ) + \
	       ', ' + str( spaceType ) + \
	       ', ' + retentionPolicy  + \
	       ', ' + hsmType )

    # spaceType should be one of 'used', 'available', 'total'
    # lifetime should be "permanent" or "volatile"
    record = Gratia.UsageRecord( 'Storage' )
    record.MachineName( value = dCacheSiteName )
    record.Disk( spaceKB,
		 storageUnit = 'kb',
		 phaseUnit = 1,
		 metric = 'total',
		 description = spaceType);
    record.AdditionalInfo( 'Type', retentionPolicy )
    record.VOName( voname )
    record.AdditionalInfo( 'srmType', 'dCache' )
    record.AdditionalInfo( 'hsmType', hsmType )

    # populate record to repository
    Gratia.Send( record )


if __name__ == '__main__' :

    connection = None
    try :
	Gratia.Initialize()
	# Extract the Gratia configuration information into config object.
	config = dCacheProbeConfig()
	log = setupLogging( config.get_LogFolder(),
			    config.get_DcacheLogLevel() )
        log.debug( 'starting dcacheStorageMeter' )

	# Set up the last update time checkpoint file management object.
	lastUpdateTimer = CheckPointTime( config.get_LogFolder() )

	# Create connection object
	password = config.get_AdminSvrPassword()
	connection = dCacheAdminSvr( log,
				     config.get_DCacheServerHost(),
				     config.get_AdminSvrPort(),
				     config.get_AdminSvrLogin(),
				     password )

	poolStorageInfo = lookupPoolStorageInfo( connection, log )
	# Close the connection - we are done.
        connection.logoff()

	# Send the data to gratia, now that we have all the pieces.
	# We sort the pools into alphabetical order because it's fun. :-)
	siteName = config.get_SiteName()
	poolStorageInfo.sort()
	for pool in poolStorageInfo :
	    log.debug( 'Sending pool info: ' + str( pool ) )
	    # Send the capacity of this pool
	    sendGratiaPoolRecord( log,
	    			  siteName,
				  pool.poolName,
				  pool.totalSpaceKB,
				  'total',
				  pool.type )
	    # Now send the used space of this pool
	    sendGratiaPoolRecord( log,
	    			  siteName,
				  pool.poolName,
				  pool.usedSpaceKB,
				  'used',
				  pool.type )

	# Set up the SRM data collector.
	srmDB = SRM_collector( config.get_DBHostName(),
			       config.get_DBLoginName(),
			       config.get_DBPassword(),
			       lastUpdateTimer,
			       log )
	# Now we load the SRM space records and iterate over them,
	# sending them to the Gratia server.
	srmStorageInfo = srmDB.lookupSRMStorageInfo()
	# Release the database connection.
	srmDB.dispose()
	for record in srmStorageInfo :
	    log.debug( 'Sending SRM info: ' + str( record ) )
	    sendGratiaSRMRecord( log,
	    			 siteName,
	    			 record.vogroup,
	    			 record.capacityKB,
				 'total',
				 record.retentionPolicy,
				 record.hsmType )
	    sendGratiaSRMRecord( log,
	    			 siteName,
	    			 record.vogroup,
	    			 record.usedSpaceKB,
				 'used',
				 record.retentionPolicy,
				 record.hsmType )

    except :
	tblist = traceback.format_exception( sys.exc_type,
					     sys.exc_value,
					     sys.exc_traceback )
	log.error( 'Dying of exception:\n\n' + "".join( tblist ) )
        if connection != None :
	    try :
		connection.logoff()
	    except :
	        pass
	sys.exit( 1 )

    log.debug( 'terminating dcacheStorageMeter' )
    sys.exit( 0 )
