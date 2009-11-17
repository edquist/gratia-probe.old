#!/usr/bin/python

import os
import re
import sys
import time
import socket
import datetime
import optparse
import ConfigParser
import xml.sax.saxutils

# Bootstrap our python configuration.  This should allow us to discover the
# configurations in the case where our environment wasn't really configured
# correctly.
sys.path.append('.')
gratia_path = os.path.expandvars('/opt/vdt/gratia/probe/common')
if gratia_path not in sys.path and os.path.exists(gratia_path):
    sys.path.append(gratia_path)
if 'VDT_LOCATION' in os.environ:
    gratia_path = os.path.expandvars('$VDT_LOCATION/gratia/probe/common')
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)
    gratia_path = os.path.expandvars('$VDT_LOCATION/gratia/probe/services')
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)

has_gratia = True
try:
    import Gratia
    import StorageElement
    import StorageElementRecord
except:
    has_gratia = False
    Gratia = None
    StorageElement = None
    StorageElementRecord = None

# Prevent us from sending in overly-large objects:
MAX_DATA_LEN = 50*1024

class GratiaConnector:
    
  def __init__(self,cp):
    global has_gratia
    global Gratia
    global StorageElement
    global StorageElementRecord
    if not has_gratia:
        try:
            gratia_loc = cp.get("Gratia", "gratia_location")
            sys.path.append(os.path.join(gratia_loc, "probe", "common"))
            sys.path.append(os.path.join(gratia_loc, "probe", "services"))
            Gratia = __import__("Gratia")
            StorageElement = __import__("StorageElement")
            StorageElementRecord = __import__("StorageElementRecord")
            has_gratia = True
        except:
            raise
    if not has_gratia:
        print "Unable to import Gratia and Storage modules!"
        sys.exit(1)
    try:
        probe_config = cp.get("Gratia", "ProbeConfig")
    except:
        raise Exception("ProbeConfig, %s, does not exist." % probe_config)

    Gratia.Initialize(probe_config)
    try:
        Gratia.Config.setSiteName(cp.get("Gratia", "SiteName"))
    except:
        if Gratia.Config.get_SiteName().lower().find('generic') >= 0:
            Gratia.Config.setSiteName(socket.getfqdn())
    try:
        Gratia.Config._ProbeConfiguration__CollectorHost = cp.get("Gratia", "Collector")
    except:
        pass
    try:
        Gratia.Config.setMeterName('dCache-storage:%s' % socket.getfqdn())
    except:
        pass

  def send(self,record):
        Gratia.Send(record)

