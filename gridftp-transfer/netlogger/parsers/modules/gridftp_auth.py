#!/usr/bin/env python
"""
Parse GridFTP (server) transfer logs.

Input format:

DATE=20070215110703.2102 HOST=pdsfgrid1.nersc.gov PROG=globus-gridftp-server NL.EVNT=FTP_INFO START=20070215110702.763298 USER=rosheck FILE=//tmp/YY5raYFdo5.local_out_moved BUFFER=0 BLOCK=262144 NBYTES=55 VOLUME=/ STREAMS=1 STRIPES=1 DEST=[129.79.4.64] TYPE=RETR CODE=226
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: gridftp_auth.py,v 1.2 2008/12/29 22:08:28 abaranov Exp $'

import calendar
import sys
import re
import time
from logging import DEBUG
from netlogger.parsers.base import BaseParser, getGuid, parseDate

dnRe = re.compile(".*DN (..*) successfully authorized.")
netRe = re.compile("New connection from: (..*):[0-9][0-9]*")
fileStartRe = re.compile("""Starting to transfer "(..*)".""")
fileEndRe = re.compile("""Finished transferring "(..*)".""")
userRe = re.compile("User (..*) successfully authorized")

def geDn(d,subValue):
        global dnRe
        dbR  = dnRe.match(subValue)

        if ( dbR == None ):
          return 0

        dn = dbR.group(1)

        d['event'] = "gridftp.auth"
        d['dn']    = dn

        return 1

def getNetContext(d,subValue):
        global netRe
        netR  = netRe.match(subValue)

        if ( netR == None ):
          return 0

        netHost = netR.group(1)

        d['event'] = "gridftp.auth.connection"

        import socket
        d['host']    = socket.gethostbyname(netHost)

        return 1

def getTransferContextStart(d,subValue):
        global fileStartRe
        fileR  = fileStartRe.match(subValue)

        if ( fileR== None ):
          return 0

        filePath = fileR.group(1)

        d['event'] = "gridftp.auth.transfer.start"
        d['file']    = filePath

        return 1

def getTransferContextEnd(d,subValue):
        global fileEndRe
        fileR  = fileEndRe.match(subValue)

        if ( fileR== None ):
          return 0

        filePath = fileR.group(1)

        d['event'] = "gridftp.auth.transfer.end"
        d['file']    = filePath

        return 1

def geUserName(d,subValue):
        global userRe
        userR  = userRe.match(subValue)

        if ( userR == None ):
          return 0

        dn = userR.group(1)

        d['event'] = "gridftp.auth.success"
        d['user']    = dn

        return 1


class Parser(BaseParser):
    """Parse GridFTP (server) transfer logs.

    Parameters:
        - one_event {*True*,False}: If true, produce a single event for the transfer,
            and if False produce a start/end event pair.
    """
    def __init__(self, f, one_event=True, raw=False, **kw):
        """Constructor.
        """
        BaseParser.__init__(self, f, raw=raw, fullname=__name__, **kw)
        self._one = one_event
        self._eventDescriminators = [ getTransferContextEnd, getTransferContextStart,getNetContext,geDn,geUserName ]

    def process(self, line):
        self.log.debug("process.start")
        d = { }
        r = re.compile(".*\[([0-9][0-9]*)\] (..*) :: (..*)$")
        lineR = r.match(line)

        if ( lineR == None ):
          return ()

        timeS = lineR.group(2)
        subValue = lineR.group(3)
        localId  = lineR.group(1)

        d['ts'] = time.mktime(time.strptime(timeS,"%a %b %d %H:%M:%S %Y"))
        d['id'] = localId

        for evDescr in self._eventDescriminators:
           try:
              if ( evDescr(d,subValue) == 1 ):
                 break
           except Exception,ex:
              self.log.warn("process.end",str(ex))

        if ( not d.has_key("event") ):
           return ()

        result = (d,)
        self.log.debug("process.end", n=len(result), status=0)
        return result
