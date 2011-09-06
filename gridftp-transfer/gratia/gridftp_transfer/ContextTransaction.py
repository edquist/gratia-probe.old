# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author: Andrii Baranovski 
# Version: $Id: ContextTransaction.py,v 1.1 2008/11/18 17:20:20 abaranov Exp $
#
# This stores a checkpoint to a file to remember which record was last sent
# to the Gratia repository. This allows us to begin searching from this
# checkpoint after a restart of the probe.

import os
import Logger
import stat
import cPickle
from datetime import datetime


class ContextTransaction:
    """
    This attempts to record a checkpoint to remember the last record read
    from a database table.
    This code is not thread safe. It is only suitable for the dCache
    aggregation system.
    """
    _context = None
    _pending_context = None
    _pending = False

    def __init__( self, tablename ):
        """
        Tablename is the name of the table in db for which we are keeping
        a checkpoint. It is used to locate the file with the pickled record
        of the last checkpoint.
        """
        self._tablename = tablename
        self._tmpFile = tablename + ".pending"
        try:
            pklFile = open( tablename, 'rb' )
            self._context  = cPickle.load( pklFile )
            pklFile.close()
        except IOError, (errno, strerror):
            # This is not really an error, since it might be the first
            # time we try to make this checkpoint.
            # We log a warning, just in case some nice person has
            # deleted the checkpoint file.
            log = Logger.getLogger( 'GridftpGratiaFeed' )
            msg = "Checkpoint: couldn't read %s: %s." % \
                  ( tablename, strerror )
            msg += "\nThis is okay the first time you run the probe."
            log.warn( msg )


    def createPending( self, context ):
        """
        Saves the specified primary key string as the new checkpoint.
        """
        if context == None:
            raise IOError( "ContextTransaction.createPending was passed null values" )

        # Get rid of extant pending file, if any.
        try:
            os.chmod( self._tmpFile, stat.S_IWRITE )
            os.unlink( self._tmpFile )
        except:
            pass # no problem if it isn't there.
        # Create new pending file.
        try:
            pklFile = open( self._tmpFile, 'wb' )
            cPickle.dump( context, pklFile, -1 )
            pklFile.close()
            self._pending = True
            self._pending_context = context
        except IOError, (errno, strerror):
            log = Logger.getLogger( 'GridftpGratiaFeed' )
            log.warn("Checkpoint.save: IOError creating file %s: %s" % \
                  ( self._tmpFile, strerror ))
            raise


    def commit ( self ):
        """
        We created the tmp file. Now make it the actual file with an atomic
        rename.
        We make the file read-only, in the hope it will reduce the risk
        of accidental/stupid deletion by third parties.
        """
        if not self._pending:
            raise IOError( "Checkpoint.commit called with no transaction" )

        self._pending = False
        try:
            if os.path.exists( self._tablename ):
                os.chmod( self._tablename, stat.S_IWRITE )
            os.rename( self._tmpFile, self._tablename )
            os.chmod( self._tablename, stat.S_IREAD )
            self._context = self._pending_context
        except OSError, (errno, strerror):
            log = Logger.getLogger( 'GridftpGratiaFeed' )
            log.warn("Checkpoint.save could not rename %s to %s: %s" % \
                  ( self._tmpFile, self._tablename, strerror ))
            raise


    def context( self ):
        return self._context


if __name__ == "__main__":
   
   import time

   tm = time.time()

   context = "This is test:"+str(tm)
   print "Will use "+context

   txn = ContextTransaction("test")

   print "Prev value"+txn.context()

   txn.createPending(context)

   if ( (int(tm) % 2) == 0 ):
        raise "Failure"

   txn.commit()

   txn1 = ContextTransaction("test")     

   print txn1.context()
# end class Checkpoint
