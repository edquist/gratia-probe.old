#!/usr/bin/python
# -*- coding: utf-8 -*-
# @(#)gratia/probe/common:$HeadURL$:$Id$

"""
Gratia Job Usage Record Library
"""

import gratia.common.GratiaCore as GratiaCore
import re
import socket
import string
import time
import xml

# For Backward compatibility
from gratia.common.GratiaCore import Send
from gratia.common.GratiaCore import SendStatus
from gratia.common.GratiaCore import SendXMLFiles
from gratia.common.GratiaCore import Reprocess
from gratia.common.GratiaCore import ProcessBundle
from gratia.common.GratiaCore import DebugPrint
from gratia.common.GratiaCore import DebugPrintTraceback
from gratia.common.GratiaCore import Error

from gratia.common.GratiaCore import ProbeConfiguration
from gratia.common.GratiaCore import Record
from gratia.common.GratiaCore import ProbeDetails
from gratia.common.GratiaCore import TimeToString
from gratia.common.GratiaCore import escapeXML
from gratia.common.GratiaCore import Mkdir

class ConfigProxy:
    def __getattr__(self, attrname):
        return getattr(GratiaCore.Config, attrname)

class BundleProxy:
    def __getattr__(self, attrname):
        return getattr(GratiaCore.CurrentBundle, attrname)

class RecordPidProxy:
    def __str__(self):
        return str(GratiaCore.RecordPid)
      
Config = ConfigProxy()
CurrentBundle = BundleProxy()
RecordPid = RecordPidProxy()

from gratia.common.GratiaCore import XmlRecordCheckers

from gratia.common.GratiaCore import StandardCheckXmldoc
from gratia.common.GratiaCore import RegisterReporterLibrary
from gratia.common.GratiaCore import RegisterReporter
from gratia.common.GratiaCore import RegisterService
from gratia.common.GratiaCore import ExtractCvsRevision
from gratia.common.GratiaCore import ExtractCvsRevisionFromFile
from gratia.common.GratiaCore import ExtractSvnRevision
from gratia.common.GratiaCore import ExtractSvnRevisionFromFile
from gratia.common.GratiaCore import Initialize
from gratia.common.GratiaCore import Maintenance
from gratia.common.GratiaCore import setProbeBatchManager
from gratia.common.GratiaCore import pythonVersionRequire


# Privates globals


class UsageRecord(Record):

    '''Base class for the Gratia Usage Record'''

    JobId = []
    UserId = []
    __Njobs = 1
    __NjobsDescription = r''
    __ResourceType = None

    def __init__(self, resourceType=None):

        # See the function ResourceType for details on the
        # parameter

        super(self.__class__, self).__init__()
        DebugPrint(1, 'Creating a UsageRecord ' + TimeToString())
        self.JobId = []
        self.UserId = []
        self.Username = 'none'
        self.__ResourceType = resourceType

    def Metric(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if len(value) > 0:
            return 'urwg:metric="' + value + '" '
        else:
            return r''

    def Unit(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if len(value) > 0:
            return 'urwg:unit="' + value + '" '
        else:
            return r''

    def StorageUnit(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if len(value) > 0:
            return 'urwg:storageUnit="' + value + '" '
        else:
            return r''

    def PhaseUnit(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if type(value) == str:
            realvalue = value
        else:
            realvalue = self.Duration(value)
        if len(realvalue) > 0:
            return 'urwg:phaseUnit="' + realvalue + '" '
        else:
            return r''

    def Type(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if len(value) > 0:
            return 'urwg:type="' + value + '" '
        else:
            return r''

    def UsageType(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if len(value) > 0:
            return 'urwg:usageType="' + value + '" '
        else:
            return r''

    # Public Interface:

    def LocalJobId(self, value):
        self.JobId = self.AddToList(self.JobId, 'LocalJobId', r'', value)

    def GlobalJobId(self, value):
        self.JobId = self.AddToList(self.JobId, 'GlobalJobId', r'', value)

    def ProcessId(self, value):
        self.JobId = self.AddToList(self.JobId, 'ProcessId', r'', str(value))

    def GlobalUsername(self, value):
        self.UserId = self.AddToList(self.UserId, 'GlobalUsername', r'', value)

    def LocalUserId(self, value):
        self.UserId = self.AddToList(self.UserId, 'LocalUserId', r'', value)

    def UserKeyInfo(self, value):  # NB This is deprecated in favor of DN, below.
        ''' Example:
            <ds:KeyInfo xmlns:ds=http://www.w3.org/2000/09/xmldsig#>
                <ds:X509Data>
                <ds:X509SubjectName>CN=john ainsworth, L=MC, OU=Manchester, O=eScience, C=UK</ds:X509SubjectName>
                </ds:X509Data>
            </ds:KeyInfo>
        '''

        complete = '''
\t\t<ds:X509Data>
\t\t<ds:X509SubjectName>''' + escapeXML(value) \
            + '''</ds:X509SubjectName>
\t\t</ds:X509Data>
\t'''
        self.UserId = self.VerbatimAddToList(self.UserId, 'ds:KeyInfo',
                                             'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" ', complete)

    def DN(self, value):
        self.UserId = self.AddToList(self.UserId, 'DN', r'', value)

    def VOName(self, value):
        self.UserId = self.AddToList(self.UserId, 'VOName', r'', value)

    def ReportableVOName(self, value):
        ''' Set reportable VOName'''

        self.UserId = self.AddToList(self.UserId, 'ReportableVOName', r'', value)

    def JobName(self, value, description=r''):
        self.RecordData = self.AddToList(self.RecordData, 'JobName', self.Description(description), value)

    def Charge(
        self,
        value,
        unit=r'',
        formula=r'',
        description=r'',
        ):
        if len(formula) > 0:
            formulaStr = 'formula="' + formula + '" '
        else:
            formulaStr = r''
        self.RecordData = self.AddToList(self.RecordData, 'Charge', self.Description(description)
                                         + self.Unit(unit) + formulaStr, value)

    def Status(self, value, description=r''):
        self.RecordData = self.AddToList(self.RecordData, 'Status', self.Description(description), str(value))

    def WallDuration(self, value, description=r''):
        if type(value) == str:
            realvalue = value
        else:
            realvalue = self.Duration(value)
        self.RecordData = self.AddToList(self.RecordData, 'WallDuration', self.Description(description),
                                         realvalue)

    def CpuDuration(
        self,
        value,
        cputype,
        description=r'',
        ):
        """Register a total cpu duration.  cputype must be either 'user' or 'system'"""

        if type(value) == str:
            realvalue = value
        else:
            realvalue = self.Duration(value)
        if cputype == 'sys':
            cputype = 'system'
        if cputype != 'user' and cputype != 'system':
            description = '(type=' + cputype + ') ' + description
            cputype = r''
        self.RecordData = self.AppendToList(self.RecordData, 'CpuDuration', self.UsageType(cputype)
                                            + self.Description(description), realvalue)

    def EndTime(self, value, description=r''):
        if type(value) == str:
            realvalue = value
        else:
            realvalue = TimeToString(time.gmtime(value))
        self.RecordData = self.AddToList(self.RecordData, 'EndTime', self.Description(description), realvalue)

    def StartTime(self, value, description=r''):
        if type(value) == str:
            realvalue = value
        else:
            realvalue = TimeToString(time.gmtime(value))
        self.RecordData = self.AddToList(self.RecordData, 'StartTime', self.Description(description), realvalue)

    def TimeDuration(
        self,
        value,
        timetype,
        description=r'',
        ):
        ''' Additional measure of time duration that is relevant to the reported usage '''

        if type(value) == str:
            realvalue = value
        else:
            realvalue = self.Duration(value)
        self.AppendToList(self.RecordData, 'TimeDuration', self.Type(timetype) + self.Description(description),
                          realvalue)

    def TimeInstant(
        self,
        value,
        timetype,
        description=r'',
        ):
        ''' Additional identified discrete time that is relevant to the reported usage '''

        if type(value) == str:
            realvalue = value
        else:
            realvalue = TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, 'TimeInstant', self.Type(timetype) + self.Description(description),
                          realvalue)

    def MachineName(self, value, description=r''):
        self.RecordData = self.AddToList(self.RecordData, 'MachineName', self.Description(description), value)

    def Host(
        self,
        value,
        primary=False,
        description=r'',
        ):
        if primary:
            pstring = 'primary="true" '
        else:
            pstring = 'primary="false" '
        pstring = pstring + self.Description(description)
        self.RecordData = self.AddToList(self.RecordData, 'Host', pstring, value)

    def SubmitHost(self, value, description=r''):
        self.RecordData = self.AddToList(self.RecordData, 'SubmitHost', self.Description(description), value)

    def Queue(self, value, description=r''):
        self.RecordData = self.AddToList(self.RecordData, 'Queue', self.Description(description), value)

    def ProjectName(self, value, description=r''):
        self.RecordData = self.AddToList(self.RecordData, 'ProjectName', self.Description(description), value)

    def Network(
        self,
        value,
        storageUnit=r'',
        phaseUnit=r'',
        metric='total',
        description=r'',
        ):
        """ Metric should be one of 'total','average','max','min' """

        self.AppendToList(self.RecordData, 'Network', self.StorageUnit(storageUnit) + self.PhaseUnit(phaseUnit)
                          + self.Metric(metric) + self.Description(description), str(value))

    def Disk(
        self,
        value,
        storageUnit=r'',
        phaseUnit=r'',
        disktype=r'',
        metric='total',
        description=r'',
        ):
        """ Metric should be one of 'total','average','max','min' """

        self.AppendToList(self.RecordData, 'Disk', self.StorageUnit(storageUnit) + self.PhaseUnit(phaseUnit)
                          + self.Type(disktype) + self.Metric(metric) + self.Description(description), str(value))

    def Memory(
        self,
        value,
        storageUnit=r'',
        phaseUnit=r'',
        memorytype=r'',
        metric='total',
        description=r'',
        ):
        """ Metric should be one of 'total','average','max','min' """

        self.AppendToList(self.RecordData, 'Memory', self.StorageUnit(storageUnit) + self.PhaseUnit(phaseUnit)
                          + self.Type(memorytype) + self.Metric(metric) + self.Description(description), str(value))

    def Swap(
        self,
        value,
        storageUnit=r'',
        phaseUnit=r'',
        swaptype=r'',
        metric='total',
        description=r'',
        ):
        """ Metric should be one of 'total','average','max','min' """

        self.AppendToList(self.RecordData, 'Swap', self.StorageUnit(storageUnit) + self.PhaseUnit(phaseUnit)
                          + self.Type(swaptype) + self.Metric(metric) + self.Description(description), str(value))

    def NodeCount(
        self,
        value,
        metric='total',
        description=r'',
        ):
        """ Metric should be one of 'total','average','max','min' """

        self.AppendToList(self.RecordData, 'NodeCount', self.Metric(metric) + self.Description(description),
                          str(value))

    def Processors(
        self,
        value,
        consumptionRate=0,
        metric='total',
        description=r'',
        ):
        """ Metric should be one of 'total','average','max','min' """

        if consumptionRate > 0:
            pstring = 'consumptionRate="' + str(consumptionRate) + '" '
        else:
            pstring = r''
        self.AppendToList(self.RecordData, 'Processors', pstring + self.Metric(metric)
                          + self.Description(description), str(value))

    def ServiceLevel(
        self,
        value,
        serviceLevelType=r'',
        description=r'',
        servicetype=r'' # Obsolete use serviceLevelType instead.
        ):
        if ( serviceLevelType == r'' ) :
           serviceLevelType = servicetype
        self.AppendToList(self.RecordData, 'ServiceLevel', self.Type(servicetype) + self.Description(description),
                          str(value))

    def Resource(self, description, value):
        self.AppendToList(self.RecordData, 'Resource', self.Description(description), str(value))

    def AdditionalInfo(self, description, value):
        self.Resource(description, value)

    # The following are not officially part of the Usage Record format

    def Njobs(self, value, description=r''):
        self.__Njobs = value
        self.__NjobsDescription = description

    def ResourceType(self, value):
        ''' Indicate the type of resource this record has been generated on.'''

        self.__ResourceType = value

    # The following usually comes from the Configuration file

    def XmlAddMembers(self):
        super(self.__class__, self).XmlAddMembers()
        self.GenericAddToList('Njobs', str(self.__Njobs), self.__NjobsDescription)
        if self.__ResourceType != None:
            self.Resource('ResourceType', self.__ResourceType)

    def VerifyUserInfo(self):
        ''' Verify user information: check for LocalUserId and add VOName and ReportableVOName if necessary'''

        id_info = {}  # Store attributes of already-present information
        interesting_keys = ['LocalUserId', 'VOName', 'ReportableVOName']
        for wanted_key in interesting_keys:  # Loop over wanted keys
            item_index = 0
            for id_item in self.UserId:  # Loop over existing entries in UserId block

            # Look for key

                match = re.search(r'<\s*(?:[^:]*:)?' + wanted_key + r'\s*>\s*(?P<Value>.*?)\s*<\s*/', id_item,
                                  re.IGNORECASE)

                # Store info

                if match:
                    id_info[wanted_key] = {'Value': match.group('Value'), 'Index': item_index}
                    break

                item_index += 1

        if not id_info.has_key('LocalUserId') or len(id_info) == len(interesting_keys):  # Nothing to do
            return

        # Obtain user->VO info from reverse gridmap file.

        vo_info = GratiaCore.VOfromUser(id_info['LocalUserId']['Value'])
        if vo_info != None:

            # If we already have one of the two, update both to remain consistent.

            for key in ('VOName', 'ReportableVOName'):
                if id_info.has_key(key):  # Replace existing value
                    self.UserId[id_info[key]['Index']] = re.sub(r'(>\s*)' + re.escape(id_info[key]['Value'])
                            + r'(\s*<)', r'\1' + vo_info[key] + r'\2', self.UserId[id_info[key]['Index']], 1)
                else:

                      # Add new

                    self.UserId = self.AddToList(self.UserId, key, r'', vo_info[key])

    def XmlCreate(self):

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.XmlData.append('<JobUsageRecord xmlns="http://www.gridforum.org/2003/ur-wg"\n')
        self.XmlData.append('        xmlns:urwg="http://www.gridforum.org/2003/ur-wg"\n')
        self.XmlData.append('        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \n')
        self.XmlData.append('        xsi:schemaLocation="http://www.gridforum.org/2003/ur-wg file:///u:/OSG/urwg-schema.11.xsd">\n'
                            )

        # Add the record indentity

        self.XmlData.append('<RecordIdentity urwg:recordId="' + socket.getfqdn() + ':' + str(RecordPid) + '.'
                            + str(GratiaCore.RecordId) + '" urwg:createTime="' + TimeToString(time.gmtime()) + '" />\n')
        GratiaCore.RecordId = GratiaCore.RecordId + 1
 
        if len(self.JobId) > 0:
            self.XmlData.append('<JobIdentity>\n')
            for data in self.JobId:
                self.XmlData.append('\t')
                self.XmlData.append(data)
                self.XmlData.append('\n')
            self.XmlData.append('</JobIdentity>\n')

        if len(self.UserId) > 0:
            self.VerifyUserInfo()  # Add VOName and Reportable VOName if necessary.
            self.XmlData.append('<UserIdentity>\n')
            for data in self.UserId:
                self.XmlData.append('\t')
                self.XmlData.append(data)
                self.XmlData.append('\n')
            self.XmlData.append('</UserIdentity>\n')
        for data in self.RecordData:
            self.XmlData.append('\t')
            self.XmlData.append(data)
            self.XmlData.append('\n')
        self.XmlData.append('</JobUsageRecord>\n')

def getUsageRecords(xmlDoc):
    if not xmlDoc.documentElement:  # Major problem
        return []
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'UsageRecord') + xmlDoc.getElementsByTagNameNS(namespace,
            'JobUsageRecord')

def UsageCheckXmldoc(xmlDoc, external, resourceType=None):
    '''Fill in missing field in the xml document if needed'''

    DebugPrint(4, 'DEBUG: In UsageCheckXmldoc')
    DebugPrint(4, 'DEBUG: Checking xmlDoc integrity')
    if not xmlDoc.documentElement:  # Major problem
        return 0
    DebugPrint(4, 'DEBUG: Checking xmlDoc integrity: OK')
    DebugPrint(4, 'DEBUG: XML record to send: \n' + xmlDoc.toxml())

    # Local namespace

    namespace = xmlDoc.documentElement.namespaceURI

    # Loop over (posibly multiple) jobUsageRecords

    DebugPrint(4, 'DEBUG: About to examine individual UsageRecords')
    for usageRecord in getUsageRecords(xmlDoc):
        DebugPrint(4, 'DEBUG: Examining UsageRecord')
        DebugPrint(4, 'DEBUG: Looking for prefix')

        # Local namespace and prefix, if any

        prefix = r''
        for child in usageRecord.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and child.prefix:
                prefix = child.prefix + ':'
                break

        DebugPrint(4, 'DEBUG: Looking for prefix: ' + prefix)

        GratiaCore.StandardCheckXmldoc(xmlDoc, usageRecord, external, prefix)

        # Add ResourceType if appropriate

        if external and resourceType != None:
            DebugPrint(4, 'DEBUG: Adding missing resourceType ' + str(resourceType))
            GratiaCore.AddResourceIfMissingKey(
                xmlDoc,
                usageRecord,
                namespace,
                prefix,
                'ResourceType',
                resourceType,
                )

        # Identity info check

        VOName = None
        id_info = {}

        DebugPrint(4, 'DEBUG: Finding userIdentityNodes')
        userIdentityNodes = usageRecord.getElementsByTagNameNS(namespace, 'UserIdentity')
        DebugPrint(4, 'DEBUG: Finding userIdentityNodes (processing)')
        if not userIdentityNodes:
            DebugPrint(4, 'DEBUG: Finding userIdentityNodes: 0')
            [jobIdType, jobId] = GratiaCore.FindBestJobId(usageRecord, namespace)
            DebugPrint(0, 'Warning: no UserIdentity block in ' + jobIdType + ' ' + jobId)
        else:
            try:
                DebugPrint(4, 'DEBUG: Finding userIdentityNodes (processing 2)')
                DebugPrint(4, 'DEBUG: Finding userIdentityNodes: ' + str(userIdentityNodes.length))
                if userIdentityNodes.length > 1:
                    [jobIdType, jobId] = GratiaCore.FindBestJobId(usageRecord, namespace)
                    DebugPrint(0, 'Warning: too many UserIdentity blocks  in ' + jobIdType + ' ' + jobId)

                DebugPrint(4, 'DEBUG: Call CheckAndExtendUserIdentity')
                id_info = GratiaCore.CheckAndExtendUserIdentity(xmlDoc, userIdentityNodes[0], namespace, prefix)
                DebugPrint(4, 'DEBUG: Call CheckAndExtendUserIdentity: OK')
                ResourceType = GratiaCore.FirstResourceMatching(xmlDoc, usageRecord, namespace, prefix, 'ResourceType')
                DebugPrint(4, 'DEBUG: Read ResourceType as ' + str(ResourceType))
                if Config.get_NoCertinfoBatchRecordsAreLocal() and ResourceType and ResourceType == 'Batch' \
                    and not (id_info.has_key('has_certinfo') and id_info['has_certinfo']):

                    # Set grid local

                    DebugPrint(4, 'DEBUG: no certinfo: setting grid to Local')
                    GratiaCore.UpdateOrInsertElement(
                        xmlDoc,
                        usageRecord,
                        namespace,
                        prefix,
                        'Grid',
                        'Local',
                        )
                if id_info.has_key('VOName'):
                    VOName = id_info['VOName']
            except Exception, e:
                DebugPrint(0, 'DEBUG: Caught exception: ', e)
                DebugPrintTraceback()
                raise

        # If we are trying to handle only GRID jobs, optionally suppress records.
        #
        # Order of preference from the point of view of data integrity:
        #
        # 1. With grid set to Local (modern condor probe (only) detects
        # attribute inserted in ClassAd by Gratia JobManager patch found
        # in OSG 1.0+).
        #
        # 2, Missing DN (preferred, but requires JobManager patch and
        # could miss non-delegated WS jobs).
        #
        # 3. A null or unknown VOName (prone to suppressing jobs we care
        # about if osg-user-vo-map.txt is not well-cared-for).

        reason = None
        grid = GratiaCore.GetElement(xmlDoc, usageRecord, namespace, prefix, 'Grid')
        if Config.get_SuppressgridLocalRecords() and grid and string.lower(grid) == 'local':

            # 1

            reason = 'Grid == Local'
        elif Config.get_SuppressNoDNRecords() and not usageRecord.getElementsByTagNameNS(namespace, 'DN'):

            # 2

            reason = 'missing DN'
        elif Config.get_SuppressUnknownVORecords() and (not VOName or VOName == 'Unknown'):

            # 3

            reason = 'unknown or null VOName'

        if reason:
            [jobIdType, jobId] = GratiaCore.FindBestJobId(usageRecord, namespace)
            DebugPrint(0, 'Info: suppressing record with ' + jobIdType + ' ' + jobId + ' due to ' + reason)
            usageRecord.parentNode.removeChild(usageRecord)
            usageRecord.unlink()
            continue

    return len(getUsageRecords(xmlDoc))


def LocalJobId(record, value):
    record.LocalJobId(value)


def GlobalJobId(record, value):
    record.GlobalJobId(value)


def ProcessJobId(record, value):
    record.ProcessJobId(value)

XmlRecordCheckers.append(UsageCheckXmldoc)

