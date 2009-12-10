"""
Simplified Globus Toolkit GT4 WS-GRAM log parser

Typical input line:
-----------------------------------------------------------------------
2008-02-05 11:16:04,071 WARN  utils.JavaUtils \
[main,isAttachmentSupported:1218] Unable to find required classes \
(javax.activation.DataHandler and javax.mail.internet.MimeMultipart). \
Attachment support is disabled.
-----------------------------------------------------------------------
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: wsgram.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

import re
#
from netlogger.parsers.base import BaseParser, parseDate
from netlogger import nllog

# Logging
log = None
def activateLogging(name=__name__, **kw):
    global log
    log = nllog.getLogger(name, **kw)

def _ns(e):
    return "globus.ws-gram.%s" % e

class Parser(BaseParser):
    """Globus Toolkit GT4 WS-GRAM log parser

    See also http://www.globus.org/toolkit/docs/4.0/execution/wsgram/developer-index.html.
    """
    # Main regex
    RE = re.compile("(?P<date>\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d,\d\d\d)\s+"
                    "(?P<level>\w+)\s+"
                    "(?P<class>\S+)\s+"
                    "\[(?P<thread>[^,]+),(?P<file>[^:]+):(?P<line>\d+)\]\s+"
                    "(?P<msg>.*)"
                    )
    MSG_RE = { 'auth.invoke' :
                   'Authorized "(?P<DN>.*?)" to invoke "(?P<target>.*?)"',
               'auth.user' :                   
                   'Peer "(?P<DN>.*)" authorized as "(?P<user>.*)"',
               'service' :
                   '[Ss]ervice (?P<name>.*)',
               'read.registration.default' :
                   'Reading default registration.*?: (?P<file>.*)',
               'job.start' :
                   'Job (?P<job__id>\S+) accepted for local user ' +
               '\'(?P<user>\S+)\'',
               'job.end':
                   'Job (?P<job__id>\S+) (finished successfully|failed)',
               }
    # pre-compile message regexes
    for k in MSG_RE.keys():
        MSG_RE[k] = re.compile(MSG_RE[k])

    def __init__(self, f, **kwargs):
        BaseParser.__init__(self, f, fullname=__name__, **kwargs)

    def process(self, line):
        m = self.RE.match(line)
        # if no match, just return the whole thing as 'unknown';
        # nothing lost except some precious CPU time
        if not m:
            return (dict(event=_ns('unknown'), msg=line),)
        d = m.groupdict()
        # parse the date
        d['ts'] = _parseDate(d['date'])
        del d['date']
        # parse the level by simply changing its case
        d['level'] = d['level'].title()
        # replace silly \" with "
        d['msg'] = d['msg'].replace(r'\"', '"').replace(r'\'', "'")
        # look for some known messages; if found,
        # replace 'msg' attribute with parsed information
        msg = d['msg']
        for suffix, regex in self.MSG_RE.items():
            m = regex.match(msg)
            if m:
                for n,v in m.groupdict().items():                    
                    # replace '__' with '.' in group keys, to get around
                    # restriction of no dots, e.g., 'job.id'
                    k = n.replace('__','.')
                    # add status for job.end
                    if suffix == 'job.end':
                        status_msg = m.group(2)
                        if status_msg == 'finished successfully':
                            d['status'] = 0
                        else:
                            d['status'] = -1
                    d[k] = v
                #d.update(m.groupdict())
                d['event' ] = _ns(suffix)
                del d['msg']
                break
        # done!
        return (d,)

def _parseDate(s):
    bp_ts = s[:10] + 'T' + s[11:19] + '.' + s[20:] + 'Z'
    return parseDate(bp_ts)
