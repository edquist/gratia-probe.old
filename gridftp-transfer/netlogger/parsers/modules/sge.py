"""
Parse output file from Sun Grid Engine

Sample input:

all.q:pc1018.nersc.gov:dayabay:jianglai:test_neutron_CDR_near_DYB_r484_c2.command:2779793:sge:0:1167554073:1167562126:1167567604:0:0:5478:5207:32:0.000000:0:0:0:0:339102:43557:0:0.000000:0:0:0:0:0:0:other:defaultdepartment:NONE:1:0:5239.000000:1024.547343:0.000000:-l h_cpu=21600,h_stack=10240K,h_vmem=1100M -P other:0.000000:NONE:219533312.000000
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: sge.py,v 1.1 2008/11/18 17:20:23 abaranov Exp $'

from logging import DEBUG
import sys
import time
from netlogger.parsers.base import BaseParser, autoParseValue

class Parser(BaseParser):
    """Parse output file from Sun Grid Engine (SGE)

    Parameters:
        - one_event {True,*False*}: If true, generate one event per SGE output record, 
          otherwise generate a start/end event pair.
    """
    # Attribute values occur in this order
    ATTRS = ( 'qname', 'hostname', 'group', 'owner', 'job_name', 'job_number',
              'account', 'priority', 'submission_time', 'start_time',
              'end_time', 'failed', 'exit_status',
              'ru_wallclock', 'ru_utime', 'ru_stime',
              'ru_maxrss', 'ru_ixrss', 'ru_ismrss', 'ru_idrss', 'ru_isrss', 
              'ru_minflt', 'ru_majflt', 'ru_nswap', 'ru_inblock', 
              'ru_oublock', 'ru_msgsnd', 'ru_msgrcv', 'ru_nsignals', 
              'ru_nvcsw', 'ru_nivcsw',
              'project', 'department', 'granted_pe', 'slots', 'task_number', 
              'cpu', 'mem', 'io', 'category', 'iow', 'pe_taskid', 'maxvmem')

    def __init__(self, f, one_event=False, **kw):
        """Parameters:
              one_event - sge.job instead of sge.job.start / sge.job.end
        """
        BaseParser.__init__(self, f, fullname=__name__, **kw)
        self._one_event = one_event

    def process(self, line):
        self.log.debug("process.start")
        if line[0] == '#':
            return () # comment
        values = line.split(':')
        if len(values) != len(self.ATTRS):
            return () # junk
        attrs = { }
        for k, v in zip(self.ATTRS, values):            
            attrs[k] = autoParseValue(v)
        jobid = attrs['job_number']
        start_time = float(attrs['submission_time'])
        end_time = float(attrs['end_time']) 
        if self._one_event:
            job = attrs
            job.update({ 'ts' : start_time,
                         'dur' : end_time - start_time,
                         'event' : 'sge.job',
                         'job.id' : jobid, 
                         'status' : attrs['exit_status'] })
        else:
            start, end = { }, attrs
	    start['ts'] = start_time
	    start['event'] = 'sge.job.start'
	    start['job.id'] = jobid
	    end['ts'] =  end_time
	    end['event'] = 'sge.job.end'
	    end['job.id'] = jobid
	    end['status'] = attrs['exit_status']
        self.log.debug("process.end", status=0, n=2)
        if self._one_event:
            return (job,)
        else:
            return (start, end)
