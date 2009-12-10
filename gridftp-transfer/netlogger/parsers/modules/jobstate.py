"""
A pegasus/dagman/condor jobstate log parser.
"""
__author__ = '$Author: abaranov $'
__rcsid__ = '$Id: jobstate.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

from hashlib import md5
import time

from netlogger.parsers.base import BaseParser, getGuid
from netlogger import nllog

# Logging
log = None
def activateLogging(name=__name__):
    global log
    log = nllog.getLogger(name)

EVENT_PREFIX="pegasus.jobstate."

class Parser(BaseParser):
    """Pegasus/dagman/condor jobstate parser.

    Parameters:
        - add_guid {True,*False*}: Add a unique identifer, using the guid= attribute,
          to each line of the output. The same identifier is used for all output from
          one instance (i.e. one run of the nl_parser).
    """

    def __init__(self, f, add_guid=False, **kwargs):
        """ Construct and initialize class vars. """
        BaseParser.__init__(self, f, fullname=__name__, **kwargs)

        self.add_guid = add_guid
        if self.add_guid:
            self.guid = getGuid(repr(time.time()))


    def process(self, line):
        """ Process a pegasus/dagman/condor jobstate line """

        # Lines are whitespace separated
        parts = line.split()

        # Lines should be 5 or 6 fields
        if len(parts) < 5 or len(parts) > 6:
            raise ValueError, "Invalid line: expected either 5 or 6 whitespace separated fields"

        # First field should be convertable to a float
        try:
            ts = float(parts[0])
        except ValueError:
            raise ValueError, "Invalid line: expected float as 1st field"

        # Assuming these timestamps are floats in UTC
        event = { 'ts' : float(parts[0]) }
        if self.add_guid:
            event['guid'] = self.guid
        
        # Look for "INTERNAL" lines
        if parts[1] == "INTERNAL":
            if parts[3] == "TAILSTATD_STARTED":
                event['event'] = EVENT_PREFIX + 'tailstatd.start'
            elif parts[3] == 'DAGMAN_STARTED':
                event['event'] = EVENT_PREFIX + 'dagman.start'
            elif parts[3] == 'DAGMAN_FINISHED':
                event['event'] = EVENT_PREFIX + 'dagman.end'
            elif parts[3] == "TAILSTATD_FINISHED":
                event['event'] = EVENT_PREFIX + 'tailstatd.end'
                event['status'] = parts[4]
            return [event,]

        # Skip UN_READY condorstate lines
        if parts[2] == "UN_READY":
            return []

        # The rest use field 2 for event, etc.
        event['event']     = EVENT_PREFIX + parts[2].lower()
        event['comp.id']   = parts[1]
        event['condor.id'] = parts[3]
        event['site.id']   = parts[4]

        return [event,]
