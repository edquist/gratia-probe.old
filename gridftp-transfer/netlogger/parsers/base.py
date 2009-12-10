"""
Common code for NetLogger parsers
"""
__author__ = 'Dan Gunter <dkgunter@lbl.gov>'
__rcsid__ = '$Id: base.py,v 1.1 2008/11/18 17:20:22 abaranov Exp $'

import calendar 
from netlogger.configobj import ConfigObj, Section
import glob
import imp
import logging
import os
from Queue import Queue, Empty
import re
import sys
import time
from warnings import warn
#
try:
    from pyparsing import Word, alphanums, CharsNotIn, ZeroOrMore
    from pyparsing import Group, Literal
    from pyparsing import StringEnd, White, QuotedString, ParseException
    from pyparsing import Each, OneOrMore, Optional, oneOf
    HAVE_PYPARSING = True
except ImportError:
    HAVE_PYPARSING = False
#
#from netlogger.util import getLogger, logged, tbString
from netlogger import nllog
from netlogger.nlapi import Log, Level
from netlogger.parsers import nlreadline

# Logging
log = nllog.NullLogger()
def activateLogging(name=__name__):
    global log
    log = nllog.getLogger(name)

# Standard field names
TS_FIELD = 'ts'
EVENT_FIELD = 'event'

def getGuid(*strings):
    import string
    c = "" 
    for s in strings:
        c += s
    guid = hash(c)
    return str(guid)

def autoParseValue(vstr):
    try:
        value = int(vstr)
    except ValueError:
        try:
            value = float(vstr)
        except ValueError:
            value = vstr
    return value

def getTimezone():
    """Return a numeric timezone offset from UTC,
    in the standard format [+/-]HH:MM.

    For example, in Berkeley in August, return '-07:00'
    """
    if time.daylight:
        tz = time.altzone # for DST
    else:
        tz = time.timezone # non-DST
    hr = tz / 3600
    min = (tz - (tz/3600)*3600)/60
    sign = ('+','-')[tz > 0] # sic.
    return "%s%02d:%02d" % (sign, hr, min)
    
def parseDate(s):
    """Parse string date into a floating point seconds since epoch UTC.

    The string may either be an ISO8601 date of the form
          YYYY-MM-DDTHH:MM:SS[.fff...](Z|[+-]dd:dd)
    or a string with a floating-point date such as
         1234567890.11122
    Anything not recognized as the first form will be parsed as a float.

    If something doesn't parse, a ValueError will be raised.

    The return value is always floating-point seconds since the UNIX
    epoch (January 1, 1970 at midnight UTC).
    """
    # if it's too short, assume a float
    if len(s) < 7:
        return float(s)
    # UTC timezone?
    if s[-1] == 'Z':
        tz_offs, tz_len = 0, 1
    # explicit +/-nn:nn timezone?
    elif s[-3] == ':':
        tz_offs = int(s[-6] + '1') * (int(s[-5:-3])*3600 + int(s[-2:])*60)
        tz_len = 6
    # otherwise try it as a float
    else:
        return float(s)
    # split into components
    cal, clock = s.split('T')
    year, month, day = cal.split('-')
    hr, minute, sec = clock[:-tz_len].split(':')
    # handle fractional seconds
    frac = 0
    point = sec.find('.')
    if point != -1:
        frac = float(sec[point+1:]) / pow(10, len(sec) - point - 1)
        sec = sec[:point]
    # use calendar to get seconds since epoch
    args = map(int, (year, month, day, hr, minute, sec)) + [0,1,-1]
    return calendar.timegm(args) + frac - tz_offs # adjust to GMT

SYSLOG_DATE_RE = re.compile("\s*(...)\s+(...)\s+(\d\d?) " + 
                            "(\d\d):(\d\d):(\d\d)\s+(\d\d\d\d)\s*")
MONTHS = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4,  'May':5,  'Jun': 6,
          'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}
def parseSyslogDate(date):
    m = SYSLOG_DATE_RE.match(date)
    if m is None:
        raise ValueError("bad syslog date '%s'" % date)
    g = m.groups()
    month = MONTHS[g[1]]
    day, hh, mm, ss, year = map(int, g[2:])        
    sec = time.mktime((year, month, day, hh, mm, ss, 0, 0, 0))
    return sec

def tolerateBlanksAndComments(line=None, error=None, linenum=0):
    """Callback function fitting the signature of the callback
    expected by NLBaseParser.parseStream() that re-raises the error unless
    the line is empty or starts with a hash character, in which
    case it does nothing.
    """
    if len(line) <= 1 or line[0] == '#':
        pass
    else:
        raise(error)

class BPError(ValueError):
    """
    Exception class to indicate violations from the logging best practices
    standard.
    """
    def __init__(self, lineno, msg):
        """Create error object.

        Arguments:
          lineno - The line number on which the error occured.
          msg    - The error message.
        """
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return "Parser error on line %i: %s" % (self.lineno, self.msg)

class BaseParser:
    """Base class for all other Parser classes in the parser modules.

    Uses iterator protocol to return one result at a time; where a
    result is a Best Practices log line (a string).
    Calls read(file) on the subclass to actually get and parse data.
    Each read() can return multiple events,
    or multiple read()s can return one event, transparently
    to the caller who only sees one log line per iteration.
    If 'unparsed_file' is not None, write all lines that returned an 
    error to this file.
    """
    def __init__(self, input_file, raw=False, fullname='unknown', 
                 unparsed_file=None, **kw):
        """Initialize base parser.

        Parameters:
            input_file - File object (must support readline)
            raw - Rather than formatting output as strings, return
                  the dictionary object
            fullname - For logging, the fully qualified name
                  for the logger (matches 'qualname' in the logging config).
            unparsed_file - File object to place records that caused
                  a parse exception
            **kw - Remaining keyword, value pairs are appended to each
                  line of the log. If the same keyword is in a
                  parsed result, the newer value takes precedence.
                  The exception to this is if the parser returns a string
                  instead of a dictionary, e.g. the 'bp' parser:
                  to avoid O(N*M) behavior where N is the number of
                  the keywords and M is the length of the output string,
                  duplicates are not checked.
        """
        if not input_file:
            raise ValueError("input file cannot be empty")
        self._infile = nlreadline.BufferedReadline(input_file)
        try:
            self._offs = self._infile.tell()
        except IOError:
            self._offs = 0
        self._prev_len, self._saved_len = 0, 0
        self._saved = [ ]
        self._name = fullname
        self._ufile = unparsed_file
        self._header_values = { }
        if raw:
            self._formatter = None
        else:
            self._formatter = Log(level=999, guid=False)
        # add these to each record
        self._const_nvp = kw
        # cache string-valued version, will be empty string if kw == {}
        self._const_nvp_str = ' '.join(["%s=%s" % (k,v) 
                                        for k,v in kw.items()])
        # Logging
        self.log = nllog.getLogger(fullname)

    def close(self):
        if self._infile:
            self._infile.close()

    def getOffset(self):
        """Return the offset of the last entirely parsed line.

        In the case of a single line that returned multiple items,
        all of which haven't yet been yet consumed, return the offset at
        the start of this line. This avoids dropping events at the
        expense of possible duplicates.

        It is best to call flush() first to avoid this issue entirely.

        """
        return self._offs

    def setOffset(self, offs):
        """Explicitly set offset.

        This is not normally necessary, as the next() function will
        advance self._offs every time all the resulting items from
        the associated input line have been returned.
        """
        self._infile.seek(offs)
        self._offs = offs

    def getParameters(self):
        """Subclasses should override this method to return
        a dictionary, with all basic types, representing any additional
        state that needs to be saved and restored.
        """
        return { }

    def setParameters(self, param):
        """Subclasses should override this method to update their
        state with the contents of the arg 'param', a dictionary.
        """
        pass

    def setHeaderValues(self, value_dict):
        """Set a dictionary of header keyword, value pairs.
        """
        self._header_values = value_dict

    def getHeaderValue(self, key):
        """Get value from group named 'key', or None.
        """
        return self._header_values.get(key, None)

    def __iter__(self):
        return self

    def next(self):
        """
        Return one saved or new item.

        Get new item(s) by reading and parsing the file.
        Return None if no result, so caller can
        count how many lines were processed and thus
        do fair sharing across multiple inputs
        """
        self.updateOffset()
        # get an item to return
        if self._saved:
            # multiple items were returned before, so just return one
            item = self._saved.pop()
            # if saved is now empty, then we have processed
            # all the items from the last readline, so
            # advance offset by its (saved) length
            if not self._saved:
                self._prev_len = self._saved_len 
        else:
            line = self._infile.readline()
            # stop if line is empty
            if line == '':
                raise StopIteration
            try:
                result = self.process(line.strip())
            except (ValueError, KeyError), E:                    
                if self._ufile:
                    self._ufile.write(line)
                else:
                    warn("parsing '%s': %s" % (line.strip(),E),
                         RuntimeWarning, stacklevel=2)
                result = False
            if not result:
                self._offs += len(line)
                if result is None:
                    raise StopIteration("EOF")
                item = None # return this to caller
            else:
                item = result[0]
                if len(result) == 1:
                    # advance offset by this on next call
                    self._prev_len = len(line)
                else:
                    # don't advance offset until all results are returned
                    self._saved = list(result[1:])
                    self._saved.reverse() # so we can pop()
                    self._saved_len = len(line)
        # if this is a dictionary, potentially do more work
        if isinstance(item, dict):            
            item = self._formatDict(item)
        elif item is not None and self._const_nvp_str:
            # put extra stuff last, before trailing newline
            item = item[:-1] + ' ' + self._const_nvp_str + '\n'
        # return the item
        return item

    def updateOffset(self):
        """Advance offset by length previously parsed input.
        """
        self._offs += self._prev_len
        self._prev_len = 0 # do not add this to offset again
        
    def _formatDict(self, item):
        """Normalize 'level' and potentially format to a string
	"""
        # Normalize the 'level' value
        if item.has_key('level'):
	    level = item['level']
	    if hasattr(level, 'upper'):
	        lvlname = item['level'].upper()
	        item['level'] = Level.getLevel(lvlname)
        # Add constant key, value pairs: do a copy and 
        # reverse update so new values override old ones.
        if self._const_nvp:
            _tmp = self._const_nvp.copy()
            _tmp.update(item)
            item = _tmp
        # If formatting is desired, serialize to a string
        if self._formatter:
            try:
	        item = self._formatter(**item)
	    except (ValueError, KeyError, IndexError), E:
	        log.warn("error while formatting: %s: %s" % (item,E))
	        item = ""
        return item

    def flush(self):
        """Return a list of all saved items, i.e., of all items 
        that were parsed but not returned yet, and clear this list.
        """
        result = [ ]
        for item in self._saved:
            if isinstance(item, dict):            
                item = self._formatDict(item)
            result.append(item)
        self._saved = [ ]
        self._offs += self._saved_len
        self._saved_len, self._prev_len = 0, 0
        return result

    def process(self, line):
        """Subclasses must override this method to return a list
        of dictionaries or formatted log strings (with newlines).

        If there is an error with the format, they should
        raise a ValueError, KeyError, or this module's ParseError.
        If nothing is yet ready, return an empty list or tuple.
        To cause the caller to stop parsing this log, i.e. nothing will
        ever be ready, return None.
        """
        pass

    def boolParam(self, s):
        """Convert a possibly-string-valued boolean parameter, from
        the configuration file, into a proper boolean value.
        """
        if isinstance(s, bool):
            return s
        if isinstance(s, str):
            sl = s.lower()
            if sl in ('yes', 'on', 'true', '1'):
                return True
            else:
                return False
        return bool(s)

    def __str__(self):
        return "%s(%s)" % (self._name, self._infile)

class NLBaseParser(BaseParser):
    def __init__(self, input_file=None, verify=False, parse_date=True,
                 strip_quotes=True, err_cb=None, **kw):
        """Create a NetLogger parser, that implements the BaseParser
        interface as well as its own API for parsing individual lines
        and streams with user-supplied callbacks.

        Arguments:
          verify - Check that the line is correct
          parse_date - Parse the ISO timestamp to seconds
          strip_quotes - Return quoted string values without quotes.
          err_cb - Optional callback on errors. Signature:
                     err_cb(line=<string with newline>, error=<Exception>,
                            linenum=<integer line number>)
                   If set to a function, the function is called.
                   If set to False, errors are completely ignored.
                   If set to True, errors are appended to err_list.
                   If None (the default) errors are propagated to the caller.
                           These errors are of type BPError.
        """
        self.verify, self.parse_date, self.strip_quotes = \
            verify, parse_date, strip_quotes
        self.err_cb = err_cb
        self.err_list = [ ]
        if input_file is None:
            input_file = NullFile()
        BaseParser.__init__(self, input_file, fullname='NLParser', 
                            raw=True, **kw)

    def parseLine(self, line):
        """Return a dictionary corresponding to the name,value pairs
        in the input 'line'.
        Raises ValueError if the format is incorrect.
        """
        pass

    def parseStream(self):
        """Parse input stream, calling parseLine() for each line.

        Return:
           generator function, yielding the result of parseLine() for
           each line in the input stream
        """        
        for line_num, line in enumerate(self._infile.xreadlines()):
            try:
                d = self.parseLine(line)
                yield d
            except ValueError,E:
                if self.err_cb is False:
                    pass
                else:
                    bpe = BPError(line_num, E)
                    if self.err_cb is True:
                        self.err_list.append(bpe)                    
                    elif self.err_cb is None:
                        raise bpe
                    else:
                        self.err_cb(line=line, error=bpe, linenum=line_num)

class NLFastParser(NLBaseParser):
    """
    Simpler, faster, less flexible NL parser.
    
    * Optionally does some error-checking, but can't tell why it is wrong.
    Note: error-checking takes 50% or so longer.
    * Uses regular expressions instead of pyparsing.
    * Observed speedups on order of 50x (YMMV).
    """
    E1 = re.compile('\s*([a-zA-Z][a-zA-Z0-9._\-]*)=([^"]\S*|"[^"]*")\s*')
    E2 = re.compile('(\s*)[a-zA-Z][a-zA-Z0-9._\-]*=(?:[^"]\S*|"[^"]*")(\s*)')

    # implementation of the BaseParser API
    def process(self, line):
        return (self.parseLine(line),)

    def parseLine(self, line):
        """Parse a BP-formatted line.
        """
        s = line.strip()
        if len(s) == 0:
            return { }
        d = { }
        fields = self.E1.findall(s)
        if self.verify:
            ws = self.E2.findall(s)
            ws_len = sum([len(x)+len(y) for x,y in ws])
            fld_len = sum([len(x)+len(y)+1 for x,y in fields])
            if ws_len + fld_len < len(s):
                n = len(s) - (ws_len + fld_len)
                raise ValueError("%d bad chars in log line '%s'" % (n, s))
        for name,value in fields:
            if name == 'ts':
                if self.parse_date:
                    d[name] = parseDate(value)
                else:
                    d[name] = value
            elif value and value[0] == '"':
                if self.strip_quotes:
                    d[name] = value[1:-1]
                else:
                    d[name] = value
            else:
                d[name] = value
        if self.verify:
            for k in 'ts', 'event':
                if not d.has_key(k):
                    raise ValueError("missing %s" % k)
        return d

if HAVE_PYPARSING:
    class NLPyParser(NLBaseParser):
        """pyparsing--based implementation of the NLBaseParser
        """
        notSpace = CharsNotIn(" \n")
        eq = Literal('=').suppress()
        value = (QuotedString('"', escChar=chr(92), unquoteResults=False) \
                     ^ OneOrMore(notSpace))
        ts = Group(Literal('ts') + eq + value)
        event = Group(Literal('event') + eq + value)
        name = ~oneOf("ts event") + Word(alphanums +'-_.')
        nv = ZeroOrMore(Group(name + eq + value))
        nvp = Each([ts, event, nv]) + White('\n').suppress() + StringEnd()

        def parseLine(self, line):
            try:
                rlist = self.nvp.parseString(line).asList()
            except ParseException, E:
                raise ValueError(E)
            result = {}
            for a in rlist:
                if self.parse_date and a[0] == 'ts':
                    result[a[0]] = parseDate(a[1])
                else:
                    result[a[0]] = a[1]
            return result

    # implementation of the BaseParser API
    def process(self, line):
        return (self.parseLine(line),)

else:
    class NLPyParser:
        BADNESS = """"
Can't use the NLPyParser class because pyparsing is not installed. 
You can use NLFastParser instead, run 'easy_install pyparsing', or 
install from http://pyparsing.wikispaces.com/ .
"""
        def __init__(self, *args, **kw):
            raise NotImplementedError(self.BADNESS)

class NullFile:
    def __init__(self, *args):
        return
    def read(self, n): return ''
    def readline(self): return ''
    def seek(self, n, mode): pass
    def tell(self): return 0

def getTimezone():
    """Return current timezone as UTC offset,
    formatted as [+/-]HH:MM
    """
    tz = time.altzone # for DST
    hr = int(tz / 3600)
    min = int((tz/3600. - hr)*60)
    sign = ('+','-')[tz > 0] # sic.
    return "%s%02d:%02d" % (sign, hr, min) 
