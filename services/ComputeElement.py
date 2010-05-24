#@(#)gratia/probe/glue:$HeadURL: https://gratia.svn.sourceforge.net/svnroot/gratia/trunk/probe/glue/ComputeElement.py $:$Id: ComputeElement.py 3000 2009-02-16 16:15:08Z pcanal $

## Updated by Brian Bockelman, University of Nebraska-Lincoln (http://rcf.unl.edu)

import types

import GratiaCore
from GratiaCore import *

class ComputeElement(GratiaCore.Record):
    "Base class for the Gratia ComputeElement"

    def __init__(self):
        # Initializer
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a ComputeElement Record"+TimeToString())

    def Print(self):
        DebugPrint(1,"ComputeElement: ",self)
        
    def XmlAddMembers(self):
        " This should add the value of the 'data' member of ComputeElement "
        " (as opposed to the information entered directly into self.RecordData "
        super(self.__class__,self).XmlAddMembers()

    def XmlCreate(self):
        global RecordId

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<ComputeElement xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(RecordPid)+"."+str(RecordId)+"\" urwg:createTime=\""+TimeToString(time.gmtime())+"\" />\n")
        RecordId = RecordId + 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</ComputeElement>\n")

    def UniqueID(self,value):
        "The value of GlueCEUniqueID"
        self.RecordData = self.AddToList(self.RecordData, "UniqueID", "", value)
        
    def CEName(self,value):
        "The value of GlueCEName"
        self.RecordData = self.AddToList(self.RecordData, "CEName", "", value)
        
    def Cluster(self,value):
        """
        GlueCEHostingCluster
        """
        self.RecordData = self.AddToList(self.RecordData, "Cluster", "", value)
       
    def HostName(self,value):
        """
        GlueCEInfoHostName
        """
        self.RecordData = self.AddToList(self.RecordData, "HostName", "", value)
 
    def Timestamp(self,value):
        " The time the GlueCE was gathered "
        " Expressed in number of second since epoch or a string formated using the format xsd:dateTime. "
        if isinstance(value, types.StringType):
            realvalue = value
        else:
            realvalue = TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "Timestamp", "", realvalue)
        
    def LrmsType(self,value):
        """
        GlueCEInfoLRMSType
        """
        self.RecordData = self.AddToList(self.RecordData, "LrmsType", "", value)
 
    def LrmsVersion(self,value):
        """
        GlueCEInfoLRMSVersion
        """
        self.RecordData = self.AddToList(self.RecordData, "LrmsVersion", "", value)
 
    def MaxRunningJobs(self,value):
        """
        GlueCEPolicyMaxRunningJobs
        """
        self.RecordData = self.AddToList(self.RecordData, "MaxRunningJobs", "", str(value))
 
    def MaxTotalJobs(self,value):
        """
        GlueCEPolicyMaxTotalJobs
        """
        self.RecordData = self.AddToList(self.RecordData, "MaxTotalJobs", "", str(value))
 
    def AssignedJobSlots(self,value):
        """
        GlueCEPolicyAssignedJobSlots
        """
        self.RecordData = self.AddToList(self.RecordData, "AssignedJobSlots", "", str(value))
 
    def Status(self,value):
        """
        GlueCEStateStatus
        """
        self.RecordData = self.AddToList(self.RecordData, "Status", "", value)
 

def getComputeElements(xmlDoc):
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'ComputeElement')

def ComputeElementCheckXmldoc(xmlDoc,external,resourceType = None):
    " Fill in missing field in the xml document if needed "
    " If external is true, also check for ProbeName, SiteName "

    if not xmlDoc.documentElement:
        return 0 # Major problem

    # Local namespace
    namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    for computeElementDescription in getComputeElements(xmlDoc):
        # Local namespace and prefix, if any
        prefix = ""
        for child in computeElementDescription.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                child.prefix:
                prefix = child.prefix + ":"
                break
                               
        StandardCheckXmldoc(xmlDoc,computeElementDescription,external,prefix)
            
    return len(getComputeElements(xmlDoc))

XmlRecordCheckers.append(ComputeElementCheckXmldoc)


         
