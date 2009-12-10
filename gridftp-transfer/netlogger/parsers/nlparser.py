from __future__ import with_statement
"""
Main 'Application' class for nl_parser program.
"""
__rcsid__ = "$Id: nlparser.py,v 1.1 2008/11/18 17:20:22 abaranov Exp $"
__author__ = "Dan Gunter (dkgunter (at) lbl.gov)"

import logging
from logging import INFO, DEBUG
import os
import sys
import time
#
from netlogger import nlapi
from netlogger import nllog
from netlogger.nllog import TRACE
from netlogger import util
from netlogger import talktome
from netlogger.parsers import config
from netlogger import pipeline
from netlogger.pipeline import PipelineApplication, ExitNow

def is_stdout(fname):
    return fname == sys.stdout.name

class Application(PipelineApplication):
    """Methods and state for nl_parser application
    """
    BATCH = 100

    def __init__(self, options, activateLoggingFn=None):
        """Initialize application from options.
        Will raise a RuntimeError if something goes awry.
        """
        self.options = options
        self.cfg = None
        self.ofile = None
        self._lastrot = None
        self.setLogger(pipeline.PROG_PARSER)
        self._reactivateLogging = self.noop
        self._rcvr = None
        if options.config and not options.noexec:
            if options.secret_file is None:
                raise KeyError("No shared-secret file given")
            # Read secret and start receiver thread
            port = pipeline.getParserPort()
            self._rcvr = talktome.initReceiver(options.secret_file, port)
            # Copy function to activate logging
            self._reactivateLogging = activateLoggingFn

    def configure(self):
        """Initialize configuration, from either a file or command-line,
        depending on the program invocation options in self.options.
        """
        if self.cfg:
            self.cfg.close()
            self.setLogger(pipeline.PROG_PARSER) # empty logger
        self.log.info("configure.start")
        if self.options.config:
            self._readConfig()
        else:
            self._createConfig()
        self.setLogger(pipeline.PROG_PARSER) # configured logger
        self._reactivateLogging()
        try:
            self._openOutputFile()
        except ValueError, E:
            raise RuntimeError("opening output file: %s" % E)
        if self.cfg.eof_event and self.ofile.tell() > 0:
            self._eraseEofMarker()
        if self._lastrot is None and self.cfg.rotate > 0:
            self._lastrot = time.time()
        elif self._lastrot and self.cfg.rotate == 0:
            self._lastrot = None
        # If the throttle ratio is not in the open interval (0, 1), 
        # then throttle() is a no-op.
        if 0 < self.cfg.throttle < 1:
            self._throttle = util.ThrottleTimer(self.cfg.throttle)
        else:
            self._throttle = util.NullThrottleTimer()
        self.log.info("configure.end", status=0)

    def addEofMarkers(self):
        """Add the EOF marker to all files (that don't already have it),
        except the current one, of course.

        This is intended for use by the nl_parser script, on startup.
        It won't have any effect until configure() has been called to
        initialize the location of the output files.
        """
        if not self.cfg or not self.cfg.ofile_name:
            return
        all_files = util.getAllNumberedFiles(self.cfg.ofile_name)
        if self.ofile is None:
            cur_fname = self._getPossibleOutputFiles()
        else:
            cur_fname = [self.ofile.name]
        for fname in all_files:
            self.log.debug("addEofMarkers.file", file=fname, cur__names=cur_fname)
            if fname in cur_fname:
                continue
            f = file(fname)
            f.seek(0,2)
            offs = self._findEofMarker(f)
            f.close()
            if offs is None:
                with nllog.logged(self.log, "addEofMarker", 
                                  level=INFO, file=fname):
                    f = file(fname, 'a')
                    f.write(self._eofEvent())

    def _getPossibleOutputFiles(self):
        """Construct a list of possible output files
          starting with the output file in the saved state (if any)
        """
        files = [ self.restoreState(ignore_ioerror=True) ]
        # add next rotated file, if this is being done
        if self.cfg.rotate:
            files.append(util.getNextNumberedFile(
                    self.cfg.ofile_name, strip=False, open_file=False))
        else:
            files.append(self.cfg.ofile_name)
        return files

    def _openOutputFile(self):
        """Open an output file.
        """
        # try to open each possible file; 
        # if all else fails, use standard output
        self.ofile = sys.stdout
        self.log.info("openOutputFile.start")
        for fname in filter(None, self._getPossibleOutputFiles()):
            self.log.debug("openOutputFile.file.start", file=fname)
            if is_stdout(fname):
                self.ofile = sys.stdout
            else:
                try:
                    self.ofile = file(fname, 'a')
                except IOError, E:
                    self.log.exc("openOutputFile.file.end", E, file=fname)
            if self.ofile:
                self.log.debug("openOutputFile.file.end", status=0, file=fname)
                break
        # done
        self.log.info("openOutputFile.end", file=self.ofile.name, 
                 is_stdout=is_stdout(self.ofile.name), status=0)

    def run(self):
        """Run application's main loop
        """
        status = 0
        sleep_sec = 0.5
        save_loops, save_i = 5 / sleep_sec, 0
        total = 0
        while 1:
            # Read until EOF
            try:
                n = self._readLoop()
            except ExitNow:
                break
            if n > 0:
                total += n
                self._logTotal(total)
            if not self.cfg.forever:
                self.log.info("run.eof")
                break
            # Occasionally save state
            save_i += 1
            if save_i > save_loops:
                with nllog.logged(self.log, "run.saveState"):
                    self.saveState()
                save_i = 0
            # Spin
            with nllog.logged(self.log, "run.eof-sleep", sec=sleep_sec):
                time.sleep(sleep_sec)
        return status

    def _logTotal(self, nevents):
        self.log.info("parsed.total", events=nevents)

    def rotate(self):
        self.log.info("rotateFile.start", file=self.ofile.name)
        # don't rotate stdout
        if self.ofile == sys.stdout:
            self.log.info("rotateFile.end", status=0, rotated=0,
                     filename="stdout", old__size=-1)
            return
        # don't rotate an empty file
        stat_failed = 0 # set to '1' if os.stat() fails
        try:
            st_size = os.stat_result(os.stat(self.ofile.name)).st_size
        except OSError, E:
            self.log.error("rotateFile.end", file=self.ofile.name,
                           status=-1, rotated=0, msg=str(E))
            return
        if st_size == 0:
            self.log.warn("rotateFile.end", file=self.ofile.name, status=0,
                          rotated=0) 
            return
        # otherwise, rotate the file
        new_ofile = util.getNextNumberedFile(self.ofile.name, strip=True)
        self._setOutputFile(new_ofile)
        # immediately save state (no-op if no state file), so that
        # there isn't a chance of a restoreState() reverting to an old file
        self.saveState()
        self.log.info("rotateFile.end", status=0, rotated=1,
                      file=self.ofile.name, old__size=st_size)

    def reconfigure(self):
        """Re-read and install configuration
        """
        self.flush()
        nllog.clear()
        self._reactivateLogging()
        self.configure()
        self.restoreState()

    def flush(self):
        """Flush and save state.
        """
        if self.cfg:
            # flush all parsers
            for parser in self.cfg.parsers.values():
                for item in parser.flush():
                    self.ofile.write(item)
            # persist their state
            self.saveState()
        # flush output (can't hurt -- much)
        if self.ofile:
            self.ofile.flush()

    def close(self):
        """Flush and save state, closing output file.
        """
        self.flush()
        self._setOutputFile(None)

    def saveState(self):
        """Save all the current file offsets to a file.
        Will raise an IOError if the file is not writable.
        """
        self.log.debug("saveState.start", file= self.cfg.state_file)
        if not self.cfg.state_file:
            self.log.warn("saveState.end", msg="no state file", status=0)
            return
        try:
            f = file(self.cfg.state_file, 'w')
            f.write(self.ofile.name + '\n')
            for path, parser in self.cfg.parsers.items():
                offs, param = parser.getOffset(), parser.getParameters()
                self.log.debug("saveState.write", path=path, 
                               offset=offs, param=param)
                f.write("%s %ld %s\n" % (path, offs, param))
        except IOError,E:
            self.log.exc("saveState", E)
        self.log.debug("saveState.end",  file=self.cfg.state_file, status=0)

    def restoreState(self, ignore_ioerror=False):
        """Restore to the saved offsets in the file.
        Will return if the file is not readable, logging an error unless
        'ignore_ioerror' is True.
        If it succeeds, it returns the filename of the state file.
        """
        if not self.cfg.state_file: 
            return None
        try:
            f = file(self.cfg.state_file)
        except IOError, E:
            if not ignore_ioerror:
                self.log.exc("restoreState.end", E)
            return  None
        ofilename = f.readline().strip()
        for line in f:
            path, offs_str, param_str = line.split(None,2)
            try:
                parser = self.cfg.parsers[path]
            except KeyError:
                continue
            parser.setOffset(int(offs_str))
            parser.setParameters(eval(param_str))
        return ofilename

    def _eraseEofMarker(self):
        """Position so as to overwrite existing end-of-file marker (if any).
        """
        tmp = file(self.ofile.name)
        tmp.seek(self.ofile.tell())
        offs = self._findEofMarker(tmp)
        tmp.close()
        if offs:
            self.ofile.truncate(offs)

    def _findEofMarker(self, f):
        """Find the offset of the first of the sequence of lines
        with the special EOF marker event in the previous 64K of the file.

        Assume that the current position in the file
        is the 'end' of the file to be examined.

        Return the (absolute, from 0) offset in the file of the first
        marker event, or None if there is no marker event.
        """
        # Go back 64K or less
        block = min(f.tell(), 65536)
        if block == 0:
            return None 
        f.seek(-block,2)
        # Read data into a buffer
        buf = f.read(block)
        # Initialize search loop
        end_pos, found_eof = block, False
        marker = 'event=%s' % util.EOF_EVENT 
        # Search loop: until beginning of buffer or
        # an event other than the marker event
        while end_pos > 0:
            pos = buf.rfind('\n', 0, end_pos - 1) + 1
            if marker not in buf[pos:end_pos]:
                break
            end_pos, found_eof = pos, True
        # Calculate return value
        if found_eof:
            offs = f.tell() - block + end_pos
        else:
            offs = None
        return offs

    def _createConfig(self):
        """Initialize configuration from command-line values.
        """
        from netlogger.parsers.config import Configuration as CFG
        lines = [
            '[%s]' % CFG.GLOBAL,
            '%s = yes' % CFG.USE_SYS_PATH,
            '%s = None' % CFG.STATE_FILE,
            '%s = %lf' % (CFG.THROTTLE, self.options.throttle),
            ]
        external = self.options.ext
        if external:
            lines.append("%s = \".\"" % CFG.PRE_PATH)
            lines.append("%s = \"\"" % CFG.MODULES_ROOT)
        if self.options.ufile is not None:
            lines.append('%s = %s' % (CFG.UFILE, self.options.ufile))
        lines.append('[user]')
        # root path
        if len(self.options._args) > 0:
            lines.append('%s = ""' % CFG.ROOT)
        # dynamic/static
        if self.options.mod_hdr:
            # dynamic header
            lines.append('%s = "%s"' % (CFG.PATTERN, self.options.mod_hdr))
        # module subsection
        lines.append('[[%s]]' % self.options.mod_name)
        # input files
        if len(self.options._args) > 0:
            infiles = '%s = %s' % (CFG.FILES, ','.join(self.options._args))
        else:
            infiles = '%s = %s' % (CFG.FILES, CFG.STDIN_PATH)
        if self.options.mod_hdr:
            lines.insert(len(lines) - 1, infiles)
        else:
            lines.append(infiles)
        # parameters
        if len(self.options._params) > 0:
            lines.append('[[[%s]]]' % CFG.PARAM)
            for name, val in self.options._params:
                lines.append('%s = %s' % (name, val))
        self.log.info("configuration", text=';;'.join(lines))
        try:
            self.cfg = config.Configuration(lines) 
        except util.ConfigError, E:
            raise RuntimeError("%s from configuration: %s .." % (E, lines[0]))

    def _readConfig(self):
        """Initialize configuration from file specified in options.
        """
        if self.cfg:
            self.cfg.close()
        try:
            self.cfg = config.Configuration(self.options.config)
        except util.ConfigError, E:
            raise RuntimeError("in file '%s': %s" % (self.options.config, E))

    def _readLoop(self):
        """Read from all parsers, writing results to 'ofile',
        until there's no more to read
        """
        self.log.trace("readloop.start")
        total = 0
        total_rpt = self.options.progress
        # count loops
        loops = 0
        n_event = 1
        while n_event:
            n_event, n_good = 0, 0
            if self.log.isEnabledFor(TRACE):
                self.log.trace("readLoop.parse",
                           files=','.join([p._infile.name 
                                          for p in self.cfg.parsers.values()]))
            for name, parser in self.cfg.parsers.items():        
                # read and write records
                any_event, good_event = self._processRecords(parser)
                n_event, n_good = n_event + any_event, n_good + good_event
                total += good_event
                # progress reporting
                while total_rpt > 0 and total >= total_rpt:
                    self._reportProgress(total)
                    total_rpt += self.options.progress
                # file rotation
                if self._lastrot and \
                        (time.time() - self._lastrot) >= self.cfg.rotate:
                    self.rotate()
                    self._lastrot = time.time()
                # end of per-parser loop
            # pipeline command
            if self._rcvr:
                self.log.trace("check_for_cmd")
                self._pipelineCommand()
            loops += 1
            if loops == 2:
                # start timing on second loop 
                # (first must have had data)
                self._throttle.start()
            elif loops > 2:
                # throttle third and all later loops
                self._throttle.throttle()
            # end of loop
        self.log.trace("readloop.end")
        return total

    def _processRecords(self, parser):
        """Process up to self.BATCH records from the parser.
        Return the total number of records and the number of good ones.
        """
        n, ngood = 0, 0
        try:
            for _ in xrange(self.BATCH):
                try:
                    record = parser.next()
                    n += 1
                except StopIteration:
                    break
                except Exception, E:
                    self.log.warn("parse.error", msg="%s" % E)
                    record = None
                if record is not None:
                    self.ofile.write(record)
                    ngood += 1
                    if self.log.isEnabledFor(DEBUG):
                        self.log.debug("readLoop.record", n=n, msg=record)
        except StopIteration:
            pass        
        if n > 0:
            self.ofile.flush()
        return n, ngood

    def _pipelineCommand(self):
        """Check for  and process commands from pipeline.
        """
        self.log.info("pipecmd.process.start")
        cmd, status, msg = self.getCommand(self._rcvr)
        # process command
        do_exit = False
        if 0 == status:
            if cmd == "save":
                self.flush()
                self.saveState()
                save_state = True
            elif cmd == "rotate":
                self.rotate()
                self._lastrot = time.time()
            elif cmd == "exit":
                self.flush()
                self.saveState()
                do_exit = True
            elif cmd == "reconfig":
                self.reconfigure()
            else:
                msg ="not_implemented"
                status = -1
        level = (logging.INFO, logging.WARN)[status < 0]
        self.log.log(level, "pipecmd.process.end", status=status, cmd=cmd)
        if do_exit:
            raise ExitNow()

    def _reportProgress(self, total):
        sys.stderr.write("%6ld lines\n" % (
                long(total / self.options.progress) * self.options.progress))

    def _setOutputFile(self, new_ofile):
        if self.ofile and self.cfg.eof_event:
            self.ofile.write(self._eofEvent())
        self.ofile.close()
        self.ofile = new_ofile

    def _eofEvent(self):
        return "ts=%s event=%s\n" % (nlapi.formatDate(time.time()), 
                                     util.EOF_EVENT)
