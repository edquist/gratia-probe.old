"""
The Grid logging "best practices" (BP) format is a name=value format
that provides flexibly structured logs. It is documented in detail
on the CEDPS project wiki at http://www.cedps.net/index.php/LoggingBestPractices

This module provides a very simple way to produce this format with the
standard Python logging library. It is not as flexible as the full python logging
module in the NetLogger Toolkit, but covers 80% of the needs with a very small
and easily integrated piece of code.

The BPize() function allows any Python 'logging' module handler to easily produce
BP-format logs, complete with an auto-generated globally unique identifier (GUID),
as long as the format of the messages is the following:
   <event-name> <name1>=<value1> <name2>="<value 2 with spaces>" ..etc..
For example:
   map(BPize, log.handlers)
   log.info('did.foo bar=purple baz="red, white and blue"')

See the __test() function for more examples of usage.

"""
import logging
import os
import time

# Environment variable to store the GUID, so all
# the various components use the same one.
# If this isn't desired, set to None or ''.
GUID_ENV = 'PROGRAM_GUID'

def BPize(handler, guid=True, namespace="program."):
    """Make a given handler produce BP-happy logs as long
    as the message itself is in name=value style.
    The handler instance is in 'handler'.
    If 'guid' is True, automatically generate a guid and use it in each message.
    The 'namespace' is placed before the event name.
    """
    import time, logging
    L = time.mktime(time.localtime())
    G = time.mktime(time.gmtime())
    sign = ('','+')[L > G]
    tzone = "%s%.02d:00" % (sign, int((L - G)/3600))
    if guid:
        g = " guid=" + getGuid(create=True, env=GUID_ENV)
    else:
        g = ''
    ts = "ts=%(asctime)s.%(msecs).03d" + tzone
    formatter = logging.Formatter(ts + g + " event=" + namespace + "%(message)s" + 
                                  " level=%(levelname)s")
    formatter.datefmt = "%Y-%m-%dT%H:%M:%S"
    handler.setFormatter(formatter)

# Import the uuid library, or use a one-off alternative
try:
    import uuid
    def _uuid():
        return str(uuid.uuid1())
except ImportError:
    # From: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/213761
    import time, random, md5
    def _uuid():
      t = long( time.time() * 1000 )
      r = long( random.random()*100000000000000000L )
      try:
        a = socket.gethostbyname( socket.gethostname() )
      except:
        # if we can't get a network address, just imagine one
        a = random.random()*100000000000000000L
      data = str(t)+' '+str(r)+' '+str(a)
      data = md5.md5(data).hexdigest()
      return "%s-%s-%s-%s-%s" % (data[0:8], data[8:12], data[12:16],
                                 data[16:20], data[20:32])

def getGuid(create=True, env=None):
    """Return a GUID.
    If 'env', then look there first for a value.
    If 'create' is True (the default), and if none is found 
    in the environment, then create one (put it in the environment if 'env')
    """
    if env:
        guid = os.environ.get(env, None)
    if guid is None:
        if create:
            guid = _uuid()
            if env:
                os.environ[env] = guid
    return guid

def __test():
    import os, sys, time
    # BPize the root logger
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    BPize(logging.getLogger().handlers[0], namespace="my.test.")
    # use the root logger 
    logging.info('start program_args="%s" pid=%d', ' '.join(sys.argv), os.getpid())
    time.sleep(0.5)
    logging.info('end status=0')

if __name__ == '__main__':
    __test()
