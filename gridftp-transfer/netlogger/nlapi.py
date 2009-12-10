
## Copyright (c) 2004, The Regents of the University of California, through 
## Lawrence Berkeley National Laboratory (subject to receipt of any required 
## approvals from the U.S. Dept. of Energy).  All rights reserved.

"""
NetLogger instrumentation API for Python

Write NetLogger log messages. Most users of this API will
use the Log class, which is a little like a 'Logger' object in the
Python logging API.

Utility functions include functions to get and set the Grid Job ID.
"""
__author__ = "Dan Gunter"
__created__ = "1 April 2004"
__rcsid__ = "$Id: nlapi.py,v 1.1 2008/11/18 17:20:21 abaranov Exp $"

import calendar
import math
import os
import socket
import string
import sys
import time
import types
import urlparse

#
## Exceptions
#

class ParseException(Exception):
    pass
class FormatException(Exception):
    pass

#
## Constants
#

# Environment variable to store GID
GID_ENV = 'NL_GID'

# Environment variable to store destination
NLDEST_ENV = 'NL_DEST'

# Environment variable for level file
CFG_ENV = 'NL_CFG'

FIELD_SEP = ' '
REC_SEP = '\n'
EOR = '\n'
KEYVAL_SEP = '='

# Port
DEFAULT_PORT = 14380

# Level
class Level:
    NOLOG = 0
    FATAL = 1
    ERROR = 2
    WARN = 3
    WARNING = 3
    INFO = 4
    DEBUG = 5
    DEBUG1 = 6
    DEBUG2 = 7
    DEBUG3 = 8
    ALL = -1

    names = { NOLOG : 'NOLOG', 
              FATAL:'Fatal', 
              ERROR:'Error', 
              WARN:'Warn', 
              INFO : 'Info',
              DEBUG:'Debug', 
              DEBUG1 : 'Debug1', 
              DEBUG2:'Debug2', 
              DEBUG3:'Debug3', }

    def getName(level):
        return Level.names.get(level, 'User')
                        
    def getLevel(name):
        if name.isupper() and hasattr(Level, name):
            return getattr(Level, name)
        raise ValueError("no such level name: %s" % name)
                 
DATE_FMT = "%04d-%02d-%02dT%02d:%02d:%02d"
#
## Utility functions
#


def getGuid(create=True, env=GID_ENV):
    """Return a GUID.
    If 'create' is True (the default), and if none is found 
    in the environment then create one.
    """
    gid = os.environ.get(env, None)
    if gid is None:
        if create:
            gid = _uuid()
    return gid

# Call this if you want to set a GID manually
def setGuid(id, env=GID_ENV):
    """Replace current guid in the environment with provided value.
    Return old value, or None if there was no old value.

    Note: may cause memory leak on FreeBSD and MacOS. See system docs.
    """
    old_gid = os.environ.get(env, None)
    os.environ[env] = id
    return old_gid

_g_hostip = None

def getHost():
    global _g_hostip
    if _g_hostip is not None:
        return _g_hostip
    try:
        ip = socket.gethostbyname(socket.getfqdn())
    except:
        ip = '127.0.0.1'
    _g_hostip = ip
    return ip

def getProg():
    import sys
    return sys.argv[0]

def getDest():
    return os.environ.get(NLDEST_ENV,None)

class LevelConfig:
    """Set logging level from a configuration file.
    The format of the file is trivial: an integer log level.
    """
    DEFAULT = Level.INFO

    def __init__(self,filename):
        self._f = filename
        self._level = None

    def getLevel(self):
        if self._level is None:
            try:
                self._level = self.DEFAULT
                f = file(self._f)
                line = f.readline()
                i = int(line.strip())
                self._level = i
            except IOError:
                pass
            except ValueError:
                pass
        return self._level
        
if os.getenv(CFG_ENV) != None:
    g_level_cfg = LevelConfig(os.getenv(CFG_ENV))
else:
    g_level_cfg = None

class Log:
    """NetLogger log class.
    
    Name=value pairs for the log are passed as keyword arguments.
    This is mostly good, but one drawback is that a period '.' in the
    name is confusing to python. As a work-around, use '__' to mean '.', 
    e.g. if you want the result to be "foo.id=bar", then do::
        log.write(.., foo__id='bar')
    Similarly, a leading '__' will be stripped (e.g. to avoid stepping
    on keywords like 'class')
    
    If you instantiate this class without a 'logfile', it will act
    as a formatter, returning a string.
    """
    class OpenError(Exception): pass
    
    def __init__(self, logfile=None, flush=False, prefix=None, 
                 level=Level.INFO, newline=True, guid=True):
        """Constructor.
        """
        self._logfile = None
        self._newline = newline
        self._flush = [None, self.flush][flush]
        self.setPrefix(prefix)
        self._meta = {}
        if isinstance(logfile,types.StringType):
            try:
                self._logfile = urlfile(logfile)
            except (socket.gaierror, socket.error, IOError), E:
                raise self.OpenError(E)
        else:
            self._logfile = logfile
        if g_level_cfg is None:
            self._level = level
        else:
            self._level = g_level_cfg.getLevel()
        if guid is True:
            guid = getGuid(create=False)
            if guid:
                self._meta[None] = {'guid':guid}
        elif isinstance(guid,str):
            self._meta[None] = {'guid':guid}
        
    def setLevel(self,level):
        """Set highest level of messages that WILL be logged.
        Messages below this level (that is, less severe,
        higher numbers) will be dropped.

        For example::
          log.setLevel(Level.WARN)
          log.error('argh',{}) # logged
          log.info('whatever',{}) # dropped!
        """
        self._level = level

    def setPrefix(self, prefix):
        if prefix is None:
            self._pfx = ''
        elif prefix.endswith('.'):
            self._pfx = prefix
        else:
            self._pfx = prefix + '.'
        
    def debugging(self):
        """Return whether the level >= debug.
        """
        return self._level >= Level.DEBUG

    def flush(self):
        """Flush output object.
        """
        if self._logfile:
            self._logfile.flush()

    def write(self, event='event', ts=None, level=Level.INFO, **kw):
        """Write a NetLogger string.
           If there is a logfile, returns None
           Otherwise, returns a string that would have been written.
        """
        if self._level != Level.ALL and level > self._level:
            return
        if not ts:
            ts = time.time()
        buf = self.format(self._pfx + event, ts, level, kw)
        if self._logfile is None:
            return buf
        self._logfile.write(buf)
        if self._flush:
            self.flush()

    __call__ = write
    
    def error(self, event='', **kwargs):
        self.write(event, level=Level.ERROR, **kwargs)
        
    def warn(self, event='', **kwargs):
        self.write(event, level=Level.WARN, **kwargs)

    def info(self, event='', **kwargs):
        self.write(event, level=Level.INFO, **kwargs)

    def debug(self, event='', **kwargs):
        self.write(event, level=Level.DEBUG, **kwargs)

    def _append(self, fields, kw):
        for k,v in kw.items():
            if k.startswith('__'):
                k = k[2:]
            k = k.replace('__','.')
            if isinstance(v,str):
                if not v:
                    v = '""'
                elif ' ' in v or '\t' in v or '"' in v or '=' in v:
                    v = '"%s"' % v.replace(r'"', r'\"')
                fields.append("%s=%s" % (k,v))
            elif isinstance(v, float):
                fields.append("%s=%lf" % (k,v))
            elif isinstance(v, int):
                fields.append("%s=%d" % (k,v))
            else:
                s = str(v)
                if ' ' in s or '\t' in s:
                    s = '"%s"' % s                
                fields.append("%s=%s" % (k,s))
            
    def format(self, event, ts, level, kw):
        rec = { }
        # format output
        fields = ["ts=" + formatDate(ts), 
                  "event=" + event]
        if level is not None:
            if isinstance(level, int):
                fields.append("level=" + Level.getName(level))
            else:
                fields.append("level=%s" % level)
        if kw:
            self._append(fields, kw)
        if self._meta.has_key(event):
            self._append(fields, self._meta[event])
        if self._meta.has_key(None):
            self._append(fields, self._meta[None])
        buf = FIELD_SEP.join(fields)
        if self._newline:
            return buf + REC_SEP
        else:
            return buf

    def setMeta(self, event=None, **kw):
        self._meta[event] = kw

    def close(self):
        self.flush()
        
    def __del__(self):
        if not hasattr(self,'closed'):
            self.close()
        self.closed = True

    def __str__(self):
        if self._logfile:
            return str(self._logfile)
        else:
            return repr(self)

def formatDate(ts):
    if isinstance(ts,str):
        return ts
    gmtm = time.gmtime(ts)
    usec = int((ts - int(ts)) * 1000000 + 0.5)
    return "%s.%06dZ" % (DATE_FMT % gmtm[0:6], usec)

# set up urlparse to recognize x-netlog schemes
for scheme in 'x-netlog','x-netlog-udp':
    urlparse.uses_netloc.append(scheme)
    urlparse.uses_query.append(scheme)

def urlfile(url):
    """urlfile(url:str) -> file
    
    Open a NetLogger URL and return a write-only file object.
    """
    # Split URL
    scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
    # Put query parts into a dictionary for easy access later
    query_data = {}
    if query:
        query_parts = query.split('&')
        for flag in query_parts:
            name, value = flag.split('=')
            query_data[name] = value
    # Create file object
    if scheme == "file" or scheme == "" or scheme is None:
        # File
        if path == '-':
            fileobj = sys.stdout
        elif path == '&':
            fileobj = sys.stderr
        else:
            if query_data.has_key('append'):
                is_append = boolparse(query_data['append'])
                open_flag = 'aw'[is_append]
            else:
                open_flag = 'a'
            fileobj = file(path,open_flag)
    elif scheme.startswith("x-netlog"):
        # TCP or UDP socket
        if netloc.find(':') == -1:
            addr = (netloc, DEFAULT_PORT)
        else:
            host, port_str = netloc.split(':')
            addr = (host, int(port_str))
        if scheme == "x-netlog":
            # TCP Socket
            sock = socket.socket()
        elif scheme == "x-netlog-udp":
            # UDP Socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            raise ValueError("Unknown URL scheme '%s', "
                             "must be empty, 'file' or 'x-netlog[-udp]'" %
                             scheme)
        #print "connect to address %s" % addr
        sock.connect(addr)
        fileobj = sock.makefile('w')
    else:
        raise ValueError("Unknown URL scheme '%s', "
                         "must be empty, 'file' or 'x-netlog[-udp]'" % scheme)
    return fileobj

def urltype(url):
    """urltype(url:str) -> 'file' | 'tcp' | None
    
    Return a canonical string representing the type of URL,
    or None if the type is unknown
    """
    scheme = urlparse.urlparse(url)[0]
    if scheme == "file" or scheme == "" or scheme is None:
        return 'file'
    elif scheme == "x-netlog":
        return 'tcp'
    else:
        return None

# Get host

_g_hostip = None
def get_host():
    global _g_hostip
    if _g_hostip is not None: 
        return _g_hostip
    try:
        ip = socket.gethostbyname(socket.getfqdn())
    except:
        ip = '127.0.0.1'
    _g_hostip = ip
    return ip

 
# Internal functions
try:
    import uuid
    def _uuid():
        return str(uuid.uuid1())
except ImportError:
    # From: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/213761
    import time, random, md5
    def _uuid():
      t = long( time.time() * 1000 )
      r = long( random.random()*100000000000000000L )
      try:
        a = socket.gethostbyname( socket.gethostname() )
      except:
        # if we can't get a network address, just imagine one
        a = random.random()*100000000000000000L
      data = str(t)+' '+str(r)+' '+str(a)
      data = md5.md5(data).hexdigest()
      return "%s-%s-%s-%s-%s" % (data[0:8], data[8:12], data[12:16],
                                 data[16:20], data[20:32])


