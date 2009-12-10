"""
Parse 'best practices' logs, essentially a no-op.
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: bp.py,v 1.1 2008/11/18 17:20:22 abaranov Exp $'

import logging
from netlogger import nllog
from netlogger.parsers.base import NLFastParser

class Parser(NLFastParser):
    """Parse Best-Practices logs into Best-Practices logs.

    Parameters:
        - has_gid {True,*False*}: If true, the "gid=" keyword in the input will be
          replaced by the currently correct "guid=".
        - verify {*True*,False}: Verify the format of the input, otherwise simply
          pass it through without looking at it.
    """
    def __init__(self, f, has_gid=False, verify=True, **kwargs):        
        self._fix_gid = has_gid
        self._verify = verify        
        NLFastParser.__init__(self, f, verify=verify, **kwargs)
        
    def process(self, line):
        self.log.debug("process.start")
        # if verification was turned on,
        # verify that the data makes sense, but throw away result
        if self._verify:            
            self.parseLine(line)
        # just return the original string, after fixing the gid= to
        # be guid= if that's requested
        if self._fix_gid:
            line = line.replace(' gid=',' guid=')
        self.log.debug("process.end", status=0, n=1)
        return (line + '\n',)

