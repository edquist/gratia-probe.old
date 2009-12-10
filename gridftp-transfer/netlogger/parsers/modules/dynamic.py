"""
Dynamic parser module that determines which actual parser
to use on a per-line basis.
"""
__author__ = 'Dan Gunter dkgunter@lbl.gov'
__rcsid__ = '$Id: dynamic.py,v 1.1 2008/11/18 17:20:22 abaranov Exp $'

import logging
import re
#
from netlogger.parsers.base import BaseParser
from netlogger import nllog

# Logging
log = None
def activateLogging(name=__name__, **kw):
    global log
    log = nllog.getLogger(name, **kw)

class Parser(BaseParser):
    def __init__(self, f, pattern=None,  show_header_groups=False, 
                 header_groups_prefix="syslog.", **kw):
        """A meta-parser that matches parser modules to a given
        line based on a header. The expected header
        is given by regular expression. For each input line, values of matching
        named groups, e.g. `(?P<name>'expr')`,
        are used to select the parser to use for that line.

        Parameters:
            - pattern: Regular expression to extract the header
            - show_header_groups {True,*False*}: A list of named groups in the
              header expression include in the output event.
              If None, False, or empty, no named header parts will not be included.
              If True, include any/all header parts.
            - header_groups_prefix {*'syslog.'*}: String prefix to add to each name in the
              header group, to avoid name-clashes with the names already in the event record. 
              The default prefix reflects the primary use-case of parsing a syslog-ng
              receiver's output.
        """
        self.header = re.compile('^' + pattern)
        self.modules = { }
        # header groups
        val = show_header_groups
        if val is True:
            self._show_hdr = True
        elif not val:
            self._show_hdr = False
        else:
            self._show_hdr = dict.fromkeys(val) # makes lookup fast
        self._pfx = str(header_groups_prefix) # a bit safer to use str()
        BaseParser.__init__(self, f, fullname=__name__, **kw)

    def add(self, module_name, named_patterns, module_instance):
        """Add a module and the dictionary of patterns (with the name of
        the matching group as the key, and a compiled regular expression
        as the value) that should match it.
        An empty dictionary for 'named_patterns' will match anything.
        """
        self.modules[module_name] = (named_patterns, module_instance)

    def getParserForLine(self, line):
        """Find parser instance matching the header that
        will be extracted from the string 'line'.

        Return triple:  parser instance, start of the line body, and the
        matched header parts as a dictionary.
        """
        # Break line into named groups
        matchobj = self.header.match(line)
        if matchobj is None:
            return None, None, None
        group_dict = matchobj.groupdict()
        # Brute-force implementation: look through all entries in
        # the dictionary, and return the first module instance
        # for which all named patterns match.
        for name, (pat_dict, inst) in self.modules.items():
            matched = True
            for key, value in pat_dict.items():
                if not group_dict.has_key(key) or \
                        not value.match(group_dict[key]):
                    matched = False
                    break
            if matched: 
                inst.setHeaderValues(group_dict)
                return inst, matchobj.span()[1], group_dict
        return None, None, None

    def process(self, line):
        parser, offs, groups = self.getParserForLine(line)
        if parser is None:
            return ()
        r = parser.process(line[offs:])
        if r and self._show_hdr:
            r = self._add_hdr_groups(r, groups)
        return r

    def _add_hdr_groups(self, r, groups):
        """Add header groups to each returned value.
        """
        add_d, add_str = { }, None
        for key, value in groups.items():
            if self._show_hdr is True or \
                    self._show_hdr.has_key(key):
                add_d[self._pfx + key] = value
        if not add_d:
            return r # nothing to add, stop
        # return value may be pre-formatted as a string
        prefmt = filter(lambda _: not isinstance(_,dict), r)
        if not prefmt: # all dict
            for d in r:
                d.update(add_d)
        else:
            # build the string to add
            s = ' '.join(["%s=%s" % (k,v) for k, v in add_d.items()])
            add_str = ' ' + s
            # if all pre-formatted, just add to all
            if len(prefmt) == len(r):
                r = map(lambda s: s + add_str, r)
            # else if mix, deal with each separately 
            else:
                r = [self._modify_if(x, add_d, add_str) for x in r]
        return r

    def _modify_if(self, x, add_d, add_str):
        if isinstance(x, dict):
            x.update(add_d)
        else:
            x = x + add_str
        return x

    def __str__(self):
        return "dynamic(%s)" % ",".join(self.modules.keys())
