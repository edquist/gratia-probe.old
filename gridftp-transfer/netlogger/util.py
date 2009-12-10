"""
Utility functions for NetLogger modules and command-line programs
"""
__rcsid__ = "$Id: util.py,v 1.1 2008/11/18 17:20:21 abaranov Exp $"
__author__ = "Dan Gunter (dkgunter (at) lbl.gov)"

from copy import copy
import glob
import logging
from optparse import OptionParser, Option, OptionValueError, make_option
import os
import Queue
import re
import signal
import sys
import tempfile
import time
import traceback
#
from netlogger import configobj

EOF_EVENT = "netlogger.EOF"

class ConfigError(Exception):
    """Use this exception for configuration-time error handling.
    """
    pass

class ScriptOptionParser(OptionParser):
    standard_option_list = (
        make_option('-q', '--quiet',
                    action='store_true', dest='quiet',
                    help="only report errors"),                
        make_option('-v', '--verbosity', default=0,
                    action='count', dest='verbosity',
                    help="show verbose status information, "
                    "repeat for even more detail"),
        )

class CountingQueue(Queue.Queue):
    """Wrapper around Queue that counts how many items
    were processed, for accounting purposes.
    """
    def __init__(self, type_, *args):
        Queue.Queue.__init__(self, *args)
        self.n = 0
        if type_ == 'get':
            self._gets, self._puts = True, False
        else:
            self._gets, self._puts = False, True
            
    def get(self, *args, **kwargs):
        if self._gets:
            self.n += 1
        return Queue.Queue.get(self, *args, **kwargs)

    def put(self, *args, **kwargs):
        if self._puts:
            self.n += 1
        return Queue.Queue.put(self, *args, **kwargs)
        
    def getNumProcessed(self):
        return self.n
      
def tbString(depth=6, sep=''):
    """More convenient function for traceback-as-a-string
    """
    error_type, error_value, trbk = sys.exc_info()
    tb_list = traceback.format_tb(trbk, depth) 
    return sep.join(tb_list)

def parse_nvp(args):
    d = { }
    for arg in args:
        try:
            name, value = arg.split('=')
        except ValueError:
            pass
        d[name] = value
    return d
   
def tzstr():
    return "%s%02d:%02d" % (('+','-')[time.timezone > 0],
                            time.timezone / 3600 ,
                            (time.timezone - int(time.timezone/3600)*3600)/60)

def parseDatetime(d, utc=False):
    """Parse a datetime object, or anything that formats itself
    with isoformat(), to number of seconds since epoch.
    """
    from netlogger.parsers.base import parseDate
    if d is None:
        raise ValueError("date is None")
    iso = d.isoformat()
    # add 'midnight' time if none given
    if 'T' not in iso:
        iso += 'T00:00:00'
    # only append timezone if none is there already        
    if not iso.endswith('Z') and not re.match('.*[+-]\d\d:\d\d$', iso):
        if utc:
            iso += 'Z'
        else:
            iso += tzstr()
    return parseDate(iso)

MAGICDATE_EXAMPLES = ', '.join(["%s" % s for s in (
     '<N> weeks|days|hours|minutes|seconds time ago',
     'Today',
     'Now',
     'Tomorrow',
     'Yesterday',
     '4th [[Jan] 2003]',
     'Jan 4th 2003',
     'mm/dd/yyyy (first)',
     'dd/mm/yyyy (second)',
     'yyyy-mm-dd',
     'yyyymmdd',
     'next Tuesday',
     'last Tuesday')])

class ProgressMeter:
    """A simple textual progress meter.
    """
    REPORT_LINES = 1000
    def __init__(self, ofile):
        self.ofile = ofile
        self.reset(0)
    def reset(self, n):
        self.t0 = time.time()
        self.last_report = n
    def setLine(self, num):
        if num - self.last_report >= self.REPORT_LINES:
            n = num - self.last_report
            dt = time.time() - self.t0
            rate = n / dt
            self.ofile.write("%5d: %d lines in %lf sec = %lf lines/sec\n" % 
                             (num, n, dt, rate))
            self.reset(num)

class NullProgressMeter:
    """Substitute for ProgressMeter when you don't want anything to
    actually be printed.
    """
    def __init__(self, ofile=None):
        return
    def setLine(self, num):
        pass

def mostRecentFile(dir, file_pattern, after_time=None):
    """Search 'dir' for all files matching glob 'file_pattern',
    and return the mostRecent one(s). If 'after_time' is given,
    it should be a number of seconds since the epoch UTC; no files
    will be returned if none is on or after this time.

    Returns a list of the full paths to file(s), or an empty list.
    More than one file may be returned, in the case that they have
    the same modification time.

    """
    if not os.path.isdir(dir):
        return [ ]
    search_path = os.path.join(dir, file_pattern)
    # make a sortable list of filenames and modification times
    timed_files = [(os.stat_result(os.stat(fname)).st_mtime, fname) 
                   for fname in glob.glob(search_path)]
    # if the list is empty, stop
    if not timed_files:
        return [ ]
    # reverse sort so most-recent is first
    timed_files.sort(reverse=True)
    most_recent_time = timed_files[0][0]
    # return nothing if the most recent time is not
    # after the cutoff
    if after_time is not None and most_recent_time < int(after_time):
        return [ ]
    # start with most recent, then append all 'ties'
    result = [ timed_files[0][1] ]
    i = 1
    try:
        while timed_files[i][0] == most_recent_time:
            result.append(timed_files[i][1])
            i += 1
    except IndexError:
        pass # ran off end of list. all ties (!)
    # return all 'most recent' files
    return result

def daemonize():
    """Make current process into a daemon."""
    # do the UNIX double-fork magic, see Stevens' "Advanced 
    # Programming in the UNIX Environment" for details (ISBN 0201563177)
    try: 
        pid = os.fork() 
        if pid > 0:
            # exit first parent
            sys.exit(0) 
    except OSError, e: 
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1)
    # do second fork
    try: 
        pid = os.fork() 
        if pid > 0:
            # exit from second parent
            sys.exit(0) 
    except OSError, e: 
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1)
    # decouple from parent environment
    os.chdir("/")
    try:
        os.setsid() 
    except OSError:
        pass
    os.umask(0) 
    # close all fd's
    for fd in xrange(1024):
        try:
            os.close(fd)
        except OSError:
            pass
    # redirect stdin, stdout, stderr
    try:
        devnull = os.devnull
    except AttributeError:
        devnull = "/dev/null"
    os.open(devnull, os.O_RDWR) # returns 0
    os.dup2(0, 1)
    os.dup2(0, 2)
    

def _getNumberedFiles(path):
    result = [ ]
    for filename in glob.glob(path + ".*"):
        try:
            name, ext = filename.rsplit('.',1)
            n = int(ext)
            result.append((n,filename))
        except (IndexError, ValueError):
            pass
    return result

def getNextNumberedFile(path, mode="w", strip=False, open_file=True):
    if strip: # take off .<num> extension first
        path = path.rsplit('.', 1)[0]
    numbered = _getNumberedFiles(path)
    if numbered:
        numbered.sort(reverse=True)
        next_num = numbered[0][0] + 1
    else:
        next_num = 1
    next_file = "%s.%d" % (path, next_num)
    if open_file:
        return file(next_file, mode)
    else:
        return next_file

def getAllNumberedFiles(path):
    nf = _getNumberedFiles(path)
    return map(lambda x: x[1], nf)

def getLowestNumberedFile(path, mode="r"):
    numbered = _getNumberedFiles(path)
    if numbered:
        numbered.sort()
        result = file(numbered[0][1], mode)
    else:
        result = None
    return result

# def BPize(h1, guid=True, pfx="netlogger."):
#     """Make a given handler produce BP-happy logs as long
#     as the message itself is in name=value style.
#     """
#     import time, logging
#     L = time.mktime(time.localtime())
#     G = time.mktime(time.gmtime())
#     sign = ('','+')[L > G]
#     tzone = "%s%.02d:00" % (sign, int((L - G)/3600))
#     if guid:
#         g = " guid=" + nlapi.getGuid()
#     else:
#         g = ''
#     ts = "ts=%(asctime)s.%(msecs).03d" + tzone
#     formatter = logging.Formatter(ts + g + " event=" + pfx + "%(message)s" + " level=%(levelname)s")
#     formatter.datefmt = "%Y-%m-%dT%H:%M:%S"
#     h1.setFormatter(formatter)

class ThrottleTimer:
    """Given a ratio of time that the program should be running
    in a given time-slice, and assuming that the program is running
    continuously between calls to throttle(), periodically sleep so
    that the program is running for roughly that proportion of time.

    For example, if run_ratio is 0.1 then calling throttle() in a 
    loop will cause it to sleep 90% of the time:
       tt = ThrottleTimer(0.1)
       ...
       tt.start()
       while 1:
           do_something()
           tt.throttle() # sleeps here

    """
    def __init__(self, run_ratio, min_sleep_sec=0.1):
        """Create timer.

        'run_ratio' is the desired ratio of the time between calls to the
          time sleeping in ths timer.
        'min_sleep_sec' is the mininum size of the argument to time.sleep(),
          before throttle() will actually call it. This attempts to minimize
          the inaccuracy encountered with very small sleep times.
        """
        self.sleep_ratio = (1/run_ratio - 1)
        self.t0 = time.time()
        self.min_sleep_sec = min_sleep_sec

    def start(self):
        """Start the timer.
        """
        self.t0 = time.time()

    def throttle(self):
        """Sleep for an appropriate time.

        If that time would be less than 'min_sleep_sec' (see constructor),
        don't actually perform the sleep. Therefore, it should be safe
        to call this in a (relatively) tight loop.
        """
        t1 = time.time()
        sleep_sec = (t1 - self.t0) * self.sleep_ratio
        if sleep_sec >= self.min_sleep_sec:
            time.sleep(sleep_sec)
            self.t0 = time.time()
        
class NullThrottleTimer(ThrottleTimer):
    """Null class for ThrottleTimer. Cleans up calling code."""
    def __init__(self, run_ratio=None, min_sleep_sec=None):
        ThrottleTimer.__init__(self, 1)
    def start(self): 
        return
    def throttle(self): 
        return

class NullFile:
    """Null-object pattern for 'file' class.
    """
    def __init__(self, name='(null)', mode='r', buffering=None):
        self.name = name
        self.mode = mode
        self.encoding = None
        self.newlines = None
        self.softspace = 0
    def close(self):
        pass
    def closed(self):
        return True
    def fileno(self):
        return -1
    def flush(self):
        pass
    def isatty(self):
        return False
    def next(self):
        raise StopIteration()
    def read(self, n):
        return ''
    def readline(self):
        return ''
    def readlines(self):
        return [ ]
    def seek(self, pos):
        pass
    def tell(self):
        return 0
    def write(self, data):
        return None
    def writelines(self, seq):
        return None
    def xreadlines(self):
        return self


class IncConfigObj(configobj.ConfigObj):
    """Recognize and process '#@include <file>' directives
    transparently. Do not deal with recursive references, i.e.
    ignore directives inside included files.
    """
    def __init__(self, infile, **kw):
        """Take same arguments as ConfigObj, but in the case of a file
        object or filename, process #@include statements in the file.
        """   

        if not(isinstance(infile,str) or hasattr(infile,'read')):
            # not a file: stop
            configobj.ConfigObj.__init__(self, infile, **kw)
            return
        # open file
        if hasattr(infile, 'read'):
            f = infile
            f.seek(0) # rewind to start of file
        else:
            f = file(infile)
        dir = os.path.dirname(f.name)
        # Create list of lines that includes the included files
        lines = [ ]
        file_lines = [ ] # tuple: (filename, linenum)
        i = 0
        for line in f:
            # look for include directive
            s = line.strip()
            m = re.match("@include (\"(.*)\"|\'(.*)\'|(\S+))", s)
            if m:
                # This line is an @include.
                # Pick out the group that matched.
                inc_path = filter(None, m.groups()[1:])[0]
                # open the corresponding file
                if not inc_path[0] == '/':
                    inc_path = os.path.join(dir, inc_path)
                try:
                    inc_file = file(inc_path)
                except IOError:
                    raise IOError("Cannot read file '%s' included from '%s'" % (inc_path, f.name))
                # add contents of file to list of lines
                j = 0
                for line in inc_file:
                    j += 1
                    file_lines.append((inc_file.name, j))
                    lines.append(line)
            else:
                # This is a regular old line
                i += 1
                file_lines.append((f.name, i))
                lines.append(line)
        # Call superclass with list of lines we built
        try:
            configobj.ConfigObj.__init__(self, lines, **kw)
        except configobj.ParseError, E:
            # Report correct file and line on parse error
            m = re.search('line "(\d+)"', str(E))
            if m is None:
                raise
            else:
                #print file_lines
                n = int(m.group(1)) - 1
                filename, lineno = file_lines[n]
                msg = "Invalid line %s in %s: \"%s\"" % (lineno, filename, lines[n].strip())
                raise configobj.ParseError(msg)
                    
def handleSignals(*siglist):
    """Set up signal handlers.

    Input is a list of pairs of a function, and then a list of signals
    that should trigger that action, e.g.:
       handleSignals( (myfun1, (signal.SIGUSR1, signal.SIGUSR2)),
                      (myfun2, (signal.SIGTERM)) )
    """
    for action, signals in siglist:
        for signame in signals:
            if hasattr(signal, signame):
                signo = getattr(signal, signame)
                signal.signal(signo, action)
       

_TPAT = re.compile("(\d+)\s*([mhds]|minutes?|hours?|days?|seconds?)?$")
_TFAC = { None : 1, 's': 1, 'm':60, 'h': 60*60, 'd': 60*60*24, 
          'seconds': 1, 'minutes':60, 'hours': 60*60, 'days': 60*60*24 ,
          'second': 1, 'minute':60, 'hour': 60*60, 'day': 60*60*24 }
def timeToSec(s):
    """Convert time period to a number of seconds.
    """
    s = s.lower()
    m = _TPAT.match(s)
    if m is None:
        raise ValueError("invalid time")
    g = m.groups()
    num = int(g[0])
    factor = _TFAC[g[1]]    
    return num * factor

def check_timeperiod(option, opt, value):
    try:
        return timeToSec(value)
    except ValueError:
        raise OptionValueError(
            "option %s: invalid time period value: %r" % (opt, value))

class ScriptOption(Option):
    TYPES = Option.TYPES + ("timeperiod",)
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["timeperiod"] = check_timeperiod

def noop(*args, **kwargs):
    """Handy no-operation function.
    """
    pass

def as_bool(x):
    if x is True or x is False:
        return x
    if isinstance(x, int):
        return bool(x)
    retval = None
    if isinstance(x, str):
        retval = {
        'yes': True, 'no': False,
        'on': True, 'off': False,
        '1': True, '0': False,
        'true': True, 'false': False,
        }.get(x.lower(), None)
    if retval is None:
        raise ValueError("Cannot convert to bool: %s" % x)
    return retval

