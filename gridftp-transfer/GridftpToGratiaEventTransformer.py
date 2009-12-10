
import time
import Gratia
import Logger
import math

class GridftpToGratiaEventTransformer:

   def __init__(self):
       self._log = Logger.getLogger( 'GridftpToGratiaEventTransformer' )

   def resolveNs(self,addr):
        try:

           import socket
           return socket.gethostbyaddr(addr)[0]

        except:
          self._log.warn("Could not resolve:"+addr)
          return addr

   def transform(self,ftpEvent): # returns gratia event

        if ( ftpEvent['type'] == "STOR" ):
           srcHost = ftpEvent['dest']
           dstHost = ftpEvent['host']
           isNew   = 1
        else:
         if ( ftpEvent['type'] == "RETR" ):
           srcHost = ftpEvent['host']
           dstHost = ftpEvent['dest']
           isNew   = 0
         else:
           return None

        srcHost = self.resolveNs(srcHost)
        dstHost = self.resolveNs(dstHost)

        initiatorHost = ftpEvent['host']
        initiatorHost = self.resolveNs(initiatorHost)
          
        protocol = "gsiftp"
        grid = "OSG"

        startTime = time.strftime( '%Y-%m-%dT%H:%M:%S', time.gmtime(float(ftpEvent['ts'])) )

        transfersize = ftpEvent['nbytes']
        connectionTimeStr = 'PT' + str(int(math.ceil(float(ftpEvent['dur'])))) + 'S'

        if ( ftpEvent.has_key('dn') ):
           dn = ftpEvent['dn']
        else:
           dn = None

        errorcode = str(ftpEvent['code'])
        if ( errorcode[0] == '2' ):
            errorcode = "0"
 
        localUserName = ftpEvent['user']


        r = Gratia.UsageRecord( 'Storage' )
        r.AdditionalInfo( 'Source', srcHost )
        r.AdditionalInfo( 'Destination', dstHost )
        r.AdditionalInfo( 'Protocol', protocol )
        r.AdditionalInfo( 'IsNew', isNew )
        r.Grid( grid )
        r.StartTime( startTime )
        r.Network( transfersize, 'b',
                   connectionTimeStr, 'total',
                   "transfer" )
        r.WallDuration( connectionTimeStr )

        # only send the initiator if it is known.
        if dn != None:
            r.DN( dn )
        # if the initiator host is "unknown", make it "Unknown".
        r.SubmitHost( initiatorHost )
        r.Status( errorcode )
        # If we included the mapped uid as the local user id, then
        # Gratia will make a best effort to map this to the VO name.

        r.LocalUserId( localUserName )
        r.LocalJobId( ftpEvent['guid'] )

        return r

if __name__ == "__main__":

  ftpRecord = {'dn': '/DC=org/DC=doegrids/OU=People/CN=Tanya Levshina 508821', 'code': 226, 'dest': '131.225.107.156', 'buffer': 0, 'stripes': 1, 'ts': 1222726365.93099, 'volume': '/', 'prog': 'globus-gridftp-server', 'host': 'osg-ress-2.fnal.gov', 'streams': 1, 'user': 'fnalgrid', 'file': '/storage/local/data1/test/test11', 'end': '2008-09-29T22:12:45.231080Z', 'dur': -0.69990992546081543, 'guid': '5357e1dc-566a-176f-0d16-8cad6f1ca070', 'type': 'STOR', 'event': 'FTP_INFO', 'block': 262144, 'nbytes': 23}

  Gratia.Initialize()

  print GriftpToGratiaEventTransformer().transform(ftpRecord)
    

