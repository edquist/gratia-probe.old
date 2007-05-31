#@(#)gratia/probe/metric:$Name: not supported by cvs2svn $:$Id: Metric.py,v 1.2 2007-05-31 17:42:00 pcanal Exp $

import Gratia
from Gratia import *

class MetricRecord(Gratia.Record):
    "Base class for the Gratia Metric Record"
    "See https://twiki.cern.ch/twiki/bin/view/LCG/GridMonitoringProbeSpecification for information of the information content"

    def __init__(self):
        # Initializer
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a metric Record "+TimeToString())

    def Print(self) :
        DebugPrint(1,"Metric Record: ",self)
        
    def XmlAddMembers(self):
        " This should add the value of the 'data' member of MetricRecord "
        " (as opposed to the information entered directly into self.RecordData "
        super(self.__class__,self).XmlAddMembers()
        self.RecordData = self.XmlAddGrid(self.RecordData)


    def XmlCreate(self):
        global RecordId

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<MetricRecord xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(RecordPid)+"."+str(RecordId)+"\" urwg:createTime=\""+TimeToString(time.gmtime())+"\" />\n")
        RecordId = RecordId + 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</MetricRecord>\n")

    def MetricName(self,value):
        " The name of the metric "
        self.RecordData = self.AddToList(self.RecordData, "MetricName", "", value)
        
    def MetricStatus(self,value):
        " This determines the status of a particular subset of functionality of the service. "
        " It is returned from the probe with key metricStatus. It uses a set of standard status values to categorize this "
        " OK, WARNING, CRITICAL, UNKNOWN "
        self.RecordData = self.AddToList(self.RecordData, "MetricStatus", "", value)
        
    def Timestamp(self,value):
        " The time the metric was gathered "
        " Expressed in number of second since epoch or a string formated using the format xsd:dateTime. "
        if type(value)==str : realvalue = value
        else : realvalue = TimeToString(time.gmtime(value))
#        self.AppendToList(self.RecordData, "Timestamp", self.Type(timetype)+self.Description(description), realvalue)
        self.AppendToList(self.RecordData, "Timestamp", "", realvalue)
        
        
def getMetricRecords(xmlDoc):
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'MetricRecord')

def MetricCheckXmldoc(xmlDoc,external):
    " Fill in missing field in the xml document if needed "
    " If external is true, also check for ProbeName, SiteName "

    # Local namespace
    namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    for usageRecord in getMetricRecords(xmlDoc):
        # Local namespace and prefix, if any
        prefix = ""
        for child in usageRecord.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                child.prefix:
                prefix = child.prefix + ":"
                break
                
        GridNodes = usageRecord.getElementsByTagNameNS(namespace, 'Grid')
        if not GridNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'Grid')
            textNode = xmlDoc.createTextNode(Gratia.Config.get_Grid())
            node.appendChild(textNode)
            usageRecord.appendChild(node)
        elif len(GridNodes) > 1:
            [jobIdType, jobId] = FindBestJobId(usageRecord, namespace, prefix)
            DebugPrint(0, "Warning: too many Grid entities in " + jobIdType + " " +
                               jobId + "(" + xmlFilename + ")");
                               
        StandardCheckXmldoc(xmlDoc,usageRecord,external)
            
    return len(getMetricRecords(xmlDoc))

XmlRecordCheckers.append(MetricCheckXmldoc)


         