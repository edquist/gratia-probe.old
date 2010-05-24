#@(#)gratia/probe/glue:$HeadURL: https://gratia.svn.sourceforge.net/svnroot/gratia/trunk/probe/glue/StorageElementRecord.py $:$Id: StorageElementRecord.py 3000 2009-02-16 16:15:08Z pcanal $

## Updated by Brian Bockelman, University of Nebraska-Lincoln (http://rcf.unl.edu)

import types

import GratiaCore
from GratiaCore import *

class StorageElementRecord(GratiaCore.Record):
    "Base class for the Gratia StorageElementRecord"

    def __init__(self):
        # Initializer
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a StorageElementRecord Record"+TimeToString())

    def Print(self):
        DebugPrint(1,"StorageElementRecord: ",self)
        
    def XmlAddMembers(self):
        " This should add the value of the 'data' member of StorageElementRecord "
        " (as opposed to the information entered directly into self.RecordData "
        super(self.__class__,self).XmlAddMembers()

    def XmlCreate(self):
        global RecordId

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<StorageElementRecord xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(RecordPid)+"."+str(RecordId)+"\" urwg:createTime=\""+TimeToString(time.gmtime())+"\" />\n")
        RecordId = RecordId + 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</StorageElementRecord>\n")

    def UniqueID(self,value):
        "Storage space UniqueID"
        self.RecordData = self.AddToList(self.RecordData, "UniqueID", "", value)
        
    def MeasurementType(self,value):
        """
        Measurement type
        """
        self.RecordData = self.AddToList(self.RecordData, "MeasurementType", "", value)

    def StorageType(self,value):
        """
        Space type
        """
        self.RecordData = self.AddToList(self.RecordData, "StorageType", "", value)

    def Timestamp(self,value):
        " The time the GlueCE was gathered "
        " Expressed in number of second since epoch or a string formated using the format xsd:dateTime. "
        if isinstance(value, types.StringType):
            realvalue = value
        else:
            realvalue = TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "Timestamp", "", realvalue)
        
    def TotalSpace(self,value):
        """
        Total space (GB)
        """
        self.RecordData = self.AddToList(self.RecordData, "TotalSpace", "", str(value))
 
    def FreeSpace(self,value):
        """
        Free space (GB)
        """
        self.RecordData = self.AddToList(self.RecordData, "FreeSpace", "", str(value))
 
    def UsedSpace(self,value):
        """
        Used space (GB)
        """
        self.RecordData = self.AddToList(self.RecordData, "UsedSpace", "", str(value)) 

    def FileCountLimit(self,value):
        """
        Number of files that can be stored in this space.
        """
        self.RecordData = self.AddToList(self.RecordData, "FileCountLimit", "", str(value))
 
    def FileCount(self,value):
        """
        Number of files currently in this space.
        """
        self.RecordData = self.AddToList(self.RecordData, "FileCount", "", str(value))

def getStorageElementRecords(xmlDoc):
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'StorageElementRecord')

def StorageElementRecordCheckXmldoc(xmlDoc,external,resourceType = None):
    " Fill in missing field in the xml document if needed "
    " If external is true, also check for ProbeName, SiteName "

    if not xmlDoc.documentElement:
        return 0 # Major problem

    # Local namespace
    namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    for StorageElementRecord in getStorageElementRecords(xmlDoc):
        # Local namespace and prefix, if any
        prefix = ""
        for child in StorageElementRecord.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                child.prefix:
                prefix = child.prefix + ":"
                break
                               
        StandardCheckXmldoc(xmlDoc,StorageElementRecord,external,prefix)
            
    return len(getStorageElementRecords(xmlDoc))

XmlRecordCheckers.append(StorageElementRecordCheckXmldoc)


         
