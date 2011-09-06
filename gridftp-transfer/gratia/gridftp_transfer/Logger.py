
import logging
from logging.handlers import RotatingFileHandler


logger = None

def getLogger(name=None):
   global logger
   return logger

def getLogLevel(cfg):
    level = cfg.AggrLogLevel
    if level == "error":
            return logging.ERROR
    elif level == "warn":
            return logging.WARN
    elif level == "info":
            return logging.INFO
    else:
            return logging.DEBUG

def createLogger():
   return logging.getLogger( 'GridFtpAccProbe' )

def configureLogger(l,cfg):
   global logger
   logger = l

   logDir = cfg.LogFolder

   # Make sure that the logging directory is present
   import os
   if not os.path.isdir( logDir ):
            os.mkdir( logDir, 0755 )


   logFileName = os.path.join( logDir, "gridftpTransfer.log" )

   hdlr = RotatingFileHandler( logFileName, 'a', 512000, 10 )
   formatter = logging.Formatter( '%(asctime)s %(levelname)s %(message)s' )
   hdlr.setFormatter( formatter )
   logger.addHandler( hdlr )
   logger.setLevel( getLogLevel(cfg) )

