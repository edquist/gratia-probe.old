#!/usr/bin/env python

import os
import re
import sys
import time
import socket
import datetime
import optparse
import ConfigParser
import GratiaConnector
import Gratia
import XmlBuilder

# Bootstrap hadoop
if 'JAVA_HOME' not in os.environ:
    os.environ['JAVA_HOME'] = '/usr/java/default'

class Config(Gratia.ProbeConfiguration):

      def __init__(self):
          Gratia.ProbeConfiguration.__init__(self)

      def __getattr__(self,name):
          return self.getConfigAttribute(name)

def configure():
    cp = Config()

    gratia_path = None

    for pathElement in sys.path:
       if ( pathElement.find("probe/common") != -1 ):
           gratia_path = pathElement+"/../../"
           break

    if ( gratia_path == None ):
      raise Exception("gratia_path can not be determined from python path")

    if not os.path.exists(gratia_path):
       raise Exception("GratiaLocation attribute in ProbeConfig file must point to the corrent gratie probe directory")

    cp.GratiaLocation = gratia_path

    os.environ['CLASSPATH'] = gratia_path+"/probe/common/jlib/xalan.jar:"+gratia_path+"/probe/common/jlib/serializer.jar"

    sys.path.append(gratia_path+"/probe/services")
    return cp

def _get_se(cp):
    try:
        return cp.SiteName
    except:
        pass
    try:
        return socket.getfqdn()
    except:
        return 'Unknown'

_my_se = None
def get_se(cp):
    global _my_se
    if _my_se:
        return _my_se
    _my_se = _get_se(cp)
    return _my_se


def main():
    cp = configure()

    gConnector = GratiaConnector.GratiaConnector(cp)

    dCacheUrl = cp.InfoProviderUrl

    poolsUsage = None
    try:
      poolsUsage = cp.ReportPoolUsage
    except:
      pass

    if ( dCacheUrl == None ):
       raise Exception("Config file does not contain dCacheInfoUrl attribute")
  
    ynMap = { 'no' : 1 , 'false' : 1 , 'n':1 , '0' : 1 }
    noPoolsArg = ""
 
    if ( poolsUsage != None and ynMap.has_key(poolsUsage.lower())):
       noPoolsArg = "-PARAM nopools 1"

    import time
    timeNow = int(time.time())

    cmd = "java  org.apache.xalan.xslt.Process %s -PARAM now %d -PARAM SE %s -XSL %s/probe/dCache-storage/create_se_record.xsl -IN %s " % ( noPoolsArg, timeNow, get_se(cp) ,cp.GratiaLocation, dCacheUrl )

    fd = os.popen(cmd)

    result = XmlBuilder.Xml2ObjectBuilder(fd)
     
    for storageRecord in result.get().get():
       gConnector.send(storageRecord)

if __name__ == '__main__':
    main()
