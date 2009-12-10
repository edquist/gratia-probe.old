"""
Library to perform authenticated message exchanges between 
a parent and child processes.

The two classes you would use are Parent and ChildThread.
See documentation on thoses classes for usage details.
"""
import hashlib
import logging
import os
import Queue
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
from netlogger import nllog

# Logging

log = nllog.getLogger("netlogger.talktome")

# Constants

DEFAULT_PORT = 25252
LOADER_PORT = DEFAULT_PORT
PARSER_PORT = DEFAULT_PORT + 1

# Exceptions

class PortNotFree(Exception):
    """Thrown when bind to port fails because
    port is already in use (by another process).
    """
    def __init__(self, hostport, orig_exc):
        msg = "Cannot bind to %s:%d, " % hostport
        msg += "address already in use. "
        msg += "Another process is already running?"
        self.host, self.port = hostport
        Exception.__init__(self, msg)

# Convenience functions

def initReceiver(secret_file, port=DEFAULT_PORT):
    """Return receiver using secret_file for the secret.
    """
    secret = _readSecret(secret_file)
    child = Child(port, secret)
    rcvr = ChildThread(child)
    rcvr.start()
    return rcvr

def initSender(secret_file, port=DEFAULT_PORT):
    """Return sender using secret_file for the secret and
    the UDP port.
    """
    parent = Parent(port)
    _writeSecret(secret_file, parent.getSecret())
    return parent

def _readSecret(filename):
    try:
        f = file(filename)
        secret = f.read(Base.SECRET_LEN)
    except IOError, E:
        raise IOError("Cannot read secret from file '%s': %s" % (
                filename, E))
    return secret


def _writeSecret(filename, secret):
    try:
        f = file(filename, 'w')
        f.write(secret)
    except IOError, E:
        raise IOError("Cannot write secret to file '%s': %s" % (
                filename, E))

# Classes

class Base:
    """Hold some common constants and functions for Parent, Child
    """
    SECRET_LEN = 40
    CMD_LEN = 4
    PACKET_LEN = SECRET_LEN + CMD_LEN

    def __init__(self, udp_port):
        if udp_port < 0:
            self._port = DEFAULT_PORT
        else:
            self._port = udp_port
        self._hasher = hashlib.sha1

class Parent(Base):
    """Parent process that will send messages to child.

    Sample usage:
        parent = Parent(port)
        cpid = os.fork()
        if cpid == 0:
            # child...
        else:
            parent.sendCommand("TEST")
    """
    def __init__(self, udp_port):
        Base.__init__(self, udp_port)
        random.seed()
        secret = hashlib.new('sha1')    
        for i in range(5):
            secret.update('%ld' % random.getrandbits(512))
        self._secret = secret.hexdigest()

    def getSecret(self):
        return self._secret

    def setSecret(self, secret):
        """Hook to set secret directly
        """
        self._secret = secret

    def sendCommand(self, cmd):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet = cmd + self._secret        
        chksum = self._hasher(packet).hexdigest()
        #print "@@ send to port",self._port
        s.sendto(cmd + chksum, ('', self._port))
        
class Child(Base):
    def __init__(self, udp_port, secret, host='127.0.0.1'):
        Base.__init__(self, udp_port)
        self._secret = secret
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((host, self._port))
        except socket.error, E:
            raise PortNotFree((host, self._port), E)

    def nextCommand(self):
        while 1:
            log.debug("cmd.read.start")
            data = self.sock.recv(self.PACKET_LEN)
            cmd = data[:self.CMD_LEN]
            chksum = data[self.CMD_LEN:]
            packet = cmd + self._secret
            my_chksum = self._hasher(packet).hexdigest()
            if chksum == my_chksum:
                break
            log.debug("cmd.read.end", status=-1, msg="bad checksum", cmd=cmd)
        log.debug("cmd.read.end", status=0, cmd=cmd)
        return cmd

class ChildThread(threading.Thread):
    """Run message receiver thread so non-blocking nextCommand() can be
    called from child process.

    Sample usage:
        child = Child(port, parent.getSecret())
        cthread = ChildThread(child)
        cthread.start()
        ...
        cmd = cthread.nextCommand()
        if cmd is not None: 
            # process command
    """
    def __init__(self, child):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self._child = child
        self._commands = Queue.Queue()
        
    def run(self):
        while 1:
            cmd = self._child.nextCommand()
            self._commands.put(cmd)
    
    def nextCommand(self):
        """Return next queued command, or None if there is none.
        """
        try:
            cmd = self._commands.get_nowait()
        except Queue.Empty:
            cmd = None
        return cmd
