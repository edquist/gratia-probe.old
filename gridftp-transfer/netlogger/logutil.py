"""
NetLogger interactions with the Python logging module.
"""
__rcsid__ = "$Id: logutil.py,v 1.1 2008/11/18 17:20:21 abaranov Exp $"

import cStringIO
import logging
import time
import traceback
import warnings
#
import nlapi

def getLogger(name, **kw):
    return NLogger(logging.getLogger(name), **kw)

def initLogging(name):
    """Initialize log handle, add a default error handler, and
    set parameters for the warnings module.
    """
    log = getLogger(name, guid=True)
    error_handler = logging.StreamHandler()
    error_handler.setLevel(logging.ERROR)
    log.addHandler(error_handler)
    log.setLevel(logging.WARN)
    warnings.simplefilter("once", RuntimeWarning)
    return log, error_handler
 
class NLogger:
    """Wrap a logging.logger instance in order
    to provide some convenience functions for writing
    NetLogger-formatted messages.
    """
    def __init__(self, log, guid=False):
        if not hasattr(log, '_nllog'):
            # the first time
            log._nllog = nlapi.Log(newline=False, guid=guid)
        self._log = log

    def addHandler(self, hndlr):
        """Add a handler to the underlying logger,
        automatically setting the formatter to be
        NetLogger-style.
        """
        fmt = NFormatter(fmt="%(message)s")
        hndlr.setFormatter(fmt)
        self._log.addHandler(hndlr)

    def log(self, level, event, exc_info=0, **kwargs):
        ts = time.time()
        if self._log.name:
            event = self._log.name + '.' + event
        level_name = logging.getLevelName(level)
        msg = self._log._nllog.format(event, ts, level_name, kwargs)
        return self._log.log(level, msg, exc_info=exc_info)

    def switchHandler(self, old_handler, fileobj):
        """Switch a handler to use fileobj as its output.
        """
        level = error_handler.getLevel()
        self.removeHandler(error_handler)
        new_handler = logging.FileHandler(fileobj, 'w')
        new_handler.setLevel(level)
        self.addHandler(new_handler)

    # syntactic sugar methods
    def debug(self, event, *args, **kwargs):
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

class NFormatter(logging.Formatter):
    """Override formatException() and format()
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

def __test(name='foo'):
    g = NLogger(logging.getLogger(name))
    g.addHandler(logging.StreamHandler())
    g.setLevel(logging.INFO)
    g.info("hello")
    g.warn("warn.hello")
    g.exception("wonder what happens", status=0)
    
if __name__ == '__main__': __test()
