
import Gratia
import GratiaConnector
import GftpLogParserCorrelator
import FileDigest
import GridftpToGratiaEventTransformer

import Logger
import time
import sys
import os

sys.path.append('.')
gratia_path = os.path.expandvars('/opt/vdt/gratia/probe/common')
if gratia_path not in sys.path and os.path.exists(gratia_path):
    sys.path.append(gratia_path)
if 'VDT_LOCATION' in os.environ:
    gratia_path = os.path.expandvars('$VDT_LOCATION/gratia/probe/common')
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)
    gratia_path = os.path.expandvars('$VDT_LOCATION/gratia/probe/services')
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)


class Config(Gratia.ProbeConfiguration):

      def __init__(self):
          Gratia.ProbeConfiguration.__init__(self)

      def __getattr__(self,name):
          return self.getConfigAttribute(name)

class Context(GftpLogParserCorrelator.Context):
      def __init__(self):
          GftpLogParserCorrelator.Context.__init__(self)
          self._digest = 0
          self._lastUpdateTime = 0

      def getFileDigest(self):
          return self._digest

      def getLastUpdateTime(self):
          return self._lastUpdateTime

      def setLastUpdateTime(self,ut):
          self._lastUpdateTime = ut

      def setFileDigest(self,d):
          self._digest = d

class ProbeDriver:
   
      def __init__(self,cfg,gconnector):
         self.logger = Logger.getLogger('ProbeDriver')

         self.gconnector = gconnector 
         self.gridftplogFilePath = cfg.GridftpLogDir +"/"+"gridftp.log"
         self.gridftpAuthlogFilePath = cfg.GridftpLogDir +"/"+"gridftp-auth.log"

         self.gridftplogFile = file(self.gridftplogFilePath)
         self.gridftpAuthlogFile = file(self.gridftpAuthlogFilePath)
       
         from ContextTransaction import ContextTransaction
         self.txn = ContextTransaction(cfg.WorkingFolder+"/GridftpAccountingProbeState")

         self.context = self.txn.context()

         fdigest =  FileDigest.getFileDigest(self.gridftplogFilePath)
         if ( self.context == None ):
            self.context = Context()

         if ( fdigest != self.context.getFileDigest() ): # new file , reset context
               self.logger.warn("gridftp.log file has been replaced, resetting log context")
               self.context = Context()
               self.context.setFileDigest(fdigest)

         self.updateTimeDiff = time.time() - self.context.getLastUpdateTime()
         self.context.setLastUpdateTime(time.time())

         self.parser = GftpLogParserCorrelator.GftpLogParserCorrelatorCtx(self.gridftplogFile,self.gridftpAuthlogFile,self.context)
         self.eventTransformer = GridftpToGratiaEventTransformer.GridftpToGratiaEventTransformer()

      def close(self):
         self.gridftpAuthlogFile.close()
         self.gridftplogFile.close()

      def loop(self):

          for ftpEvent in self.parser: 
          
              currentRunningTime = time.time() - self.context.getLastUpdateTime()

              if ( currentRunningTime  > 20*60 or currentRunningTime > ( self.updateTimeDiff - 10 ) ):
                  break

              self.txn.createPending(self.context)


              try:
                 gEvent = self.eventTransformer.transform(ftpEvent)
              except Exception,ex:
                 self.logger.error("Could not transform ftpEvent:"+str(ftpEvent)+",ex:"+str(ex))
                 self.txn.commit()
                 continue

              try:
                 self.gconnector.send(gEvent)
              except GratiaConnector.TransientFailure,ex:
                 self.logger.error("Transient failure sending the event:"+str(gEvent)+",ex:"+str(ex))
                 time.sleep(15)
              self.txn.commit() 
              time.sleep(0.1)

if __name__ == "__main__":

   logger = Logger.createLogger()

   cfg = Config()
  
   Logger.configureLogger(logger,cfg)

   workingDir = cfg.WorkingFolder
   import os
   if not os.path.isdir( workingDir ):
            os.mkdir( workingDir , 0755 )

   rev =  Gratia.ExtractCvsRevision("$Revision: 1.2 $")
   tag =  Gratia.ExtractCvsRevision("$Name:  $")

   conn = GratiaConnector.GratiaConnector(("gridftp","2.0"),
                                          ("GridftpTransferProbeDriver.py",
                                           str(rev) + " (tag " + str(tag) + ")"))

   logger = Logger.getLogger("main")
   logger.debug("Starting log file scan cycle")
   probDriver = ProbeDriver(cfg,conn)
   probDriver.loop()
   probDriver.close()
   logger.debug("Log file scan is done")
