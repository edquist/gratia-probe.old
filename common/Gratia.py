import os, sys, time, glob, string, httplib, xml.dom.minidom, socket
import traceback
import re, fileinput

oldexitfunc = getattr(sys, 'exitfunc', None)
def disconnect_at_exit(last_exit = oldexitfunc):
    if Config: RemoveOldLogs(Config.get_LogRotate())
    DebugPrint(1, "End-of-execution disconnect ...")
    __disconnect()
    if last_exit: last_exit()

sys.exitfunc = disconnect_at_exit

class ProbeConfiguration:
    __doc = None
    __configname = "ProbeConfig"
    __MeterName = None
    __SiteName = None
    __DebugLevel = None
    __LogLevel = None
    __LogRotate = None
    __UseSyslog = None
    __UserVOMapFile = None

    def __init__(self, customConfig = "ProbeConfig"):
        if os.path.exists(customConfig):
            self.__configname = customConfig

    def loadConfiguration(self):
        self.__doc = xml.dom.minidom.parse(self.__configname)
        DebugPrint(0, 'Using config file: ' + self.__configname)

    def __getConfigAttribute(self, attributeName):
        if self.__doc == None:
            self.loadConfiguration()

        # TODO:  Check if the ProbeConfiguration node exists
        # TODO:  Check if the requested attribute exists
        return self.__doc.getElementsByTagName('ProbeConfiguration')[0].getAttribute(attributeName)

    def __findVDTTop(self):
        mvt = self.__getConfigAttribute('VDTSetupFile')
        if mvt and os.path.isfile(mvt):
            return os.path.dirname(mvt)
        else:
            mvt = os.getenv('OSG_GRID') or \
                  os.getenv('OSG_LOCATION') or \
                  os.getenv('VDT_LOCATION') or \
                  os.getenv('GRID3_LOCATIION')
        if mvt != None and os.path.isdir(mvt):
            return mvt
        else:
            return None

    def get_SSLHost(self):
        return self.__getConfigAttribute('SSLHost')

    def get_SSLRegistrationHost(self):
        return self.__getConfigAttribute('SSLRegistrationHost')

    def get_SOAPHost(self):
        return self.__getConfigAttribute('SOAPHost')

    def get_CollectorService(self):
        return self.__getConfigAttribute('CollectorService')

    def get_SSLCollectorService(self):
        return self.__getConfigAttribute('SSLCollectorService')

    def get_SSLRegistrationService(self):
        return self.__getConfigAttribute('SSLRegistrationService')

    def get_GratiaCertificateFile(self):
        return self.__getConfigAttribute('GratiaCertificateFile')

    def get_GratiaKeyFile(self):
        return self.__getConfigAttribute('GratiaKeyFile')

    def setMeterName(self,name):
        self.__MeterName = name

    def get_MeterName(self):
        if (self.__MeterName == None):
            return self.__getConfigAttribute('MeterName')
        else:
            return self.__MeterName

    def setSiteName(self,name):
        self.__SiteName = name

    def get_SiteName(self):
        if (self.__SiteName == None):
            val = self.__getConfigAttribute('SiteName')
            if val == None or val == "":
                self.__SiteName =  "generic Site"
            else:
                self.__SiteName = val
        return self.__SiteName

    def get_UseSSL(self):
        val = self.__getConfigAttribute('UseSSL')
        if val == None or val == "":
            return 0
        else:
            return int(val)

    def get_UseSoapProtocol(self):
        val = self.__getConfigAttribute('UseSoapProtocol')
        if val == None or val == "":
            return 0
        else:
            return int(val)

    def get_UseGratiaCertificates(self):
        return int(self.__getConfigAttribute('UseGratiaCertificates'))

    def get_DebugLevel(self):
        if (self.__DebugLevel == None):
            self.__DebugLevel = int(self.__getConfigAttribute('DebugLevel'))
        return self.__DebugLevel

    def get_LogLevel(self):
        if (self.__LogLevel == None):
            val = self.__getConfigAttribute('LogLevel')
            if val == None or val == "":
                self.__logLevel = self.get_DebugLevel()
            else:
                self.__LogLevel = int(val)
        return self.__LogLevel

    def get_LogRotate(self):
        if (self.__LogRotate == None):
            val = self.__getConfigAttribute('LogRotate')
            if val == None or val == "":
                self.__LogRotate = 31
            else:
                self.__LogRotate = int(val)
        return self.__LogRotate

    def get_UseSyslog(self):
        if (self.__UseSyslog == None):
            val = self.__getConfigAttribute('UseSyslog')
            if val == None or val == "":
                self.__UseSyslog = False
            else:
                self.__UseSyslog = int(val)
        return self.__UseSyslog

    def get_GratiaExtension(self):
        return self.__getConfigAttribute('GratiaExtension')

    def get_CertificateFile(self):
        return self.__getConfigAttribute('CertificateFile')

    def get_KeyFile(self):
        return self.__getConfigAttribute('KeyFile') 

    def get_MaxPendingFiles(self):
        return self.__getConfigAttribute('MaxPendingFiles')

    def get_DataFolder(self):
        return self.__getConfigAttribute('DataFolder')

    def get_WorkingFolder(self):
        return self.__getConfigAttribute('WorkingFolder')

    def get_LogFolder(self):
        return self.__getConfigAttribute('LogFolder')

    def get_PSACCTFileRepository(self):
        return self.__getConfigAttribute('PSACCTFileRepository')

    def get_PSACCTBackupFileRepository(self):
        return self.__getConfigAttribute('PSACCTBackupFileRepository')

    def get_PSACCTExceptionsRepository(self):
        return self.__getConfigAttribute('PSACCTExceptionsRepository')

    def get_UserVOMapFile(self):
        if self.__UserVOMapFile:
            return self.__UserVOMapFile
        val = self.__getConfigAttribute('UserVOMapFile')
        if val and re.search(r'MAGIC_VDT_LOCATION', val):
            val = re.sub(r'MAGIC_VDT_LOCATION',
                         self.__findVDTTop(),
                         val)
            if path.os.isfile(val): self.__UserVOMapFile = val
        elif val and os.path.isfile(val):
            self.__UserVOMapFile = val
        else: # Invalid or missing config entry
            # Locate mapfile from osg-attributes.conf
            if val and os.path.isfile(val + '/monitoring/osg-attributes.conf'):
                try:
                    filehandle = open(val + '/monitoring/osg-attributes.conf')
                    mapMatch = \
                             re.search(r'^(?:OSG|GRID3)_USER_VO_MAP="(.*)"\s*(?:#.*)$',
                                       filehandle.read(), re.DOTALL)
                    filehandle.close()
                    if mapMatch: self.__UserVOMapFile = mapMatch.group(1)
                except IOError, e:
                    pass
            else: # Last ditch guess
                vdttop = self.__findVDTTop()
                if vdttop != None: 
                   self.__UserVOMapFile = self.__findVDTTop() + \
                                     '/monitoring/grid3-user-vo-map.txt'
                   if not os.path.isfile(self.__UserVOMapFile): self.__UserVOMapFile = None
        return self.__UserVOMapFile

class Event:
    _xml = ""
    _id = ""

    def __init__(self):
        self._xml = ""
        self._id = ""

    def __init__(self, id, xml):
        self._xml = xml
        self._id = id

    def get_id(self):
        return self._id

    def get_xml(self):
        return self._xml

    def set_id(self, id):
        self._id = id

    def set_xml(self, xml):
        self._xml = xml

class Response:
    _code = -1
    _message = ""

    def __init__(self):
        self._code = -1
        self._message = ""

    def __init__(self, code, message):
        if code == -1:
            if message == "OK":
                self._code = 0
            else:
                self._code = 1
        else:
            self._code = code
        self._message = message

    def get_code(self):
        return self._code

    def get_message(self):
        return self._message

    def set_code(self, code):
        self._code = code

    def set_message(self, message):
        self._message = message

BackupDirList = []
OutstandingRecord = { }
RecordPid = os.getpid()
RecordId = 0
Config = None
MaxConnectionRetries = 2
MaxFilesToReprocess = 100000

# Instantiate a global connection object so it can be reused for
# the lifetime of the server Instantiate a 'connected' flag as
# well, because at times we cannot interrogate a connection
# object to see if it has been connected yet or not
__connection = None
__connected = False
__connectionError = False
__connectionRetries = 0


def Initialize(customConfig = "ProbeConfig"):
    "This function initializes the Gratia metering engine"
    "We connect/register with the collector and load"
    "this meter's configuration"
    "We also load the list of record files that have not"
    "yet been sent"

    global Config
    if len(BackupDirList) == 0:
        # This has to be the first thing done (DebugPrint uses
	# the information
        Config = ProbeConfiguration(customConfig)

        DebugPrint(0, "Initializing Gratia with "+customConfig)

        # Need to initialize the list of possible directories
        InitDirList()

        # Need to look for left over files
        SearchOutstandingRecord()

        # Attempt to reprocess any outstanding records
        Reprocess()



##
## encodeXML
##
## Author - Tim Byrne
##
##  Replaces xml-specific characters with their substitute values.  Doing so allows an xml string
##  to be included in a web service call without interfering with the web service xml.
##
## param - xmlData:  The xml to encode
## returns - the encoded xml
##
def __encodeXML(xmlData):
    return string.rstrip(xmlData).replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;")

##
## __connect
##
## Author - Tim Byrne
##
## Connect to the web service on the given server, sets the module-level object __connection
##  equal to the new connection.  Will not reconnect if __connection is already connected.
##
def __connect():
    global __connection
    global __connected
    global __connectionError
    if __connectionError:
        __disconnect()
        __connectionRetries += 1
        if __connectionRetries > MaxConnectionRetries:
            Error("Unable to reconnect after ", MaxConnectionRetries, " attempts")
            sys.exit(1)
        __connectionError = False

    if not __connected:
        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            __connection = httplib.HTTP(Config.get_SOAPHost())            
            DebugPrint(1, 'Connected via HTTP to:  ' + Config.get_SOAPHost())
            #print "Using SOAP protocol"
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:
            __connection = httplib.HTTPConnection(Config.get_SOAPHost())
            __connection.connect()
            DebugPrint(1,"Connection via HTTP to: " + Config.get_SOAPHost())
            #print "Using POST protocol"
        elif Config.get_UseSSL() == 1 and Config.get_UseGratiaCertificates() == 0:
            __connection = httplib.HTTPSConnection(Config.get_SSLHost(),
                                                   cert_file = Config.get_CertificateFile(),
                                                   key_file = Config.get_KeyFile())
            __connection.connect()
            DebugPrint(1, "Connected via HTTPS to: " + Config.get_SSLHost())
            #print "Using SSL protocol"
        else:
            __connection = httplib.HTTPSConnection(Config.get_SSLHost(),
                                                   cert_file = Config.get_GratiaCertificateFile(),
                                                   key_file = Config.get_GratiaKeyFile())
            __connection.connect()
            DebugPrint(1, "Connected via HTTPS to: " + Config.get_SSLHost())
            #print "Using SSL protocol"
        __connected = True

##
## __disconnect
##
## Author - Tim Byrne
##
## Disconnects the module-level object __connection.
##
def __disconnect():
    global __connection
    global __connected
    global __connectionError
    
    try:
        if __connected and Config.get_UseSSL() != 0:
            __connection.system.logout()
            DebugPrint(1, 'Disconnected from ' + Config.get_SSLHost() )
    except:
        if not __connectionError: # We've already complained, so shut up
            DebugPrint(0, 'Failed to disconnect from ' + Config.get_SSLHost() + ': ', sys.exc_info(),"--",sys.exc_info()[0],"++",sys.exc_info()[1])

    __connected = False

##
## sendUsageXML
##
## Author - Tim Byrne
##
##  Contacts the 'GratiaCollector' web service, sending it an xml representation of Usage data
##
##  param - meterId:  A unique Id for this meter, something the web service can use to identify communication from this meter
##  param - xmlData:  A string representation of usage xml
##
def __sendUsageXML(meterId, recordXml):
    global __connection
    global __connectionError
    global __connectionRetries

    try:
        # Connect to the web service, in case we aren't already
        # connected.  If we are already connected, this call will do
        # nothing
        __connect()

        # Generate a unique Id for this transaction
        transactionId = meterId + TimeToString().replace(":","")
        DebugPrint(1, 'TransactionId:  ' + transactionId)

        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            # Use the following template to call the interface that has the 'Event' object as a paraeter
            soapServiceTemplate = """<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">
                <soap:Body>
                    <collectUsageXml>
                        <event xmlns:ns2="http://gratia.sf.net" xsi:type="ns2:event">
                            <_id >%s</_id>
                            <_xml>%s</_xml>
                        </event>
                    </collectUsageXml>
                </soap:Body>
            </soap:Envelope>
            """

            # Insert the actual xml data into the soap template, being sure to clean out any illegal characters
            soapMessage = soapServiceTemplate%(transactionId, __encodeXML(recordXml))
            DebugPrint(4, 'Soap message:  ' + soapMessage)

            # Configure the requestor to request a Post to the GratiaCollector web service
            __connection.putrequest('POST', Config.get_CollectorService())

            # Include user and data information
            __connection.putheader('Host', Config.get_SOAPHost())
            __connection.putheader('User-Agent', 'Python post')
            __connection.putheader('Content-type', 'text/xml; charset=\'UTF-8\'')
            __connection.putheader('Content-length', '%d' % len(soapMessage))
            __connection.putheader('SOAPAction', '')
            __connection.endheaders()

            # Send the soap message to the web service
            __connection.send(soapMessage)

            # Get the web service response to the request    
            (status_code, message, reply_headers) = __connection.getreply()

            # Read the response attachment to get the actual soap response
            responseString = __connection.getfile().read()
            DebugPrint(2, 'Response:  ' + responseString)

            # Parse the response string into a response object
            try: 
                doc = xml.dom.minidom.parseString(responseString)
                codeNode = doc.getElementsByTagName('ns1:_code')
                messageNode = doc.getElementsByTagName('ns1:_message')
                if codeNode.length == 1 and messageNode.length == 1:
                    response = Response(int(codeNode[0].childNodes[0].data), messageNode[0].childNodes[0].data)
                else:
                    response = Response(-1, responseString)
            except:
                response = Response(1,responseString)
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:
            __connection.request("POST",Config.get_CollectorService(),"command=update&arg1=" + recordXml)
            responseString = __connection.getresponse().read()
            response = Response(-1, responseString)
        else:
            __connection.request("POST",Config.get_SSLCollectorService(),"command=update&arg1=" + recordXml)
            responseString = __connection.getresponse().read()
            response = Response(-1, responseString)
    except:
        DebugPrint(0,'Failed to send xml to web service:  ', sys.exc_info(), "--", sys.exc_info()[0], "++", sys.exc_info()[1])
        # Upon a connection error, we will stop to try to reprocess but will continue to
        # try sending
        __connectionError = True

        response = Response(1,"Failed to send xml to web service")

    if (__connectionRetries > 0) and (response.get_code() == 0):
        # Successful transaction after a reconnect
        __connectionRetries = 0
    return response

LogFileIsWriteable = True

def LogToFile(message):
    "Write a message to the Gratia log file"

    global LogFileIsWriteable
    file = None
    filename = "none"

    try:
        # Ensure the 'logs' folder exists
        if os.path.exists(Config.get_LogFolder()) == 0:
            Mkdir(Config.get_LogFolder())

        filename = time.strftime("%Y-%m-%d") + ".log"
        filename = os.path.join(Config.get_LogFolder(),filename)

        if os.path.exists(filename) and not os.access(filename,os.W_OK):
            os.chown(filename, os.getuid(), os.getgid())
            os.chmod(filename, 0755)

        # Open/Create a log file for today's date
        file = open(filename, 'a')

        # Append the message to the log file
        file.write(message + "\n")

        LogFileIsWriteable = True
    except:
        if LogFileIsWriteable:
            # Print the error message only once
            print "Gratia: Unable to log to file:  ", filename, " ",  sys.exc_info(), "--", sys.exc_info()[0], "++", sys.exc_info()[1]
        LogFileIsWriteable = False

    if file != None:
        # Close the log file
        file.close()

def LogToSyslog(level, message) :
    import syslog
    if (level == -1) : syslevel = syslog.LOG_ERR
    else: 
        if (level == 0) : syslevel = syslog.LOG_INFO
        else: 
           if (level == 1) : syslevel = syslog.LOG_INFO
           else: syslevel = syslog.LOG_DEBUG

    try:
        syslog.openlog("Gratia ")
        syslog.syslog( syslevel, message)

        LogFileIsWriteable = True
    except:
        if LogFileIsWriteable:
            # Print the error message only once
            print "Gratia: Unable to log to syslog:  ",  sys.exc_info(), "--", sys.exc_info()[0], "++", sys.exc_info()[1]
        LogFileIsWriteable = False
        
    syslog.closelog()


def RemoveOldLogs(nDays = 31):

   backupDir = Config.get_LogFolder()
   cutoff = time.time() - nDays * 24 * 3600

   DebugPrint(1, " Removing log files older than ", nDays, " days from " , backupDir)
 
   # Get the list of all files in the PSACCT File Backup Repository
   files = glob.glob(os.path.join(backupDir,"*")+".log")

   DebugPrint(3, " Will check the files: ",files)
        
   for f in files:
      if os.path.getmtime(f) < cutoff:
         DebugPrint(2, "Will remove: " + f)
         #os.remove(f)
                
   files = None


def GenerateOutput(prefix,*arg):
    out = prefix
    for val in arg:
        out = out + str(val)
    return out

def DebugPrint(level, *arg):
    if (not Config or level<Config.get_DebugLevel()):
        out = GenerateOutput("Gratia: ",*arg)
        print out
    if Config and level<Config.get_LogLevel():
        out = GenerateOutput("Gratia: ",*arg)
        if (Config.get_UseSyslog()):
           LogToSyslog(level,GenerateOutput("",*arg))
        else:
           LogToFile(out)

def Error(*arg):
    out = GenerateOutput("Error in Gratia probe: ",*arg)
    print out
    if (Config.get_UseSyslog()):
       LogToSyslog(-1,GenerateOutput("",*arg))
    else:
       LogToFile(out)

##
## Mkdir
##
## Author - Trent Mick (other recipes)
##
## A more friendly mkdir() than Python's standard os.mkdir().
## Limitations: it doesn't take the optional 'mode' argument
## yet.
##
## http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/82465

def Mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            Mkdir(head)
        # Mkdir can not use DebugPrint since it is used
        # while trying to create the log file!
        #print "Mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)


def DirListAdd(value):
    "Utility method to add directory to the list of directories"
    "to be used for backup of the xml record"
    if len(value)>0 and value!="None" : BackupDirList.append(value)

def InitDirList():
    "Initialize the list of backup directories"
    "We prefer $DATA_DIR, but will also (if needed)"
    "try various tmp directory (/var/tmp, /tmp,"
    "$TMP_DIR, etc.."

    Mkdir(Config.get_WorkingFolder())

    DirListAdd(Config.get_WorkingFolder())
    DirListAdd(os.getenv('DATA_DIR',""))
    DirListAdd("/var/tmp")
    DirListAdd("/tmp")
    DirListAdd(os.getenv('TMP_DIR',""))
    DirListAdd(os.getenv('TMP_WN_DIR ',""))
    DirListAdd(os.getenv('TMP',""))
    DirListAdd(os.getenv('TMPDIR',""))
    DirListAdd(os.getenv('TMP_DIR',""))
    DirListAdd(os.getenv('TEMP',""))
    DirListAdd(os.getenv('TEMPDIR',""))
    DirListAdd(os.getenv('TEMP_DIR',""))
    DirListAdd(os.environ['HOME'])
    DebugPrint(1,"List of backup directories: ",BackupDirList)

def SearchOutstandingRecord():
    "Search the list of backup directories for"
    "any record that has not been sent yet"

    for dir in BackupDirList:
        path = os.path.join(dir,"gratiafiles")
        path = os.path.join(path,"*"+"."+Config.get_GratiaExtension())
        files = glob.glob(path)
        for f in files:
            OustandingRecord[f] = 1
            if len(OutstandingRecord) >= MaxFilesToReprocess: break

        if len(OutstandingRecord) >= MaxFilesToReprocess: break

    DebugPrint(1,"List of Outstanding records: ",OutstandingRecord.keys())

def GenerateFilename(dir,RecordIndex):
    "Generate a filename of the for gratia/r$index.$pid.gratia.xml"
    "in the directory 'dir'"
    filename = "r"+str(RecordIndex)+"."+str(RecordPid)+"."+Config.get_GratiaExtension()
    filename = os.path.join(dir,filename)
    return filename

def OpenNewRecordFile(DirIndex,RecordIndex):
    "Try to open the first available file"
    "DirIndex indicates which directory to try first"
    "RecordIndex indicates which file index to try first"
    "The routine returns the opened file and the next"
    "directory index and record index"
    "If all else fails, we print the xml to stdout"

    # The file name will be r$index.$pid.gratia.xml

    DebugPrint(3,"Open request: ",DirIndex," ",RecordIndex)
    index = 0
    for dir in BackupDirList:
        index = index + 1
        if index <= DirIndex or not os.path.exists(dir):
            continue
        DebugPrint(3,"Open request: looking at ",dir)
        dir = os.path.join(dir,"gratiafiles")
        if not os.path.exists(dir):
            try:
                Mkdir(dir)
            except:
                continue
        if not os.path.exists(dir):
            continue
        if not os.access(dir,os.W_OK): continue
        filename = GenerateFilename(dir,RecordIndex)
        while os.access(filename,os.F_OK):
            RecordIndex = RecordIndex + 1
            filename = GenerateFilename(dir,RecordIndex)
        try:
            DebugPrint(1,"Creating file:",filename)
            f = open(filename,'w')
            DirIndex = index
            return(f,DirIndex,RecordIndex)
        except:
            continue
    f = sys.stdout
    DirIndex = index
    return (f,DirIndex,RecordIndex)


def TimeToString(t = time.gmtime() ):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ",t)

#
# Remove old backups
#
# Remove any backup older than the request number of days
#
# Parameters
#   nDays - remove file older than 'nDays' (default 31)
#
def RemoveOldBackups(self, probeConfig, nDays = 31):
    logDir = Config.get_LogFolder()
    cutoff = time.time() - nDays * 24 * 3600

    DebugPrint(1, " Removing Gratia log files older than ", nDays, " days from " , backupDir)

    # Get the list of all files in the PSACCT File Backup Repository
    files = glob.glob(os.path.join(backupDir,"*.log"))

    DebugPrint(3, " Will check the files: ",files)

    for f in files:
        if os.path.getmtime(f) < cutoff:
            DebugPrint(2, "Will remove: " + f)
            os.remove(f)

    files = None

class UsageRecord:
    "Base class for the Gratia Usage Record"
    XmlData = []
    RecordData = []
    JobId = []
    UserId = []
    __ProbeName = ""
    __ProbeNameDescription = ""
    __SiteName = ""
    __SiteNameDescription = ""
    __Njobs = 1
    __NjobsDescription = ""

    def __init__(self):
        DebugPrint(0,"Creating a usage Record "+TimeToString())
        self.XmlData = []
        self.RecordData = []
        self.JobId = []
        self.UserId = []
        self.Username = "none"
        self.__ProbeName = Config.get_MeterName()
        self.__SiteName = Config.get_SiteName()

    def Description(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:description=\""+value+"\" "
        else : return ""

    def Metric(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:metric=\""+value+"\" "
        else : return ""

    def Unit(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:unit=\""+value+"\" "
        else : return ""

    def StorageUnit(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:storageUnit=\""+value+"\" "
        else : return ""

    def PhaseUnit(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        if len(realvalue)>0 : return  "urwg:phaseUnit=\""+realvalue+"\" "
        else : return ""

    def Type(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:type=\""+value+"\" "
        else : return ""

    def UsageType(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:usageType=\""+value+"\" "
        else : return ""

    def Duration(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        seconds = (int(value*100) % 6000 ) / 100.0
        value = int( (value - seconds) / 60 )
        minutes = value % 60
        value = (value - minutes) / 60
        hours = value % 24
        value = (value - hours) / 24
        result = "P"
        if value>0: result = result + str(value) + "D"
        if (hours>0 or minutes>0 or seconds>0) :
            result = result + "T"
            if hours>0 : result = result + str(hours)+ "H"
            if minutes>0 : result = result + str(minutes)+ "M"
            if seconds>0 : result = result + str(seconds)+ "S"
        else : result = result + "T0S"
        return result

    def AddToList(self,where,what,comment,value):
        " Helper Function to generate the xml (Do not call directly)"
        # First filter out the previous value
        where = [x for x in where if x.find("<"+what)!=0]
        where.append("<"+what+" "+comment+">"+value+"</"+what+">")
        return where

    def AppendToList(self,where,what,comment,value):
        " Helper Function to generate the xml (Do not call directly)"
        where.append("<"+what+" "+comment+">"+value+"</"+what+">")
        return where

    # Public Interface:
    def LocalJobId(self,value):
        self.JobId = self.AddToList(self.JobId,"LocalJobId","",value)

    def GlobalJobId(self,value):
        self.JobId = self.AddToList(self.JobId,"GlobalJobId","",value)

    def ProcessId(self,value):
        self.JobId = self.AddToList(self.JobId,"ProcessId","",str(value))

    def GlobalUsername(self,value): 
        self.UserId = self.AddToList(self.UserId,"GlobalUsername","",value)

    def LocalUserId(self,value):
        self.UserId = self.AddToList(self.UserId,"LocalUserId","",value)

    def UserKeyInfo(self,value):
        " Example: \
            <ds:KeyInfo xmlns:ds=""http://www.w3.org/2000/09/xmldsig#""> \
        <ds:X509Data> \
           <ds:X509SubjectName>CN=john ainsworth, L=MC, OU=Manchester, O=eScience, C=UK</ds:X509SubjectName> \
        </ds:X509Data> \
          </ds:KeyInfo>"
        complete = "\n\t\t<ds:X509Data>\n\t\t<ds:X509SubjectName>"+value+"</ds:X509SubjectName>\n\t\t</ds:X509Data>\n\t"
        self.UserId = self.AddToList(self.UserId,"ds:KeyInfo","xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\" ",complete)

    def VOName(self,value):
        self.UserId = self.AddToList(self.UserId,"VOName","",value)

    def ReportableVOName(self,value):
        " Set reportable VOName"
        self.UserId = self.AddToList(self.UserId,"ReportableVOName","",value)

    def JobName(self, value, description = ""):
        self.RecordData = self.AddToList(self.RecordData, "JobName", self.Description(description) ,value)

    def Charge(self,value, unit = "", formula = "", description = ""):
        if len(formula)>0 : Formula = "formula=\""+formula+"\" "
        else : Formula = ""
        self.RecordData = self.AddToList(self.RecordData,"Charge",self.Description(description)+self.Unit(unit)+Formula , value)

    def Status(self,value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "Status", self.Description(description), str(value))

    def WallDuration(self, value, description = ""):
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        self.RecordData = self.AddToList(self.RecordData, "WallDuration", self.Description(description), realvalue)

    def CpuDuration(self, value, cputype, description = ""):
        "Register a total cpu duration.  cputype must be either 'user' or 'system'"
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        if cputype=="sys" : cputype="system"
        if cputype!="user" and cputype!="system" : 
            description = "(type="+cputype+") "+description
            cputype = ""
        self.RecordData = self.AppendToList(self.RecordData, "CpuDuration", self.UsageType(cputype)+self.Description(description), realvalue)

    def EndTime(self, value, description = ""):
        if type(value)==str : realvalue = value
        else : realvalue = TimeToString(time.gmtime(value))
        self.RecordData = self.AddToList(self.RecordData, "EndTime", self.Description(description), realvalue)

    def StartTime(self, value, description = ""):
        if type(value)==str : realvalue = value
        else : realvalue = TimeToString(time.gmtime(value))
        self.RecordData = self.AddToList(self.RecordData, "StartTime", self.Description(description), realvalue)

    def TimeDuration(self, value, timetype, description = ""):
        " Additional measure of time duration that is relevant to the reported usage "
        " timetype can be one of 'submit','connect','dedicated' (or other) "
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        self.AppendToList(self.RecordData, "TimeDuration", self.Type(timetype)+self.Description(description), realvalue)

    def TimeInstant(self, value, timetype, description = ""):
        " Additional identified discrete time that is relevant to the reported usage "
        " timetype can be one of 'submit','connect' (or other) "
        if type(value)==str : realvalue = value
        else : realvalue = TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "TimeInstant", self.Type(timetype)+self.Description(description), realvalue)

    def MachineName(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "MachineName", self.Description(description), value)

    def Host(self, value, primary = False, description = "") :
        if primary : pstring = "primary=\"true\" "
        else : pstring = "primary=\"false\" "
        pstring = pstring + self.Description(description)
        self.RecordData = self.AddToList(self.RecordData, "Host", pstring, value)

    def SubmitHost(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "SubmitHost", self.Description(description), value)

    def Queue(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "Queue", self.Description(description), value)

    def ProjectName(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "ProjectName", self.Description(description), value)


    def Network(self, value, storageUnit = "", phaseUnit = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        self.AppendToList(self.RecordData, "Network",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Metric(metric)+self.Description(description),
          str(value))

    def Disk(self, value, storageUnit = "", phaseUnit = "", type = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " Type can be one of scratch or temp "
        self.AppendToList(self.RecordData, "Disk",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Type(type)+self.Metric(metric)+self.Description(description),
          str(value))

    def Memory(self, value, storageUnit = "", phaseUnit = "", type = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " Type can be one of shared, physical, dedicated "
        self.AppendToList(self.RecordData, "Memory",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Type(type)+self.Metric(metric)+self.Description(description),
          str(value))

    def Swap(self, value, storageUnit = "", phaseUnit = "", type = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " Type can be one of shared, physical, dedicated "
        self.AppendToList(self.RecordData, "Swap",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Type(type)+self.Metric(metric)+self.Description(description),
          str(value))

    def NodeCount(self, value, metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        self.AppendToList(self.RecordData, "NodeCount",
          self.Metric(metric)+self.Description(description),
          str(value))

    def Processors(self, value, consumptionRate = 0, metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " consumptionRate specifies te consumption rate for the report "
        " processor usage.  The cinsumption rate is a sclaing factor that "
        " indicates the average percentage of utilization. "
        if consumptionRate>0 : pstring = "consumptionRate=\""+str(consumptionRate)+"\" "
        else : pstring = ""
        self.AppendToList(self.RecordData, "Processors",
          pstring+self.Metric(metric)+self.Description(description),
          str(value))

    def ServiceLevel(self, value, type, description = ""):
        self.AppendToList(self.RecordData, "ServiceLevel", self.Type(type)+self.Description(description), str(value))


    def Resource(self,description,value) :
        self.AppendToList(self.RecordData, "Resource", self.Description(description), str(value))

    def AdditionalInfo(self,description,value) :
        self.Resource(description,value)

    # The following are not officially part of the Usage Record format

    def Njobs(self, value, description = "") :
        self.__Njobs = value
        self.__NjobsDescription = description

    # The following usually comes from the Configuration file

    def ProbeName(self, value, description = "") :
        self.__ProbeName = value
        self.__ProbeNameDescription = description

    def SiteName(self, value, description = "") :
        " Indicates which site the service accounted for belong to"
        self.__SiteName = value
        self.__SiteNameDescription = description

    def GenericAddToList(self, xmlelem, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, xmlelem, self.Description(description), value)

    def XmlAddMembers(self):
        self.GenericAddToList( "ProbeName", self.__ProbeName, self.__ProbeNameDescription )
        self.GenericAddToList( "SiteName", self.__SiteName, self.__SiteNameDescription )
        self.GenericAddToList( "Njobs", str(self.__Njobs), self.__NjobsDescription )

    def VerifyUserInfo(self):
        " Verify user information: check for LocalUserId and add VOName and ReportableVOName if necessary"
        id_info = { } # Store attributes of already-present information
        interesting_keys = [ "LocalUserId", "VOName", "ReportableVOName" ]
        for wanted_key in interesting_keys: # Loop over wanted keys
            item_index = 0
            for id_item in self.UserId: # Loop over existing entries in UserId block
                # Look for key
                match = re.search(r'<\s*(?:[^:]*:)?'+wanted_key+r'\s*>\s*(?P<Value>.*?)\s*<\s*/',
                                  id_item, re.IGNORECASE)
                # Store info
                if match:
                    id_info[wanted_key] = { "Value" : match.group("Value"),
                                            "Index" : item_index }
                    break

                item_index += 1

        if not id_info.has_key("LocalUserId") or \
           len(id_info) == len(interesting_keys): return # Nothing to do
        # Obtain user->VO info from reverse gridmap file.
        vo_info = VOfromUser(id_info["LocalUserId"]["Value"])
        if vo_info != None:
            # If we already have one of the two, update both to remain consistent.
            for key in "VOName", "ReportableVOName":
                if id_info.has_key(key): # Replace existing value
                    self.UserId[id_info[key]["Index"]] = re.sub(r'(>\s*)'+re.escape(id_info[key]["Value"])+r'(\s*<)',
                                                                r'\1'+vo_info[key]+r'\2',
                                                                self.UserId[id_info[key]["Index"]],
                                                                1)
                else: # Add new
                    self.UserId = self.AddToList(self.UserId, key, "", vo_info[key])

    def XmlCreate(self):
        global RecordId

        self.XmlAddMembers()

        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<JobUsageRecord xmlns=\"http://www.gridforum.org/2003/ur-wg\"\n")
        self.XmlData.append("		xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\"\n")
        self.XmlData.append("		xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" \n")
        self.XmlData.append("		xsi:schemaLocation=\"http://www.gridforum.org/2003/ur-wg file:///u:/OSG/urwg-schema.11.xsd\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(RecordPid)+"."+str(RecordId)+"\" urwg:createTime=\""+TimeToString(time.gmtime())+"\" />\n")
        RecordId = RecordId + 1

        if len(self.JobId)>0 :
            self.XmlData.append("<JobIdentity>\n")
            for data in self.JobId:
                self.XmlData.append("\t")
                self.XmlData.append(data)
                self.XmlData.append("\n")
            self.XmlData.append("</JobIdentity>\n")
        if len(self.UserId)>0 :
            self.VerifyUserInfo() # Add VOName and Reportable VOName if necessary.
            self.XmlData.append("<UserIdentity>\n")
            for data in self.UserId:
                self.XmlData.append("\t")
                self.XmlData.append(data)
                self.XmlData.append("\n")
            self.XmlData.append("</UserIdentity>\n")
        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</JobUsageRecord>\n")

def LocalJobId(record,value):
    record.LocalJobId(value)

def GlobalJobId(record,value):
    record.GlobalJobId(value)

def ProcessJobId(record,value):
    record.ProcessJobId(value)

#
# Reprocess
#
#  Loops through all outstanding records and attempts to send them again
#
def Reprocess():
    responseString = ""

    # Loop through and try to send any outstanding records
    for failedRecord in OutstandingRecord.keys():
        xmlData = None
        #if os.path.isfile(failedRecord):
        DebugPrint(1, 'Reprocessing:  ' + failedRecord)

        # Read the contents of the file into a string of xml
        try:
            in_file = open(failedRecord,"r")
            xmlData = in_file.read()
            in_file.close()
        except:
            DebugPrint(1, 'Reprocess failure: unable to read file' + failedRecord)
            responseString = responseString + '\nUnable to read from ' + failedRecord
            continue

        if not XmlData:
            DebugPrint(1, 'Reprocess failure: ' + failedRecord +
                       ' was empty: skip send')
            responseString = responseString + '\nEmpty file ' + failedRecord + ': XML not sent'
            continue
        
        # Send the xml to the collector for processing
        response = __sendUsageXML(Config.get_MeterName(), xmlData)
        DebugPrint(1, 'Reprocess Response:  ' + response.get_message())
        responseString = responseString + '\nReprocessed ' + failedRecord + ':  ' + response.get_message()

        # Determine if the call succeeded, and remove the file if it did
        if response.get_code() == 0:
            os.remove(failedRecord)
            del OutstandingRecord[failedRecord]

    if responseString <> "":
        DebugPrint(0, responseString)

    return responseString

failedSendCount = 0

def Send(record):
    global failedSendCount

    DebugPrint(0, "***********************************************************")
    DebugPrint(1,"Record: ",record)
    DebugPrint(1,"Username: ", record.Username)
    if (failedSendCount + len(OutstandingRecord)) >= Config.get_MaxPendingFiles():
        responseString = "Fatal Error: too many pending files"
        DebugPrint(0, responseString)
        DebugPrint(0, "***********************************************************")
        return responseString

    # Assemble the record into xml
    record.XmlCreate()

    dirIndex = 0
    recordIndex = 0
    success = False
    ind = 0
    f = 0

    while not success:
        (f,dirIndex,recordIndex) = OpenNewRecordFile(dirIndex,recordIndex)
        DebugPrint(1,"Will save in the record in:",f.name)
        DebugPrint(3,"DirIndex=",dirIndex," RecordIndex=",recordIndex)
        if f.name != "<stdout>":
            try:
                for line in record.XmlData:
                    f.write(line)
                f.flush()
                if f.tell() > 0:
                    success = True
                    DebugPrint(0, 'Saved record to ' + f.name)
                else:
                    DebugPrint(0,"failed to fill: ",f.name)
                    if f.name != "<stdout>": os.remove(f.name)
                f.close()
            except:
                DebugPrint(0,"failed to fill with exception: ",f.name,"--", sys.exc_info(),"--",sys.exc_info()[0],"++",sys.exc_info()[1])

    # Currently, the recordXml is in a list format, with each item being a line of xml.  
    # the collector web service requires the xml to be sent as a string.  
    # This logic here turns the xml list into a single xml string.
    usageXmlString = ""
    for line in record.XmlData:
        usageXmlString = usageXmlString + line
    DebugPrint(3, 'UsageXml:  ' + usageXmlString)

    # Attempt to send the record to the collector
    response = __sendUsageXML(Config.get_MeterName(), usageXmlString)
    responseString = response.get_message()

    DebugPrint(0, 'Response code:  ' + str(response.get_code()))
    DebugPrint(0, 'Response message:  ' + response.get_message())

    # Determine if the call was successful based on the response
    # code.  Currently, 0 = success
    if response.get_code() == 0:
        DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
        os.remove(f.name)
    else:
        failedSendCount += 1
        if (f.name == "<stdout>"):
            DebugPrint(0, 'Record send failed and no backup made: record lost!')
            responseString += "\nFatal: failed record lost!"
            match = re.search(r'^<(?:[^:]*:)?RecordIdentity.*/>$', usageXmlString, re.MULTILINE)
            if match:
                DebugPrint(0, match.group(0))
                responseString += "\n", match.group(0)
            match = re.search(r'^<(?:[^:]*:)?GlobalJobId.*/>$', usageXmlString, re.MULTILINE)
            if match:
                DebugPrint(0, match.group(0))
                responseString += "\n", match.group(0)
            responseString += "\n" + usageXmlString
        else:
            DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

    DebugPrint(0, responseString)
    DebugPrint(0, "***********************************************************")
    return responseString

# This sends the file contents of the given directory as raw XML. The
# writer of the XML files is responsible for making sure that it is
# readable by the Gratia server.
def SendXMLFiles(fileDir, removeOriginal = False):
    global Config

    path = os.path.join(fileDir, "*")
    files = glob.glob(path)

    probeNamePattern = re.compile(r'<\s*(?:[^:]*:)?ProbeName\s*>')
    siteNamePattern = re.compile(r'<\s*(?:[^:]*:)?SiteName\s*>')
    endUsageRecordPattern = re.compile(r'<\s*/\s*(?:[^:]*:)?UsageRecord\s*>')
    LocalUserIdPattern = re.compile(r'<\s*(?:[^:]*:)?LocalUserId\s*>\s*(?P<Value>.*?)\s*<\s*/')
    VONamePattern = re.compile(r'<\s*(?:[^:]*:)?VOName\s*>\s*(?P<Value>.*?)\s*<\s*/')
    ReportableVONamePattern = re.compile(r'<\s*(?:[^:]*:)?ReportableVOName\s*>\s*(?P<Value>.*?)\s*<\s*/')
    endUserIdentityPattern = re.compile(r'<\s*/\s*(?:[^:]*:)?UserIdentity\s*>')
    responseString = ""

    for xmlFilename in files:

        DebugPrint(0, "***********************************************************")
        DebugPrint(1,"xmlFilename: ",xmlFilename)
        if (failedSendCount + len(OutstandingRecord)) >= Config.get_MaxPendingFiles():
            responseString = "Fatal Error: too many pending files"
            DebugPrint(0, responseString)
            DebugPrint(0, "***********************************************************")
            return responseString

        # Open the XML file
        in_file = open(xmlFilename, "r")
        xmlData = []

        # Need to check for keys that may be missing and add them:
        hasProbeName = False
        hasSiteName = False
        LocalUserId = None
        VOName = None
        ReportableVOName = None
        seenEndUserIdentity = None

        for line in in_file:
            if probeNamePattern.match(line):
                hasProbeName = True
            if siteNamePattern.match(line):
                hasSiteName = True
            match = LocalUserIdPattern.search(line, re.IGNORECASE)
            if match and not seenEndUserIdentity:
                LocalUserId = match.group('Value')
            match = VONamePattern.search(line, re.IGNORECASE)
            if match and not seenEndUserIdentity:
                VOName = match.group('Value')
            match = ReportableVOName.search(line, re.IGNORECASE)
            if match and not seenEndUserIdentity:
                ReportableVOName = match.group('Value')
            if endUserIdentityPattern.match(line, re.IGNORECASE):
                # Check for VOName and ReportableVOName in UserIdentity
                # clause and update or add if necessary
                seenEndUserIdentity = True
                if LocalUserId and not \
                       (VOName and ReportableVOName):
                    vo_info = VOfromUser(LocalUserId)
                    if vo_info:
                        if (VOName and VOName != vo_info[VOName]):
                            # Update entry
                            XmlData = map(lambda x: re.sub(r'(<\s*(?:[^:]*:)?VOName\s*>\s*).*?(\s*<\s*/)',
                                                           r'\1' + vo_info[VOName] + r'\2',
                                                           x))
                        elif (not VOName):
                            # New entry
                            xmlData.append('<VOName>' + vo_info[VOName] + '</VOName>\n')

                        if (ReportableVOName and ReportableVOName != vo_info[ReportableVOName]):
                            # Update entry
                            XmlData = map(lambda x: re.sub(r'(<\s*(?:[^:]*:)?ReportableVOName\s*>\s*).*?(\s*<\s*/)',
                                                           r'\1' + vo_info[ReportableVOName] + r'\2',
                                                           x))
                        elif (not ReportableVOName):
                            # New entry
                            xmlData.append('<ReportableVOName>' + vo_info[ReportableVOName] + '</ReportableVOName>\n')


            if endUsageRecordPattern.match(line):
                if not hasProbeName:
                    xmlData.append('<ProbeName>' +
                                   Config.get_MeterName() +
                                   '</ProbeName>\n')
                if not hasSiteName:
                    xmlData.append('<SiteName>' +
                                   Config.get_SiteName() +
                                   '</SiteName>\n')
            xmlData.append(line)
        in_file.close()

        # Open the back up file
        # fill the back up file

        dirIndex = 0
        recordIndex = 0
        success = False
        ind = 0
        f = 0

        while not success:
            (f,dirIndex,recordIndex) = OpenNewRecordFile(dirIndex,recordIndex)
            DebugPrint(1,"Will save in the record in:",f.name)
            DebugPrint(3,"DirIndex=",dirIndex," RecordIndex=",recordIndex)
            if f.name == "<stdout>":
                responseString = "Fatal Error: unable to save record prior to send attempt"
                DebugPrint(0, responseString)
                DebugPrint(0, "***********************************************************")
                return responseString    
            else:
                try:
                    for line in xmlData:
                        f.write(line)
                    f.flush()
                    if f.tell() > 0:
                        success = True
                        DebugPrint(3,"suceeded to fill: ",f.name)
                    else:
                        DebugPrint(0,"failed to fill: ",f.name)
                        if f.name != "<stdout>": os.remove(f.name)
                except:
                    DebugPrint(0,"failed to fill with exception: ",f.name,"--",
                               sys.exc_info(),"--",sys.exc_info()[0],"++",sys.exc_info()[1])
                    if f.name != "<stdout>": os.remove(f.name)

        if removeOriginal and f.name != "<stdout>": os.remove(xmlFilename)

        DebugPrint(0, 'Saved record to ' + f.name)

        # Currently, the recordXml is in a list format, with each
        # item being a line of xml. The collector web service
        # requires the xml to be sent as a string. This logic here
        # turns the xml list into a single xml string.
        usageXmlString = ""
        for line in xmlData:
            usageXmlString = usageXmlString + line
        DebugPrint(1, 'UsageXml:  ' + usageXmlString)

        # Attempt to send the record to the collector
        response = __sendUsageXML(Config.get_MeterName(), usageXmlString)

        DebugPrint(0, 'Response code:  ' + str(response.get_code()))
        DebugPrint(0, 'Response message:  ' + response.get_message())

        # Determine if the call was successful based on the
        # response code.  Currently, 0 = success
        if response.get_code() == 0:
            DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
            os.remove(f.name)
        else:
            failedSendCount += 1
            DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

    DebugPrint(0, responseString)
    DebugPrint(0, "***********************************************************")
    return responseString

__UserVODictionary = { }

def VOfromUser(user):
    " Helper function to obtain the voi and VOc from the user name via the reverse gridmap file"
    if (len(__UserVODictionary) == 0):
        # Initialize dictionary
        mapfile = Config.get_UserVOMapFile()
        if mapfile == None:
             return None
        __voiToVOcDictionary = { }
        __voi = []
        __VOc = []
        try:
            for line in fileinput.input([mapfile]):
                mapMatch = re.match(r'#(voi|VOc)\s', line)
                if mapMatch:
                    # Translation line: fill translation tables
                    exec "__" + mapMatch.group(1) + " = re.split(r'\s*', line[mapMatch.end(0):])"
                if re.match(r'\s*#', line): continue
                mapMatch = re.match('\s*(?P<User>\S+)\s*(?P<voi>\S+)', line)
                if mapMatch:
                    if not len(__voiToVOcDictionary) and len(__voi) and len(__VOc):
                        for index in xrange(0, len(__voi) - 1):
                            __voiToVOcDictionary[__voi[index]] = __VOc[index]
                    __UserVODictionary[mapMatch.group('User')] = { "VOName" : mapMatch.group('voi'),
                                                                   "ReportableVOName" : __voiToVOcDictionary[mapMatch.group('voi')] }
        except IOError, c:
            print c
            return None
    return __UserVODictionary.get(user, None)
