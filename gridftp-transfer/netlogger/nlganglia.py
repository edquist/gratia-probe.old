"""
Ganglia / NetLogger interface module

Dan Gunter, dkgunter@lbl.gov
"""
__rcsid__ = "$Id: nlganglia.py,v 1.1 2008/11/18 17:20:21 abaranov Exp $"

import re
import socket
import time

import nlapi, nllog

log = None
def activateLogging(name=__name__):
    global log
    log = nllog.getLogger(name)

class Gmetad:
    """Class representing a gmetad server, with convenient defaults for
    reading off the local host.
     
    To read locally: g = Gmetad() ; xmlstring = g.read()
    To read from remote: g = Gmetad('remote.host'); xstr = g.read()
    """
    def __init__(self, host='localhost', port=8161, default_timeout=0.5):
        """Initialize with location of server and
        a default value for a timeout (in seconds) to wait
        for some data to be returned when we connect.
        """
        self.host, self.port, self.tmout = host, port, default_timeout

    def read(self, timeout=None):
        """Connect to gmetad and return its output as a string.
        """
        sock = socket.socket()
        sock.connect((self.host,self.port))
        timeout = (timeout, self.tmout)[timeout is None]
        sock.settimeout(timeout)
        data = [ ]
        while 1:
            buf = sock.recv(65536)
            if buf == '':
                break
            data.append(buf)
        return ''.join(data)
        

attrs_re = re.compile('([A-Z]+)="([^"]*)"')

def parse(buf):
    """Parse XML returned by gmetad into BP-formatted log lines
    and for each return a pair (metric-name, log-line). 
    Explicitly returning the metric name makes filtering on metric
    very easy.
    """
    ts = time.time()
    log = nlapi.Log()
    log.setLevel(nlapi.Level.INFO)
    results = [ ]
    log_meta = { }    
    # don't really need an xml parser for this!
    # a simple state-machine works fine
    state='hdr'    
    for line in buf.split('\n'):
        line = line.strip()
        if state == 'hdr':
            if line.startswith('<GANGLIA_XML'):
                state = 'body'
        elif state == 'body':
            if line.startswith('<METRIC'):
                # write out metric
                attrs = { }
                for k,v in attrs_re.findall(line):
                    attrs[k.lower()] = v
                metric = attrs['name']
                event = "ganglia.metric.%s" % metric
                del attrs['name']
                if attrs['units'] == "":
                    attrs['units'] = "none"
                log_str = log.write(event=event, ts=ts, **attrs)
                results.append((metric, log_str))
            elif line.startswith('</'):
                if line.startswith('</GANGLIA_XML'):
                    state='done'
            else:
                # update metadata with <container>.<attr>, value pairs
                attrs = attrs_re.findall(line)
                pfx = line[1:line.find(' ')].lower()
                for k,v in attrs:
                    log_meta["%s.%s" % (pfx, k.lower())] = v
                log.setMeta(None, **log_meta)
    return results
