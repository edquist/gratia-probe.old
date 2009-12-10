"""
NetLogger interactions with the Python logging module.
"""

__rcsid__ = "$Id: nllog.py,v 1.1 2008/11/18 17:20:21 abaranov Exp $"


import cStringIO
import logging
import time
import traceback
#
import nlapi
from netlogger import configobj
from util import ConfigError

# extra logging levels
TRACE = logging.DEBUG -1
DEBUG2 = TRACE

def getLogger(name=None):
    """Call logging.getLogger(name, **kw) and wrap the
    result with a NLLogger object.

    To avoid a warning like:
          No handlers could be found for logger "netlogger.parsers.nlparser"
    If the name of the logger starts with 'netlogger.' get the 'netlogger'
    logger and, if there are no handlers for it, add a Null one.
    """
    if name is None:
        logger = logging.getLogger()
    else:
        if name.startswith('netlogger.'):
            _ = logging.getLogger('netlogger')
            if len(_.handlers) == 0:
                _.addHandler(NullHandler())
        logger = logging.getLogger(name)
    return NLLogger(logger)

def getScriptLogger(name):
    """Set GUID, if not already set, before wrapping the
    logging.getLogger call as in getLogger(), above.
    The returned object is an NLScriptLogger.
    Unlike getLogger(), the 'name' is required.
    """
    nlapi.setGuid(nlapi.getGuid(True))
    return NLScriptLogger(logging.getLogger(name))

def clear(root=None):
    """Remove all loggers under 'root', which is logging.root if
       not specified.
    """ 
    if root is None: root = logging.root
    # close all handlers in all loggers
    # - this avoids a file descriptor leak
    logger_dict = root.manager.loggerDict
    for key in logger_dict:
        logr = logger_dict[key]
        if not hasattr(logr, 'handlers'): continue
        for hndlr in logr.handlers:
            hndlr.close()
            logr.removeHandler(hndlr)
    # clear loggers
    root.manager.loggerDict = { }

def verbosityToLevel(vb):
    """Convert a count of verbosity, from 0 to 2, to
    a logging level:
     vb   level
     --   -----
    -2    CRITICAL
    -1    ERROR
     0    WARN
     1    INFO
     2    DEBUG
    """
    vb = min(vb, 2)
    return logging.WARN - (10 * vb)



class NLLogger:
    """Wrap a logging.logger instance in order
    to provide some convenience functions for writing
    NetLogger-formatted messages.

    For the resulting log object, L
      OLD: L.info("something happened, foo is %s", "123")
      NEW: L.info("something.happened", foo=123)

    In other words, the first string is the event name
    and the rest of the parameters are name=value pairs.
    A timestamp is automatically added to the message, and
    the name of the logger is prefixed to the event name.
    """
    def __init__(self, log):
        if not hasattr(log, '_nllog'):
            # the first time
            log._nllog = nlapi.Log(newline=False)
        self._log = log

    def addHandler(self, hndlr):
        """Add a handler to the underlying logger,
        automatically setting the formatter to be
        NetLogger-style.
        """
        fmt = NLFormatter(fmt="%(message)s")
        hndlr.setFormatter(fmt)
        self._log.addHandler(hndlr)

    def log(self, level, event, exc_info=0, **kwargs):
        ts = time.time()
        if self._log.name:
            event = self._log.name + '.' + event
        if level == TRACE:
            level_name = 'TRACE'
        else:
            level_name = logging.getLevelName(level)
        self._massageKeywords(kwargs)
        msg = self._log._nllog.format(event, ts, level_name, kwargs)
        return self._log.log(level, msg, exc_info=exc_info)

    def _massageKeywords(self, kw):
        """Replace '__' in kwargs key with '.'
        """
        dash_dash = [k for k in kw if '__' in k]
        if not dash_dash: return
        for k in dash_dash:
            k_dot = k.replace('__', '.')
            kw[k_dot] = kw[k]
            del kw[k]
            
    # syntactic sugar methods
    def debug2(self, event, *args, **kwargs):
        if self._log.isEnabledFor(TRACE):
            self.log(TRACE, event, **kwargs)
    trace = debug2
    def debug(self, event, *args, **kwargs):
        if self._log.isEnabledFor(logging.DEBUG):
            self.log( logging.DEBUG, event, **kwargs)
    def info(self, event, *args, **kwargs):
        self.log( logging.INFO, event,  **kwargs)
    def warning(self, event, *args, **kwargs):
        self.log( logging.WARNING, event,  **kwargs)
    warn = warning
    def error(self, event, *args, **kwargs):
        self.log( logging.ERROR, event,  **kwargs)
    def exception(self, event, E, **kwargs):
        self.log(logging.ERROR, event, msg=str(E), status=-1, exc_info=1,
                 **kwargs)
    exc = exception
    def critical(self, event, *args, **kwargs):
        self.log( logging.CRITICAL, event,  **kwargs)
    fatal = critical
    
    def __getattr__(self, key):
        """Simulated inheritance
        """
        try:
            return self.__dict__[key]
        except KeyError:
            return getattr(self._log, key)

class NLScriptLogger(NLLogger):
    """Subclass of NLogger for scripts.
    Adds a default error handler that goes to stderr.
    Provides methods to set the default logging level and
    to redirect the default error handler to a file, which is
    useful if the program is a daemon and has closed stderr.
    """
    def __init__(self, log):
        NLLogger.__init__(self, log)
        self._default_handler = logging.StreamHandler()
        self._default_handler.setLevel(logging.ERROR)
        self.addHandler(self._default_handler)
        self.setLevel(logging.WARN)

    def setDefaultLevel(self, level):
        self._default_handler.setLevel(level)
        self.setLevel(level)

    def redirectDefaultOutput(self, fileobj):
        """Remove default handler and add a new default handler
        that uses 'fileobj' as its output.
        The 'fileobj' may be a file object or just a filename;
        if it's not a string it's assumed to be a file object.
        """
        level = self._default_handler.level
        self.removeHandler(self._default_handler)
        if isinstance(fileobj, str):
            filename = fileobj
        else:
            filename = fileobj.name
        new_handler = logging.FileHandler(filename, 'w')
        new_handler.setLevel(level)
        self.addHandler(new_handler)
        self._default_handler = new_handler

    def getDefaultHandler(self):
        return self._default_handler

class NullLogger:
    """Null object pattern for Logger
    """
    def addHandler(self, hndlr): pass
    def isEnabledFor(self, level): return False
    def log(self, level, event, exc_info=0, **kwargs): pass
    def setLevel(self, level): pass
    def info(self, event, *args, **kwargs): pass
    critical = fatal = error = warn = warning = debug = trace = info
    def exception(self, event, E, **kwargs): pass
    exc = exception

class NullHandler(logging.Handler):
    """Null object pattern for handlers.
    """
    def __init__(self):
        logging.Handler.__init__(self)
    def emit(self, record):
        return

class NLFormatter(logging.Formatter):
    """Override formatException() and format() to produce
    NetLogger (or CEDPS Best-Practices if you prefer) formatted
    log entries.
    """
    def formatException(self, ei):
        """Format and return the specified exception information as a string.
        """
        sio = cStringIO.StringIO()
        traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
        s = sio.getvalue()
        sio.close()
        if s[-1] == "\n":
            s = s[:-1]
        return s.replace("\n", "\\")

    def format(self, record):
        """If there is exception info, replace the newline delimiter
        with 'text=<the traceback>'
        """
        s = logging.Formatter.format(self, record)
        if record.exc_info:
            newline = s.find("\n")
            tb_text = s[newline+1:]
            tb_text_quoted = '"%s"' % tb_text.replace(r'"', r"'")
            s = s[:newline] + ' text=' + tb_text_quoted
        return s

# ----------------------------------------------------------------------------
# The following code is taken from TurboGears (TG), which uses the MIT license.
# It comes from turbogears/config.py. Some minor modifications have been made 
# to remove TG-specific functions and fit our naming conventions.

def _getFormatters(formatters):
    for key, formatter in formatters.items():
        kw = {}
        fmt = formatter.get("format", None)
        if fmt:
            fmt = fmt.replace("*(", "%(")
            kw["fmt"] = fmt
        datefmt = formatter.get("datefmt", None)
        if datefmt:
            kw["datefmt"] = datefmt
        formatter = logging.Formatter(**kw)
        formatters[key] = formatter

def _getHandlers(handlers, formatters):
    for key, handler in handlers.items():
        kw = {}
        try:
            cls = handler.get("class")
            args = handler.get("args", tuple())
            level = handler.get("level", None)
            try:
                cls = eval(cls, logging.__dict__)
            except NameError:
                try:
                    cls = eval(cls, logging.handlers.__dict__)
                except NameError, err:
                    raise ConfigError("Specified class in handler "
                        "%s is not a recognizable logger name" % key)
            try:
                handler_obj = cls(*eval(args, logging.__dict__))
            except IOError, E:
                raise ConfigError("Missing or wrong argument in '%s' to "
                    "%s in handler %s: %s " % (args, cls.__name__, key, E))
            except TypeError, E:
                raise ConfigError("Wrong format for arguments '%s' "
                    "to %s in handler %s: %s" % (args, cls.__name__, key, E))
            except SyntaxError, E:
                hint = ""
                if cls != 'logging.StreamHandler':
                    if args and '"' not in args[0] and "'" not in args[0]:
                        hint = " Unquoted string value?"
                raise ConfigError("Syntax error for arguments '%s' "
                    "to %s in handler %s: %s.%s" % (
                        args, cls.__name__, key, E, hint))
            if level:
                level = eval(level, logging.__dict__)
                handler_obj.setLevel(level)
        except KeyError:
            raise ConfigError("No class specified for logging "
                "handler %s" % key)
        formatter = handler.get("formatter", None)
        if formatter:
            try:
                formatter = formatters[formatter]
            except KeyError:
                raise ConfigError("Handler %s references unknown "
                            "formatter %s" % (key, formatter))
            handler_obj.setFormatter(formatter)
        handlers[key] = handler_obj

def _getLoggers(loggers, handlers):
    """Get logger objects for all the loggers whose names
    are keys in the dictionary 'loggers', using the values
    associated with each name to configure the logger.
    """
    for key, logger in loggers.items():
        qualname = logger.get("qualname", '')
        log = logging.getLogger(qualname)
        level = logger.get("level", None)
        if level:
            level = eval(level, logging.__dict__)
        else:
            level = logging.NOTSET
        log.setLevel(level)
        if logger.has_key("propagate"):
            propagate = logger.as_bool("propagate")
            log.propagate = propagate
        cfghandlers = logger.get("handlers", None)
        if cfghandlers:
            if isinstance(cfghandlers, basestring):
                cfghandlers = [cfghandlers]
            for handler in cfghandlers:
                try:
                    handler = handlers[handler]
                except KeyError:
                    raise ConfigError("Logger %s references unknown "
                                "handler %s" % (key, handler))
                log.addHandler(handler)

def configureLogging(logcfg):
    """Configures the Python logging module from 'logcfg'.
    This may be either a dictionary-like object (i.e. has 'get' method),
    or something accepted by the configobj.ConfigObj constructor.

    If it is one of the latter, then configobj.ConfigObj() will be called
    first to parse it into a dictionary.

    Either way, if the dictionary has a top-level "logging" key, then it
    will be processed and True will be returned or, on error, a ConfigError
    will be raised. If there is no "logging" key, False will be returned.

    The options that are very similar to the ones listed in the 
    Python logging module's documentation.

    One notable format difference is that *() is used in the formatter
    instead of %() because %() is already used for config file
    interpolation.
    """
    if not hasattr(logcfg, 'get'):
        logcfg = configobj.ConfigObj(logcfg)
    logging_section = logcfg.get("logging", None)
    if logging_section is None:
        return False
    
    formatters = logging_section.get("formatters", {})
    _getFormatters(formatters)

    handlers = logging_section.get("handlers", {})
    _getHandlers(handlers, formatters)

    loggers = logging_section.get("loggers", {})
    _getLoggers(loggers, handlers)

    return True

#
# end of TurboGears code
# ----------------------------------------------------------------------------

def __test(name='foo'):
    g = NLogger(logging.getLogger(name))
    g.addHandler(logging.StreamHandler())
    g.setLevel(logging.INFO)
    g.info("hello")
    g.warn("warn.hello")
    g.exception("wonder what happens", status=0)
    
if __name__ == '__main__': __test()
