
import gratia.common.Gratia as Gratia
import Logger

class PermanentFailure(Exception):
      pass

class TransientFailure(Exception):
      pass

class GratiaConnector:
    

      def __init__(self,service,reporter):
          Gratia.RegisterReporter( reporter[0],reporter[1] )
          Gratia.RegisterService( service[0], service[1] )
          Gratia.RegisterReporterLibrary("GratiaConnector.py",
                                         Gratia.ExtractCvsRevision("$Revision: 1.3 $"))

          # Report info before sending in handshake

          self._log = Logger.getLogger( 'GratiaConnector' )


      def send(self,usageRecord):
          if ( usageRecord == None ):
             return
          # Send to gratia, and see what it says.
          response = Gratia.Send( usageRecord )
          if response.startswith( 'Fatal Error' ) or \
               response.startswith( 'Internal Error' ):
                self._log.critical( '\ngot response ' + response )
                raise PermanentFailure()

          # If we got a non-fatal error, slow down since the server
          # might be overloaded.
          if response[0:2] != 'OK':
                self._log.error( 'got response ' + response )
                raise TransientFailure()

