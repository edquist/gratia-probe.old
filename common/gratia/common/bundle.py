
import re

from gratia.common.debug import DebugPrint
import gratia.common.sandbox_mgmt as sandbox_mgmt
import gratia.common.global_state as global_state
import gratia.common.response as response
import gratia.common.connect_utils as connect_utils
import gratia.common.config as config

Config = config.ConfigProxy()

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
estimatedServiceBacklog = 0

__xmlintroRemove = re.compile(r'<\?xml[^>]*\?>')

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
            (responseString, response_obj) = ProcessBundle(self)
            if response_obj.getCode() != 0:
                return (responseString, response_obj)
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
            (responseString, response_obj) = ProcessBundle(self)
            if response_obj.getCode() == response.Response.BundleNotSupported:
                return responseString, response_obj
            elif response_obj.getCode() != 0:

               # For simplicity we return here, this means that the 'incoming' record is actually
               # not processed at all this turn

                self.nLastProcessed += 1
                action()
                failedSendCount += self.nRecords
                failedHandshakes += self.nHandshakes
                failedReprocessCount += self.nReprocessed
                self.clear()
                return (responseString, response_obj)
            what = '(nested process: ' + responseString + ')' + '; ' + what
        else:
            self.nLastProcessed = 0

        self.__addContent(filename, xmlData)
        action()
        self.nBytes += len(xmlData)
        return self.checkAndSend('OK - ' + what + ' added to bundle (' + str(self.nItems) + r'/'
                                 + str(global_state.bundle_size) + ')')

    def hasFile(self, filename):
        for [name, _] in self.content:
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

        if self.nItems >= global_state.bundle_size or self.nBytes > self.__maxPostSize:
            return ProcessBundle(self)
        else:
            return (defaultmsg, response.Response(response.Response.Success, defaultmsg))

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

    global successfulHandshakes
    global successfulSendCount
    global failedHandshakes
    global failedSendCount
    global successfulReprocessCount
    global successfulBundleCount
    global failedReprocessCount
    global quarantinedFiles
    global failedBundleCount

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

    response_obj = connect_utils.sendUsageXML(Config.get_ProbeName(), bundleData, 'multiupdate')

    DebugPrint(2, 'Processing bundle Response code:  ' + str(response_obj.getCode()))
    DebugPrint(2, 'Processing bundle Response message:  ' + response_obj.getMessage())

    if response_obj.getCode() == response.Response.BundleNotSupported:
        DebugPrint(0, "Collector is too old to handle 'bundles', reverting to sending individual records.")
        global_state.bundle_size = 0
        bundle.nLastProcessed = 0
        hasHandshake = bundle.nHandshakes > 0
        bundle.clear()
        if hasHandshake:
            # Done to break circular dependency between send and bundle
            __import__("gratia.common.send").common.send.Handshake()
        else:
            sandbox_mgmt.SearchOutstandingRecord()
            # Done to break circular dependency between bundle and reprocess
            __import__("gratia.common.reprocess").common.reprocess.Reprocess()
        return 'Bundling has been canceled.', response_obj
    elif response_obj.getCode() == response.Response.PostTooLarge:
        if bundle.nItems > 1:

           # We let a large record to be added to already too many data.
           # Let's try to restrict more the size of the record

            Bundle.decreaseMaxPostSize(0.9)
            #__maxPostSize = 0.9 * Bundle.__maxPostSize
        elif bundle.nItems == 1:
            DebugPrint(0, 'Error: a record is larger than the Collector can receive. (' + str(len(bundleData)
                       * 10 / 1000 / 1000 / 10.0) + 'Mb vs 2Mb).  Record will be Quarantined.')
            quarantinedFiles += 1
            sandbox_mgmt.QuarantineFile(bundle.content[0][0], False)
        else:
            DebugPrint(0,
                       "Internal error, got a 'too large of a post' response eventhough we have no record at all!"
                       )

    responseString = 'Processed bundle with ' + str(bundle.nItems) + ' records:  ' + response_obj.getMessage()

    # Determine if the call succeeded, and remove the file if it did

    if response_obj.getCode() == 0:
        successfulSendCount += bundle.nRecords
        successfulHandshakes += bundle.nHandshakes
        successfulReprocessCount += bundle.nReprocessed
        successfulBundleCount += 1
        for item in bundle.content:
            filename = item[0]
            if filename != r'':
                DebugPrint(1, 'Bundle response indicates success, ' + filename + ' will be deleted')
                sandbox_mgmt.RemoveRecordFile(filename)
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

    return responseString, response_obj

