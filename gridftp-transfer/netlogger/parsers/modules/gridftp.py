#!/usr/bin/env python
"""
Parse GridFTP (server) transfer logs.

Input format:

DATE=20070215110703.2102 HOST=pdsfgrid1.nersc.gov PROG=globus-gridftp-server NL.EVNT=FTP_INFO START=20070215110702.763298 USER=rosheck FILE=//tmp/YY5raYFdo5.local_out_moved BUFFER=0 BLOCK=262144 NBYTES=55 VOLUME=/ STREAMS=1 STRIPES=1 DEST=[129.79.4.64] TYPE=RETR CODE=226
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: gridftp.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

import calendar
import sys
from logging import DEBUG
from netlogger.parsers.base import BaseParser, getGuid, parseDate

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
        if raw:
            # only parse to int if returning raw dict
            self._ints = dict.fromkeys(('buffer', 'block', 'nbytes', 
                                        'streams','stripes', 'code'))
        else:
            self._ints = None

    def process(self, line):
        self.log.debug("process.start")
        if line.startswith('ts='): # BP-style
            line = line.replace(r'\"', '"') # fix bug w/DN quotes
            return (line + '\n',)
        d = { }
        dates = ""
        for nvp in line.split():        
            try:
                name, value = nvp.split('=',1)
            except:
                self.log.warn("process.split.error", field=nvp)
                continue
            else:
                nm = name.lower()
                if nm in ('start', 'date'):
                    if value[0] == '0': # FUBAR Date!
                        value = '20' + value[2:]
                    dates += value
                    bpdate = value[:4] + '-' + value[4:6] + '-' + \
                        value[6:8] + 'T' + \
                        value[8:10] + ':' + value[10:12] + ':' + \
                        value[12:14] + '.' + value[15:] + 'Z'
                    d[nm] = parseDate(bpdate)
                    if nm == 'date' and self._one:
                        end_str = bpdate
                elif nm == 'nl.evnt':
                    d['event'] = value
                elif self._ints and self._ints.has_key(nm):
                    d[nm] = int(value)
                elif nm == 'dest':
                    # strip off silly square brackets
                    d[nm] = value[1:-1]
                else:
                    d[nm] = value
        self.log.trace("process.values", v=d)
        try:
            d['guid'] = getGuid(dates, d['user'], d['dest'])
            start, end = d['start'], d['date']
            d['dur'] = end - start
        except KeyError, E:
            self.log.exc("process.end", E, reason="missing values")
            return ()
        del d['start']
        del d['date']
        if self._one:
            d['ts'] = start
            d['end'] = end_str
            result = (d,)
        else:
            d1 = d
            d2 = d.copy()
            d1['ts'] = start
            d1['event'] = d1['event'] + '.start'
            d2['ts'] = end
            d2['event'] = d2['event'] + '.end'
            result = (d1,d2)
        self.log.debug("process.end", n=len(result), status=0)
        return result
