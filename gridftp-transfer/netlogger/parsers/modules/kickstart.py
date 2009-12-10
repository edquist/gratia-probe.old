"""
A Pegasus log parser.
"""
__author__ = '$Author: abaranov $'
__rcsid__ = '$Id: kickstart.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

from hashlib import md5
import time

from netlogger.parsers.base import BaseParser, getGuid, parseDate
from netlogger.parsers.modules import ks
from netlogger import nllog

from xml.parsers.expat import ExpatError
try:
    from xml.etree.cElementTree import XML
except:
    from xml.etree.ElementTree import XML

# Logging
log = None
def activateLogging(name=__name__):
    global log
    log = nllog.getLogger(name)

PEGASUS_NS = 'http://pegasus.isi.edu/schema/invocation'
MAIN_JOB_STATUS_XPATH = '{%(pns)s}mainjob/{%(pns)s}status/{%(pns)s}regular' % \
                            {'pns':PEGASUS_NS}

# put in pegasus namespace
_ns = lambda x: '{' + PEGASUS_NS + '}' + x
# make xpath in pegasus namespace
_xp = lambda comp: '/'.join(map(_ns, comp))

class Parser(BaseParser):
    """Parse the Kickstart job wrapper output.

    Parameters:
        - one_event {True,*False*}: If true, generate one event per kickstart invocation record,
          otherwise generate a start/end event pair.
       - use_c {True,*False*}: Use the *experimental* C parser instead. This requires that
         you compiled the parser with "python setup.py swig".

    See also: http://pegasus.isi.edu/
    """
    def __init__(self, f, one_event=False, use_c=False, **kwargs):
        """ Construct and initialize class vars. """
        BaseParser.__init__(self, f, fullname=__name__, **kwargs)

        self._one_event = one_event or use_c
        if use_c:
            self.input = ""
            self.process = self._c_process
        else:
            # A list for storing the invocation document line by
            # line until the complete document has been read.
            self.input = []

            # The resulting event list from an invocation
            self.events = []

            # The ElementTree used for this invocation
            self.root = None

            # The guid used to tie all events for this invocation together
            self.guid = None


    def process(self, line):
        """ Process a line, when a complete invocation document has
        been read, process it otherwise return an empty list
        indicating not enough has arrived yet.
        """
        self.input.append(line)
        if line.find("</invocation>") == -1:
            return ()

        try:
            self.root = XML(''.join(self.input))
        except ExpatError, experr:
            self.input = [ ]
            raise ValueError("expat error: %s" % experr)
        self.input, self.events = [ ], [ ]

        # We've got a complete ElementTree
        return self._process_root()

    def _c_process(self, line):
        self.input += line
        if line.find("</invocation>") == -1:
            return ()
        event = ks.parseBuffer(self.input)
        self.input = ""
        # if last char before newline is ' ', this is a flag
        # indicating there are errors (hopefully rare)
        if event[-2] == ' ':
            return [s + '\n' for s in event.split('\n')[:-1]]
        else:
            return (event,)


    def _process_root(self):
        """ Process the entire invocation doc parsed and rooted at
        self.root."""
       
        qname = self.root.tag.split('}')
        if len(qname) != 2 or qname[0][1:] != PEGASUS_NS or \
                qname[1] != 'invocation':
            raise ValueError("Invalid pegasus invocation document")

        # Initialize invocation
        if self._one_event:
            invoke = { 'ts' : self.root.get('start') }
        else:
            invoke = { 'ts' : parseDate(self.root.get('start')),
                       'guid' : getGuid(repr(time.time()), 
                                        *self.root.attrib.values()) }

        # Add in invocation optional attributes, if they are found
        attrs = (('hostname', 'host'), ('user', 'user'),
                 ('transformation', 'type'), ('wf-label', 'workflow.id'))
        self._populate_event(invoke, self.root, attrs)

        # Pull usage info in from usage element
        usage = self.root.find(_xp(('mainjob', 'usage')))
        self._populate_event(invoke, usage, (('nsignals', 'nsignals'),))

        # Pull in duration and exit status in from mainjob element 
        duration = float(self.root.get('duration'))
        mainjob_status = self.root.find(MAIN_JOB_STATUS_XPATH).get('exitcode')

        self.events.append(invoke)
        if self._one_event:
            # Spit out only one event per invocation
            invoke['event'] = "pegasus.invocation"
            invoke['duration'] = duration
            invoke['status'] = mainjob_status
        else:
            # Spit out a pair of start/end events per invocation
            invoke['event'] = "pegasus.invocation.start"
            
            invoke_end = {
                'event' : "pegasus.invocation.end",
                'ts' : invoke['ts'] + duration,
                'guid' : invoke['guid'],
                'status' : mainjob_status
                }
            self.events.append(invoke_end)

        # Add events for failed stat calls
        for statcall in self.root.findall(_ns('statcall')):
            errnum = int(statcall.get('error'))
            # assume non-zero means "failed" (?)
            if errnum != 0:
                filename = statcall.find(_ns('file')).get('name')
                statinfo = statcall.find(_ns('statinfo'))
                if statinfo is None: # fix Issue #217
                    statinfo = {'user':'unknown', 'group':'unknown'} 
                _e = { 'event' : 'pegasus.invocation.stat.error',
                       'ts' : invoke['ts'],
                       'file' : filename, 
                       'user' : statinfo.get('user'),
                       'group' : statinfo.get('group'),
                       'status' : errnum }
                if invoke.has_key('guid'):
                       _e['guid'] = invoke['guid']
                self.events.append(_e)

        return self.events


    def _populate_event(self, event, elem, attrs):
        """ Ultility method for populating the given event with
        attributes from the given element, if those attributes exist
        within that element."""

        if elem is not None:
            for attr, new_name in attrs:
                if elem.attrib.has_key(attr):
                    event[new_name] = elem.get(attr)
