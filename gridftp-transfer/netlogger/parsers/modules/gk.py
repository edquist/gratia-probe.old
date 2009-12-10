"""
Simplified Globus Toolkit GT2 Gatekeeper log parser.
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: gk.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

from logging import DEBUG
import re
#
from netlogger.parsers.base import BaseParser, parseSyslogDate

def _ns(e):
    return "globus.gatekeeper.%s" % e

class Parser(BaseParser):
    """Simplified Globus Toolkit GT2 Gatekeeper log parser.

    The oddly-formatted input is transformed into a sequence of 3 events:

        * globus.gatekeeper.start
        * globus.gatekeeper.auth
        * globus.gatekeeper.end
    """
    PID_RE = re.compile("\s*PID: (?P<pid>\d+) -- Notice: "
                        "(?P<level>\d+):\s*(?P<rest>.*)")
    START_RE = re.compile("pid=(?P<pid>\d+) starting at (?P<date>.*)")
    CONN_RE = re.compile("[Gg]ot connection "
                         "(?P<ip>(?:\d\d?\d?\.){3}\d\d?\d?) at (?P<date>.*)")
    AUTH_RE = re.compile("[Aa]uthenticated globus user:\s*(?P<dn>.*)")
    END_RE = re.compile("[Cc]hild (?P<pid>\d+) started")
    FAIL_RE = re.compile("Failure: (?P<msg>.*)")

    def __init__(self, f, **kwargs):
        BaseParser.__init__(self, f, fullname=__name__, **kwargs)
        self._cur_time = 0

    def process(self, line):
        if line.startswith('TIME'):
            self._setTime(line[6:])
            return ()
        m = self.PID_RE.match(line)
        if not m:
            return ({'ts': self._cur_time, 'event': _ns("unknown"), 
                     'process.id':-1, 'msg': line }, )
        pid = int(m.group('pid'))
        level = int(m.group('level'))
        line = m.group('rest')
        e = {'ts':self._cur_time, 'process.id': pid, 'notice.level': level}
        m = self.START_RE.search(line)
        if m:
            self._setTime(m.group('date'))
            pid = int(m.group('pid'))
            e.update({'ts': self._cur_time, 'event': _ns("start"), 
                      'process.id': pid })
            return (e,)
        m = self.CONN_RE.search(line)
        if m:
            self._setTime(m.group('date'))
            ip = m.group('ip')
            e.update({'ts': self._cur_time, 'event': _ns("conn"), 'host':ip})
            return (e,)
        m = self.AUTH_RE.search(line)
        if m:
            e.update({'event': _ns("auth"), 'DN' : m.group('dn')})
            return (e,)
        m = self.END_RE.search(line)
        if m:
            cpid = int(m.group('pid'))
            e.update({'event':_ns("end"), 'status': 0, 
                      'child.process.id':cpid})
            return (e,)
        m = self.FAIL_RE.search(line)
        if m:
            msg = m.group('msg')
            e.update({'event': _ns("end"), 'status': -1, 'msg':msg})
            return(e,)
        e.update({ 'event': _ns("unknown"), 'msg':line })
        return(e,)

    def _setTime(self, date):
        t = parseSyslogDate(date)
        if t < self._cur_time:
            self.log.debug("setTime.ignoreEarlier", earlier=t, 
                           current=self._cur_time)
        else:
            self._cur_time = t
