from __future__ import with_statement
"""
Shared variables, classes for NetLogger Pipeline components
"""
__rcsid__ = "$Id: pipeline.py,v 1.1 2008/11/18 17:20:21 abaranov Exp $"

# Imports
import logging
import os
import sys
import tempfile
# Local imports
from netlogger import nllog
from netlogger import talktome
from netlogger import util

# Constants

# Note: Keywords must be 4 letters long
KNOWN_COMMANDS = dict(SAVE='save', EXIT='exit', ROTT='rotate', 
                      RECF='reconfig')
KNOWN_COMMANDS[None] =  None

PARSER_PORT = talktome.DEFAULT_PORT
LOADER_PORT = talktome.DEFAULT_PORT + 5

ENV_PARSER_PORT = 'NL_PARSER_PORT'
ENV_LOADER_PORT = 'NL_LOADER_PORT'

PROG_PARSER = 'parser'
PROG_LOADER = 'loader'

# Exceptions

class ExitNow(RuntimeError):
    """Raised when the application wants to exit.
    """
    pass

# Classes

class PipelineApplication:
    """Superclass of nlloader.Application, nlparser.Application
    """
    _logclass = {PROG_PARSER:"netlogger.nlparser",
                 PROG_LOADER:"netlogger.nlloader"}
    def setLogger(self, component):
        s = self._logclass[component]
        self.log = nllog.getLogger(s)

    def exit(self, status, component, pidfile=None):
        """Exit application cleanly
        Assume whether or not it's a daemon is contained in the
        boolean 'self.options.daemon'.
        """
        if pidfile:
            try:
                self.log.info("rm_pid.start", file=pidfile)
                os.unlink(pidfile)
                self.log.info("rm_pid.end", file=pidfile, status=0)
            except OSError, E:
                self.log.error("rm_pid.end", file=pidfile, status=-1,
                              msg=E)
        errfile = getDaemonErr(component)
        if errfile:
            try:
                self.log.info("rm_err.start", file=errfile)
                os.unlink(errfile)
                self.log.info("rm_err.end", file=errfile, status=0)
            except OSError, E:
                self.log.error("rm_err.end", file=errfile, status=-1, msg=E)
        sys.exit(status)

    def getCommand(self, rcvr):
        """Check for  and process commands from pipeline.

        Return a tuple (command-string, status-code, message)
        where status is 0 for success, otherwise failure and
        on failure the 'message' has more info.
        """
        status, msg = 0, "OK"
        raw_cmd = rcvr.nextCommand()
        cmd = KNOWN_COMMANDS.get(raw_cmd, "__none__")
        self.log.debug("getCommand", cmd=cmd, raw_cmd=raw_cmd)
        if cmd is None:
            status = -1
            msg = "bad"
        elif cmd == "__none__":
            msg = "unknown"
            status = -1
        return cmd, status, msg

    def noop(self):
        return

_errfiles = { }
def getDaemonErr(component):
    """Get temporary error file for the component.
    """
    if _errfiles.has_key(component):
        return _errfiles[component]
    fd, filename = tempfile.mkstemp(dir="/tmp", prefix="nl_%s-" % component,
                                    suffix=".err")
    _errfiles[component] = filename
    return filename

def getPidFile(pidfile, parser):
    """Check pid-file option
    """
    if pidfile.startswith('-'):
        parser.error("PIDFILE '%s' starts with a '-'" % pidfile)
    pidfile = os.path.realpath(pidfile)
    try:
        file(pidfile, 'w')
    except IOError, E:
        parser.error("Cannot open PIDFILE '%s': %s" % (pidfile,E))
    return pidfile

def daemonize(log, prog, pidfile):
    """Daemonize and write PID.
    Also switch the log's error handler to the daemon's file.    
    """
    util.daemonize()
    # switch default error handler with daemon's file
    log.redirectDefaultOutput(getDaemonErr(prog))
    # write our PID
    pid = os.getpid()
    log.info("pidfile.write.start", pid=pid, file=pidfile)
    try:
        open(pidfile, 'w').write("%d\n" % pid)
    except IOError, E:
        log.exc("pidfile.write.end", E, pid=pid, file=pidfile)
        raise

def dumpConfigAndExit(app):
    print "Would run with configuration:"
    print app.cfg.dump()
    sys.exit(0)      

def getParserPort():
    """Get the UDP port for the nl_parser to
    receive messages from the nl_pipeline
    """
    return _getPort(0)

def setParserPort(port):
    """Set (into the environment) the UDP port 
    for the nl_parser to receive messages from the nl_pipeline.

    Any child process will get this port with a call
    to getParserPort().
    """
    _setPort(0, port)

def getLoaderPort():
    """Get the UDP port for the nl_loader to
    receive messages from the nl_pipeline
    """
    return _getPort(1)

def setLoaderPort(port):
    """Set (into the environment) the UDP port 
    for the nl_loader to receive messages from the nl_pipeline.

    Any child process will get this port with a call
    to getLoaderPort().
    """
    _setPort(1, port)

def _getPort(i):
    """0 for parser, 1 for loader"""
    evar = (ENV_PARSER_PORT, ENV_LOADER_PORT)[i]
    eport = os.getenv(evar)
    if eport:
        port = int(eport)
    else:
        port = (PARSER_PORT, LOADER_PORT)[i]
    return port

def _setPort(i, port):
    """0 for parser, 1 for loader"""
    evar = (ENV_PARSER_PORT, ENV_LOADER_PORT)[i]
    os.environ[evar] = '%d' % port

