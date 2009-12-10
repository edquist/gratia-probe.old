"""
Parse output file from Sun Grid Engine 'reporting'

Sample input:

1213137874:host_consumable:global:1213137874:X:snapidl=150.000000=768.000000,scpidl=0.000000=25.000000,dv13io=0.000000=40.000000,dv34io=0.000000=40.000000,dv35io=0.000000=40.000000,dv37io=0.000000=40.000000,dv38io=0.000000=40.000000,dv39io=0.000000=40.000000,dv40io=0.000000=40.000000,dv42io=0.000000=40.000000,dv43io=0.000000=40.000000,dv45io=0.000000=40.000000,dv47io=0.000000=40.000000,dv48io=0.000000=40.000000,dv61io=0.000000=40.000000,dv64io=0.000000=40.000000,dv65io=0.000000=40.000000,dv70io=0.000000=40.000000,dv71io=0.000000=40.000000,dv0302io=0.000000=40.000000,dv0308io=0.000000=40.000000,danteio=0.000000=500.000000,eliza1io=0.000000=500.000000,eliza2io=0.000000=500.000000,eliza3io=0.000000=500.000000,eliza5io=0.000000=500.000000,eliza6io=104.000000=500.000000,eliza10io=0.000000=500.000000,eliza11io=0.000000=500.000000,eliza12io=234.000000=500.000000,eliza13io=280.000000=500.000000,projectio=25.000000=500.000000,hpssio=0.000000=500.000000
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: sge_rpt.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

from logging import DEBUG
import sys
import time
from netlogger.parsers.base import BaseParser, autoParseValue
from netlogger import util

class Parser(BaseParser):
    """Parse output file from Sun Grid Engine 'reporting' logs

    The parameters control which types of SGE reporting output are parsed.
    With no parameters, no types are parsed.

    Parameters:
        - host_consumable {True,*False*}: Parse the 'host_consumable' type of record.
    """
    def __init__(self, f, host_consumable=False, **kw):
        BaseParser.__init__(self, f, fullname=__name__, **kw)
        # configure parsers called on each line
        host_consumable = util.as_bool(host_consumable)
        self._parsers = [
           (False, self._hostConsumable)[host_consumable]
        ]
        # drop False's
        self._parsers = filter(None, self._parsers)

    def process(self, line):
        if not self._parsers:
            return ()
        # split into fields
        fields = line.split(':')
        # try each parser on fields
        for parse_fn in self._parsers:
            events = parse_fn(fields)
            if events: 
                break
        return events

    def _hostConsumable(self, fields): 
        # see if we have a parseable line
        if len(fields) != 6:
            return ()
        if fields[1] != 'host_consumable' or fields[2] != 'global':
            return ()
        # timestamp
        ts = float(fields[0])
        # build one event per value
        events = [ ]
        for value in fields[5].split(','):
            vf = value.split('=')        
            event = { 'ts' : ts, 'event' : 'sge.rpt', 'rsrc' : vf[0],
                      'val' : float(vf[1]), 'limit' : float(vf[2]) }
            events.append(event)
        # done
        return events
