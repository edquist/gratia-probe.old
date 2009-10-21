#!/usr/bin/env python

import os
import re
import sys
import socket
import cPickle
import datetime
import optparse

# Bootstrap our python configuration.  This should allow us to discover the
# configurations in the case where our environment wasn't really configured
# correctly.
sys.path.append('.')
gratia_path = os.path.expandvars('/opt/vdt/gratia/probe/common')
if gratia_path not in sys.path and os.path.exists(gratia_path):
    sys.path.append(gratia_path)
if 'VDT_LOCATION' in os.environ:
    gratia_path = os.path.expandvars('$VDT_LOCATION/gratia/probe/common')
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)
    gratia_path = os.path.expandvars('$VDT_LOCATION/gratia/probe/services')
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)

import Gratia

hostname = socket.gethostname()

class XrootdTransferRecord(object):

    def __init__(self, filename):
        self._filename = filename
        self._bytesRead = 0
        self._openTime = None

    def open(self, timestamp):
        self._openTime = timestamp

    def read(self, bytes, pos, timestamp):
        self._bytesRead += bytes

    def close(self, timestamp):
        record = Gratia.UsageRecord("Storage")
        record.AdditionalInfo("IsNew", False)
        if self._openTime:
            record.StartTime(self._openTime.strftime("%Y-%m-%dT%H:%M:%SZ"))
            duration = timestamp - self._openTime
            duration = 86400*duration.days + duration.seconds
            durationStr = "PT%iS" % duration
            record.WallDuration(durationStr)
            record.Network(self._bytesRead, "b", durationStr, "total",
                "transfer")
        else:
            record.Network(self._bytesRead, "b", "PT3600S", "total", "transfer")
        record.Status(0)
        Gratia.DebugPrint(1, "File read finished; name=%s, bytes=%i" % \
            (self._filename, self._bytesRead))
        return record
        

class XrootdSessionRecord(object):

    def __init__(self, sessionID):
        self.files = {}
        self._localUser = None
        self._remoteHost = None
        self.sessionID = sessionID

    def connect(self, user, timestamp):
        self._localUser = user
        info = self.sessionID.split("@")
        if info == 2:
            self._remoteHost = info[1]
        else:
            self._remoteHost = "UNKNOWN"

    def disconnect(self, timestamp):
        my_files = self.files.keys()
        for file in my_files:
            self.close(file, timestamp)
        self.files = {}

    def open(self, filename, timestamp):
        f = XrootdTransferRecord(filename)
        f.open(timestamp)
        self.files[filename] = f

    def read(self, filename, bytes, pos, timestamp):
        f = self.files.get(filename, None)
        if not f:
            return
        f.read(bytes, pos, timestamp)

    def close(self, filename, timestamp):
        f = self.files.get(filename, None)
        if not f:
            return
        record = f.close(timestamp)
        if not record:
            return
        record.AdditionalInfo("Source", hostname)
        record.AdditionalInfo("Destination", self._remoteHost)
        record.AdditionalInfo("Protocol", "xrootd")
        record.LocalJobId(self.sessionID)
        record.LocalUserId(self._localUser)
        Gratia.DebugPrint(5, Gratia.Send(record))
        del self.files[filename]

class XrootdLogParser(object):

    def __init__(self, filename):
        self.filename = filename
        self.sessions = {}
        self.reset_file()

    # The next two functions are to make this class serializable in python.
    def __getstate__(self):
        Gratia.DebugPrint(1, "Saving state of xrootd log parser")
        odict = self.__dict__.copy()
        del odict['fd']
        return odict

    def __setstate__(self, dict):
        Gratia.DebugPrint(1, "Loading XrootdLogParser state from file.")
        fh = open(dict['filename'], 'r')
        pos = dict['last_parsed_pos']
        fh.seek(pos)
        line = fh.readline()
        self.fd = fh
        self.__dict__.update(dict)
        if dict['last_parsed_line'] != None and line != \
                dict['last_parsed_line']:
            Gratia.DebugPrint(1, "Last parse mismatch (possible log rotate?);" \
                " resetting file pointer to 0")
            self.reset_file()
        else:
            Gratia.DebugPrint(1, "Successfully loaded state; no log-rotate " \
                "detected.")

    def reset_file(self):
        self.fd = open(self.filename, 'r')
        self.last_parsed_line = None
        self.line_number = 0
        self.prev_pos = 0
        self.file_pos = 0
        self.last_parsed_pos = 0

    def save_progress(self):
        # If we couldn't read the last line, it could be because it was
        # incomplete; re-read next time.
        dir = Gratia.Config.get_WorkingFolder()
        filename = os.path.join(dir, "xrootd-transfer.state.new")
        filename_real = os.path.join(dir, "xrootd-transfer.state")
        fd = open(filename, 'w')
        cPickle.dump(self, fd)
        fd.close()
        os.rename(filename, filename_real)

    def load_state(self, xrootd_log=None):
        if not xrootd_log:
            xrootd_log = "/var/log/xrootd/xrootd.log"
        if not os.path.exists(xrootd_log):
            raise Exception("Xrootd log path, %s, does not exist." % xrootd_log)
        dir = Gratia.Config.get_WorkingFolder()
        filename = os.path.join(dir, "xrootd-transfer.state")
        try:
            fd = open(filename, 'r')
            results = cPickle.load(fd)
            return results
        except:
            return XrootdLogParser(xrootd_log)
    load_state = classmethod(load_state)

    # Format: YYMMDD HH:MM:SS PID XrootdXeq: SESSIONID ACTION_INFO
    _session_re = re.compile("(\d\d)(\d\d)(\d\d) (\d\d):(\d\d):(\d\d) \d+ " \
        "XrootdXeq: (.*?) (.*)")
    _session_login_re = re.compile("login as (.*)")
    _session_disc_re = re.compile("disc .*")
    # Format: YYMMDD HH:MM:SS PID SESSIONID ofs_OP INFO fn=FILENAME
    _ofs_re = re.compile("(\d\d)(\d\d)(\d\d) (\d\d):(\d\d):(\d\d) \d+ (.*?) " \
        "ofs_(.*?): (.*?) fn=(.*)")
    _ofs_read_re = re.compile("(\d+)@(\d+)")
    def parse(self):
        self.prev_pos = 0
        for line in self.fd.readlines():
            if line[-1] != '\n': # Last line in file
                break
            self.prev_pos = self.file_pos
            self.file_pos += len(line)
            m = self._ofs_re.match(line)
            if m:
                year, month, day, hour, minute, second, session, op, info, fn \
                    = m.groups()
                timestamp = datetime.datetime(2000 + int(year), int(month),
                    int(day), int(hour), int(minute), int(second))
                s = self.sessions.get(session, None)
                if not s:
                    continue
                if op == 'open':
                    s.open(fn, timestamp)
                    self.tagPosition(line)
                    continue
                elif op == 'close':
                    s.close(fn, timestamp)
                    self.tagPosition(line)
                    continue
                elif op == 'read':
                    m = self._ofs_read_re.match(info)
                    if m:
                        amt, pos = m.groups()
                        s.read(fn, int(amt), int(pos), timestamp)
                    else:
                        continue
                self.tagPosition(line)
                continue
            m = self._session_re.match(line)
            if m:
                year, month, day, hour, minute, second, session, action = \
                    m.groups()
                timestamp = datetime.datetime(2000 + int(year), int(month), \
                    int(day), int(hour), int(minute), int(second))
                m = self._session_login_re.match(action)
                if m:
                    new_session = XrootdSessionRecord(session)
                    user = m.groups()[0]
                    new_session.connect(user, timestamp)
                    self.sessions[session] = new_session
                    self.tagPosition(line)
                    continue
                m = self._session_disc_re.match(action)
                if m:
                    s = self.sessions.get(session, None)
                    if not s:
                        continue
                    s.disconnect(timestamp)
                    del self.sessions[session]
                    self.tagPosition(line)
                    continue
                continue
            # If we reached here, the line was not parsed!
            Gratia.DebugPrint(9, "Ignored line: %s" % line.strip())

    def tagPosition(self, line):
        self.last_parsed_line = line
        self.last_parsed_pos = self.prev_pos


def main():
    parser = optparse.OptionParser()
    parser.add_option("-c", "--config", help="Gratia ProbeConfig file location",
        dest="probeConfig")
    parser.add_option("-l", "--log", help="Xrootd logfile location", dest="log")
    options, args = parser.parse_args()
    if not options.probeConfig or not os.path.exists(options.probeConfig):
        options.probeConfig = "/opt/vdt/gratia/xrootd-transfer/ProbeConfig"
    if not os.path.exists(options.probeConfig):
        print "The ProbeConfig file, %s, does not exist.  Try to specify the " \
            "correct location using the -c option." % options.probeConfig
        sys.exit(1)
    Gratia.Initialize(options.probeConfig)

    parser = XrootdLogParser.load_state(options.log)
    parser.parse()
    parser.save_progress()

if __name__ == '__main__':
    main()

