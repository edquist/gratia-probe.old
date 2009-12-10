"""
Parse XML condor logs.

Sample:
<c>
<a n="MyType"><s>JobTerminatedEvent</s></a>
<a n="EventTypeNumber"><i>5</i></a>
<a n="MyType"><s>JobTerminatedEvent</s></a>
<a n="EventTime"><s>2008-02-06T16:45:10</s></a>
<a n="Cluster"><i>5</i></a>
<a n="Proc"><i>0</i></a>
<a n="Subproc"><i>0</i></a>
<a n="TerminatedNormally"><b v="t"/></a>
<a n="ReturnValue"><i>0</i></a>
<a n="RunLocalUsage"><s>Usr 0 00:00:00, Sys 0 00:00:00</s></a>
<a n="RunRemoteUsage"><s>Usr 0 00:00:00, Sys 0 00:00:00</s></a>
<a n="TotalLocalUsage"><s>Usr 0 00:00:00, Sys 0 00:00:00</s></a>
<a n="TotalRemoteUsage"><s>Usr 0 00:00:00, Sys 0 00:00:00</s></a>
<a n="SentBytes"><r>0.000000000000000E+00</r></a>
<a n="ReceivedBytes"><r>0.000000000000000E+00</r></a>
<a n="TotalSentBytes"><r>0.000000000000000E+00</r></a>
<a n="TotalReceivedBytes"><r>0.000000000000000E+00</r></a>
</c>

"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: condorxml.py,v 1.1 2008/11/18 17:20:22 abaranov Exp $'

import re
from StringIO import StringIO
import xml
from xml.etree import ElementTree as ET
#
from netlogger import nllog
from netlogger.parsers.base import BaseParser, parseDate

# Logging
log = None
def activateLogging(name=__name__, **kw):
    global log
    log = nllog.getLogger(name, **kw)

def _ns(e):
    return "condor.%s" % e

class Parser(BaseParser):
    """Parse XML condor logs.

    The logs are a series of XML fragments whose outer element is '<c>'.
    The information in each fragment includes an event type, time,
    return value, resource usage stats, and bytes sent and received.
    """
    def __init__(self, f, **kwargs):
        BaseParser.__init__(self, f, fullname=__name__, **kwargs)
        self._event = [ ]
        self._prev_ts = None

    def process(self, line):
        result = ( )
        line = line.replace(r'\"','"') # un-escape quotes
        if line == '<c>':
            if self._event:
                raise ValueError("unexpected start of event, "
                                 "last line was: %s" % self._event[-1])
            self._event = [ line ]
        elif line == '</c>':
            self._event.append(line)
            result = (self._parseEvent(),)
            self._event = [ ]
        else:
            self._event.append(line)
        return result

    def _parseEvent(self):
        e = ' '.join(self._event)
        try:
            p = ET.fromstring(e)
        except xml.parsers.expat.ExpatError, E:
            raise ValueError("in line '%s': %s" % (e,E))
        d = { }
        for a in p:
            if a.tag != 'a':
                raise ValueError("expected 'a' element in: %s" % _xs(a))
            name = a.get('n')
            if name is None:
                raise ValueError("'a' element missing 'n' attr: %s" % _xs(a))
            try:
                vc = a[0]
            except IndexError:
                raise ValueError("'a' element missing value: %s" % _xs(a))
            if vc.tag == 'b':
                value = int(vc.get('v') == "t")
            elif vc.tag == 'i':
                value = int(vc.text)
            elif vc.tag == 'r':
                value = float(vc.text)
            else: # 's', or anything else!
                value = vc.text
            # do some simple transformations "on the way in"
            if name == 'MyType':
                if value.endswith('Event'): # strip any 'Event' suffix
                    d['event'] = value[:-5]
                else:
                    d['event'] = value
            elif name == 'EventTime':
                d['ts'] = parseDate(value + 'Z') # XXX: timezone??
            elif name == 'TerminatedNormally':
                d['status'] = [-1, 0][value]
            elif name.endswith('Host') and (
                value[0] == '<' and value[-1] == '>'):
                host, port = value[1:-1].split(':')
                d['host'] = host
                d['port'] = int(port)            
            else:
                d[_camel(name)] = value
        ts = d.get('ts', None)
        if ts is None:
            if self._prev_ts is None:
                raise ValueError("no timestamp in event, "
                                 "or previous one to copy: %s" % _xs(p))
            else:
                d['ts'] = self._prev_ts
        else:
            self._prev_ts = ts
        return d

def _xs(elt):
    """Get element as string. For error reporting."""
    sio = StringIO()
    ET.ElementTree(elt).write(sio)
    return sio.getvalue()

def _camel(s):
    """Change string to start with lowercase"""
    return s[0].lower() + s[1:]
