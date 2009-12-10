"""
Parse output file from SGI csa process accounting
"""

__author__ = 'Tina Declerck tinad@nersc.gov'
__rcsid__ = '$Id: csa_acct.py,v 1.1 2008/11/18 17:20:22 abaranov Exp $' 

"""
Sample input:

NOTE:  This is running accounting as follows:  csacom -pPXY

#usrmod           root     11:05:03 11:05:03     0.02     0.01        0   7638   7637 Mon Jul 14 2008 Mon Jul 14 2008
usrmod            cam      11:05:03 11:05:03     0.08     0.02        0   7637   7561 Mon Jul 14 2008 Mon Jul 14 2008
perl              cam      11:05:02 11:05:04     2.52     0.39        0   7561   7559 Mon Jul 14 2008 Mon Jul 14 2008
sh                cam      11:05:02 11:05:04     2.53     0.00        0   7559      1 Mon Jul 14 2008 Mon Jul 14 2008
#cron             root     11:05:02 11:05:04     2.56     0.00        0   7539  26996 Mon Jul 14 2008 Mon Jul 14 2008
sleep             fogal1   11:04:50 11:05:05    15.00     0.00        0   7532   7419 Mon Jul 14 2008 Mon Jul 14 2008
sleep             fogal1   11:04:50 11:05:05    15.00     0.00        0   7536   7418 Mon Jul 14 2008 Mon Jul 14 2008
sleep             fogal1   11:04:50 11:05:05    15.00     0.00        0   7535   7421 Mon Jul 14 2008 Mon Jul 14 2008
ps                fogal1   11:05:05 11:05:05     0.11     0.10        0   7642   7641 Mon Jul 14 2008 Mon Jul 14 2008
grep              fogal1   11:05:05 11:05:05     0.11     0.00        0   7643   7641 Mon Jul 14 2008 Mon Jul 14 2008

"""

from logging import DEBUG
import sys
import time
from netlogger.parsers.base import BaseParser, autoParseValue, parseDate
from netlogger.parsers.base import getTimezone

class Parser(BaseParser):
    """SGI Comprehensive System Accounting (CSA) process accounting parser.

    See also http://oss.sgi.com/projects/csa/.
    """
    # Attribute values occur in this order
    ATTRS = ( 'cmd', 'local_user', 
              'tod_start', 'tod_stop', 
              'walltime', 'cputime', 'ignore',
              'pid', 'ppid', 
              'dow_start', 'month_start', 'monthday_start', 'year_start', 
              'dow_end', 'month_end', 'monthday_end', 'year_end')
    
    def __init__(self, f, one_event=True, **kw):
	"""Parameters:
		one_event - csa.process instead of csa.process.start/csa.process.end
	"""
        BaseParser.__init__(self, f, fullname=__name__, **kw)
	self._one_event = one_event
  
    def process(self, line):
        tzstr = getTimezone() 
	mondict={'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6,
            'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}
	self.log.debug("process.start")
        values = line.split()
        if len(values) != len(self.ATTRS):
            return () # junk
        attrs = { }
        for k, v in zip(self.ATTRS, values):            
            attrs[k] = autoParseValue(v)
	monst = mondict[attrs['month_start']]
	monend = mondict[attrs['month_end']]
        stime= "%s-%02d-%02dT%s%s" % (attrs['year_start'], monst, 
                                      attrs['monthday_start'], 
                                      attrs['tod_start'], tzstr)
        etime= "%s-%02d-%02dT%s%s" % (attrs['year_end'], monend,
                                      attrs['monthday_end'], 
                                      attrs['tod_stop'], tzstr)
	if self._one_event:
	    process = attrs
	    process.update({ 'ts' : stime,
			     'dur' : parseDate(etime) - parseDate(stime),
			     'event' : 'csa.process',
			     'process.pid' : attrs['pid'],
			     'process.ppid' : attrs['ppid'] })
	else:
            start, end = { }, attrs
            start['ts'] = stime
            start['event'] = 'csa.process.start'
            start['pid'] = int(attrs['pid'])
            start['ppid'] = int(attrs['ppid'])
            end['ts'] = etime
            end['event'] = 'csa.process.end'
            end['pid'] = int(attrs['pid'])
            end['ppid'] = int(attrs['ppid'])
            end['status'] = "NA"
	self.log.debug("process.end", status=0, n=2)
	if self._one_event:
	    return (process,)
	else:
            return (start, end)
