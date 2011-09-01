#@(#)gratia/probe/glue:$HeadURL: https://gratia.svn.sourceforge.net/svnroot/gratia/trunk/probe/glue/Subcluster.py $:$Id: Subcluster.py 3000 2009-02-16 16:15:08Z pcanal $

## Updated by Brian Bockelman, University of Nebraska-Lincoln (http://rcf.unl.edu)

import types

import gratia.common.GratiaCore
from gratia.common.GratiaCore import *

class Subcluster(GratiaCore.Record):
    "Base class for the Gratia Subcluster"

    def __init__(self):
        # Initializer
        super(self.__class__, self).__init__()
        DebugPrint(0, "Creating a Subcluster Record"+TimeToString())

    def Print(self):
        DebugPrint(1, "Subcluster: ", self)
        
    def XmlAddMembers(self):
        """
        This should add the value of the 'data' member of Subcluster
        (as opposed to the information entered directly into self.RecordData
        """
        super(self.__class__, self).XmlAddMembers()

    def XmlCreate(self):
        global RecordId

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<Subcluster xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(RecordPid)+"."+str(RecordId)+"\" urwg:createTime=\""+TimeToString(time.gmtime())+"\" />\n")
        RecordId = RecordId + 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</Subcluster>\n")

    def UniqueID(self, value):
        "GlueSubClusterUniqueID"
        self.RecordData = self.AddToList(self.RecordData, "UniqueID", "", value)
        
    def Name(self, value):
        "GlueSubClusterName"
        self.RecordData = self.AddToList(self.RecordData, "Name", "", value)
        
    def Cluster(self, value):
        """
        GlueClusterName
        """
        self.RecordData = self.AddToList(self.RecordData, "Cluster", "", value)
       
    def Platform(self, value):
        """
        Processor Platform
        """
        self.RecordData = self.AddToList(self.RecordData, "Platform", "", value)
 
    def OS(self, value):
        """
        GlueHostOperatingSystemName
        """
        self.RecordData = self.AddToList(self.RecordData, "OS", "", value)

    def OSVersion(self, value):
        """
        GlueHostOperatingSystemRelease
        """
        self.RecordData = self.AddToList(self.RecordData, "OSVersion", "", value)

    def Timestamp(self, value):
        """ The time the record was gathered
        Expressed in number of second since epoch or a string formated using the format xsd:dateTime. """
        if isinstance(value, types.StringType):
            realvalue = value
        else:
            realvalue = TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "Timestamp", "", realvalue)
        
    def Cores(self, value):
        """
        Cores
        """
        self.RecordData = self.AddToList(self.RecordData, "Cores", "", str(value))
 
    def Hosts(self, value):
        """
        Hosts
        """
        self.RecordData = self.AddToList(self.RecordData, "Hosts", "", str(value))
 
    def Cpus(self, value):
        """
        GlueCEPolicyMaxRunningJobs
        """
        self.RecordData = self.AddToList(self.RecordData, "Cpus", "", str(value))
 
    def RAM(self, value):
        """
        RAM
        """
        self.RecordData = self.AddToList(self.RecordData, "RAM", "", str(value))
 
    def Processor(self, value):
        """
        Processor name (from /etc/cpuinfo)
        """
        self.RecordData = self.AddToList(self.RecordData, "Processor", "", str(value))
 
    def BenchmarkName(self, value):
        """
        Name of benchmark measurement recorded
        """
        self.RecordData = self.AddToList(self.RecordData, "BenchmarkName", "", value)
 
    def BenchmarkValue(self, value):
        """
        Value of benchmark measurement recorded
        """
        self.RecordData = self.AddToList(self.RecordData, "BenchmarkValue", "", str(value))


def getSubclusters(xmlDoc):
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'Subcluster')

def SubclusterCheckXmldoc(xmlDoc, external, resourceType = None):
    """
    Fill in missing field in the xml document if needed
    If external is true, also check for ProbeName, SiteName
    """

    if not xmlDoc.documentElement:
        return 0 # Major problem

    # Local namespace
    # namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    for subClusterNode in getSubclusters(xmlDoc):
        # Local namespace and prefix, if any
        prefix = ""
        for child in subClusterNode.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                child.prefix:
                prefix = child.prefix + ":"
                break
                               
        StandardCheckXmldoc(xmlDoc, subClusterNode, external, prefix)
            
    return len(getSubclusters(xmlDoc))

XmlRecordCheckers.append(SubclusterCheckXmldoc)


         
