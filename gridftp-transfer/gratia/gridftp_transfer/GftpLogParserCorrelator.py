
import netlogger.parsers.modules.gridftp
import netlogger.parsers.modules.gridftp_auth


def findMinOffset(parser, timeMin):

    atLeastOneIteration = 0
    currentOffset = parser.getOffset()
    lastOffset = currentOffset

    for r in parser:
       if ( r != None ):
          if ( r['ts'] < timeMin ):
             atLeastOneIteration = 1
          else:
             lastOffset = parser.getOffset()
             break

    parser.flush()
    parser.setOffset(lastOffset)

    if ( atLeastOneIteration == 1 ):
       return

    currentOffset = int(currentOffset/2)
    if ( currentOffset == 0 ):
       return

    parser.setOffset(currentOffset)
    findMinOffset(parser,timeMin)

    
# algo 
# read N records starting from previous offset of the gridftp.log file
# find the min and max time observed among collected records
# find offset range inside grid-auth file which would corresponds to min - 1h , max + 1h time range, use bin search algo expanding
# from stored offset indicator
# collected all records from grid-auth file corresponding to that range
# remember ( range_min + range_max ) / 2 number

# correlation
# generate bin structure - int(time/15): [ gridftp event, gridftp-auth events ]
# for each bin collapse gridftp-auth events based on local id - correlation phase 1 (implemented for simplicity by
# findAndCreateTimeBin
# for each bin find suitable gridftp event with grid-auth pair - correlation phase 2 ( each bin is compared against content of 2 neighboring bins)
# join two events

class Context:
   def __init__(self):
     self._gftpOffset = 0
     self._authgftpOffset = 0
     self._i = 0
     self._r = 0

   def getGridftpLastOffset(self):
       return self._gftpOffset

   def getAuthgridftpOffset(self):
       return self._authgftpOffset

   def setGridftpLastOffset(self,off):
       self._gftpOffset = off

   def setAuthgridftpOffset(self,off):
       self._authgftpOffset = off

   def getBufferIndex(self):
       return self._i
   
   def setBufferIndex(self,i):
       self._i = i

   def setReadAhead(self,i):
       self._r = i

   def getReadAhead(self):
       return self._r


class GftpLogParserCorrelator:

    def __init__(self,gftpTransferFile,gftpAuthFile):
        self.authParser = netlogger.parsers.modules.gridftp_auth.Parser(gftpAuthFile,True)
        self.transferParser  = netlogger.parsers.modules.gridftp.Parser(gftpTransferFile,True)
        self.buffer = []
        self.i = 0

    
    def binInt(self,number):
        return int(number/15.)
    
    def findAndCreateTimeBin(self,binId,correlationBins,id): # group auth events based on the bin the first event ended up in

        timeBin = None

        for b in [ binId -1 ,  binId+1, binId]:
            if ( correlationBins.has_key(b) ):
                timeBin = correlationBins[b]
                if ( timeBin[1].has_key(id) ):
                    return timeBin[1][id]

        if ( timeBin != None ): # we don't have suitable bin, stick it in the middle
            timeBin[1][id] = []
        else:
            return None # there was no transfer event corresponding to that

        return timeBin[1][id]

    def createCorrelationBins(self,maxCount):

        correlationBins = {}

        count = 0
        timeMin = 0x7fffffff
        timeMax = 0

        l = None
        for l in self.transferParser:
            if ( l != None ):
            
                count += 1

                binId = self.binInt(l['ts'])
            
                if ( not correlationBins.has_key(binId ) ):
                    correlationBins[binId] = ( [],{} )

                correlationBins[binId][0].append(l)
            
                if ( timeMin > l['ts'] ):
                    timeMin = l['ts']

                if ( timeMax < l['ts'] ):
                    timeMax = l['ts']

                if count >= maxCount:
                    break

        timeMin -= 1000
        timeMax += 10

        findMinOffset(self.authParser,timeMin)

        for l in self.authParser:
            if ( l != None ):

                if ( l['ts'] > timeMax ):
                    break 
                else:
                    binId = self.binInt(l['ts'])
                    authEventPlaceHolder = self.findAndCreateTimeBin(binId,correlationBins,l['PID'])
                    if ( authEventPlaceHolder != None):
                        authEventPlaceHolder.append(l)

        return correlationBins,count


    def findEvent(self,authEvent,eventName):
        for event in authEvent:
            if (  event['event'] == eventName ):
                return event

        return None

    def matchAuthEvent(self,ts,filePath,host,authEvent):

        event = self.findEvent(authEvent,"gridftp.auth")

        if ( event == None ):
            return None

        if ( abs(ts-int(event['ts'])) > 7 ):
           return None

        if ( not event.has_key('dn') ):
           return None

        dn = event['dn']

        event = self.findEvent(authEvent,"gridftp.auth.transfer.start")
        if ( event == None ):
            return None

        if ( event['file'] != filePath ):
            return None

        return dn

    def findDn(self,ts, filePath,host, authEvents ):

        for ( authEventId , authEvent ) in authEvents.items():
            dn = self.matchAuthEvent(ts,filePath,host,authEvent)
            if ( dn != None ):
                return dn
            
        return None
            

    def generateCorrelationAffinity(self,correlationBins,key,size):

        result = {}
 
        for i in range(-size,size): 
          if ( correlationBins.has_key(key+i) ):
           result.update(correlationBins[key+i][1])

        return result

    def createTransferEvents(self,maxCount):

        correlationBins,count = self.createCorrelationBins(maxCount)

        results = []

        if ( len(correlationBins.items()) == 0 ):
            return results

        for (key,value ) in correlationBins.items():
            affinity = self.generateCorrelationAffinity(correlationBins,key,1)

            for transferEvent in value[0]:
                  dn = self.findDn(int(transferEvent['ts']),transferEvent['file'],transferEvent['dest'], affinity )
                  if ( dn != None ):
                    transferEvent['dn'] = dn
                  results.append(transferEvent)

        return results

    def __iter__(self):
        return self

    def next(self):
        if self.i >= len(self.buffer) :
            self.buffer = self.createTransferEvents(1000)
            self.i = 0

        if ( len(self.buffer) == 0 ):
           raise StopIteration()

        o = self.buffer[self.i]
        self.i += 1
        return o

class GftpLogParserCorrelatorCtx(GftpLogParserCorrelator):
     
    def __init__(self,gftpTransferFile,gftpAuthFile,context):
        GftpLogParserCorrelator.__init__(self,gftpTransferFile,gftpAuthFile)
        self.context = context

    def createCorrelationBins(self,maxCount):

        gridftpLastOffset = self.context.getGridftpLastOffset()


        if ( gridftpLastOffset != 0 ):
           self.transferParser.flush()
           self.transferParser.setOffset(gridftpLastOffset)
           try:
              if ( self.context.getReadAhead() ):
                 self.transferParser.next()
              pass
           except StopIteration,ex:
              return {}

        self.authParser.flush()
        self.authParser.setOffset(self.context.getAuthgridftpOffset())

        correlationBins,count = GftpLogParserCorrelator.createCorrelationBins(self,maxCount)

        if ( count < maxCount ):
            self.context.setReadAhead(0)
        else:
            self.context.setReadAhead(1)
           
        self.context.setGridftpLastOffset(self.transferParser.getOffset())
        self.context.setAuthgridftpOffset(self.authParser.getOffset())

        return correlationBins,count
 
    def next(self):
        self.i = self.context.getBufferIndex()
        o = GftpLogParserCorrelator.next(self)
        self.context.setBufferIndex(self.i)
        return o

if ( __name__ == "__main__" ):
   c = GftpLogParserCorrelator(file("gridftp.log"),file("gridftp-auth.log"))

   for i in c:
     print i
