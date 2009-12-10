"""
Parse output file from SRM "Bestman" implementation

Sample input: see netlogger/tests/data/srm-transfer.log
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: bestman.py,v 1.1 2008/11/18 17:20:22 abaranov Exp $'

import hashlib
from logging import DEBUG
from pprint import pprint as pp
import re
import string
import sys
import time
from netlogger.parsers.base import BaseParser, autoParseValue
from netlogger import util

_NS = "gov.lbl.srm."

class Parser(BaseParser):
    """Parse logs from Berkeley Storage Manager (BeStMan).

    Parameters:
        - version {1,2}: Version 1 is anything before bestman-2.2.1.r3, Version 2 is that 
                         version and later ones.

    See also http://datagrid.lbl.gov/bestman/
    """

    # V1 events
    REQUEST_EVENT = 'gov.lbl.srm.server.TSRMRequestCopy'
    STATUS_EVENT = 'gov.lbl.srm.server.TSRMRequestCopyToRemote.setStatus'

    # V2 events, etc.
    READY_EVENT = _NS + 'server.ContainerThread.ServerReady'
    E1 = re.compile('\s*([a-zA-Z][a-zA-Z0-9._\-]*)=([^"]\S*|"[^"]*")\s*')
    BM_DOMAIN = 'gov.lbl.srm.'
    BM_SERVER = 'srm.server.'

    # An 'event map' mapping 2-tuples of (class, <event, status or code>) to event to use
    EVENT_MAP = {
        ('server.ContainerThread',           'ServerReady')                       : 'ready',
        ('server.TSRMServer',                'incoming.srmPing')                  : 'ping.in',
        ('impl.TSRMService',                 'outcoming.srmPing')                 : 'ping.out',
        ('server.TSRMServer',                'incoming.srmGetTransferProtocols')  : 'getTransferProtocols.in',
        ('impl.TSRMService',                 'outcoming.srmGetTransferProtocols') : 'getTransferProtocols.out',
        ('server.TSRMServer',                'incoming.srmGetSpaceTokens')        : 'getSpaceTokens.in',
        ('impl.TSRMService',                 'outcoming.srmGetSpaceTokens')       : 'getSpaceTokens.out',
        ('server.TSRMServer',                'incoming.srmCopy')                  : 'copy.in',
        ('server.TUserRequestCopy',          'start')                             : 'req.start',
        ('server.TSRMServer',                'list')                              : 'list',
        ('server.TSRMRequestCopyFromRemote', 'reqStatus')                         : 'req.status',
        ('server.TSRMRequestCopyFromRemote', 'queued')                            : 'req.queued',
        ('server.TSRMRequestCopyFromRemote', 'scheduled')                         : 'req.scheduled',
        ('server.TSRMRequestCopyFromRemote', 'end')                               : 'req.end',
        ('impl.TSRMService',                 'outcoming.SrmCopy')                 : 'copy.out',
        ('server.TSRMSourceFile',            'download')                          : 'download',
        ('server.TSRMDownloadCommon',        'txfSetup')                          : 'tx.size',
        ('server.TSRMDownloadCommon',        'TxfStartsPull')                     : 'tx.pull.start',
        ('server.TSRMDownloadCommon',        'TxfEndsPull')                       : 'tx.pull.end',
        ('server.TSRMUploadCommon',          'TxfStartsPush')                     : 'tx.push.start',
        ('server.TSRMUploadCommon',          'TxfEndsPush')                       : 'tx.push.end',
        ('server.TSRMUploadCommon',          'TxfSetup')                          : 'tx.setup'
        }

    STATUS_MAP = {
        'SRM_SUCCESS'            :  0,
        'SRM_REQUEST_INPROGRESS' :  1,
        'SRM_RELEASED'           :  2,
        'SRM_FILE_IN_CACHE'      :  3,
        'SRM_DUPLICATION_ERROR'  : -1
        }

    def __init__(self, f, version="1", **kw):
        BaseParser.__init__(self, f, fullname=__name__, **kw)
        if version == "1":
            self.proc_func = self._process_v1
        elif version == "2":
            self.proc_func = self._process_v2
        else:
            raise ValueError("Unknown version: %s" % version)
        # state for matching requests to status
        # maybe not needed? self._req = { }

    def process(self, line):
        return self.proc_func(line)


#### V2 methods ####

    def _process_v2(self, line):
        """ This is the Keith's newer version 2 """
        
        s = line.strip()
        if len(s) == 0 or s.startswith("#"):
            return { }

        #print "\n  %s" % line
        d = {}
        fields = self.E1.findall(s)
        # Changes to name
        for n, v in fields:
            v = v.strip('"')
            if n == 'rid':
                d['req.id'] = v
            elif n == 'tid':
                d['th.id'] = v.partition("Thread-")[2]
            elif n == 'reqSize':
                d['req.size'] = v
            elif n == 'statusCode':
                d['status'] = self.STATUS_MAP[v]
            elif n == 'class':
                bm_class = v
            elif v != 'null':
                d[n] = v

        # Change event values to preferred values from EVENT_MAP
        event_val = d.get('event', None)
        em_key = (bm_class.partition(self.BM_DOMAIN)[2], event_val)
        if em_key in self.EVENT_MAP:
            d['event'] = self.BM_SERVER + self.EVENT_MAP[em_key]

        #pp(d)
        return (d,)


#### V1 methods ####
    def _process_v1(self, line):
        """ This is the Dan's older version 1 """

        # split into fields
        fields = line.split()
        result = () # no branch taken -> no result
        if len(fields) > 4:
            # branch on event name
            event = fields[3]
            if event.startswith(self.STATUS_EVENT):
                status = fields[4]
                # branch on status token
                if status == 'SRM_SUCCESS':
                    result = self._processSuccess(fields)
            elif event.startswith(self.REQUEST_EVENT):
                result = self._processRequest(fields)
        # done
        return result

    def _gmt(self, fields):
        date, time = fields[1][:-3].split('-')
        date = date.replace('.', '-')
        return date + 'T' + time + 'Z'
        
    _URL_RE = "(?P<url>[^:]*://.*)"
    _FROM_RE = re.compile(".*\[from\]=" + _URL_RE)
    _TO_RE = re.compile("\[to\]=" + _URL_RE)
    def _processRequest(self, fields):
        m = self._FROM_RE.match(fields[3])
        if not m: return ()
        from_url = m.groupdict()['url']
        m = self._TO_RE.match(fields[4])
        to_url = m.groupdict()['url']
        guid = self._getGuid(from_url, to_url)
        event = { 'ts' : self._gmt(fields), 
                  'event': _NS + "server.TSRMRequestCopy.start",
                  'guid' : guid,
                  'src' : from_url, 
                  'dst' : to_url }
        # not yet: self._req[guid] = event
        return (event,)
    
    def _processSuccess(self, fields):
        p = fields[9].find(':')
        if p < 0: return ()
        from_url = fields[9][p+1:]
        to_url = fields[11][4:] # after 'tgt='
        guid = self._getGuid(from_url, to_url)
        event_name = _NS + "server.TSRMRequestCopy.end"
        event = { 'ts' : self._gmt(fields), 
                  'event': event_name,
                  'guid' : guid,
                  'src' : from_url, 
                  'dst' : to_url,
                  'status': 0
                  }    
        return (event,)

    def _getGuid(self, *args):
        h = hashlib.md5()
        for arg in args:
            h.update(arg)
        guid = h.hexdigest()
        return guid
