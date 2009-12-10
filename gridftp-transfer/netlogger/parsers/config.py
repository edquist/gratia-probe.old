"""
New and improved parser configuration module, using ConfigObj
to get nested sections and the 'dynamic' parser module to simplify
the case with line-by-line parser matching.
"""
__author__ = 'Dan Gunter <dkgunter@lbl.gov>'
__rcsid__ = '$id: config.py 678 2008-04-10 17:31:54Z dang $'

import glob
import imp
import logging
from logging import INFO, DEBUG
import os
import re
import sys
from warnings import warn
#
from netlogger import nllog
from netlogger.parsers.modules import dynamic
from netlogger import util
from netlogger.configobj import ConfigObj, Section
from netlogger.util import ConfigError

# Logging
log = nllog.NullLogger()
def activateLogging(name=__name__):
    global log
    log = nllog.getLogger("netlogger.parsers.config")

def _strOrList(item):
    if isinstance(item, str):
        return [item]
    return item

def _testopen(filename, mode='r'):
    if log.isEnabledFor(DEBUG):
        log.debug("testopen.start", file=filename)
    f = None
    try:
        f = file(filename, mode)
    except IOError, E:
        if os.path.isfile(filename):
            log.exception("testopen.end", E, file=filename)
    else:
        if log.isEnabledFor(DEBUG):
            log.debug("testopen.end", status=0, file=filename)
    return f

class Configuration(util.IncConfigObj):
    # section names
    PARAM = 'parameters'
    MATCH = 'match'
    GLOBAL = 'global'
    LOGGING = 'logging'
    # variables
    ROOT = 'files_root'
    ROOT_DEFAULT = '.'
    FILES = 'files'
    OFILE = 'output_file'
    PATTERN = 'pattern'
    STATE_FILE = 'state_file'
    STATE_FILE_DEFAULT = '/tmp/netlogger_parser_state'
    THROTTLE = 'throttle'
    UFILE = 'ufile'
    PRE_PATH = 'pre_path'
    POST_PATH = 'post_path'
    USE_SYS_PATH = 'use_system_path'
    MODULES_ROOT = 'modules_root'
    MODULES_ROOT_DEFAULT = 'netlogger.parsers.modules'
    ROTATE = "rotate"
    ROTATE_DEFAULT = '0'
    EOF = 'eof_event'
    FOREVER = 'tail'
    STDIN_PATH = '@STDIN@' # use as a filename to indicate standard input
    PAT_FIELD_PARAM = 'add_fields'
    PAT_FIELD_PFX_PARAM = 'field_prefix'

    def __init__(self, path_or_lines):
        activateLogging()
        try:
            util.IncConfigObj.__init__(self, path_or_lines, file_error=True, 
                                       interpolation='Template')
        except SyntaxError, E:
            raise ConfigError("Illegal configuration syntax: %s" % E)
        except IOError, E:
            raise ConfigError("Error reading config file: %s" % E)
        self._cached_classes = { }
        # global options
        _g = self._section(self.GLOBAL, { 
                self.ROOT:self.ROOT_DEFAULT,
                self.OFILE:sys.stdout.name,
                self.ROTATE:self.ROTATE_DEFAULT,
                self.STATE_FILE:self.STATE_FILE_DEFAULT,
                self.EOF:False,
                self.FOREVER:False,
                self.THROTTLE:1.0,
                self.UFILE:'' })
        self.global_root = _g[self.ROOT]
        self.ofile_name = _g[self.OFILE]
        self.rotate = util.timeToSec(_g[self.ROTATE])
        self.state_file = _g[self.STATE_FILE]
        if self.state_file.lower() == 'none' or self.state_file == '':
            self.state_file = None
        self.eof_event = _g.as_bool(self.EOF)
        self.forever = _g.as_bool(self.FOREVER)
        self.throttle = _g.as_float(self.THROTTLE)
        if self.throttle <= 0 or self.throttle > 1:
            raise ConfigError("throttle(%lf) is out of range (0,1]" % 
                             self.throttle)
        self.ufile, ufile_name = None, _g[self.UFILE]
        if ufile_name:
            try:
                self.ufile = file(ufile_name, 'w')
            except IOError, E:
                raise ConfigError("cannot open unparsed-events file: %s" %E)
        self.parsers, self._num_files = { }, 0
        # other sections
        for key, val in self.items():
            if not isinstance(val, Section):
                pass
            elif key not in ('DEFAULT', self.GLOBAL, self.LOGGING):
                self._processSection(val, key)
        # Logging, if present
        nllog.configureLogging(self)
        # sanity check
        if self._num_files == 0:
            warn("No files to parse now, or ever")
        elif not self.parsers:
            warn("No files matched by configuration", RuntimeWarning)

    def close(self):
        for p in self.parsers.values():
            p.close()

    def _section(self, name, defaults):
        section = self.get(name, {})
        for k,v in defaults.items():
            section.setdefault(k, v)
        return section

    def _getDynamicParser(self, section, f):
        # find parameters, if any
        kw = { }
        for key, value in section.items():
            if key == self.PAT_FIELD_PARAM:
                if isinstance(value, str):
                    value = (value,)
                kw['show_header_groups'] = value
            elif key == self.PAT_FIELD_PFX_PARAM:
                kw['header_groups_prefix'] = value 
        # create parser
        dynmod = dynamic.Parser(f, pattern=section[self.PATTERN], **kw)
        # add sub-parsers
        for key, value in section.items():
            if isinstance(value, Section):
                module_name, subsection = key, value
                params = subsection.get(self.PARAM, {})
                m = self._getModule(module_name, f, params)
                named_patterns = subsection.get(self.MATCH, { })
                for k,v in named_patterns.items():
                    named_patterns[k] = re.compile(v)
                dynmod.add(module_name, named_patterns, m)
        return dynmod

        dynmod = dynamic.Parser(f, pattern=section[self.PATTERN])
        for module_name, subsection in section.items():
            if not isinstance(subsection, Section):
                continue
            params = subsection.get(self.PARAM, {})
            m = self._getModule(module_name, f, params)
            named_patterns = subsection.get(self.MATCH, { })
            for k,v in named_patterns.items():
                named_patterns[k] = re.compile(v)
            dynmod.add(module_name, named_patterns, m)
        return dynmod

    def _processSection(self, section, key):
        """Process one dynamic or static section
        """        
        root = section.get(self.ROOT, self.global_root)
        section_files = _strOrList(section.get(self.FILES, [ ]))
        is_dynamic = section.has_key(self.PATTERN)
        if is_dynamic:
            # Loop through per-section files,
            # then through all the possible modules.
            # Combine possible modules into a single 'dynamic' module
            # for each file.
            for path in section_files:
                self._num_files += 1 # for sanity check later
                if path == self.STDIN_PATH:                    
                    if self.parsers.has_key(path): continue
                    m = self._getDynamicParser(section, sys.stdin)
                    self.parsers[self.STDIN_PATH] = m
                else:
                    full_path = os.path.join(root, path)
                    log.info("parsers.dyn.start", glob=full_path)
                    for filename in glob.glob(full_path):
                        if self.parsers.has_key(filename): continue
                        f = _testopen(filename)
                        if f is None: 
                            log.warn("parsers.dyn.end", file=filename,
                                          msg="open failed", status=-1)
                            continue
                        m = self._getDynamicParser(section, f)
                        log.info("parsers.dyn.end", file=filename,
                                      module=m, status=0)
                        self.parsers[filename] = m
        else:
            # Loop through each module,
            # and then through all files matching for that module.
            # Create parsers for each file not already assigned.
            for module_name, subsection in section.items():
                #print '@@ loading module:',module_name
                if not isinstance(subsection, Section):
                    continue
                file_list = _strOrList(subsection.get(self.FILES, 
                                                      section_files))
                if not file_list:
                    # to make sure module works at all,
                    # try loading module even if no files exist for it
                    self._getModule(module_name, util.NullFile(), {})
                    continue

                for path in file_list:
                    self._num_files += 1 # for sanity check later
                    if path == self.STDIN_PATH: 
                        if self.parsers.has_key(path): continue
                        params = subsection.get(self.PARAM, {})
                        m = self._getModule(module_name, sys.stdin, params)
                        self.parsers[path] = m
                    else:
                        full_path = os.path.join(root, path)
                        log.info("parsers.static.start", glob=full_path)
                        for filename in glob.glob(full_path):
                            if self.parsers.has_key(filename): continue
                            f = _testopen(filename)
                            if f is None: 
                                log.warn("parsers.static.end", file=filename,
                                         msg="open failed", status=-1)
                                continue
                            params = subsection.get(self.PARAM, {})
                            m = self._getModule(module_name, f, params)
                            self.parsers[filename] = m
                            log.info("parsers.static.end",
                                     file=filename, module=m, status=0)

    def _getModule(self, name, fileobj, params):
        """Return an initialized module instance, given the
        module name and parameters. Raise a ValueError if the
        module cannot be found.
        """
        # set up paths
        section = self.get(self.GLOBAL, {})
        mroot = section.get(self.MODULES_ROOT, self.MODULES_ROOT_DEFAULT)
        if mroot:
            module_name = mroot + '.' + name
        else:
            module_name = name
        if self._cached_classes.has_key(module_name):
            # used cached module class
            clazz = self._cached_classes[module_name]
        else:
            # find the module class
            path = [ ]
            if section.get(self.PRE_PATH, None):
                path.extend(section[self.PRE_PATH].split(':'))
            if section.get(self.USE_SYS_PATH, 'yes').lower() == 'yes':
                path.extend(sys.path)
            if section.get(self.POST_PATH, None):
                path.extend(section[self.POST_PATH].split(':'))
            path_str = ':'.join(path)
            module_parts = module_name.split('.')
            # find and load in module, piece by piece
            for i in xrange(len(module_parts)):
                if i > 0:
                    path = module.__path__
                try:
                    module_info = imp.find_module(module_parts[i], path)
                except ImportError, E:
                    raise ConfigError("No module %s in path '%s': %s"
                                      % (module_name, path_str, E))
                name = '.'.join(module_parts[:i+1])
                try:
                    module = imp.load_module(name, *module_info)
                except ImportError, E:
                    raise ConfigError("Error importing module %s: %s ::\n%s" % 
                                      (name, E, util.tbString()))
            clazz = vars(module)['Parser']
            # cache class
            self._cached_classes[module_name] = clazz
        # instantiate module's Parser class
        try:
            instance = clazz(fileobj, unparsed_file=self.ufile, **params)
        except (ValueError, KeyError, IndexError), E:
            raise ConfigError("Could not instantiate module " +
                              "'%s' on file '%s': %s\n%s" % (
                    module, fileobj.name, E, util.tbString()))
        return instance

    def getModuleClass(self, name):
        return self._cached_classes.get(name, None)

    def dump(self):
        filenames = self.parsers.keys()[:]
        if not filenames:
            return "<NOTHING TO PARSE>\n"
        filenames.sort()
        n = max(max(map(len, filenames)), 8)
        s = "%-*s  %s\n" % (n, "filename", "parser")
        s += "%-*s  %s\n" % (n, '-' * 8, '-' * 6)
        for filename in filenames:
            parser_module = self.parsers[filename]
            s += "%-*s  %s\n" % (n, filename, parser_module)
        return s
