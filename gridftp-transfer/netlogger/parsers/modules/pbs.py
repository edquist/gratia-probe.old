"""
Parse contents of PBS accounting file

PBS log format: 
timestamp;rec_type;job_id;pbs_record
in the above line "pbs_record" is a set of key value pairs

sample line:
07/23/2008 00:43:53;S;545489.myhost.domain.com;user=foo group=bar account=testrepo jobname=STDIN queue=debug ctime=1216799025 qtime=1216799025 etime=1216799025 start=1216799033 owner=foo@myhost.domain.com exec_host=nodename343/1+nodename343/0 Resource_List.neednodes=nodename343:ppn=2 Resource_List.nodect=1 Resource_List.nodes=1:ppn=2 Resource_List.walltime=00:30:00 
"""
__author__ = 'Shreyas Cholia scholia@lbl.gov'
__rcsid__ = '$Id: pbs.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

import time
from netlogger.parsers.base import BaseParser

class Parser(BaseParser):
    """Parse contents of PBS accounting file.

    Parameters:
        - site {*org.mydomain*}: Site name, for site-specific processing.
          Current recognized sites are: *.nersc.gov = NERSC.
        - suppress_hosts {True,*False*}: Do not include the list of hosts in the output.
          This list could be very long if the job has a high degree of parallelism.
    """
    # Mapping of input keywords to output keywords
    # Any keys not mapped stay the same
    DEFAULT_KEYMAP = { 'Exit_status' : 'status' }

    def __init__(self, f, site='org.mydomain', suppress_hosts = False, **kw):
        BaseParser.__init__(self, f, fullname=__name__, **kw)
        self._site = site
        self._suppress_hosts = suppress_hosts
        self._keymap = self.DEFAULT_KEYMAP
        # Choose site-specific function for 'other' field
        if self._site.endswith(".nersc.gov"):
            self._other = self._otherNersc
        # put other ones here..
        else:
            # do nothing
            self._other = None

    def _otherNersc(self, key, value):
        """Process NERSC 'other' field.
        """
        qsubpid, ppid, submit_host = value.split(':',2)
        return (("qsubpid", qsubpid), ("ppid", ppid), ("submit_host", submit_host))

    def _resourceListNodes(self, key, value):
        """Process NERSC 'Resource_List.nodes' field.
        """
        if value.find(":ppn=") > -1:
            nodes, ppnstring = value.split(':',1)
            ppnkey,ppnvalue = ppnstring.split('=',1)
            return (("nodes", nodes), (ppnkey, ppnvalue), ("num_procs", int(nodes)*int(ppnvalue)))
        else:
            return ((key, value))
    def process(self, line):
        """Process one PBS job record.
        """
        # split out header fields
        timestamp, rectype, jobid, record = line.split(';',3)
        # convert the timestamp
        parsed_ts = time.strptime(timestamp, "%m/%d/%Y %H:%M:%S")
        d = dict(ts=time.mktime(parsed_ts), event="pbs.job." + rectype, type=rectype, job__id=jobid, site=self._site)
        # parse the record field's name=value pairs
        if record:
            for item in record.split(' '):
                k, v = item.split('=',1)
                if k == "other" and self._other:
                    # call special function for 'other'
                    for kk, vv in self._other(k,v):
                        d[kk] = vv
                elif k == "Resource_List.nodes":
                    for kk, vv in self._resourceListNodes(k,v):
                        d[kk] = vv
                elif self._suppress_hosts and (k == "exec_host" or k == "Resource_List.neednodes"):
                    # Do nothing - skip
                    continue
                else:
                    k = self._keymap.get(k, k)
                    d[k] = v
        return (d,)

