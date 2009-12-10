"""
Generic parser that uses a fixed event name and puts all the
information in a single string-valued attribute.
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: generic.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

from logging import DEBUG
import time
#
from netlogger.parsers.base import BaseParser

class Parser(BaseParser):
    """Generic parser that uses a fixed event name and puts all the
    information in a single string-valued attribute.

    Parameters:
        - attribute_name {*'msg'*}: Output name for the attribute containing the input line.
        - event_name {*'event'*}: Output event name
    """
    def __init__(self, f, attribute_name='msg', event_name='event', **kwargs):
        BaseParser.__init__(self, f, fullname=__name__, **kwargs)
        self.event = event_name
        self.attr = attribute_name

    def process(self, line):
        self.log.debug("process.start")
        now = time.time()
        result = ({'ts':now, 'event':self.event, self.attr:line},)
        self.log.debug("process.end", status=0, n=len(result))
        return result

