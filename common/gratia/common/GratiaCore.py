#!/usr/bin/python
# -*- coding: utf-8 -*-
# @(#)gratia/probe/common:$HeadURL: https://gratia.svn.sourceforge.net/svnroot/gratia/trunk/probe/common/Gratia.py $:$Id$

"""
Gratia Core Probe Library
"""

import os
import signal
import errno
import sys
import time
import glob
import string
import httplib
import xml.dom.minidom
import socket
import StringIO
import traceback
import re
import fileinput
import tarfile
import shutil
import atexit
import urllib
import ProxyUtil
import xml.sax.saxutils
import exceptions
import pwd
import grp
import math
from OpenSSL import crypto

# Public switches
quiet = 0
Config = None

# Privates globals
collector__wantsUrlencodeRecords = 1
__xmlintroRemove = re.compile(r'<\?xml[^>]*\?>')
__certinfoLocalJobIdMunger = re.compile(r'(?P<ID>\d+(?:\.\d+)*)')
__certinfoJobManagerExtractor = re.compile(r'gratia_certinfo_(?P<JobManager>(?:[^\d_][^_]*))')
__lrms = None
__quoteSplit = re.compile(' *"([^"]*)"')

# List of externals files used:
# Probe configuration file
# Grid mapfile as defined by Config.get_UserVOMapFile()
# Certificate information files matching the pattern: Config.get_DataFolder() + 'gratia_certinfo' + r'_' + jobManager + r'_' + localJobId

def __disconnect_at_exit__():
    """
    Insure that we properly shutdown the connection at the end of the process.
    
    This includes sending any outstanding records and printing the statistics
    """

    if __bundleSize__ > 1 and CurrentBundle.nItems > 0:
        (responseString, response) = ProcessBundle(CurrentBundle)
        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')
    __disconnect()
    if Config:
        try:
            RemoveOldLogs(Config.get_LogRotate())
            RemoveOldJobData(Config.get_DataFileExpiration())
            RemoveOldQuarantine(Config.get_DataFileExpiration(), Config.get_QuarantineSize())
        except Exception, exception:
            DebugPrint(0, 'Exception caught at top level: ' + str(exception))
            DebugPrintTraceback()
    DebugPrint(0, 'End of execution summary: new records sent successfully: ' + str(successfulSendCount))
    DebugPrint(0, '                          new records suppressed: ' + str(suppressedCount))
    DebugPrint(0, '                          new records failed: ' + str(failedSendCount))
    DebugPrint(0, '                          records reprocessed successfully: '
               + str(successfulReprocessCount))
    DebugPrint(0, '                          reprocessed records failed: ' + str(failedReprocessCount))
    DebugPrint(0, '                          handshake records sent successfully: ' + str(successfulHandshakes))
    DebugPrint(0, '                          handshake records failed: ' + str(failedHandshakes))
    DebugPrint(0, '                          bundle of records sent successfully: '
               + str(successfulBundleCount))
    DebugPrint(0, '                          bundle of records failed: ' + str(failedBundleCount))
    DebugPrint(0, '                          outstanding records: ' + str(__outstandingRecordCount__))
    DebugPrint(0, '                          outstanding staged records: ' + str(__outstandingStagedRecordCount__))
    DebugPrint(0, '                          outstanding records tar files: ' + str(__outstandingStagedTarCount__))
    DebugPrint(1, 'End-of-execution disconnect ...')


class GratiaTimeout:
    """
    Exception class to mark a connection timeout caught via the signal.alarm.
    """ 
    
    __message = None
    
    def __init__(self, message = None):
       self.__message = message

def __handle_timeout__(signum, frame):
    """
    Insure that we properly shutdown the connection in case of timeout
    """
    DebugPrint(3, 'Signal handler "handle_timeout" called with signal', signum)
    raise GratiaTimeout("Connection to Collector lasted more than: "+str(__timeout__)+" second")


class ProbeConfiguration:
    """
    Class giving access (and in some cases override capability) to the ProbeConfig files
    """
    
    __doc = None
    __configname = 'ProbeConfig'
    __CollectorHost = None
    __ProbeName = None
    __SiteName = None
    __Grid = None
    __DebugLevel = None
    __LogLevel = None
    __LogRotate = None
    __DataFileExpiration = None
    __QuarantineSize = None
    __UseSyslog = None
    __UserVOMapFile = None
    __FilenameFragment = None
    __CertInfoLogPattern = None

    def __init__(self, customConfig='ProbeConfig'):
        if os.path.exists(customConfig):
            self.__configname = customConfig
	else:
		DebugPrint(0,"Error: configuration file %s doesn't exist" % (customConfig,))
		raise InternalError("Error: configuration file %s doesn't exist" % (customConfig,))

    def __loadConfiguration__(self):
        self.__doc = xml.dom.minidom.parse(self.__configname)
        DebugPrint(0, 'Using config file: ' + self.__configname)

    def __getConfigAttribute(self, attributeName):
        """
        Return the value of a configuration attribute name 'attributeName'
        """
        if self.__doc == None:
            try:
                self.__loadConfiguration__()
            except xml.parsers.expat.ExpatError, ex:
                sys.stderr.write('Parse error in ' + self.__configname + ': ' + str(ex) + '\n')
                raise

        # TODO:  Check if the ProbeConfiguration node exists
        # TODO:  Check if the requested attribute exists

        return self.__doc.getElementsByTagName('ProbeConfiguration')[0].getAttribute(attributeName)

    def __findVDTTop(self):
        """
        Internal routine returning the top level directory of the VDT installation.
        """
        mvt = self.__getConfigAttribute('VDTSetupFile')
        if mvt and os.path.isfile(mvt):
            return os.path.dirname(mvt)
        else:
            mvt = os.getenv('OSG_GRID') or os.getenv('OSG_LOCATION') or os.getenv('VDT_LOCATION') \
                or os.getenv('GRID3_LOCATIION')
        if mvt != None and os.path.isdir(mvt):
            return mvt
        else:
            return None

    # Public interface


    def getConfigAttribute(self, attributeName):
        return self.__getConfigAttribute(attributeName)

    def get_SSLHost(self):
        return self.__getConfigAttribute('SSLHost')

    def get_SSLRegistrationHost(self):
        return self.__getConfigAttribute('SSLRegistrationHost')

    def get_SOAPHost(self):
        return self.get_CollectorHost()

    def get_CollectorHost(self):
        if self.__CollectorHost != None:
            return self.__CollectorHost
        coll = self.__getConfigAttribute('CollectorHost')
        soap = self.__getConfigAttribute('SOAPHost')
        if coll == 'gratia-osg.fnal.gov:8880' and soap != None and soap != r'' and soap \
            != 'gratia-osg.fnal.gov:8880':
            self.__CollectorHost = soap
        elif coll != None and coll != r'':
            self.__CollectorHost = coll
        else:
            self.__CollectorHost = soap
        return self.__CollectorHost

    def get_CollectorService(self):
        return self.__getConfigAttribute('CollectorService')

    def get_SSLCollectorService(self):
        return self.__getConfigAttribute('SSLCollectorService')

    def get_RegistrationService(self):
        result = self.__getConfigAttribute('RegistrationService')
        if result == None or result == r'':
            return '/gratia-registration/register'
        else:
            return result

    def __createCertificateFile(self, keyfile, certfile):

        # Get a fresh certificate.

        # if (False):
        #  cakey = createKeyPair(crypto.TYPE_RSA, 1024)
        #  careq = createCertRequest(cakey, CN='Certificate Authority')
        #  cacert = createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*1)) # one year
        #  open(keyfile, 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cakey))
        #  open(certfile, 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert))
        #  return True
        # else:
        # Download it from the server.

        # Try this only once per run

        if isCertrequestRejected():
            return False

        # qconnection = ProxyUtil.HTTPConnection(self.get_SSLRegistrationHost(),
        #                                       http_proxy = ProxyUtil.findHTTPProxy())

        qconnection = httplib.HTTPConnection(self.get_SSLRegistrationHost())
        qconnection.connect()

        queryString = urllib.urlencode([('command', 'request'), ('from', self.get_ProbeName()), ('arg1',
                                       'not really')])
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        qconnection.request('POST', self.get_RegistrationService(), queryString, headers)
        responseString = qconnection.getresponse().read()
        resplist = responseString.split(':')
        if len(resplist) == 3 and resplist[0] == 'ok':

            # We received the info, let's store it
            # cert = crypto.load_certificate(crypto.FILETYPE_PEM,resplist[1])
            # key = crypto.load_privatekey(crypto.FILETYPE_PEM,resplist[1])

            # First create any sub-directory if needed.

            keydir = os.path.dirname(keyfile)
            if keydir != r'' and os.path.exists(keydir) == 0:
                Mkdir(keydir)
            certdir = os.path.dirname(certfile)
            if certdir != r'' and os.path.exists(certdir) == 0:
                Mkdir(certdir)

            # and then save the pem files

            open(keyfile, 'w').write(resplist[2])
            open(certfile, 'w').write(resplist[1])
        else:

            # We could do
            # os.chmod(keyfile,0600)

            DebugPrint(4, 'DEBUG: Connect: FAILED')
            DebugPrint(0, 'Error: while getting new certificate: ' + responseString)
            DebugPrintTraceback()
            setCertrequestRejected()
            return False
        return True

    def __get_fullpath_cert(self, filename):
        cdir = os.path.dirname(filename)
        if cdir != r'' or cdir == None:
            return filename
        return os.path.join(os.path.join(self.get_WorkingFolder(), 'certs'), filename)

    def get_GratiaCertificateFile(self):
        filename = self.__getConfigAttribute('GratiaCertificateFile')
        if filename == None or filename == r'':
            filename = 'gratia.probecert.pem'
        filename = self.__get_fullpath_cert(filename)
        keyfile = self.get_GratiaKeyFile()
        try:
            cryptofile = open(filename, 'r')
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cryptofile.read())
            if cert.has_expired() or os.path.exists(keyfile) == 0:
                if not self.__createCertificateFile(keyfile, filename):
                    return None
        except IOError:

            # If we can not read it, let get a new one.

            if not self.__createCertificateFile(keyfile, filename):
                return None

        return filename

    def get_GratiaKeyFile(self):
        filename = self.__getConfigAttribute('GratiaKeyFile')
        if filename == None or filename == r'':
            filename = 'gratia.probekey.pem'
        return self.__get_fullpath_cert(filename)

    def setMeterName(self, name):
        self.__ProbeName = name

    def get_MeterName(self):
        return self.get_ProbeName()

    def setProbeName(self, name):
        self.__ProbeName = name
        self.__FilenameFragment = None

    def get_ProbeName(self):
        if self.__ProbeName == None:
            result = self.__getConfigAttribute('ProbeName')
            if result == None or result == r'':
                result = self.__getConfigAttribute('MeterName')
            elif result == 'generic':

                # If ProbeName has not been changed, maybe MeterName has been

                mresult = self.__getConfigAttribute('MeterName')
                if mresult != None and mresult != r'':
                    result = mresult
            if result == None or result == r'':
                self.setProbeName(genDefaultProbeName())
                DebugPrint(0, 'INFO: ProbeName not specified in ' + self.__configname + ': defaulting to '
                           + self.__ProbeName)
            else:
                self.setProbeName(result)
        return self.__ProbeName

    def getFilenameFragment(self):
        '''Generate a filename fragment based on the collector destination'''

        if self.__FilenameFragment == None:
            fragment = self.get_ProbeName()
            if fragment:
                fragment += r'_'
            fragment += self.get_SOAPHost()
            __FilenameFragment = re.sub(r'[:/]', r'_', fragment)
        return __FilenameFragment

    def get_Grid(self):
        if self.__Grid == None:
            val = self.__getConfigAttribute('Grid')
            if val == None or val == r'':
                self.__Grid = 'OSG'
            else:
                self.__Grid = val
        return self.__Grid

    def setSiteName(self, name):
        self.__SiteName = name

    def get_SiteName(self):
        if self.__SiteName == None:
            val = self.__getConfigAttribute('SiteName')
            if val == None or val == r'':
                self.__SiteName = 'generic Site'
            else:
                self.__SiteName = val
        return self.__SiteName

    def get_UseSSL(self):
        val = self.__getConfigAttribute('UseSSL')
        if val == None or val == r'':
            return 0
        else:
            return int(val)

    def get_UseSoapProtocol(self):
        val = self.__getConfigAttribute('UseSoapProtocol')
        if val == None or val == r'':
            return 0
        else:
            return int(val)

    def get_UseGratiaCertificates(self):
        return int(self.__getConfigAttribute('UseGratiaCertificates'))

    def get_DebugLevel(self):
        if self.__DebugLevel == None:
            self.__DebugLevel = int(self.__getConfigAttribute('DebugLevel'))
        return self.__DebugLevel

    def get_LogLevel(self):
        if self.__LogLevel == None:
            val = self.__getConfigAttribute('LogLevel')
            if val == None or val == r'':
                self.__LogLevel = self.get_DebugLevel()
            else:
                self.__LogLevel = int(val)
        return self.__LogLevel

    def get_LogRotate(self):
        if self.__LogRotate == None:
            val = self.__getConfigAttribute('LogRotate')
            if val == None or val == r'':
                self.__LogRotate = 31
            else:
                self.__LogRotate = int(val)
        return self.__LogRotate

    def get_DataFileExpiration(self):
        if self.__DataFileExpiration == None:
            val = self.__getConfigAttribute('DataFileExpiration')
            if val == None or val == r'':
                self.__DataFileExpiration = 31
            else:
                self.__DataFileExpiration = int(val)
        return self.__DataFileExpiration

    def get_QuarantineSize(self):
        if self.__QuarantineSize == None:
            val = self.__getConfigAttribute('QuarantineSize')
            if val == None or val == r'':
                self.__QuarantineSize = 200 * 1000 * 1000
            else:
                self.__QuarantineSize = int(val) * 1000 * 1000
        return self.__QuarantineSize

    def get_UseSyslog(self):
        if self.__UseSyslog == None:
            val = self.__getConfigAttribute('UseSyslog')
            if val == None or val == r'':
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
        val = self.__getConfigAttribute('MaxPendingFiles')
        if val == None or val == r'':
            return 100000
        else:
            return int(val)

    def get_MaxStagedArchives(self):
        val = self.__getConfigAttribute('MaxStagedArchives')
        if val == None or val == r'':
            return 400
        else:
            return int(val)

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

    def get_CertInfoLogPattern(self):
        if self.__CertInfoLogPattern:
            return self.__CertInfoLogPattern
        val = self.__getConfigAttribute('CertInfoLogPattern')
        if val == None: val = ''
        self.__CertInfoLogPattern = val
        return self.__CertInfoLogPattern

    def get_UserVOMapFile(self):
        if self.__UserVOMapFile:
            return self.__UserVOMapFile
        val = self.__getConfigAttribute('UserVOMapFile')

        # The vestigial escape here is to prevent substitution during a
        # VDT install.

        if val and re.search("MAGIC\_VDT_LOCATION", val):
            vdttop = self.__findVDTTop()
            if vdttop != None:
                val = re.sub("MAGIC\_VDT_LOCATION", vdttop, val)
                if os.path.isfile(val):
                    self.__UserVOMapFile = val
        elif val and os.path.isfile(val):
            self.__UserVOMapFile = val
        else:

              # Invalid or missing config entry
            # Locate mapfile from osg-attributes.conf

            if val and os.path.isfile(val + '/monitoring/osg-attributes.conf'):
                try:
                    filehandle = open(val + '/monitoring/osg-attributes.conf')
                    mapMatch = re.search(r'^(?:OSG|GRID3)_USER_VO_MAP="(.*)"\s*(?:#.*)$', filehandle.read(),
                                         re.DOTALL)
                    filehandle.close()
                    if mapMatch:
                        self.__UserVOMapFile = mapMatch.group(1)
                except IOError:
                    pass
            else:

                  # Last ditch guess

                vdttop = self.__findVDTTop()
                if vdttop != None:
                    self.__UserVOMapFile = self.__findVDTTop() + '/monitoring/osg-user-vo-map.txt'
                    if not os.path.isfile(self.__UserVOMapFile):
                        self.__UserVOMapFile = self.__findVDTTop() + '/monitoring/grid3-user-vo-map.txt'
                        if not os.path.isfile(self.__UserVOMapFile):
                            self.__UserVOMapFile = None

        return self.__UserVOMapFile

    def get_SuppressUnknownVORecords(self):
        result = self.__getConfigAttribute('SuppressUnknownVORecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return None

    def get_MapUnknownToGroup(self):
        result = self.__getConfigAttribute('MapUnknownToGroup')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return None

    def get_SuppressNoDNRecords(self):
        result = self.__getConfigAttribute('SuppressNoDNRecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return None

    def get_SuppressgridLocalRecords(self):
        result = self.__getConfigAttribute('SuppressGridLocalRecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return False  # If the config entry is missing, default to false

    def get_NoCertinfoBatchRecordsAreLocal(self):
        result = self.__getConfigAttribute('NoCertinfoBatchRecordsAreLocal')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return True  # If the config entry is missing, default to true

    def get_BundleSize(self):
        global __bundleSize__
        result = self.__getConfigAttribute('BundleSize')
        if result:
            __bundleSize__ = int(result)
        elif result == None or result == r'':
            __bundleSize__ = 100
        maxpending = self.get_MaxPendingFiles()
        if __bundleSize__ > maxpending:
            __bundleSize__ = maxpending
        return __bundleSize__

    def get_ConnectionTimeout(self):
        val = self.__getConfigAttribute('ConnectionTimeout')
        if val == None or val == r'':
            return 900
        else:
            return int(val)    


class Response:

    __responseMatcherURLCheck = re.compile(r'Unknown Command: URL', re.IGNORECASE)
    __responseMatcherErrorCheck = re.compile(r'Error report</title', re.IGNORECASE)
    __BundleProblemMatcher = re.compile(r'Error: Unknown Command: multiupdate', re.IGNORECASE)
    __certRejection = 'Error: The certificate has been rejected by the Gratia Collector!'
    __responseMatcherPostTooLarge = re.compile(r'.*java.lang.IllegalStateException: Post too large.*',
                                               re.IGNORECASE)

    AutoSet = -1
    Success = 0
    Failed = 1
    CollectorError = 2
    UnknownCommand = 3
    ConnectionError = 4
    BadCertificate = 5
    BundleNotSupported = 6
    PostTooLarge = 7

    _codeString = {
        -1: 'UNSET',
        0: 'SUCCESS',
        1: 'FAILED',
        2: 'COLLECTOR_ERROR',
        3: 'UNKNOWN_COMMAND',
        4: 'CONNECTION_ERROR',
        5: 'BAD_CERTIFICATE',
        6: 'BUNDLE_NOT_SUPPORTED',
        7: 'POST TOO LARGE',
        }

    _code = -1
    _message = r''

    def __init__(self, code, message):
        global collector__wantsUrlencodeRecords

        if code == -1:
            if message == 'OK':
                self._code = Response.Success
            elif message == 'Error':

                self._code = Response.CollectorError
            elif message == None:

                self._code = Response.ConnectionError
            elif message == self.__certRejection:

                self._code = Response.BadCertificate
            elif Response.__BundleProblemMatcher.match(message):

                self._code = Response.BundleNotSupported
            elif collector__wantsUrlencodeRecords == 1 and Response.__responseMatcherURLCheck.search(message):

                self._code = Response.UnknownCommand
            elif Response.__responseMatcherPostTooLarge.search(message):

                self._code = Response.PostTooLarge
            elif Response.__responseMatcherErrorCheck.search(message):

                self._code = Response.ConnectionError
            else:

                self._code = Response.Failed
        else:

            self._code = code
        if message:
            self._message = message

    def __str__(self):
        return '(' + self.getCodeString() + r', ' + self.getMessage() + ')'

    def getCodeString(self):
        return self._codeString[self._code]

    def getCode(self):
        return self._code

    def getMessage(self):
        return str(self._message)

    def setCode(self, code):
        self._code = code

    def setMessage(self, message):
        self._message = message


# Externally accesible
RecordPid = os.getpid()
RecordId = 0
XmlRecordCheckers = []
CurrentBundle = None

# Private
__backupDirList__ = []
__outstandingRecord__ = {}
__hasMoreOutstandingRecord__ = False
__outstandingRecordCount__ = 0
__outstandingStagedRecordCount__ = 0
__outstandingStagedTarCount__ = 0
__estimatedServiceBacklog__ = 0
__maxConnectionRetries__ = 2
__maxFilesToReprocess__ = 100000
__handshakeReg__ = []
__bundleSize__ = 0
__timeout__ = 3600

# Instantiate a global connection object so it can be reused for
# the lifetime of the server Instantiate a 'connected' flag as
# well, because at times we cannot interrogate a connection
# object to see if it has been connected yet or not

__connection__ = None
__connected__ = False
__connectionError__ = False
__connectionRetries__ = 0
__certificateRejected__ = False
__certrequestRejected__ = False


def isCertrequestRejected():
    global __certrequestRejected__
    return __certrequestRejected__


def setCertrequestRejected():
    global __certrequestRejected__
    global __connectionError__
    __connectionError__ = True
    __certrequestRejected__ = True


def RegisterReporterLibrary(name, version):
    """Register the library named 'name' with version 'version'"""

    __handshakeReg__.append(('ReporterLibrary', 'version="' + version + '"', name))


def RegisterReporter(name, version):
    """Register the software named 'name' with version 'version'"""

    __handshakeReg__.append(('Reporter', 'version="' + version + '"', name))


def RegisterService(name, version):
    '''Register the service (Condor, PBS, LSF, DCache) which is being reported on '''

    __handshakeReg__.append(('Service', 'version="' + version + '"', name))

def RegisterEstimatedServiceBacklog(count):
    '''Register the estimated amount of data that the probe still have to process. '''
    '''It should be the number of records/jobs for which Send is still to be called. '''

    global __estimatedServiceBacklog__
    __estimatedServiceBacklog__ = count

def ExtractCvsRevision(revision):

    # Extra the numerical information from the CVS keyword:
    # $Revision\: $

    return revision.split('$')[1].split(':')[1].strip()


def ExtractCvsRevisionFromFile(filename):
    pipe = os.popen(r"sed -ne 's/.*\$Revision\: \([^$][^$]*\)\$.*$/\1/p' " + filename)
    result = None
    if pipe != None:
        result = string.strip(pipe.readline())
        pipe.close()
    return result


def ExtractSvnRevision(revision):

    # Extra the numerical information from the SVN keyword:
    # $Revision\: $

    return revision.split('$')[1].split(':')[1].strip()


def ExtractSvnRevisionFromFile(filename):
    pipe = os.popen(r"sed -ne 's/.*\$Revision\: \([^$][^$]*\)\$.*$/\1/p' " + filename)
    result = None
    if pipe != None:
        result = string.strip(pipe.readline())
        pipe.close()
    return result


def Initialize(customConfig='ProbeConfig'):
    '''This function initializes the Gratia metering engine'''

    global Config
    global __bundleSize__
    global __timeout__
    global CurrentBundle
    if len(__backupDirList__) == 0:

        # This has to be the first thing done (DebugPrint uses
        # the information

        Config = ProbeConfiguration(customConfig)

        DebugPrint(0, 'Initializing Gratia with ' + customConfig)

        # Initialize cleanup function.

        atexit.register(__disconnect_at_exit__)

        __bundleSize__ = Config.get_BundleSize()
        __timeout__ = Config.get_ConnectionTimeout()
        
        CurrentBundle = Bundle()

        Handshake()

        # Need to initialize the list of possible directories

        InitDirList()

        # Need to look for left over files

        SearchOutstandingRecord()

        # Attempt to reprocess any outstanding records

        Reprocess()


def Maintenance():
    '''This perform routine maintenance that is usually done at'''

    Handshake()

    # Need to look for left over files

    SearchOutstandingRecord()

    # Attempt to reprocess any outstanding records

    Reprocess()

    if __bundleSize__ > 1 and CurrentBundle.nItems > 0:
        (responseString, response) = ProcessBundle(CurrentBundle)
        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')


##
## Certificate handling routine
##


def createKeyPair(keytype, bits):
    """
    Create a public/private key pair.

    Arguments: keytype - Key type, must be one of TYPE_RSA and TYPE_DSA
               bits - Number of bits to use in the key
    Returns:   The public/private key pair in a PKey object
    """

    pkey = crypto.PKey()
    pkey.generate_key(keytype, bits)
    return pkey


def createCertRequest(pkey, digest='md5', **name):
    """
    Create a certificate request.

    Arguments: pkey   - The key to associate with the request
               digest - Digestion method to use for signing, default is md5
               **name - The name of the subject of the request, possible
                        arguments are:
                          C     - Country name
                          ST    - State or province name
                          L     - Locality name
                          O     - Organization name
                          OU    - Organizational unit name
                          CN    - Common name
                          emailAddress - E-mail address
    Returns:   The certificate request in an X509Req object
    """

    req = crypto.X509Req()
    subj = req.get_subject()
    for (key, value) in name.items():
        setattr(subj, key, value)
    req.set_pubkey(pkey)
    req.sign(pkey, digest)
    return req


def createCertificate(
    req,
    (issuerCert, issuerKey),
    serial,
    (notBefore, notAfter),
    digest='md5',
    ):
    """
    Generate a certificate given a certificate request.

    Arguments: req        - Certificate reqeust to use
               issuerCert - The certificate of the issuer
               issuerKey  - The private key of the issuer
               serial     - Serial number for the certificate
               notBefore  - Timestamp (relative to now) when the certificate
                            starts being valid
               notAfter   - Timestamp (relative to now) when the certificate
                            stops being valid
               digest     - Digest method to use for signing, default is md5
    Returns:   The signed certificate in an X509 object
    """

    cert = crypto.X509()
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(notBefore)
    cert.gmtime_adj_notAfter(notAfter)
    cert.set_issuer(issuerCert.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(issuerKey, digest)
    return cert



def escapeXML(xmlData):
##
## escapeXML
##
## Author - Tim Byrne
##
##  Replaces xml-specific characters with their substitute values.  Doing so allows an xml string
##  to be included in a web service call without interfering with the web service xml.
##
## param - xmlData:  The xml to encode
## returns - the encoded xml
##
    return xml.sax.saxutils.escape(xmlData, {"'": '&apos;', '"': '&quot;'})



__maximumDelay = 900
__initialDelay = 30
__retryDelay = __initialDelay
__backoff_factor = 2
__last_retry_time = None


def __connect():
##
## __connect
##
## Author - Tim Byrne
##
## Connect to the web service on the given server, sets the module-level object __connection__
##  equal to the new connection.  Will not reconnect if __connection__ is already connected.
##
    global __connection__
    global __connected__
    global __connectionError__
    global __certificateRejected__
    global __connectionRetries__
    global __retryDelay
    global __last_retry_time

    # __connectionError__ = True
    # return __connected__

    if __connectionError__:
        __disconnect()
        __connectionError__ = False
        if __connectionRetries__ > __maxConnectionRetries__:
            current_time = time.time()
            if not __last_retry_time:  # Set time but do not reset failures
                __last_retry_time = current_time
                return __connected__
            if current_time - __last_retry_time > __retryDelay:
                __last_retry_time = current_time
                DebugPrint(1, 'Retry connection after ', __retryDelay, 's')
                __retryDelay = __retryDelay * __backoff_factor
                if __retryDelay > __maximumDelay:
                    __retryDelay = __maximumDelay
                __connectionRetries__ = 0
        __connectionRetries__ = __connectionRetries__ + 1

    if not __connected__ and __connectionRetries__ <= __maxConnectionRetries__:
        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            DebugPrint(0, 'Error: SOAP connection is no longer supported.')
            __connectionError__ = True
            return __connected__
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:

            try:
                if ProxyUtil.findHTTPProxy():
                    DebugPrint(0, 'WARNING: http_proxy is set but not supported')

                # __connection__ = ProxyUtil.HTTPConnection(Config.get_SOAPHost(),
                #                                        http_proxy = ProxyUtil.findHTTPProxy())

                __connection__ = httplib.HTTPConnection(Config.get_SOAPHost())
            except Exception, ex:
                DebugPrint(0, 'ERROR: could not initialize HTTP connection')
                DebugPrintTraceback()
                __connectionError__ = True
                return __connected__
            try:
                prev_handler = signal.signal(signal.SIGALRM, __handle_timeout__)
                signal.alarm(__timeout__)
                DebugPrint(4, 'DEBUG: Connect')
                __connection__.connect()
                DebugPrint(4, 'DEBUG: Connect: OK')
                signal.alarm(0)
                signal.signal(signal.SIGALRM, prev_handler)
            except socket.error, ex:
                DebugPrint(3, 'Socket connection error: '+str(ex))
                __connectionError__ = True
                raise
            except GratiaTimeout:
                DebugPrint(3, 'Connection timeout (GratiaTimeout exception).')
                __connectionError__ = True
                raise                
            except Exception, ex:
                __connectionError__ = True
                DebugPrint(4, 'DEBUG: Connect: FAILED')
                DebugPrint(0, 'Error: While trying to connect to HTTP, caught exception ' + str(ex))
                DebugPrintTraceback()
                return __connected__
            DebugPrint(1, 'Connection via HTTP to: ' + Config.get_SOAPHost())
        else:

            # print "Using POST protocol"
            # assert(Config.get_UseSSL() == 1)

            if Config.get_UseGratiaCertificates() == 0:
                pr_cert_file = Config.get_CertificateFile()
                pr_key_file = Config.get_KeyFile()
            else:
                pr_cert_file = Config.get_GratiaCertificateFile()
                pr_key_file = Config.get_GratiaKeyFile()

            if pr_cert_file == None:
                DebugPrint(0, 'Error: While trying to connect to HTTPS, no valid local certificate.')
                __connectionError__ = True
                return __connected__

            DebugPrint(4, 'DEBUG: Attempting to connect to HTTPS')
            try:
                if ProxyUtil.findHTTPSProxy():
                    DebugPrint(0, 'WARNING: http_proxy is set but not supported')

                # __connection__ = ProxyUtil.HTTPSConnection(Config.get_SSLHost(),
                #                                        cert_file = pr_cert_file,
                #                                        key_file = pr_key_file,
                #                                        http_proxy = ProxyUtil.findHTTPSProxy())

                __connection__ = httplib.HTTPSConnection(Config.get_SSLHost(), cert_file=pr_cert_file,
                                                       key_file=pr_key_file)
            except Exception, ex:
                DebugPrint(0, 'ERROR: could not initialize HTTPS connection')
                DebugPrintTraceback()
                __connectionError__ = True
                return __connected__
            try:
                prev_handler = signal.signal(signal.SIGALRM, __handle_timeout__)
                signal.alarm(__timeout__)
                DebugPrint(4, 'DEBUG: Connect')
                __connection__.connect()
                DebugPrint(4, 'DEBUG: Connect: OK')
                signal.alarm(0)
                signal.signal(signal.SIGALRM, prev_handler)
            except socket.error, ex:
                __connectionError__ = True
                raise
            except GratiaTimeout:
                DebugPrint(3, 'Connection (GratiaTimeout exception).')
                __connectionError__ = True
                raise                
            except Exception, ex:
                DebugPrint(4, 'DEBUG: Connect: FAILED')
                DebugPrint(0, 'Error: While trying to connect to HTTPS, caught exception ' + str(ex))
                DebugPrintTraceback()
                __connectionError__ = True
                return __connected__
            DebugPrint(1, 'Connected via HTTPS to: ' + Config.get_SSLHost())

            # print "Using SSL protocol"
        # Successful

        DebugPrint(4, 'DEBUG: Connection SUCCESS')
        __connected__ = True

        # Reset connection retry count to 0 and the retry delay to its initial value

        __connectionRetries__ = 0
        __retryDelay = __initialDelay
    return __connected__


def __disconnect():
##
## __disconnect
##
## Author - Tim Byrne
##
## Disconnects the module-level object __connection__.
##

    global __connection__
    global __connected__
    global __connectionError__

    try:
        if __connected__ and Config.get_UseSSL() != 0:
            __connection__.close()
            DebugPrint(1, 'Disconnected from ' + Config.get_SSLHost())
    except:
        if not __connectionError__:  # We've already complained, so shut up
            DebugPrint(
                0,
                'Failed to disconnect from ' + Config.get_SSLHost() + ': ',
                sys.exc_info(),
                '--',
                sys.exc_info()[0],
                '++',
                sys.exc_info()[1],
                )

    __connected__ = False



__resending = 0

def __postRequest(connection, to, what, headers):
    """
    __postRequest calls requests on the connection to the destination 'to'
    and containing the header 'headers' and the content 'what'.
    
    The resulting information is returned as as string object.
    In case of connection time, the excetion GratiaTimeout is raised.
    """
    
    prev_handler = signal.signal(signal.SIGALRM, __handle_timeout__)
    signal.alarm(__timeout__)
    
    DebugPrint(4, 'DEBUG: POST')
    connection.request('POST', to, what, headers)
    DebugPrint(4, 'DEBUG: POST: OK')
    DebugPrint(4, 'DEBUG: Read response')
    responseString = connection.getresponse().read()
    DebugPrint(4, 'DEBUG: Read response: OK')
    
    signal.alarm(0)
    signal.signal(signal.SIGALRM, prev_handler)
    
    return responseString

def __sendUsageXML(meterId, recordXml, messageType='URLEncodedUpdate'):
    """
    sendUsageXML
   
    Author - Tim Byrne

    Contacts the 'GratiaCollector' web service, sending it an xml representation of Usage data
 
    param - meterId:  A unique Id for this meter, something the web service can use to identify 
          communication from this meter
    param - xmlData:  A string representation of usage xml
    """

    global __connection__
    global __connectionError__
    global __certificateRejected__
    global __connectionRetries__
    global collector__wantsUrlencodeRecords
    global __resending

    # Backward compatibility with old collectors

    if collector__wantsUrlencodeRecords == 0:
        messageType = 'update'

    try:

        # Connect to the web service, in case we aren't already
        # connected.  If we are already connected, this call will do
        # nothing

        if not __connect():  # Failed to connect
            raise IOError  # Kick out to except: clause

        # Generate a unique Id for this transaction

        transactionId = meterId + TimeToString().replace(':', r'')
        DebugPrint(3, 'TransactionId:  ' + transactionId)

        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:

            DebugPrint(0, 'Error: SOAP connection is no longer supported.')
            __connectionError__ = True

            response = Response(Response.Failed, 'Error: SOAP connection is no longer supported.')
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:
            queryString = __encodeData(messageType, recordXml)

            # Attempt to make sure Collector can actually read the post.

            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            
            responseString = __postRequest(__connection__, Config.get_CollectorService(), queryString, headers)
            
            response = Response(Response.AutoSet, responseString)
            if response.getCode() == Response.UnknownCommand:

                # We're talking to an old collector

                DebugPrint(0,
                           'Unable to send new record to old collector -- engaging backwards-compatible mode for remainder of connection'
                           )
                collector__wantsUrlencodeRecords = 0

                # Try again with the same record before returning to the
                # caller. There will be no infinite recursion because
                # __url_records has been reset

                response = __sendUsageXML(meterId, recordXml, messageType)
        else:

              # SSL

            DebugPrint(4, 'DEBUG: Encoding data for SSL transmission')
            queryString = __encodeData(messageType, recordXml)
            DebugPrint(4, 'DEBUG: Encoding data for SSL transmission: OK')

            # Attempt to make sure Collector can actually read the post.

            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            responseString = __postRequest(__connection__, Config.get_SSLCollectorService(), queryString, headers)
            response = Response(Response.AutoSet, responseString)

            if response.getCode() == Response.UnknownCommand:

                # We're talking to an old collector

                DebugPrint(0,
                           'Unable to send new record to old collector -- engaging backwards-compatible mode for remainder of connection'
                           )
                collector__wantsUrlencodeRecords = 0

                # Try again with the same record before returning to the
                # caller. There will be no infinite recursion because
                # __url_records has been reset

                response = __sendUsageXML(meterId, recordXml, messageType)
            elif response.getCode() == Response.BadCertificate:
                __connectionError__ = True
                __certificateRejected__ = True
                response = Response(Response.AutoSet, responseString)

        if response.getCode == Response.ConnectionError or response.getCode == Response.CollectorError:

            # Server threw an error - 503, maybe?

            __connectionError__ = True
            response = Response(Response.Failed, r'Server unable to receive data: save for reprocessing')
    except SystemExit:

        raise
    except socket.error, ex:
        if ex.args[0] == 111:
            DebugPrint(0, 'Connection refused while attempting to send xml to web service')
        else:
            DebugPrint(0, 'Failed to send xml to web service due to an error of type "', sys.exc_info()[0],
                       '": ', sys.exc_info()[1])
            DebugPrintTraceback(1)
        response = Response(Response.Failed, r'Server unable to receive data: save for reprocessing')
    except GratiaTimeout, ex:
        __connectionError__ = True
        if not __resending:
            DebugPrint(0, 'Connection timeout.  Will now attempt to re-establish connection and send record.')
            DebugPrint(2, 'Timeout seen as a GratiaTimeout.')
            __resending = 1
            response = __sendUsageXML(meterId, recordXml, messageType)
        else:
            DebugPrint(0, 'Received GratiaTimeout exception:')
            DebugPrintTraceback(1)
            response = Response(Response.Failed, 'Failed to send xml to web service')
    except httplib.BadStatusLine, ex:
        __connectionError__ = True
        if ex.args[0] == r'' and not __resending:
            DebugPrint(0, 'Possible connection timeout.  Will now attempt to re-establish connection and send record.')
            DebugPrint(2, 'Timeout seen as a BadStatusLine exception with the following argument:', ex.args)
            __resending = 1
            response = __sendUsageXML(meterId, recordXml, messageType)
        else:
            DebugPrint(0, 'Received BadStatusLine exception:', ex.args)
            DebugPrintTraceback(1)
            response = Response(Response.Failed, 'Failed to send xml to web service')
    except:
        DebugPrint(0, 'Failed to send xml to web service due to an error of type "', sys.exc_info()[0], '": ',
                   sys.exc_info()[1])
        DebugPrintTraceback(1)

        # Upon a connection error, we will stop to try to reprocess but will continue to
        # try sending

        __connectionError__ = True
        response = Response(Response.Failed, 'Failed to send xml to web service')

    __resending = 0
    DebugPrint(2, 'Response: ' + str(response))
    return response


def SendStatus(meterId):

    # This function is not yet used.
    # Use Handshake() and SendHandshake() instead.

    global __connection__
    global __connectionError__
    global __connectionRetries__

    try:

        # Connect to the web service, in case we aren't already
        # connected.  If we are already connected, this call will do
        # nothing

        if not __connect():  # Failed to connect
            raise IOError  # Kick out to except: clause

        # Generate a unique Id for this transaction

        transactionId = meterId + TimeToString().replace(':', r'')
        DebugPrint(1, 'Status Upload:  ' + transactionId)

        queryString = __encodeData('handshake', 'probename=' + meterId)
        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            response = Response(Response.Success, 'Status message not supported in SOAP mode')
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:

            responseString = __postRequest(__connection__, Config.get_CollectorService(), queryString)
            response = Response(Response.AutoSet, responseString)
        else:
            responseString = __postRequest(__connection__, Config.get_SSLCollectorService(), queryString)
            response = Response(Response.AutoSet, responseString)
    except SystemExit:
        raise
    except socket.error, ex:
        if ex.args[0] == 111:
            DebugPrint(0, 'Connection refused while attempting to send xml to web service')
        else:
            DebugPrint(0, 'Failed to send xml to web service due to an error of type "', sys.exc_info()[0],
                       '": ', sys.exc_info()[1])
            DebugPrintTraceback(1)
    except:
        DebugPrint(0, 'Failed to send xml to web service due to an error of type "', sys.exc_info()[0], '": ',
                   sys.exc_info()[1])
        DebugPrintTraceback(1)

        # Upon a connection error, we will stop to try to reprocess but will continue to
        # try sending

        __connectionError__ = True

        response = Response(Response.Failed, 'Failed to send xml to web service')

    return response


__logFileIsWriteable__ = True


def LogFileName():
    '''Return the name of the current log file'''

    filename = time.strftime('%Y-%m-%d') + '.log'
    return os.path.join(Config.get_LogFolder(), filename)


def LogToFile(message):
    '''Write a message to the Gratia log file'''

    global __logFileIsWriteable__
    current_file = None
    filename = 'none'

    try:

        # Ensure the 'logs' folder exists

        if os.path.exists(Config.get_LogFolder()) == 0:
            Mkdir(Config.get_LogFolder())

        filename = time.strftime('%Y-%m-%d') + '.log'
        filename = os.path.join(Config.get_LogFolder(), filename)

        if os.path.exists(filename) and not os.access(filename, os.W_OK):
            os.chown(filename, os.getuid(), os.getgid())
            os.chmod(filename, 0755)

        # Open/Create a log file for today's date

        current_file = open(filename, 'a')

        # Append the message to the log file

        current_file.write(message + '\n')

        __logFileIsWriteable__ = True
    except:
        if __logFileIsWriteable__:

            # Print the error message only once

            print >> sys.stderr, 'Gratia: Unable to log to file:  ', filename, ' ', sys.exc_info(), '--', \
                sys.exc_info()[0], '++', sys.exc_info()[1]
        __logFileIsWriteable__ = False

    if current_file != None:

        # Close the log file

        current_file.close()


def LogToSyslog(level, message):
    global __logFileIsWriteable__
    import syslog
    if level == -1:
        syslevel = syslog.LOG_ERR
    else:
        if level == 0:
            syslevel = syslog.LOG_INFO
        else:
            if level == 1:
                syslevel = syslog.LOG_INFO
            else:
                syslevel = syslog.LOG_DEBUG

    try:
        syslog.openlog('Gratia ')
        syslog.syslog(syslevel, message)

        __logFileIsWriteable__ = True
    except:
        if __logFileIsWriteable__:

            # Print the error message only once

            print >> sys.stderr, 'Gratia: Unable to log to syslog:  ', sys.exc_info(), '--', sys.exc_info()[0], \
                '++', sys.exc_info()[1]
        __logFileIsWriteable__ = False

    syslog.closelog()


def RemoveFile(filename):

    # Remove the file, ignore error if the file is already gone.

    result = True
    try:
        os.remove(filename)
    except os.error, err:
        if err.errno == errno.ENOENT:
            result = False
        else:
            raise err
    return result


def RemoveDir(dirname):

   # Remove the file, ignore error if the file is already gone.

    try:
        os.rmdir(dirname)
    except os.error, err:
        if err.errno == errno.ENOENT:
            pass
        else:
            raise err


def QuarantineFile(filename, isempty):

   # If we have trouble with a file, let's quarantine it
   # If the quarantine reason is 'only' that the file is empty,
   # list the file as such.

    dirname = os.path.dirname(filename)
    pardirname = os.path.dirname(dirname)
    if os.path.basename(dirname) != 'outbox':
        toppath = dirname
    else:
        if os.path.basename(pardirname) == 'staged':
            toppath = os.path.dirname(pardirname)
        else:
            toppath = pardirname
    quarantine = os.path.join(toppath, 'quarantine')
    Mkdir(quarantine)
    DebugPrint(0, 'Putting a quarantine file in: ' + quarantine)
    DebugPrint(3, 'Putting a file in quarantine: ' + os.path.basename(filename))
    if isempty:
        try:
            emptyfiles = open(os.path.join(quarantine, 'emptyfile'), 'a')
            emptyfiles.write(filename + '\n')
            emptyfiles.close()
        except:
            DebugPrint(
                0,
                'failed to record that file was empty: ',
                filename,
                '--',
                sys.exc_info(),
                '--',
                sys.exc_info()[0],
                '++',
                sys.exc_info()[1],
                )
    else:
        shutil.copy2(filename, os.path.join(quarantine, os.path.basename(filename)))
    RemoveRecordFile(filename)


def RemoveRecordFile(filename):
   # Remove a record file and reduce the oustanding record count

   global __outstandingRecordCount__
   global __outstandingStagedRecordCount__

   if RemoveFile(filename):
      # Decrease the count only if the file was really removed

      dirname = os.path.dirname(filename)
      if os.path.basename(dirname) == 'outbox' and os.path.basename(os.path.dirname(dirname)) == 'staged':
         DebugPrint(3, 'Remove the staged record: ' + filename)
         __outstandingStagedRecordCount__ += -1
      else:
         __outstandingRecordCount__ += -1
         DebugPrint(3, 'Remove the record: ' + filename)


def RemoveOldFiles(nDays=31, globexp=None, req_maxsize=0):

    if not globexp:
        return

    # Get the list of all files in the log directory

    files = glob.glob(globexp)
    if not files:
        return

    DebugPrint(3, ' Will check the files: ', files)

    cutoff = time.time() - nDays * 24 * 3600

    totalsize = 0

    date_file_list = []
    for oldfile in files:
        lastmod_date = os.path.getmtime(oldfile)
        if lastmod_date < cutoff:
            DebugPrint(2, 'Will remove: ' + oldfile)
            RemoveFile(oldfile)
        else:
            size = os.path.getsize(oldfile)
            totalsize += size
            date_file_tuple = (lastmod_date, size, oldfile)
            date_file_list.append(date_file_tuple)

    if len(date_file_list) == 0:

       # No more files.

        return

    dirname = os.path.dirname(date_file_list[0][2])
    statfs = os.statvfs(dirname)
    disksize = statfs.f_blocks
    freespace = statfs.f_bfree
    ourblocks = totalsize / statfs.f_frsize
    percent = ourblocks * 100.0 / disksize

    if percent < 1:
        DebugPrint(1, dirname + ' uses ' + niceNum(percent, 1e-3) + '% and there is ' + niceNum(freespace * 100
                   / disksize) + '% free')
    else:
        DebugPrint(1, dirname + ' uses ' + niceNum(percent, 0.10000000000000001) + '% and there is '
                   + niceNum(freespace * 100 / disksize) + '% free')

    minfree = 0.10000000000000001 * disksize  # We want the disk to be no fuller than 95%
    # We want the directory to not be artificially reduced below 5% because other things are filling up the disk.
    minuse = 0.05 * disksize  
    calc_maxsize = req_maxsize
    if freespace < minfree:

       # The disk is quite full

        if ourblocks > minuse:

          # We already use more than 5%, let's see how much we can delete to get under 95% full but not under 5% of
          # our own use

            target = minfree - freespace  # We would like to remove than much

            if ourblocks - target < minuse:

             # But it would take us under 5%, so do what we can

                calc_maxsize = minuse
            else:
                calc_maxsize = ourblocks - target

            if 0 < req_maxsize and req_maxsize < calc_maxsize * statfs.f_frsize:
                calc_maxsize = req_maxsize
            else:
                DebugPrint(4,
                           "DEBUG: The disk is quite full and this directory is 'large' attempting to reduce from "
                            + niceNum(totalsize / 1000000) + 'Mb to ' + niceNum(calc_maxsize / 1000000) + 'Mb.')
                calc_maxsize = calc_maxsize * statfs.f_frsize

    if calc_maxsize > 0 and totalsize > calc_maxsize:
        DebugPrint(1, 'Cleaning up directory due to space overflow: ' + niceNum(totalsize / 1e6,
                   0.10000000000000001), 'Mb for a limit of ', niceNum(calc_maxsize / 1e6,
                   0.10000000000000001), ' Mb.')
        calc_maxsize = 0.8 * calc_maxsize
        date_file_list.sort()

       # To get the newest first (for debugging purpose only)
       # date_file_list.reverse()

        currentLogFile = LogFileName()
        for file_tuple in date_file_list:
            DebugPrint(2, 'Will remove: ' + file_tuple[2])
            RemoveFile(file_tuple[2])
            totalsize = totalsize - file_tuple[1]
            if currentLogFile == file_tuple[2]:

             # We delete the current log file! Let's record this explicitly!

                DebugPrint(0, 'EMERGENCY DELETION AND TRUNCATION OF LOG FILES.')
                DebugPrint(0, 'Current log file was too large: ' + niceNum(file_tuple[1] / 1000000) + 'Mb.')
                DebugPrint(0, 'All prior information has been lost.')
            if totalsize < calc_maxsize:
                return


def RemoveOldBackups(nDays=31):
#
# Remove old backups
#
# Remove any backup older than the request number of days
#
# Parameters
#   nDays - remove file older than 'nDays' (default 31)
#

    backupDir = Config.get_PSACCTBackupFileRepository()
    DebugPrint(1, ' Removing Gratia data backup files older than ', nDays, ' days from ', backupDir)
    RemoveOldFiles(nDays, os.path.join(backupDir, '*.log'))


def RemoveOldLogs(nDays=31):
    logDir = Config.get_LogFolder()
    DebugPrint(1, 'Removing log files older than ', nDays, ' days from ', logDir)
    RemoveOldFiles(nDays, os.path.join(logDir, '*.log'))


def RemoveOldJobData(nDays=31):
    dataDir = Config.get_DataFolder()
    DebugPrint(1, 'Removing incomplete data files older than ', nDays, ' days from ', dataDir)
    RemoveOldFiles(nDays, os.path.join(dataDir, 'gratia_certinfo_*'))
    RemoveOldFiles(nDays, os.path.join(dataDir, 'gratia_condor_log*'))
    RemoveOldFiles(nDays, os.path.join(dataDir, 'gram_condor_log*'))


def RemoveOldQuarantine(nDays=31, maxSize=200):

    # Default to 31 days or 200Mb whichever is lower.

    global __backupDirList__
    global Config

    RemoveOldFiles(nDays, os.path.join(os.path.join(Config.get_DataFolder(),"quarantine"),"*"))
    fragment = Config.getFilenameFragment()
    for current_dir in __backupDirList__:
        gratiapath = os.path.join(current_dir, 'gratiafiles')
        subpath = os.path.join(gratiapath, 'subdir.' + fragment)
        quarantine = os.path.join(subpath, 'quarantine')
        if os.path.exists(quarantine):
            DebugPrint(1, 'Removing quarantines data files older than ', nDays, ' days from ', quarantine)
            RemoveOldFiles(nDays, os.path.join(quarantine, '*'), maxSize)


def GenerateOutput(prefix, *arg):
    out = prefix
    for val in arg:
        out = out + str(val)
    return out


def DebugPrint(level, *arg):
    if quiet:
        return
    try:
        if not Config or level < Config.get_DebugLevel():
            out = time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + ' ' + GenerateOutput('Gratia: ',
                    *arg)
            print >> sys.stderr, out
        if Config and level < Config.get_LogLevel():
            out = GenerateOutput('Gratia: ', *arg)
            if Config.get_UseSyslog():
                LogToSyslog(level, GenerateOutput(r'', *arg))
            else:
                LogToFile(time.strftime(r'%H:%M:%S %Z', time.localtime()) + ' ' + out)
    except:
        out = time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + ' ' \
            + GenerateOutput('Gratia: printing failed message: ', *arg)
        sys.stderr.write(out + '\n')
        sys.exit()


def Error(*arg):
    out = GenerateOutput('Error in Gratia probe: ', *arg)
    print >> sys.stderr, time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + ' ' + out
    if Config.get_UseSyslog():
        LogToSyslog(-1, GenerateOutput(r'', *arg))
    else:
        LogToFile(time.strftime(r'%H:%M:%S %Z', time.localtime()) + ' ' + out)


# Returns a nicely formatted string for the floating point number
# provided.  This number will be rounded to the supplied accuracy
# and commas and spaces will be added.  I think every language should
# do this for numbers.  Why don't they?  Here are some examples:
# >>> print niceNum(123567.0, 1000)
# 124,000
# >>> print niceNum(5.3918e-07, 1e-10)
# 0.000 000 539 2
# This kind of thing is wonderful for producing tables for
# human consumption.
#


def niceNum(num, precision=1):
    """Returns a string representation for a floating point number
    that is rounded to the given precision and displayed with
    commas and spaces."""

    accpow = int(math.floor(math.log10(precision)))
    if num < 0:
        digits = int(math.fabs(num / pow(10, accpow) - 0.5))
    else:
        digits = int(math.fabs(num / pow(10, accpow) + 0.5))
    result = r''
    if digits > 0:
        for i in range(0, accpow):
            if i % 3 == 0 and i > 0:
                result = '0,' + result
            else:
                result = '0' + result
        curpow = int(accpow)
        while digits > 0:
            adigit = chr(digits % 10 + ord('0'))
            if curpow % 3 == 0 and curpow != 0 and len(result) > 0:
                if curpow < 0:
                    result = adigit + ' ' + result
                else:
                    result = adigit + ',' + result
            elif curpow == 0 and len(result) > 0:
                result = adigit + '.' + result
            else:
                result = adigit + result
            digits = digits / 10
            curpow = curpow + 1
        for i in range(curpow, 0):
            if i % 3 == 0 and i != 0:
                result = '0 ' + result
            else:
                result = '0' + result
        if curpow <= 0:
            result = '0.' + result
        if num < 0:
            result = '-' + result
    else:
        result = '0'
    return result


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
        raise OSError("a file with the same name as the desired dir, '%s', already exists." % newdir)
    else:
        (head, tail) = os.path.split(newdir)
        if head and not os.path.isdir(head):
            Mkdir(head)

        # Mkdir can not use DebugPrint since it is used
        # while trying to create the log file!
        # print "Mkdir %s" % repr(newdir)

        if tail:
            os.mkdir(newdir)


def DirListAdd(value):
    '''Utility method to add directory to the list of directories'''

    if len(value) > 0 and value != 'None':
        __backupDirList__.append(value)


def InitDirList():
    '''Initialize the list of backup directories'''

    Mkdir(Config.get_WorkingFolder())

    DirListAdd(Config.get_WorkingFolder())
    DebugPrint(1, 'List of backup directories: ', __backupDirList__)


def AddOutstandingRecord(filename):
    '''Add the file to the outstanding list, unless it is'''

    if not (__bundleSize__ > 1 and CurrentBundle.hasFile(filename)):
        __outstandingRecord__[filename] = 1


def ListOutstandingRecord(dirname, isstaged):
    '''Put in OustandingRecord the name of the file in dir, if any'''
    '''Return true if reach the maximum number of files'''

    global __outstandingStagedRecordCount__
    global __outstandingRecordCount__

    if not os.path.exists(dirname):
        return False

    files = os.listdir(dirname)
    nfiles = len(files)
    DebugPrint(4, 'DEBUG: ListOutstanding for ' + dirname + ' adding ' + str(nfiles))
    if isstaged:
        __outstandingStagedRecordCount__ += nfiles
    else:
        __outstandingRecordCount__ += nfiles
    for f in files:
        AddOutstandingRecord(os.path.join(dirname, f))
        if len(__outstandingRecord__) >= __maxFilesToReprocess__:
            return True
    return False


def SearchOutstandingRecord():
    '''Search the list of backup directories for'''

    global __hasMoreOutstandingRecord__
    global __outstandingRecordCount__
    global __outstandingStagedTarCount__
    global __outstandingStagedRecordCount__

    __outstandingRecord__.clear()
    __outstandingRecordCount__ = 0
    __outstandingStagedTarCount__ = 0
    __outstandingStagedRecordCount__ = 0

    fragment = Config.getFilenameFragment()

    DebugPrint(4, 'DEBUG: Starting SearchOutstandingRecord')
    for current_dir in __backupDirList__:
        DebugPrint(4, 'DEBUG: SearchOutstandingRecord ' + current_dir)
        DebugPrint(4, 'DEBUG: Middle of SearchOutstandingRecord outbox:' + str(__outstandingRecordCount__)
                   + ' staged outbox:' + str(__outstandingStagedRecordCount__) + ' tarfiles:'
                   + str(__outstandingStagedTarCount__))

        gratiapath = os.path.join(current_dir, 'gratiafiles')
        subpath = os.path.join(gratiapath, 'subdir.' + fragment)
        outbox = os.path.join(subpath, 'outbox')
        staged = os.path.join(subpath, 'staged')
        stagedoutbox = os.path.join(subpath, 'staged', 'outbox')

        # For backward compatibility still look for the records in the top level
        # gratiafiles directories.

        path = os.path.join(gratiapath, 'r*.' + Config.get_GratiaExtension())
        files = glob.glob(path) + glob.glob(path + '__*')
        DebugPrint(4, 'DEBUG: Search add ' + str(len(files)) + ' for ' + path)
        __outstandingRecordCount__ += len(files)
        for f in files:

            # Legacy reprocess files or ones with the correct fragment

            if re.search(r'/?r(?:[0-9]+)?\.?[0-9]+(?:\.' + fragment + r')?\.' + Config.get_GratiaExtension()
                         + r'(?:__.{10})?$', f):
                AddOutstandingRecord(f)
                if len(__outstandingRecord__) >= __maxFilesToReprocess__:
                    break

        # Record the number of tar file already on disk.

        stagedfiles = glob.glob(os.path.join(staged, 'store', 'tz.*'))
        __outstandingStagedTarCount__ += len(stagedfiles)

        if len(__outstandingRecord__) >= __maxFilesToReprocess__:
            break

        # Now look for the record in the probe specific subdirectory.

        if ListOutstandingRecord(outbox, False):
            break
        prevOutstandingStagedRecordCount = __outstandingStagedRecordCount__
        if ListOutstandingRecord(stagedoutbox, True):
            break

        # If total number of outstanding files is less than the number of files already in the bundle,
        # Let's decompress one of the tar file (if any)

        needmorefiles = __outstandingStagedRecordCount__ == 0 or \
            __outstandingRecordCount__ + __outstandingStagedRecordCount__ <= CurrentBundle.nFiles
        if needmorefiles and len(stagedfiles) > 0:

            # the staged/outbox is low on files and we have some staged tar files

            in_stagedoutbox = __outstandingStagedRecordCount__ - prevOutstandingStagedRecordCount
            if in_stagedoutbox != 0 and CurrentBundle.nFiles > 0:
                # This staged outbox is not empty, so let's first empty it.
                (responseString, response) = ProcessBundle(CurrentBundle)
                DebugPrint(0, responseString)
                DebugPrint(0, '***********************************************************')
                if CurrentBundle.nItems > 0:
                    # The upload did not work, there is no need to proceed with the record collection
                    break

            # The staged outbox is empty, we can safely untar the file without risking over-writing
            # a files.
            stagedfile = stagedfiles[0]
            if UncompressOutbox(stagedfile, stagedoutbox):
                RemoveFile(stagedfile)
            else:
                Mkdir(os.path.join(staged, 'quarantine'))
                os.rename(stagedfile, os.path.join(staged, 'quarantine', os.path.basename(stagedfile)))

            __outstandingStagedTarCount__ += -1
            __outstandingStagedRecordCount__ = prevOutstandingStagedRecordCount
            if ListOutstandingRecord(stagedoutbox, True):
                break

    # Mark that we probably have more outstanding record to look at.

    __hasMoreOutstandingRecord__ = __outstandingStagedTarCount__ > 0 or len(__outstandingRecord__) >= __maxFilesToReprocess__

    DebugPrint(4, 'DEBUG: List of Outstanding records: ', __outstandingRecord__.keys())
    DebugPrint(4, 'DEBUG: After SearchOutstandingRecord outbox:' + str(__outstandingRecordCount__)
               + ' staged outbox:' + str(__outstandingStagedRecordCount__) + ' tarfiles:'
               + str(__outstandingStagedTarCount__))


def GenerateFilename(prefix, current_dir):
    '''Generate a filename of the for current_dir/prefix.$pid.ConfigFragment.gratia.xml__Unique'''

    filename = prefix + str(RecordPid) + '.' + Config.getFilenameFragment() + '.' + Config.get_GratiaExtension() \
        + '__XXXXXXXXXX'
    filename = os.path.join(current_dir, filename)
    mktemp_pipe = os.popen('mktemp -q "' + filename + '"')
    if mktemp_pipe != None:
        filename = mktemp_pipe.readline()
        mktemp_pipe.close()
        filename = string.strip(filename)
        if filename != r'':
            return filename

    raise IOError


def UncompressOutbox(staging_name, target_dir):

    # Compress the probe_dir/outbox and stored the resulting tar.gz file
    # in probe_dir/staged

    # staged_dir = os.path.join(probe_dir,"staged")
    # outbox = os.path.join(probe_dir,"outbox")

    DebugPrint(1, 'Uncompressing: ' + staging_name)
    try:
        tar = tarfile.open(staging_name, 'r')
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while opening tar file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        for tarinfo in tar:
            DebugPrint(1, 'Extracting: ' + tarinfo.name)
            tar.extract(tarinfo, target_dir)
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while extracting from tar file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        tar.close()
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while closing tar file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    return True


def CompressOutbox(probe_dir, outbox, outfiles):

    # Compress the probe_dir/outbox and stored the resulting tar.gz file
    # in probe_dir/staged

    global __outstandingStagedTarCount__

    staged_store = os.path.join(probe_dir, 'staged', 'store')
    Mkdir(staged_store)

    staging_name = GenerateFilename('tz.', staged_store)
    DebugPrint(1, 'Compressing outbox in tar.bz2 file: ' + staging_name)

    try:
        tar = tarfile.open(staging_name, 'w:bz2')
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while opening tar.bz2 file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        for f in outfiles:

            # Reduce the size of the file name in the archive

            arcfile = f.replace(Config.getFilenameFragment(), r'')
            arcfile = arcfile.replace('..', '.')
            tar.add(os.path.join(outbox, f), arcfile)
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while adding ' + f + ' from ' + outbox + ' to tar.bz2 file: '
                   + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        tar.close()
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while closing tar.bz2 file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    __outstandingStagedTarCount__ += 1
    return True


def OpenNewRecordFile(dirIndex):

    # The file name will be r$pid.ConfigFragment.gratia.xml__UNIQUE

    global __outstandingRecordCount__
    DebugPrint(3, 'Open request: ', dirIndex)
    index = 0
    toomanyfiles = __outstandingRecordCount__ >= Config.get_MaxPendingFiles()
    toomanystaged = __outstandingStagedTarCount__ >= Config.get_MaxStagedArchives()

    if not toomanyfiles or not toomanystaged:
        for current_dir in __backupDirList__:
            index = index + 1
            if index <= dirIndex or not os.path.exists(current_dir):
                continue
            DebugPrint(3, 'Open request: looking at ', current_dir)
            current_dir = os.path.join(current_dir, 'gratiafiles')
            probe_dir = os.path.join(current_dir, 'subdir.' + Config.getFilenameFragment())
            working_dir = os.path.join(probe_dir, 'outbox')
            if toomanyfiles:
                if not os.path.exists(working_dir):
                    continue

                # Need to find and pack the full outbox

                outfiles = os.listdir(working_dir)
                if len(outfiles) == 0:
                    continue

                if CompressOutbox(probe_dir, working_dir, outfiles):

                    # then delete the content
                    for f in os.listdir(working_dir):
                        RemoveRecordFile(os.path.join(working_dir, f))
                        
                    # And reset the Bundle if needed.
                    if CurrentBundle.nItems > 0:
                       hasHandshake = CurrentBundle.nHandshakes > 0
                       CurrentBundle.clear()
                       if hasHandshake:
                          Handshake()
                else:
                    continue

                # and retry

                toomanyfiles = __outstandingRecordCount__ >= Config.get_MaxPendingFiles()
                if toomanyfiles:

                    # We did not suppress enough file, let's go on

                    continue

            if not os.path.exists(working_dir):
                try:
                    Mkdir(working_dir)
                except:
                    continue
            if not os.path.exists(working_dir):
                continue
            if not os.access(working_dir, os.W_OK):
                continue
            try:
                filename = GenerateFilename('r.', working_dir)
                DebugPrint(3, 'Creating file:', filename)
                __outstandingRecordCount__ += 1
                f = open(filename, 'w')
                dirIndex = index
                return (f, dirIndex)
            except:
                continue
    else:
        DebugPrint(0, 'DEBUG: Too many pending files, the record has not been backed up')
    f = sys.stdout
    dirIndex = index
    return (f, dirIndex)


def TimeToString(targ=None):
    ''' Return the XML version of the given time.  Default to the current time '''
    if not targ:
        targ = time.gmtime()
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', targ)


class Record(object):

    '''Base class for the Gratia Record'''

    # List the damember for documentation purpose only,
    # We do not want 'class-wide' variables
    # XmlData = []
    # RecordData = []
    # TransientInputFiles = []

    # __ProbeName = r''
    # __ProbeNameDescription = r''
    # __SiteName = r''
    # __SiteNameDescription = r''
    # __Grid = r''
    # __GridDescription = r''

    def __init__(self):

        # See the function ResourceType for details on the
        # parameter
	if not Config:
		DebugPrint(0,"Error: Configuration is not initialized")
		raise InternalError("Configuration is not initialized") 

        DebugPrint(2, 'Creating a Record ' + TimeToString())
        self.XmlData = []
        self.__ProbeName = Config.get_ProbeName()
        self.__ProbeNameDescription = r''
        self.__SiteName = Config.get_SiteName()
        self.__SiteNameDescription = r''
        self.__Grid = Config.get_Grid()
        self.__GridDescription = r''
        self.RecordData = []
        self.TransientInputFiles = []

    def Print(self):
        DebugPrint(3, 'Usage Record: ', self)

    def VerbatimAppendToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        where.append('<' + what + ' ' + comment + '>' + value + '</' + what + '>')
        return where

    def VerbatimAddToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        # First filter out the previous value

        where = [x for x in where if x.find('<' + what) != 0]
        return self.VerbatimAppendToList(where, what, comment, value)

    def AddToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        return self.VerbatimAddToList(where, what, comment, escapeXML(value))

    def AppendToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        return self.VerbatimAppendToList(where, what, comment, escapeXML(value))

    def GenericAddToList(
        self,
        xmlelem,
        value,
        description=r'',
        ):
        self.RecordData = self.AddToList(self.RecordData, xmlelem, self.Description(description), value)

    def XmlAddMembers(self):
        self.GenericAddToList('ProbeName', self.__ProbeName, self.__ProbeNameDescription)
        self.GenericAddToList('SiteName', self.__SiteName, self.__SiteNameDescription)
        self.GenericAddToList('Grid', self.__Grid, self.__GridDescription)

    def Duration(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        seconds = long(value * 100) % 6000 / 100.0
        value = long((value - seconds) / 60)
        minutes = value % 60
        value = (value - minutes) / 60
        hours = value % 24
        value = (value - hours) / 24
        result = 'P'
        if value > 0:
            result = result + str(value) + 'D'
        if hours > 0 or minutes > 0 or seconds > 0:
            result = result + 'T'
            if hours > 0:
                result = result + str(hours) + 'H'
            if minutes > 0:
                result = result + str(minutes) + 'M'
            if seconds > 0:
                result = result + str(seconds) + 'S'
        else:
            result = result + 'T0S'
        return result

    def Description(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if len(value) > 0:
            return 'urwg:description="' + escapeXML(value) + '" '
        else:
            return r''

    def ProbeName(self, value, description=r''):
        self.__ProbeName = value
        self.__ProbeNameDescription = description

    def SiteName(self, value, description=r''):
        ''' Indicates which site the service accounted for belong to'''

        self.__SiteName = value
        self.__SiteNameDescription = description

    def Grid(self, value, description=r''):
        ''' Indicates which grid the service accounted for belong to'''

        self.__Grid = value
        self.__GridDescription = description
        
    def AddTransientInputFile(self, filename):
        ''' Register a file that should be deleted if the record has been properly processed '''
       
        DebugPrint(1, 'Registering transient input file: '+filename)
        self.TransientInputFiles.append(filename)
        
    def QuarantineTransientInputFiles(self):
        ''' Copy to a quarantine directories any of the input files '''
        
        quarantinedir = os.path.join(Config.get_DataFolder(),"quarantine")
        Mkdir(quarantinedir)
        for filename in self.TransientInputFiles:
            DebugPrint(1, 'Moving transient input file: '+filename+' to quarantine in '+quarantinedir)
            shutil.copy2(filename,quarantinedir)
            RemoveFile(filename)
        self.TransientInputFiles = []
        
    def RemoveTransientInputFiles(self):
        ''' Delete all the transient input files. '''

        for filename in self.TransientInputFiles:
            DebugPrint(1, 'Deleting transient input file: '+filename)
            RemoveFile(filename)
        self.TransientInputFiles = []

class ProbeDetails(Record):

#    ProbeDetails

    def __init__(self):

        # Initializer

        super(self.__class__, self).__init__()
        DebugPrint(1, 'Creating a ProbeDetails record ' + TimeToString())

        self.__ProbeDetails__ = []

        # Extract the revision number

        rev = ExtractSvnRevision('$Revision: 3997 $')

        self.ReporterLibrary('Gratia', rev)

        for data in __handshakeReg__:
            self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, data[0], data[1], data[2])

    def ReporterLibrary(self, name, version):
        self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, 'ReporterLibrary', 'version="' + version + '"'
                                              , name)

    def Reporter(self, name, version):
        self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, 'Reporter', 'version="' + version + '"', name)

    def Service(self, name, version):
        self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, 'Service', 'version="' + version + '"', name)

    def XmlAddMembers(self):
        """ This should add the value of the 'data' member of ProbeDetails """

        super(self.__class__, self).XmlAddMembers()

    def XmlCreate(self):
        global RecordId
        global __handshakeReg__

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.XmlData.append('<ProbeDetails>\n')

        # Add the record indentity

        self.XmlData.append('<RecordIdentity recordId="' + socket.getfqdn() + ':' + str(RecordPid) + '.'
                            + str(RecordId) + '" createTime="' + TimeToString(time.gmtime()) + '" />\n')
        RecordId = RecordId + 1

        for data in self.RecordData:
            self.XmlData.append('\t')
            self.XmlData.append(data)
            self.XmlData.append('\n')

        if len(self.__ProbeDetails__) > 0:
            for data in self.__ProbeDetails__:
                self.XmlData.append('\t')
                self.XmlData.append(data)
                self.XmlData.append('\n')

        self.XmlData.append('</ProbeDetails>\n')

    def Print(self):
        DebugPrint(1, 'ProbeDetails Record: ', self)

def FindBestJobId(usageRecord, namespace):

    # Get GlobalJobId first, next recordId

    jobIdentityNodes = usageRecord.getElementsByTagNameNS(namespace, 'JobIdentity')
    if jobIdentityNodes:
        globalJobIdNodes = jobIdentityNodes[0].getElementsByTagNameNS(namespace, 'GlobalJobId')
        if globalJobIdNodes and globalJobIdNodes[0].firstChild and globalJobIdNodes[0].firstChild.data:
            return [globalJobIdNodes[0].localName, globalJobIdNodes[0].firstChild.data]

    recordIdNodes = usageRecord.getElementsByTagNameNS(namespace, 'RecordId')
    if recordIdNodes and recordIdNodes[0].firstChild and recordIdNodes[0].firstChild.data:
        return [recordIdNodes[0].localName, recordIdNodes[0].firstChild.data]

    localJobIdNodes = usageRecord.getElementsByTagNameNS(namespace, 'LocalJobId')
    if localJobIdNodes and localJobIdNodes[0].firstChild and localJobIdNodes[0].firstChild.data:
        return [localJobIdNodes[0].localName, localJobIdNodes[0].firstChild.data]

    return ['Unknown', 'Unknown']

def StandardCheckXmldoc(
    xmlDoc,
    recordElement,
    external,
    prefix,
    ):
    '''Check for and fill in suitable values for important attributes'''

    if not xmlDoc.documentElement:  # Major problem
        return

    if external:

        # Local namespace

        namespace = xmlDoc.documentElement.namespaceURI

        # ProbeName

        probeNameNodes = recordElement.getElementsByTagNameNS(namespace, 'ProbeName')
        if not probeNameNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'ProbeName')
            textNode = xmlDoc.createTextNode(Config.get_ProbeName())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif probeNameNodes.length > 1:
            [jobIdType, jobId] = FindBestJobId(recordElement, namespace)
            DebugPrint(0, 'Warning: too many ProbeName entities in ' + jobIdType + ' ' + jobId)

        # SiteName

        siteNameNodes = recordElement.getElementsByTagNameNS(namespace, 'SiteName')
        if not siteNameNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'SiteName')
            textNode = xmlDoc.createTextNode(Config.get_SiteName())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif siteNameNodes.length > 1:
            [jobIdType, jobId] = FindBestJobId(recordElement, namespace)
            DebugPrint(0, 'Warning: too many SiteName entities in ' + jobIdType + ' ' + jobId)

        # grid

        gridNodes = recordElement.getElementsByTagNameNS(namespace, 'Grid')
        if not gridNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'Grid')
            textNode = xmlDoc.createTextNode(Config.get_Grid())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif gridNodes.length == 1:
            grid = gridNodes[0].firstChild.data
            grid_info = Config.get_Grid()
            if grid_info and (not grid or grid == 'Unknown'):
                gridNodes[0].firstChild.data = grid_info
            if not gridNodes[0].firstChild.data:  # Remove null entry
                recordElement.removeChild(gridNodes[0])
                gridNodes[0].unlink()
        else:

              # Too many entries

            [jobIdType, jobId] = FindBestJobId(recordElement, namespace)
            DebugPrint(0, 'Warning: too many grid entities in ' + jobIdType + ' ' + jobId)


failedSendCount = 0
suppressedCount = 0
successfulSendCount = 0
successfulReprocessCount = 0
successfulHandshakes = 0
failedHandshakes = 0
failedReprocessCount = 0
successfulBundleCount = 0
failedBundleCount = 0
quarantinedFiles = 0

#
# Bundle class
#


class Bundle:

    nBytes = 0
    nRecords = 0
    nHandshakes = 0
    nReprocessed = 0
    nItems = 0
    nFiles = 0
    nLastProcessed = 0
    content = []
    __maxPostSize = 2000000 * 0.9  # 2Mb

    def __init__(self):
        pass

    def __addContent(self, filename, xmlData):
        self.content.append([filename, xmlData])
        self.nItems += 1
        if len(filename):
            self.nFiles += 1

    def __checkSize(self, msg, xmlDataLen):
        if self.nBytes + xmlDataLen > self.__maxPostSize:
            (responseString, response) = ProcessBundle(self)
            if response.getCode() != 0:
                return (responseString, response)
            msg = responseString + '; ' + msg
        return msg

    def addGeneric(
        self,
        action,
        what,
        filename,
        xmlData,
        ):
        global failedSendCount
        global failedHandshakes
        global failedReprocessCount
        if self.nItems > 0 and self.nBytes + len(xmlData) > self.__maxPostSize:
            (responseString, response) = ProcessBundle(self)
            if response.getCode() == Response.BundleNotSupported:
                return (responseString, response)
            elif response.getCode() != 0:

               # For simplicity we return here, this means that the 'incoming' record is actually
               # not processed at all this turn

                self.nLastProcessed += 1
                action()
                failedSendCount += self.nRecords
                failedHandshakes += self.nHandshakes
                failedReprocessCount += self.nReprocessed
                self.clear()
                return (responseString, response)
            what = '(nested process: ' + responseString + ')' + '; ' + what
        else:
            self.nLastProcessed = 0

        self.__addContent(filename, xmlData)
        action()
        self.nBytes += len(xmlData)
        return self.checkAndSend('OK - ' + what + ' added to bundle (' + str(self.nItems) + r'/'
                                 + str(__bundleSize__) + ')')

    def hasFile(self, filename):
        for [name, data] in self.content:
            if filename == name:
                return True
        return False

    def __actionHandshake(self):
        self.nHandshakes += 1

    def addHandshake(self, xmlData):
        return self.addGeneric(self.__actionHandshake, 'Handshake', r'', xmlData)

    def __actionRecord(self):
        self.nRecords += 1

    def addRecord(self, filename, xmlData):
        return self.addGeneric(self.__actionRecord, 'Record', filename, xmlData)

    def __actionReprocess(self):
        self.nReprocessed += 1

    def addReprocess(self, filename, xmlData):
        return self.addGeneric(self.__actionReprocess, 'Record', filename, xmlData)

    def checkAndSend(self, defaultmsg):

        # Check if the bundle is full, if it is, do the
        # actuall sending!

        if self.nItems >= __bundleSize__ or self.nBytes > self.__maxPostSize:
            return ProcessBundle(self)
        else:
            return (defaultmsg, Response(Response.Success, defaultmsg))

    def decreaseMaxPostSize(howMuch):
        """
        Decrease the maximum allowed size for a 'post'.
        """
        Bundle.__maxPostSize = howMuch * Bundle.__maxPostSize

    decreaseMaxPostSize = staticmethod(decreaseMaxPostSize)

    def clear(self):
        self.nBytes = 0
        self.nRecords = 0
        self.nHandshakes = 0
        self.nItems = 0
        self.nFiles = 0
        self.content = []
        self.nReprocessed = 0


#
# ProcessBundle
#
#  Loops through all the bundled records and attempts to send them.
#


def ProcessBundle(bundle):
    global failedSendCount
    global suppressedCount
    global successfulSendCount
    global successfulReprocessCount
    global successfulHandshakes
    global failedHandshakes
    global failedReprocessCount
    global successfulBundleCount
    global failedBundleCount
    global __bundleSize__
    global quarantinedFiles

    responseString = r''

    # Loop through and try to send any outstanding records

    bundleData = '''<?xml version="1.0" encoding="UTF-8"?>
<RecordEnvelope>
'''
    for item in bundle.content:
        xmlData = None

        filename = item[0]
        xmlData = item[1]

        DebugPrint(1, 'Processing bundle file: ' + filename)

        if xmlData == r'':

            # Read the contents of the file into a string of xml

            try:
                in_file = open(filename, 'r')
                xmlData = in_file.read()
                in_file.close()
            except:
                DebugPrint(1, 'Processing bundle failure: unable to read file: ' + filename)
                responseString = responseString + '\nUnable to read from ' + filename
                failedBundleCount += 1
                continue

        if not xmlData:
            DebugPrint(1, 'Processing bundle failure: ' + filename + ' was empty: skip send')
            responseString = responseString + '\nEmpty file ' + filename + ': XML not sent'
            failedBundleCount += 1
            continue

        xmlData = __xmlintroRemove.sub(r'', xmlData)

        bundleData = bundleData + xmlData + '\n'

        # if (len(bundleData)==0):
        #  bundleData = xmlData
        # else:
        #  bundleData = bundleData + '|' + xmlData

    bundleData = bundleData + '</RecordEnvelope>'

    # Send the xml to the collector for processing

    response = __sendUsageXML(Config.get_ProbeName(), bundleData, 'multiupdate')

    DebugPrint(2, 'Processing bundle Response code:  ' + str(response.getCode()))
    DebugPrint(2, 'Processing bundle Response message:  ' + response.getMessage())

    if response.getCode() == Response.BundleNotSupported:
        DebugPrint(0, "Collector is too old to handle 'bundles', reverting to sending individual records.")
        __bundleSize__ = 0
        bundle.nLastProcessed = 0
        hasHandshake = bundle.nHandshakes > 0
        bundle.clear()
        if hasHandshake:
            Handshake()
        else:
            SearchOutstandingRecord()
            Reprocess()
        return ('Bundling has been canceled.', response)
    elif response.getCode() == Response.PostTooLarge:
        if bundle.nItems > 1:

           # We let a large record to be added to already too many data.
           # Let's try to restrict more the size of the record

            Bundle.decreaseMaxPostSize(0.9)
            #__maxPostSize = 0.9 * Bundle.__maxPostSize
        elif bundle.nItems == 1:
            DebugPrint(0, 'Error: a record is larger than the Collector can receive. (' + str(len(bundleData)
                       * 10 / 1000 / 1000 / 10.0) + 'Mb vs 2Mb).  Record will be Quarantined.')
            quarantinedFiles += 1
            QuarantineFile(bundle.content[0][0], False)
        else:
            DebugPrint(0,
                       "Internal error, got a 'too large of a post' response eventhough we have no record at all!"
                       )

    responseString = 'Processed bundle with ' + str(bundle.nItems) + ' records:  ' + response.getMessage()

    # Determine if the call succeeded, and remove the file if it did

    if response.getCode() == 0:
        successfulSendCount += bundle.nRecords
        successfulHandshakes += bundle.nHandshakes
        successfulReprocessCount += bundle.nReprocessed
        successfulBundleCount += 1
        for item in bundle.content:
            filename = item[0]
            if filename != r'':
                DebugPrint(1, 'Bundle response indicates success, ' + filename + ' will be deleted')
                RemoveRecordFile(filename)
        responseString = 'OK - ' + responseString
    else:
        DebugPrint(1, 'Response indicates failure, the following files will not be deleted:')
        for item in bundle.content:
            filename = item[0]
            if filename != r'':
                DebugPrint(1, '   ' + filename)
        failedSendCount += bundle.nRecords
        failedHandshakes += bundle.nHandshakes
        failedReprocessCount += bundle.nReprocessed
        failedBundleCount += 1

    bundle.nLastProcessed = bundle.nItems
    bundle.clear()

    return (responseString, response)


#
# Reprocess
#
#  Loops through all outstanding records and attempts to send them again
#


def Reprocess():
    (response, result) = ReprocessList()
    while not __connectionError__ and result and __hasMoreOutstandingRecord__:
        # This is decreased in SearchOutstanding

        tarcount = __outstandingStagedTarCount__
        scount = __outstandingStagedRecordCount__

        # Need to look for left over files

        SearchOutstandingRecord()

        if len(__outstandingRecord__) == 0:
            DebugPrint(4, 'DEBUG: quit reprocessing loop due empty list')
            break

        # This is potentially decreased in ReprocessList

        rcount = __outstandingRecordCount__

        # Attempt to reprocess any outstanding records

        ReprocessList()
        if rcount == __outstandingRecordCount__ and scount == __outstandingStagedRecordCount__ and tarcount \
            == __outstandingStagedTarCount__:
            DebugPrint(3, 'Reprocessing seems stalled, stopping it until next successful send')

            # We are not making progress

            break


#
# ReprocessList
#
#  Loops through all the record in the OustandingRecord list and attempts to send them again
#


def ReprocessList():
    global successfulReprocessCount
    global failedReprocessCount
    global quarantinedFiles

    currentFailedCount = 0
    currentSuccessCount = 0
    currentBundledCount = 0
    prevBundled = CurrentBundle.nItems
    prevQuarantine = quarantinedFiles

    responseString = r''

    # Loop through and try to send any outstanding records

    filenames = __outstandingRecord__.keys()
    filenames.sort()
    for failedRecord in filenames:
        if __connectionError__:

            # Fail record without attempting to send.

            failedReprocessCount += 1
            currentFailedCount += 1
            continue

        xmlData = None

        # if os.path.isfile(failedRecord):

        DebugPrint(1, 'Reprocessing:  ' + failedRecord)

        # Read the contents of the file into a string of xml

        try:
            in_file = open(failedRecord, 'r')
            xmlData = in_file.read()
            in_file.close()
        except:
            DebugPrint(1, 'Reprocess failure: unable to read file: ' + failedRecord)
            responseString = responseString + '\nUnable to read from ' + failedRecord
            failedReprocessCount += 1
            currentFailedCount += 1
            RemoveRecordFile(failedRecord)
            del __outstandingRecord__[failedRecord]
            continue

        if not xmlData:
            DebugPrint(1, 'Reprocess failure: ' + failedRecord + ' was empty: skip send')
            responseString = responseString + '\nEmpty file ' + failedRecord + ': XML not sent'
            failedReprocessCount += 1
            currentFailedCount += 1
            RemoveRecordFile(failedRecord)
            del __outstandingRecord__[failedRecord]
            continue

        if __bundleSize__ > 1:

            # Delay the sending until we have 'bundleSize' records.

            (addReponseString, response) = CurrentBundle.addReprocess(failedRecord, xmlData)

            if response.getCode() == Response.BundleNotSupported:

                # The bundling was canceled, Reprocess was called recursively, we are done.

                break
            elif response.getCode() != 0:
                currentFailedCount += CurrentBundle.nLastProcessed - prevBundled
                currentBundledCount = CurrentBundle.nItems
                prevBundled = 0
                if __connectionError__:
                    DebugPrint(1,
                               'Connection problems: reprocessing suspended; new record processing shall continue'
                               )
            else:
                if CurrentBundle.nReprocessed == 0:
                    currentSuccessCount += CurrentBundle.nLastProcessed - prevBundled
                    currentBundledCount = CurrentBundle.nItems
                    prevBundled = 0
                else:
                    currentBundledCount += 1
        else:

            # Send the xml to the collector for processing

            response = __sendUsageXML(Config.get_ProbeName(), xmlData)

            # Determine if the call succeeded, and remove the file if it did

            if response.getCode() == 0:
                DebugPrint(3, 'Processing bundle Response code for ' + failedRecord + ':  '
                           + str(response.getCode()))
                DebugPrint(3, 'Processing bundle Response message for ' + failedRecord + ':  '
                           + response.getMessage())
                DebugPrint(1, 'Response indicates success, ' + failedRecord + ' will be deleted')
                currentSuccessCount += 1
                successfulReprocessCount += 1
                RemoveRecordFile(failedRecord)
                del __outstandingRecord__[failedRecord]
            else:
                DebugPrint(1, 'Processing bundle Response code for ' + failedRecord + ':  '
                           + str(response.getCode()))
                DebugPrint(1, 'Processing bundle Response message for ' + failedRecord + ':  '
                           + response.getMessage())
                currentFailedCount += 1
                if __connectionError__:
                    DebugPrint(1,
                               'Connection problems: reprocessing suspended; new record processing shall continue'
                               )
                failedReprocessCount += 1

    if currentFailedCount == 0:
        responseString = 'OK'
    elif currentSuccessCount != 0:
        responseString = 'Warning'
    else:
        responseString = 'Error'
    responseString += ' - Reprocessing ' + str(currentSuccessCount) + ' record(s) uploaded, ' \
        + str(currentBundledCount) + ' bundled, ' + str(currentFailedCount) + ' failed'

    DebugPrint(0, 'Reprocessing response: ' + responseString)
    DebugPrint(1, 'After reprocessing: ' + str(__outstandingRecordCount__) + ' in outbox '
               + str(__outstandingStagedRecordCount__) + ' in staged outbox ' + str(__outstandingStagedTarCount__)
               + ' tar files')
    return (responseString, currentSuccessCount > 0 or currentBundledCount == len(__outstandingRecord__.keys())
            or prevQuarantine != quarantinedFiles)


def CheckXmlDoc(xmlDoc, external, resourceType=None):
    content = 0
    DebugPrint(4, 'DEBUG: In CheckXmlDoc')
    for checker in XmlRecordCheckers:
        DebugPrint(3, 'Running : ' + str(checker) + str(xmlDoc) + str(external) + str(resourceType))
        content = content + checker(xmlDoc, external, resourceType)
    return content


def Handshake():
    global Config
    global __connection__
    global __connectionError__
    global __connectionRetries__
    global failedHandshakes

    pdetails = ProbeDetails()

    if __connectionError__:

        # We are not currently connected, the SendHandshake
        # will reconnect us if it is possible

        result = SendHandshake(pdetails)
    else:

        # We are connected but the connection may have timed-out

        result = SendHandshake(pdetails)
        if __connectionError__:

            # Case of timed-out connection, let's try again

            failedHandshakes -= 1  # Take a Mulligan
            result = SendHandshake(pdetails)

    return result


def SendHandshake(record):
    global successfulHandshakes
    global failedHandshakes

    DebugPrint(0, '***********************************************************')

    # Assemble the record into xml

    record.XmlCreate()

    # Parse it into nodes, etc (transitional: this will eventually be native format)

    xmlDoc = safeParseXML(string.join(record.XmlData, r''))

    if not xmlDoc:
        failedHandshakes += 1
        responseString = 'Internal Error: cannot parse internally generated XML record'
        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')
        return responseString

    xmlDoc.normalize()

    # Generate the XML

    record.XmlData = safeEncodeXML(xmlDoc).splitlines(True)

    # Close and clean up the document

    xmlDoc.unlink()

    # Currently, the recordXml is in a list format, with each item being a line of xml.
    # the collector web service requires the xml to be sent as a string.
    # This logic here turns the xml list into a single xml string.

    usageXmlString = r''
    for line in record.XmlData:
        usageXmlString = usageXmlString + line
    DebugPrint(3, 'UsageXml:  ' + usageXmlString)

    connectionProblem = __connectionRetries__ > 0 or __connectionError__

    if __bundleSize__ > 1:

        # Delay the sending until we have 'bundleSize' records.

        (responseString, response) = CurrentBundle.addHandshake(usageXmlString)
    else:

        # Attempt to send the record to the collector. Note that this must
        # be sent currently as an update, not as a handshake (cf unused
        # SendStatus() call)

        response = __sendUsageXML(Config.get_ProbeName(), usageXmlString)
        responseString = response.getMessage()

        DebugPrint(1, 'Response code:  ' + str(response.getCode()))
        DebugPrint(1, 'Response message:  ' + response.getMessage())

        # Determine if the call was successful based on the response
        # code.  Currently, 0 = success

        if response.getCode() == 0:
            DebugPrint(1, 'Response indicates success, ')
            successfulHandshakes += 1
            if connectionProblem or __hasMoreOutstandingRecord__:

                # Reprocess failed records before attempting more new ones

                SearchOutstandingRecord()
                Reprocess()
        else:
            DebugPrint(1, 'Response indicates failure, ')
            failedHandshakes += 1

    DebugPrint(0, responseString)
    DebugPrint(0, '***********************************************************')
    return responseString


def Send(record):
    global failedSendCount
    global suppressedCount
    global successfulSendCount
    global __estimatedServiceBacklog__

    try:
        DebugPrint(0, '***********************************************************')
        DebugPrint(4, 'DEBUG: In Send(record)')
        DebugPrint(4, 'DEBUG: Printing record to send')
        record.Print()
        DebugPrint(4, 'DEBUG: Printing record to send: OK')

        DebugPrint(4, 'DEBUG: File Count: ' + str(__outstandingRecordCount__))
        toomanyfiles = __outstandingRecordCount__ >= Config.get_MaxPendingFiles()

        if __estimatedServiceBacklog__ > 0 : __estimatedServiceBacklog__ -= 1

        # Assemble the record into xml

        DebugPrint(4, 'DEBUG: Creating XML')
        record.XmlCreate()
        DebugPrint(4, 'DEBUG: Creating XML: OK')

        # Parse it into nodes, etc (transitional: this will eventually be native format)

        DebugPrint(4, 'DEBUG: parsing XML')
        xmlDoc = safeParseXML(string.join(record.XmlData, r''))
        DebugPrint(4, 'DEBUG: parsing XML: OK')

        if not xmlDoc:
            responseString = 'Internal Error: cannot parse internally generated XML record'
            # We intentionally do not delete the input files.
            DebugPrint(0, responseString)
            DebugPrint(0, '***********************************************************')
            return responseString

        DebugPrint(4, 'DEBUG: Checking XML content')
        if not CheckXmlDoc(xmlDoc, False):
            DebugPrint(4, 'DEBUG: Checking XML content: BAD')
            xmlDoc.unlink()
            responseString = 'OK: No unsuppressed usage records in this packet: not sending'
            record.QuarantineTransientInputFiles()
            suppressedCount += 1
            DebugPrint(0, responseString)
            DebugPrint(0, '***********************************************************')
            return responseString
        DebugPrint(4, 'DEBUG: Checking XML content: OK')

        DebugPrint(4, 'DEBUG: Normalizing XML document')
        xmlDoc.normalize()
        DebugPrint(4, 'DEBUG: Normalizing XML document: OK')

        # Generate the XML

        DebugPrint(4, 'DEBUG: Generating data to send')
        record.XmlData = safeEncodeXML(xmlDoc).splitlines(True)
        DebugPrint(4, 'DEBUG: Generating data to send: OK')

        # Close and clean up the document2

        xmlDoc.unlink()

        dirIndex = 0
        success = False
        f = 0

        DebugPrint(4, 'DEBUG: Attempt to back up record to send')
        while not success:
            (f, dirIndex) = OpenNewRecordFile(dirIndex)
            DebugPrint(3, 'Will save the record in:', f.name)
            DebugPrint(3, 'dirIndex=', dirIndex)
            if f.name != '<stdout>':
                try:
                    for line in record.XmlData:
                        f.write(line)
                    f.flush()
                    if f.tell() > 0:
                        success = True
                        DebugPrint(1, 'Saved record to ' + f.name)
                    else:
                        DebugPrint(0, 'failed to fill: ', f.name)
                        if f.name != '<stdout>':
                            RemoveRecordFile(f.name)
                    f.close()
                    record.RemoveTransientInputFiles()
                except:
                    DebugPrint(
                        0,
                        'failed to fill with exception: ',
                        f.name,
                        '--',
                        sys.exc_info(),
                        '--',
                        sys.exc_info()[0],
                        '++',
                        sys.exc_info()[1],
                        )
                DebugPrint(4, 'DEBUG: Backing up record to send: OK')
            else:
                break

        # Currently, the recordXml is in a list format, with each item being a line of xml.
        # the collector web service requires the xml to be sent as a string.
        # This logic here turns the xml list into a single xml string.

        usageXmlString = r''
        for line in record.XmlData:
            usageXmlString = usageXmlString + line
        DebugPrint(3, 'UsageXml:  ' + usageXmlString)

        connectionProblem = __connectionRetries__ > 0 or __connectionError__

        if __bundleSize__ > 1 and f.name != '<stdout>':

            # Delay the sending until we have 'bundleSize' records.

            (responseString, response) = CurrentBundle.addRecord(f.name, usageXmlString)
        else:

            # Attempt to send the record to the collector

            response = __sendUsageXML(Config.get_ProbeName(), usageXmlString)
            responseString = response.getMessage()

            DebugPrint(1, 'Response code:  ' + str(response.getCode()))
            DebugPrint(1, 'Response message:  ' + response.getMessage())

            # Determine if the call was successful based on the response
            # code.  Currently, 0 = success

            if response.getCode() == 0:
                if f.name != '<stdout>':
                    DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
                    RemoveRecordFile(f.name)
                else:
                    record.RemoveTransientInputFiles()
                    DebugPrint(1, 'Response indicates success')
                successfulSendCount += 1
            else:
                failedSendCount += 1
                if toomanyfiles:
                    DebugPrint(1,
                               'Due to too many pending files and a connection error, the following record was not sent and has not been backed up.'
                               )
                    DebugPrint(1, 'Lost record: ' + usageXmlString)
                    responseString = 'Fatal Error: too many pending files'
                elif f.name == '<stdout>':
                    DebugPrint(0, 'Record send failed and no backup made: record lost!')
                    responseString += '\nFatal: failed record lost!'
                    match = re.search(r'^<(?:[^:]*:)?RecordIdentity.*/>$', usageXmlString, re.MULTILINE)
                    if match:
                        DebugPrint(0, match.group(0))
                        responseString += ('\n', match.group(0))
                    match = re.search(r'^<(?:[^:]*:)?GlobalJobId.*/>$', usageXmlString, re.MULTILINE)
                    if match:
                        DebugPrint(0, match.group(0))
                        responseString += ('\n', match.group(0))
                    responseString += '\n' + usageXmlString
                else:
                    DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')

        if (connectionProblem or __hasMoreOutstandingRecord__) and CurrentBundle.nItems == 0 \
            and response.getCode() == 0:

            # Reprocess failed records before attempting more new ones

            SearchOutstandingRecord()
            Reprocess()

        return responseString
    except Exception, e:
        DebugPrint(0, 'ERROR: ' + str(e) + ' exception caught while processing record ')
        DebugPrint(0, '       This record has been LOST')
        DebugPrintTraceback()
        return 'ERROR: record lost due to internal error!'


# This sends the file contents of the given directory as raw XML. The
# writer of the XML files is responsible for making sure that it is
# readable by the Gratia server.


def SendXMLFiles(fileDir, removeOriginal=False, resourceType=None):
    global Config
    global failedSendCount
    global suppressedCount
    global successfulSendCount

    path = os.path.join(fileDir, '*')
    files = glob.glob(path)

    responseString = r''

    for xmlFilename in files:

        DebugPrint(0, '***********************************************************')
        if os.path.getsize(xmlFilename) == 0:
            DebugPrint(0, 'File ' + xmlFilename + ' is zero-length: skipping')
            RemoveFile(xmlFilename)
            continue
        DebugPrint(2, 'xmlFilename: ', xmlFilename)
        if __outstandingRecordCount__ >= Config.get_MaxPendingFiles():
            responseString = 'Fatal Error: too many pending files'
            DebugPrint(0, responseString)
            DebugPrint(0, '***********************************************************')
            return responseString

        # Open the XML file

        try:
            xmlDoc = xml.dom.minidom.parse(xmlFilename)
        except:
            DebugPrint(
                0,
                'Failed to parse XML file ',
                xmlFilename,
                '--',
                sys.exc_info(),
                '--',
                sys.exc_info()[0],
                '++',
                sys.exc_info()[1],
                )
            xmlDoc = None

        if xmlDoc:
            DebugPrint(3, 'Adding information to parsed XML')

            xmlDoc.normalize()

            if not CheckXmlDoc(xmlDoc, True, resourceType):
                xmlDoc.unlink()
                DebugPrint(0, 'No unsuppressed usage records in ' + xmlFilename + ': not sending')
                suppressedCount += 1

                # Cleanup old records - SPC - NERSC 08/28/07

                if removeOriginal:
                    RemoveFile(xmlFilename)
                continue

            # Generate the XML

            xmlData = safeEncodeXML(xmlDoc)

            # Close and clean up the document

            xmlDoc.unlink()
        else:

              # XML parsing failed: slurp the file in to xmlData and
            # send as-is.

            DebugPrint(1, 'Backing up and sending failed XML as is.')
            try:
                in_file = open(xmlFilename, 'r')
            except:
                DebugPrint(0, 'Unable to open xmlFilename for simple read')
                continue

            xmlData = in_file.readlines()
            in_file.close()

        # Open the back up file
        # fill the back up file

        dirIndex = 0
        success = False
        f = 0

        toomanyfiles = __outstandingRecordCount__ >= Config.get_MaxPendingFiles()
        toomanystaged = __outstandingStagedTarCount__ >= Config.get_MaxStagedArchives()

        if toomanyfiles and toomanystaged:
            DebugPrint(4, 'DEBUG: Too many pending files, the record has not been backed up')
            f = sys.stdout
        else:
            DebugPrint(4, 'DEBUG: Back up record to send')
            while not success:
                (f, dirIndex) = OpenNewRecordFile(dirIndex)
                DebugPrint(3, 'Will save in the record in:', f.name)
                DebugPrint(3, 'dirIndex=', dirIndex)
                if f.name == '<stdout>':
                    responseString = 'Fatal Error: unable to save record prior to send attempt'
                    DebugPrint(0, responseString)
                    DebugPrint(0, '***********************************************************')
                    return responseString
                else:
                    try:
                        for line in xmlData:
                            f.write(line)
                        f.flush()
                        if f.tell() > 0:
                            success = True
                            DebugPrint(3, 'suceeded to fill: ', f.name)
                        else:
                            DebugPrint(0, 'failed to fill: ', f.name)
                            if f.name != '<stdout>':
                                RemoveRecordFile(f.name)
                    except:
                        DebugPrint(
                            0,
                            'failed to fill with exception: ',
                            f.name,
                            '--',
                            sys.exc_info(),
                            '--',
                            sys.exc_info()[0],
                            '++',
                            sys.exc_info()[1],
                            )
                        if f.name != '<stdout>':
                            RemoveRecordFile(f.name)
                    DebugPrint(4, 'DEBUG: Backing up record to send: OK')

        if removeOriginal and f.name != '<stdout>':
            RemoveFile(xmlFilename)

        DebugPrint(1, 'Saved record to ' + f.name)

        # Currently, the recordXml is in a list format, with each
        # item being a line of xml. The collector web service
        # requires the xml to be sent as a string. This logic here
        # turns the xml list into a single xml string.

        usageXmlString = r''
        for line in xmlData:
            usageXmlString = usageXmlString + line
        DebugPrint(3, 'UsageXml:  ' + usageXmlString)

        if __bundleSize__ > 1 and f.name != '<stdout>':

            # Delay the sending until we have 'bundleSize' records.

            (responseString, response) = CurrentBundle.addRecord(f.name, usageXmlString)
        else:

            # If XMLFiles can ever be anything else than Update messages,
            # then one should be able to deduce messageType from the root
            # element of the XML.

            messageType = 'URLEncodedUpdate'

            # Attempt to send the record to the collector

            response = __sendUsageXML(Config.get_ProbeName(), usageXmlString, messageType)
            responseString = response.getMessage()

            DebugPrint(1, 'Response code:  ' + str(response.getCode()))
            DebugPrint(1, 'Response message:  ' + response.getMessage())

            # Determine if the call was successful based on the
            # response code.  Currently, 0 = success

            if response.getCode() == 0:
                if f.name != '<stdout>':
                    DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
                    RemoveRecordFile(f.name)
                else:
                    DebugPrint(1, 'Response indicates success')
                successfulSendCount += 1
            else:
                failedSendCount += 1
                DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

    DebugPrint(0, responseString)
    DebugPrint(0, '***********************************************************')
    return responseString


class InternalError(exceptions.Exception):

    pass


def __ResourceTool__(
    action,
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value=r'',
    ):
    '''Private routine sitting underneath (possibly) several public ones'''

    if value == None:
        value = r''

    if action != 'UpdateFirst' and action != 'ReadValues' and action != 'ReadFirst' and action \
        != 'AddIfMissingValue' and action != 'AddIfMissingKey' and action != 'UnconditionalAdd':
        raise InternalError("__ResourceTool__ gets unrecognized action '%s'" % action)

    resourceNodes = usageRecord.getElementsByTagNameNS(namespace, 'Resource')
    wantedResource = None
    foundValues = []

    # Look for existing resource of desired type

    for resource in resourceNodes:
        description = resource.getAttributeNS(namespace, 'description')
        if description == key:
            if action == 'UpdateFirst':
                wantedResource = resource
                break
            elif action == 'AddIfMissingValue':

                # Kick out if we have the attribute and value

                if resource.firstChild and resource.firstChild.data == value:
                    return None
            elif action == 'AddIfMissingKey':

                # Kick out, since we're not missing the key

                return None
            elif action == 'ReadFirst' and resource.firstChild:
                return resource.firstChild.data
            elif action == 'ReadValues' and resource.firstChild:
                foundValues.append(resource.firstChild.data)

    if action == 'ReadValues' or action == 'ReadFirst':
        return foundValues  # Done, no updating necessary

    # Found

    if wantedResource:  # UpdateFirst
        if wantedResource.firstChild:  # Return replaced value
            oldValue = wantedResource.firstChild.data
            wantedResource.firstChild.data = value
            return oldValue
        else:

              # No text data node

            textNode = xmlDoc.createTextNode(value)
            wantedResource.appendChild(textNode)
    else:

          # AddIfMissing{Key,Value}, UpdateFirst and UnconditionalAdd
            # should all drop through to here.
        # Create Resource node

        wantedResource = xmlDoc.createElementNS(namespace, prefix + 'Resource')
        wantedResource.setAttribute(prefix + 'description', key)
        textNode = xmlDoc.createTextNode(value)
        wantedResource.appendChild(textNode)
        usageRecord.appendChild(wantedResource)

    return None


def UpdateResource(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value,
    ):
    '''Update a resource key in the XML record'''

    return __ResourceTool__(
        'UpdateFirst',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def FirstResourceMatching(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    ):
    '''Return value of first matching resource'''

    return __ResourceTool__(
        'ReadFirst',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        )


def ResourceValues(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    ):
    '''Return all found values for a given resource'''

    return __ResourceTool__(
        'ReadValues',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        )


def AddResourceIfMissingValue(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value,
    ):
    """Add a resource key in the XML record if there isn't one already with the desired value"""

    return __ResourceTool__(
        'AddIfMissingValue',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def AddResourceIfMissingKey(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value=r'',
    ):
    """Add a resource key in the XML record if there isn't at least one resource with that key"""

    return __ResourceTool__(
        'AddIfMissingKey',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def AddResource(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value,
    ):
    '''Unconditionally add a resource key in the XML record'''

    return __ResourceTool__(
        'UnconditionalAdd',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def GetElement(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    ):
    return __ElementTool__(
        xmlDoc,
        parent,
        namespace,
        prefix,
        tag,
        None,
        )


def GetElementOrCreateDefault(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    default,
    ):
    if default == None:
        default = r''
    return __ElementTool__(
        xmlDoc,
        parent,
        namespace,
        prefix,
        tag,
        default,
        )


def __ElementTool__(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    default,
    ):
    '''Get the value if the element exists; otherwise create with default value if specified.'''

    nodes = parent.getElementsByTagNameNS(namespace, tag)

    if nodes and nodes.length > 0 and nodes[0].firstChild:
        return nodes[0].firstChild.data
    elif default != None:
        UpdateOrInsertElement(
            xmlDoc,
            parent,
            namespace,
            prefix,
            tag,
            default,
            )
        return default
    else:
        return None


def UpdateOrInsertElement(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    value,
    ):
    '''Update or insert the first matching node under parent.'''

    if value == None:
        value = r''

    nodes = parent.getElementsByTagNameNS(namespace, tag)

    if nodes and nodes.length > 0:
        if nodes[0].firstChild:
            nodes[0].firstChild.data = value
        else:
            textNode = xmlDoc.createTextNode(value)
            nodes[0].appendChild(textNode)
    else:
        node = xmlDoc.createElementNS(namespace, prefix + tag)
        textNode = xmlDoc.createTextNode(value)
        node.appendChild(textNode)
        parent.appendChild(node)


def CheckAndExtendUserIdentity(
    xmlDoc,
    userIdentityNode,
    namespace,
    prefix,
    ):
    '''Check the contents of the UserIdentity block and extend if necessary'''

    result = {}

    # LocalUserId

    localUserIdNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'LocalUserId')
    if not localUserIdNodes or localUserIdNodes.length != 1 or not (localUserIdNodes[0].firstChild
            and localUserIdNodes[0].firstChild.data):
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
        DebugPrint(0, 'Warning: UserIdentity block does not have exactly ', 'one populated LocalUserId node in '
                    + jobIdType + ' ' + jobId)
        return result

    LocalUserId = localUserIdNodes[0].firstChild.data

    # VOName

    VONameNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'VOName')
    if VONameNodes and  VONameNodes.length ==1 :
    	if VONameNodes[0].hasChildNodes() and not VONameNodes[0].firstChild.data:
    		[jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
       		DebugPrint(0, 'Warning: UserIdentity block has VOName node, but value is set to None  in ' + jobIdType + ' ' + jobId)
     	VONameNodes=[]
    if not VONameNodes:
        DebugPrint(4, 'DEBUG: Creating VONameNodes elements')
        VONameNodes.append(xmlDoc.createElementNS(namespace, prefix + 'VOName'))
        textNode = xmlDoc.createTextNode(r'')
        VONameNodes[0].appendChild(textNode)
        userIdentityNode.appendChild(VONameNodes[0])
        DebugPrint(4, 'DEBUG: Creating VONameNodes elements DONE')
    elif VONameNodes.length > 1:
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
        DebugPrint(0, 'Warning: UserIdentity block has multiple VOName nodes in ' + jobIdType + ' ' + jobId)
        return result

    # ReportableVOName

    ReportableVONameNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'ReportableVOName')
    if not ReportableVONameNodes:
        DebugPrint(4, 'DEBUG: Creating ReortableVONameNodes elements')
        ReportableVONameNodes.append(xmlDoc.createElementNS(namespace, prefix + 'ReportableVOName'))
        textNode = xmlDoc.createTextNode(r'')
        ReportableVONameNodes[0].appendChild(textNode)
        userIdentityNode.appendChild(ReportableVONameNodes[0])
        DebugPrint(4, 'DEBUG: Creating ReortableVONameNodes elements DONE')
    elif len(ReportableVONameNodes) > 1:
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
        DebugPrint(0, 'Warning: UserIdentity block has multiple ', 'ReportableVOName nodes in ' + jobIdType
                   + ' ' + jobId)
        return result

    # ###################################################################
    # Priority goes as follows:
    #
    # 1. Existing VOName if FQAN.
    #
    # 2. Certinfo.
    #
    # 3. Existing VOName if not FQAN.
    #
    # 4. VOName from reverse map file.

    DebugPrint(4, 'DEBUG: Calling verifyFromCertInfo')
    vo_info = verifyFromCertInfo(xmlDoc, userIdentityNode, namespace)
    DebugPrint(4, 'DEBUG: Calling verifyFromCertInfo: DONE')
    if vo_info != None:
        result['has_certinfo'] = 1
        if vo_info and not (vo_info['VOName'] or vo_info['ReportableVOName']):
            DebugPrint(4, 'DEBUG: No VOName data from verifyFromCertInfo')
            vo_info = None  # Reset if no output.

    # 1. Initial values

    DebugPrint(4, 'DEBUG: reading initial VOName')
    VOName = VONameNodes[0].firstChild.data
    DebugPrint(4, 'DEBUG: current VOName = ' + VONameNodes[0].firstChild.data)

    DebugPrint(4, 'DEBUG: reading initial ReportableVOName')
    ReportableVOName = ReportableVONameNodes[0].firstChild.data
    DebugPrint(4, 'DEBUG: current ReportableVOName = ' + ReportableVONameNodes[0].firstChild.data)

    # 2. Certinfo

    if vo_info and (not VOName or VOName[0] != r'/'):
        DebugPrint(4, 'DEBUG: Received values VOName: ' + str(vo_info['VOName']) + ' and ReportableVOName: '
                   + str(vo_info['ReportableVOName']))
        VONameNodes[0].firstChild.data = vo_info['VOName']
        VOName = vo_info['VOName']
        if vo_info['ReportableVOName'] == None:
           if VOName[0] == r'/':
              vo_info['ReportableVOName'] = string.split(VOName,r'/')[1]
           else:
              vo_info['ReportableVOName'] = VOName
        ReportableVONameNodes[0].firstChild.data = vo_info['ReportableVOName']
        ReportableVOName = vo_info['ReportableVOName']

    # 3. & 4.

    if not vo_info and not VOName:
        DebugPrint(4, 'DEBUG: Calling VOfromUser')
        vo_info = VOfromUser(LocalUserId)
        if Config.get_MapUnknownToGroup() and not vo_info:
            fromuserid = LocalUserId
            try:
                gid = pwd.getpwnam(LocalUserId)[3]
                fromuserid = grp.getgrgid(gid)[0]
            except:
                pass
            vo_info = {'VOName': fromuserid, 'ReportableVOName': fromuserid}

    # Resolve.

    if vo_info:
        if vo_info['VOName'] == None:
            vo_info['VOName'] = r''
        if vo_info['ReportableVOName'] == None:
            vo_info['ReportableVOName'] = r''
        if not (VOName and ReportableVOName) or VOName == 'Unknown':
            DebugPrint(4, 'DEBUG: Updating VO info: (' + vo_info['VOName'] + r', ' + vo_info['ReportableVOName'
                       ] + ')')

            # VO info from reverse mapfile only overrides missing or
            # inadequate data.

            VONameNodes[0].firstChild.data = vo_info['VOName']
            ReportableVONameNodes[0].firstChild.data = vo_info['ReportableVOName']

    VOName = VONameNodes[0].firstChild.data
    ReportableVOName = ReportableVONameNodes[0].firstChild.data

    DebugPrint(4, 'DEBUG: final VOName = ' + VONameNodes[0].firstChild.data)
    DebugPrint(4, 'DEBUG: final ReportableVOName = ' + ReportableVONameNodes[0].firstChild.data)

    # ###################################################################

    # Clean up.

    if not VOName:
        userIdentityNode.removeChild(VONameNodes[0])
        VONameNodes[0].unlink()

    if not ReportableVOName:
        userIdentityNode.removeChild(ReportableVONameNodes[0])
        ReportableVONameNodes[0].unlink()

    result['VOName'] = VOName
    result['ReportableVOName'] = ReportableVOName

    return result

# Check Python version number against requirements


def pythonVersionRequire(
    major,
    minor=0,
    micro=0,
    releaseLevel='final',
    serial=0,
    ):
    result = False
    if not 'version_info' in dir(sys):
        if major < 2:  # Unlikely
            return True
        else:
            return False
    releaseLevelsDir = {
        'alpha': 0,
        'beta': 1,
        'candidate': 2,
        'final': 3,
        }
    if major > sys.version_info[0]:
        result = False
    elif major < sys.version_info[0]:
        result = True
    elif minor > sys.version_info[1]:
        result = False
    elif minor < sys.version_info[1]:
        result = True
    elif micro > sys.version_info[2]:
        result = False
    elif micro < sys.version_info[2]:
        result = True
    else:
        try:
            releaseLevelIndex = releaseLevelsDir[string.lower(releaseLevel)]
            releaseCompareIndex = releaseLevelsDir[string.lower(sys.version_info[3])]
        except KeyError:
            result = False
        if releaseLevelIndex > releaseCompareIndex:
            result = False
        elif releaseLevelIndex < releaseCompareIndex:
            result = True
        elif serial > sys.version_info[4]:
            result = False
        else:
            result = True
    return result


def safeEncodeXML(xmlDoc):
    if pythonVersionRequire(2, 3):
        xmlOutput = xmlDoc.toxml(encoding='utf-8')
    else:
        xmlOutput = xmlDoc.toxml()  # No UTF-8 encoding for python < 2.3
        re.sub(r'(<\?xml version="1\.0")( \?>)', r'\1 encoding="utf-8"\2', xmlOutput, 1)

    return xmlOutput


def safeParseXML(xmlString):
    if pythonVersionRequire(2, 3):
        return xml.dom.minidom.parseString(xmlString)
    else:

          # python < 2.3
        # parseString is not UTF-safe: use StringIO instead

        stringBuf = StringIO.StringIO(xmlString)
        xmlDoc = xml.dom.minidom.parse(stringBuf)
        stringBuf.close()
        return xmlDoc


__UserVODictionary = {}
__voiToVOcDictionary = {}
__dictionaryErrorStatus = False


def __InitializeDictionary__():
    global __UserVODictionary
    global __voiToVOcDictionary
    global __dictionaryErrorStatus
    if __dictionaryErrorStatus:
        return None
    mapfile = Config.get_UserVOMapFile()
    if mapfile == None:
        return None
    __voi = []
    __VOc = []
    DebugPrint(4, 'DEBUG: Initializing (voi, VOc) lookup table')
    for line in fileinput.input([mapfile]):
        try:
            mapMatch = re.match(r'#(voi|VOc)\s', line)
            if mapMatch:

                # Translation line: fill translation tables

                exec '__' + mapMatch.group(1) + " = re.split(r'\s*', line[mapMatch.end(0):])"
            if re.match(r'\s*#', line):
                continue
            mapMatch = re.match('\s*(?P<User>\S+)\s*(?P<voi>\S+)', line)
            if mapMatch:
                if not len(__voiToVOcDictionary) and len(__voi) and len(__VOc):
                    try:
                        for index in xrange(0, len(__voi) - 1):
                            __voiToVOcDictionary[__voi[index]] = __VOc[index]
                            if __voiToVOcDictionary[__voi[index]] == None or __voiToVOcDictionary[__voi[index]] \
                                == r'':
                                DebugPrint(0, 'WARNING: no VOc match for voi "' + __voi[index]
                                           + '": not entering in (voi, VOc) table.')
                                del __voiToVOcDictionary[__voi[index]]
                    except IndexError, i:
                        DebugPrint(0, 'WARNING: VOc line does not have at least as many entries as voi line in '
                                    + mapfile + ': truncating')
                __UserVODictionary[mapMatch.group('User')] = {'VOName': mapMatch.group('voi'),
                        'ReportableVOName': __voiToVOcDictionary[mapMatch.group('voi')]}
        except KeyError, e:
            DebugPrint(0, 'WARNING: voi "' + str(e.args[0]) + '" listed for user "' + mapMatch.group('User')
                       + '" not found in (voi, VOc) table')
        except IOError, e:
            DebugPrint(0, 'IO error exception initializing osg-user-vo-map dictionary ' + str(e))
            DebugPrintTraceback()
            __dictionaryErrorStatus = True
        except Exception, e:
            DebugPrint(0, 'Unexpected exception initializing osg-user-vo-map dictionary ' + str(e))
            __dictionaryErrorStatus = True


def VOc(voi):
    if len(__UserVODictionary) == 0:

        # Initialize dictionary

        __InitializeDictionary__()
    return __voiToVOcDictionary.get(voi, voi)


def VOfromUser(user):
    ''' Helper function to obtain the voi and VOc from the user name via the reverse gridmap file'''

    global __UserVODictionary
    if len(__UserVODictionary) == 0:

        # Initialize dictionary

        __InitializeDictionary__()
    return __UserVODictionary.get(user, None)


def __encodeData(messageType, xmlData):
    ''' To the payload, we add the meta information: '''
    '''    from: the name of the sender '''
    '''    xmlfiles: number of records already passed to GratiaCore, still to be sent and still in individual xml files (i.e. number of gratia record in the outbox)'''
    '''    tarfiles: number of outstanding tar files '''
    '''    maxpendingfiles: 'current' number of files in a new tar file (i.e. an estimate of the number of individual records per tar file). '''
    '''    backlog: estimated amount of data to be processed by the probe '''
    probename = Config.get_ProbeName()
    maxpending = Config.get_MaxPendingFiles()
    xmlfiles = __outstandingRecordCount__ + __outstandingStagedRecordCount__
    # Remove from the backlog number, the number of record we are about to upload
    if __bundleSize__ > 0:
       xmlfiles -= (CurrentBundle.nItems - CurrentBundle.nHandshakes)
    else:
       xmlfiles -= 1
    if messageType[0:3] == 'URL' or messageType == 'multiupdate':
        result =  urllib.urlencode([
               ('command', messageType), ('arg1', xmlData), ('from', probename),
               ('xmlfiles', xmlfiles),  ('tarfiles', __outstandingStagedTarCount__),  ('maxpendingfiles', maxpending),  ('backlog', __estimatedServiceBacklog__),
               ('bundlesize', __bundleSize__),
               ])
#        print >> sys.stderr,  "xmlfiles: "+str(xmlfiles)+" bundle:"+str(CurrentBundle.nItems - CurrentBundle.nHandshakes)
        return result
    else:
        return 'command=' + messageType + '&arg1=' + xmlData + '&from=' + probename + \
               '&xmlfiles=' + str(xmlfiles) + \
               '&tarfiles=' + str(__outstandingStagedTarCount__) + \
               '&maxpendingfiles=' + str(maxpending) + \
               '&backlog=' + str(__estimatedServiceBacklog__) + \
               '&bundlesize=' + str(__bundleSize__)

def verifyFromCertInfo(
    xmlDoc,
    userIdentityNode,
    namespace,
    ):
    ''' Use localJobID and probeName to find cert info file and insert info into XML record'''

    # Collect data needed by certinfo reader

    DebugPrint(4, 'DEBUG: Get JobIdentity')
    jobIdentityNode = GetNode(xmlDoc.getElementsByTagNameNS(namespace, 'JobIdentity'))
    if jobIdentityNode == None:
        return
    DebugPrint(4, 'DEBUG: Get JobIdentity: OK')
    localJobId = GetNodeData(jobIdentityNode.getElementsByTagNameNS(namespace, 'LocalJobId'))
    DebugPrint(4, 'DEBUG: Get localJobId: ', localJobId)
    usageRecord = userIdentityNode.parentNode
    probeName = GetNodeData(usageRecord.getElementsByTagNameNS(namespace, 'ProbeName'))
    DebugPrint(4, 'DEBUG: Get probeName: ', probeName)

    # Read certinfo

    DebugPrint(4, 'DEBUG: call readCertInfo(' + str(localJobId) + r', ' + str(probeName) + ')')
    certInfo = readCertInfo(localJobId, probeName)
    DebugPrint(4, 'DEBUG: call readCertInfo: OK')
    DebugPrint(4, 'DEBUG: certInfo: ' + str(certInfo))
    if certInfo == None:
        DebugPrint(4, 'DEBUG: Returning without processing certInfo')
        return
    elif not certInfo.has_key('DN') or not certInfo['DN']:

        # Found a certinfo file, but no useful info.

        DebugPrint(4, 'DEBUG: Certinfo with no DN: WS without delegation?')
        return {'VOName': certInfo['FQAN'], 'ReportableVOName': certInfo['VO']}

    # Use certinfo

    DebugPrint(4, 'DEBUG: fixing DN')
    certInfo['DN'] = FixDN(certInfo['DN'])  # "Standard" slash format

    # First, find a KeyInfo node if it is there

    DebugPrint(4, 'DEBUG: looking for KeyInfo node')

    #    keyInfoNS = 'http://www.w3.org/2000/09/xmldsig#';
    #    keyInfoNode = GetNode(userIdentityNode.getElementsByTagNameNS(keyInfoNS, 'KeyInfo'))

    DNnode = GetNode(userIdentityNode.getElementsByTagNameNS(namespace, 'DN'))
    if DNnode and DNnode.firstChild:  # Override
        DebugPrint(4, 'DEBUG: overriding DN from certInfo')
        DNnode.firstChild.data = certInfo['DN']
    else:
        DebugPrint(4, 'DEBUG: creating fresh DN node')
        if not DNnode:
            DNnode = xmlDoc.createElementNS(namespace, 'DN')
        textNode = xmlDoc.createTextNode(certInfo['DN'])
        DNnode.appendChild(textNode)
        if not DNnode.parentNode:
            userIdentityNode.appendChild(DNnode)
        DebugPrint(4, 'DEBUG: creating fresh DN node: OK')

    # Return VO information for insertion in a common place.

    DebugPrint(4, 'DEBUG: returning VOName ' + str(certInfo['FQAN']) + ' and ReportableVOName '
               + str(certInfo['VO']))
    return {'VOName': certInfo['FQAN'], 'ReportableVOName': certInfo['VO']}


jobManagers = []

def readCertInfoLog(localJobId):
    ''' Look for and read contents of certificate log if present'''

    DebugPrint(4, 'readCertInfoLog: received (' + str(localJobId) + r')')

    global __quoteSplit

    # First get the list of accounting log file
    pattern = Config.get_CertInfoLogPattern()

    if pattern == r'': 
        return None
    logs = glob.glob(pattern)
    if not logs:
        return None

    # Sort from newest first
    logs_sorting = [(-os.path.getmtime(filename),filename) for filename in logs]
    logs_sorting.sort()
    logs = [filename for (key,filename) in logs_sorting]
    
    # Search in each log
    what="lrmsID="+str(localJobId)
    for file in logs:
        for line in open(file).readlines():
            if what in line:
               # If we could use a newer version of python (we have to work with 1.4), we could use
               # shlex:
               # res = dict(item.split('=',1) for item in shlex.split(line))
               # Newer version of python support this one line creation of the dictionary by not 1.3.4 (SL4 :()
               # res = dict(item.split('=',1) for item in __quoteSplit.findall(line))
               res = {}
               for item in __quoteSplit.findall(line):
                  split_item = item.split('=',1)
                  res[split_item[0]] = split_item[1]
               if res.has_key('lrmsID') and res['lrmsID'] == str(localJobId):
                  if res.has_key('userDN'):
                     res['DN'] = res['userDN']
                  else:
                     res['DN'] = None
                  if res.has_key('userFQAN'):
                     res['FQAN'] = res['userFQAN']
                  else:
                     res['FQAN'] = None
                  res['VO'] = None
                  DebugPrint(0, 'Warning: found valid certinfo file for '+str(localJobId)+' in the log files: ' + pattern + ' with ' + str(res))
                  return res
    DebugPrint(0, 'Warning: unable to find valid certinfo file for '+str(localJobId)+' in the log files: ' + pattern)
    return None

def readCertInfoFile(localJobId, probeName):
    ''' Look for and read contents of cert info file if present'''

    global Config
    global jobManagers
    certinfo_files = []

    DebugPrint(4, 'readCertInfo: received (' + str(localJobId) + r', ' + str(probeName) + ')')

    # Ascertain LRMS type -- from explicit set method if possible, from probe name if not

    lrms = __lrms
    if lrms == None:
        match = re.search(r'^(?P<Type>.*?):', probeName)
        if match:
            lrms = string.lower(match.group('Type'))
            DebugPrint(4, 'readCertInfo: obtained LRMS type ' + lrms + ' from ProbeName')
        elif len(jobManagers) == 0:
            DebugPrint(0,
                       'Warning: unable to ascertain lrms to match against multiple certinfo entries and no other possibilities found yet -- may be unable to resolve ambiguities'
                       )
    elif len(jobManagers) == 0:
        jobManagers.append(lrms)  # Useful default
        DebugPrint(4, 'readCertInfo: added default LRMS type ' + lrms + ' to search list')

    # Ascertain local job ID

    idMatch = __certinfoLocalJobIdMunger.search(localJobId)
    if idMatch:
        DebugPrint(4, 'readCertInfo: trimming ' + localJobId + ' to ' + idMatch.group(1))
        localJobId = idMatch.group('ID')
    if localJobId == None:  # No LocalJobId, so no dice
        return

    DebugPrint(4, 'readCertInfo: continuing to process')

    for jobManager in jobManagers:
        filestem = Config.get_DataFolder() + 'gratia_certinfo' + r'_' + jobManager + r'_' + localJobId
        DebugPrint(4, 'readCertInfo: looking for ' + filestem)
        if os.path.exists(filestem):
            certinfo_files.append(filestem)
            break
        elif os.path.exists(filestem + '.0.0'):
            certinfo_files.append(filestem + '.0.0')
            break

    if len(certinfo_files) == 1:
        DebugPrint(4, 'readCertInfo: found certinfo file ' + certinfo_files[0])
    else:
        DebugPrint(4, 'readCertInfo: globbing for certinfo file')
        certinfo_files = glob.glob(Config.get_DataFolder() + 'gratia_certinfo_*_' + localJobId + '*')
        if certinfo_files == None or len(certinfo_files) == 0:
            DebugPrint(4, 'readCertInfo: could not find certinfo files matching localJobId ' + str(localJobId))
            return None  # No files

        if len(certinfo_files) == 1:
            fileMatch = __certinfoJobManagerExtractor.search(certinfo_files[0])
            if fileMatch:
                jobManagers.insert(0, fileMatch.group(1))  # Save to short-circuit glob next time
                DebugPrint(4, 'readCertInfo: (1) saving jobManager ' + fileMatch.group(1)
                           + ' for future reference')

    result = None
    for certinfo in certinfo_files:
        found = 0  # Keep track of whether to return info for this file.
        result = None

        try:
            certinfo_doc = xml.dom.minidom.parse(certinfo)
        except Exception, e:
            DebugPrint(0, 'ERROR: Unable to parse XML file ' + certinfo, ': ', e)
            continue

        # Next, find the correct information and send it back.

        certinfo_nodes = certinfo_doc.getElementsByTagName('GratiaCertInfo')
        if certinfo_nodes.length == 1:
            if len(certinfo_files) == 1:
                found = 1  # Only had one candidate -- use it
            else:

                # Check LRMS as recorded in certinfo matches our LRMS ascertained from system or probe.

                certinfo_lrms = string.lower(GetNodeData(certinfo_nodes[0].getElementsByTagName('BatchManager'
                                             ), 0))
                DebugPrint(4, 'readCertInfo: want LRMS ' + lrms + ': found ' + certinfo_lrms)
                if certinfo_lrms == lrms:  # Match
                    found = 1
                    fileMatch = __certinfoJobManagerExtractor.search(certinfo)
                    if fileMatch:
                        jobManagers.insert(0, fileMatch.group(1))  # Save to short-circuit glob next time
                        DebugPrint(4, 'readCertInfo: saving jobManager ' + fileMatch.group(1)
                                   + ' for future reference')

            if found == 1:
                result = {'DN': GetNodeData(certinfo_nodes[0].getElementsByTagName('DN'), 0),
                          'VO': GetNodeData(certinfo_nodes[0].getElementsByTagName('VO'), 0),
                          'FQAN': GetNodeData(certinfo_nodes[0].getElementsByTagName('FQAN'), 0)}
                DebugPrint(4, 'readCertInfo: removing ' + str(certinfo))
                RemoveFile(certinfo)  # Clean up.
                break  # Done -- stop looking
        else:
            DebugPrint(0, 'ERROR: certinfo file ' + certinfo + ' does not contain one valid GratiaCertInfo node'
                       )

    if result == None:
        DebugPrint(0, 'ERROR: unable to find valid certinfo file for job ' + localJobId)
    return result


def readCertInfo(localJobId, probeName):
    ''' Look for the certifcate information for a job if available'''

    # First try the one per job CertInfo file
    result = readCertInfoFile(localJobId, probeName)
    
    if (result == None):
        # Second try the log files containing many certicate info, one per line.
        result = readCertInfoLog(localJobId)
    
    return result

def GetNode(nodeList, nodeIndex=0):
    if nodeList == None or nodeList.length <= nodeIndex:
        return None
    return nodeList.item(0)


def GetNodeData(nodeList, nodeIndex=0):
    if nodeList == None or nodeList.length <= nodeIndex or nodeList.item(0).firstChild == None:
        return None
    return nodeList.item(0).firstChild.data


def FixDN(DN):

    # Put DN into a known format: /-separated with USERID= instead of UID=

    fixedDN = string.replace(string.join(string.split(DN, r', '), r'/'), r'/UID=', r'/USERID=')
    if fixedDN[0] != r'/':
        fixedDN = r'/' + fixedDN
    return fixedDN


def DebugPrintTraceback(debugLevel=4):
    DebugPrint(4, 'In traceback print (0)')
    message = string.join(traceback.format_exception(*sys.exc_info()), r'')
    DebugPrint(4, 'In traceback print (1)')
    DebugPrint(debugLevel, message)


def genDefaultProbeName():
    f = os.popen('hostname -f')
    meterName = 'auto:' + f.read().strip()
    f.close()
    return meterName

def setProbeBatchManager(lrms):
    global __lrms
    __lrms = string.lower(lrms)

