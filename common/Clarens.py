#     Clarens client using the Python HTTP transport
#     Supports GSI and SSL Authentication
#
#    Copyright (C) 2004 California Institute of Technology
#    Author: Conrad D. Steenberg <conrad@hep.caltech.edu>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# $Id: Clarens.py,v 1.1 2006-08-21 21:10:03 greenc Exp $

import xmlrpclib, httplib
xmlrpc=xmlrpclib
import cStringIO as StringIO

import os
import sys
import time
import string, urlparse
from base64 import encodestring, decodestring
import random
import gzip
import sha
import Cookie
import re
random.seed()
import getpass
import socket

client_registry={}

try:
  import json
  jsonrpc=json
except:
  jsonrpc=json=None

#-------------------------------------------------------------------------------
def err_msg(mes):
  """Prints an error message on stderr
     Input: a string

     Returns: None
  """
  sys.stderr.write(mes+"\n")
  sys.stderr.flush()

#-----------------------------------------------------------------------
def path_join(args):
  """Utility function to join paths"""
  if type(args)==str:
   args=[args]
  retval=[]
  for arg in args:
    retval+=filter(None,string.split(arg,'/'))
  return reduce(os.path.join,retval,'/')

#-------------------------------------------------------------------------------
def repr_headers(hdict):
  """Returns HTTP headers in dictionary as a list of key/value pairs,
  one pairper line"""
  sio=StringIO.StringIO()
  for key, value in hdict.items():
    sio.write("%s: %s\n"%(key,value))

  return sio.getvalue()

#-------------------------------------------------------------------------------
def parse_response_xmlrpc(f, conn, debug=0):
    """parse_response(file_obj)

    Read response from input file object, and parse it

    The parsed data is returned to the caller
    """
    p,u=xmlrpclib.getparser()
    if debug:
      s=StringIO.StringIO()
    i=0
    try:
      while 1:
        try:
          response = f.read()
        except AssertionError:
          break
        if not response:
            break
        if debug:
          s.write(response)
        p.feed(response)
      if debug:
        err_msg(s.getvalue())
      p.close()
      return u.close()
    except:
      if debug:
        err_msg(s.getvalue())
      raise

#-------------------------------------------------------------------------------
def load_cert(certfile, guest=None, debug=None):
  for fname in [certfile,'/tmp/x509up_u%s'%(os.getuid()),
                '%s/.globus/usercert.pem'%(os.environ['HOME'])]:
    if not fname: continue
    text_file=None
    try:
      text_file=open(fname)
    except:
      pass
    if text_file:
      certfile=fname
      break
  if not text_file:
    if guest: return
    raise ValueError("Could not open certificate file. Tried:\n%s\n%s\n%s"\
      %(certfile,'/tmp/x509up_u%s'%(os.getuid()),
                '%s/.globus/usercert.pem'%(os.environ['HOME'])))
  if debug: err_msg("Using certificate from '%s'\n"%fname)

  text_ucert=text_file.read()
  text_file.close()
  return text_ucert, certfile

#-------------------------------------------------------------------------------
def load_key(keyfile, guest=None, debug=None):
  for fname in [keyfile,'/tmp/x509up_u%s'%(os.getuid()),
                '%s/.globus/userkey.pem'%(os.environ['HOME'])]:
    if not fname: continue
    text_file=None
    try:
      text_file=open(fname)
    except:
      pass
    if text_file:
      keyfile=fname
      break
  if not text_file:
    if guest: return
    raise ValueError("Could not open key file. Tried:\n%s\n%s\n%s"\
      %(keyfile,'/tmp/x509up_u%s'%(os.getuid()),
                '%s/.globus/userkey.pem'%(os.environ['HOME'])))
  if debug: err_msg("Using key from '%s'\n"%fname)

  text_key=text_file.read()
  text_file.close()
  return text_key, keyfile


#-------------------------------------------------------------------------------
def create_session_key():
  """Creates a printable random set of characters

     Input:  no arguments
     Output: a string
  """
  ustring_raw="%s_%f_%f"%(os.getpid(),time.time(),random.random())
  ustring=sha.new(ustring_raw).hexdigest()
  return ustring

#-------------------------------------------------------------------------------
class _caller:
  '''Internal class used to give the user a callable object
    that calls back to the Binding object to make an RPC call.'''

  def __init__(self, binding, name):
    self.__binding, self.__name = binding, name

  def __getattr__(self, name):
    return _caller(self.__binding, "%s.%s" % (self.__name, name))

  def __call__(self, *args):
    return self.__binding.execute(self.__name, args)


#-------------------------------------------------------------------------------
class client:
  def __init__(self, url, certfile=None, keyfile=None,
               callback=getpass.getpass, async=None, do_login=1,
               passwd=None, debug=0, cert_text=None, key_text=None,
               progress_cb=None, rpc="xmlrpc", guest=None):
      """ Constructor

      Mandatory arguments:
       (string) url:  The URL of the remote server

      Optional arguments:
       (string) certfile: name of a file containing an X509 certificate
       (string) keyfile : name of a file containing an RSA private key
       (string) cert_text: X509 certificate in PEM format
       (string) key_text : an RSA private key in base64 format
       (string) passwd: the private key password
       (object) debug : if this objects evaluates to True, turn debugging on
       (object) do_login: if this objects evaluates to True, call system.auth2()
                          newer servers log you in automatically using SSL
                          defaults to True
       (object) guest: if this objects evaluates to True, makes all calls as the
                       guest user, i.e. no certificate/key is used to make the
                       SSL connection
       (string) rpc: RPC protocol to be used, "xmlrpc" (default) or "jsonrpc"

       (function) callback: a function that returns the private key password

       After the client object is constructed, methods on the server can be called
       as if the remote classes are members of the client class. E.g. to call the
       echo.echo method on the server using a client object, myclient, do
       myclient.echo.echo("hello")

       When the objoect is destroyed, the remote method system.logout() is called
       automatically.
      """
      global client_registry
      self.pwcallback=callback
      self.passwd_set(passwd)
      self.debug=debug

      self.login_callback=None
      self.url=url
      self.rpc=rpc
      self.id=0
      self.callback=None
      self.callback_args=None
      self.file_obj=None
      self.server_cert=None
      self.deserialize=1
      self.filename=None

      self.url=url

      ustring=create_session_key()

      # Parse URL to see if we need to load key/cert ourselves
      purl=urlparse.urlparse(url)
      self.server_path=purl[2]

      hostport=string.split(purl[1],":")
      if len(hostport)==1:
        self.host=hostport[0]
        if string.lower(purl[0])=='https':
          self.port=443
        else:
          self.port=80
      elif len(hostport)==2:
        self.host=hostport[0]
        self.port=int(hostport[1])

      if debug:
        err_msg("(debug, host,port,url)=(%s, %s,%s,%s)"%(self.debug, self.host,self.port,self.url))


      # Read certificate file, or use supplied text

      if not guest:
        files=load_cert(certfile, guest=1)
        if files:
          text_ucert, self.certfile=files
          files=load_key(keyfile,guest=1)
          if files:
            text_ukey, self.keyfile=files
            self.conn_passwd='BROWSER'
      if guest or not files:
        guest=1
        self.certfile = self.keyfile = None
        text_ucert = text_ukey = ""

      # Create transport object
      if  string.lower(purl[0])!='https':
        self.conn=httplib.HTTPConnection(self.host, self.port)
      else:
        self.conn=httplib.HTTPSConnection(self.host, self.port, self.keyfile, self.certfile)
      if self.debug:
        err_msg(repr(self.conn))

      self.debug=debug
      self.proto=string.lower(purl[0])

      self.conn_user=ustring
      login_num=0

      self.guest=guest
      if not guest and do_login:
        if not async:
          try:
            self.do_login(text_ucert)
            client_registry[str(id(self))]=debug
          except:
            raise
        else:
          self.perform_callback=self.login_handler
      else:
        self.execute("echo.echo",["hello"])
        client_registry[str(id(self))]=debug

  #-----------------------------------------------------------------------------
  def __getattr__(self, name):
    '''Return a callable object that will invoke the RPC method
     named by the attribute.'''
    if name[:2] == '__' and len(name) > 5 and name[-2:] == '__':
            if self.__dict__.has_key(name):
              return self._dict__[name]
            return self.__class__.__dict__[name]
    return _caller(self, name)

  #-----------------------------------------------------------------------------
  def re_use(self,url,username,passwd):
    """Re-use the client object with a different URL and connection username
    and password
    Experts only!
    """
    self.url=url
    self.conn_user=username
    self.conn_passwd=passwd

  #-----------------------------------------------------------------------------
  def nb_dispatch(self,method,args,timeout=5):
    """Dispatch a HTTP request and return to the caller
    (string) method: The remote method on the server
    (list)   args  : A list of arguments

    Used internally
    """
    if self.rpc=="xmlrpc":
      request_body=xmlrpclib.dumps(tuple(args),method)
      content_type="text/xml"
    elif self.rpc=="jsonrpc":
      self.id=self.id+1
      request_body=json.objToJson({"method":method, \
                                   "params":args, \
                                   "id": self.id })
      content_type="text/json"


    xmlrpc_h={"Content-Type": content_type,
              "User-Agent": "ClarensDpe.py version 1.4",
             }

    if not self.guest:
      xmlrpc_h["AUTHORIZATION"]="Basic %s" % string.replace(
               encodestring("%s:%s" % (self.conn_user, self.conn_passwd)),"\012", "")

    connected=0

    if self.debug:
      err_msg("sending request...")
      err_msg(repr_headers(xmlrpc_h))
      err_msg(request_body)
    self.conn.request("POST",self.server_path,request_body,xmlrpc_h)
    connected=1

  #-----------------------------------------------------------------------------
  def get_result(self):
    """Internal method to get the result object from a connection
    """
    if not self.conn.sock: return
    return self.conn.getresponse()

  #-----------------------------------------------------------------------------
  def execute(self,method,args):
    """Public method to call a method on the remote server synchronously
    (string) method: The remote method on the server
    (list)   args  : A list of arguments

    Returns the result of the method call, or raises an exception
    """
    i=0
    self.nb_dispatch(method,args)
    stime=0.1
    self.result_obj=None
    while not self.result_obj and i<7:
      try:
        self.result_obj=self.get_result()
        if self.debug:
          err_msg("result_obj = %s"%self.result_obj)

        if self.result_obj: break
        time.sleep(1)
      except httplib.CannotSendRequest,v:
        err_msg("Could not connect. Make sure certificate is still valid")
        err_msg("%s: %s"%(repr(v), dir(v)))
        connected=0
        return
      except httplib.ResponseNotReady:
        pass
      except httplib.BadStatusLine:
        self.conn=httplib.HTTPSConnection(self.host, self.port, self.keyfile, self.certfile)
        self.nb_dispatch(method,args)
      i=i+1
    if not self.result_obj:
       raise httplib.CannotSendRequest("Could not connect. Make sure certificate is still valid")

    # Return data in file or as string to user
    if not self.deserialize:
      if not self.filename:
        s=StringIO.StringIO()
      else:
        s=open(filename,"w")
      try:
        while 1:
          data = self.result_obj.read(1048576)
          s.write(data)
          if not data:
              break
      except:
        raise
      if not self.filename:
        return s.getvalue()
      else:
        return s
    # Return parsed response
    if self.rpc=="xmlrpc":
      retval = parse_response_xmlrpc(self.result_obj, self.conn, self.debug)
      return retval[0]
    elif self.rpc=="jsonrpc":
      data=self.result_obj.read()
      if self.debug:
        err_msg(data)
      d=json.jsonToObj(data)
      if d["error"]:
        raise RuntimeError(d["error"]["code"], d["error"]["message"])
      return d["result"]

  #-----------------------------------------------------------------------------
  def do_login(self, passwd):
    """Internal callback function to do logins
    """
    if self.proto=='http':
      err_msg("This client only supports HTTPS (SSL) connections")
    elif self.proto=='https':
      try:
        response=self.execute("system.auth2",[])
      except:
        raise
      if not response: return
      self.https_login_handler(response)

  #-----------------------------------------------------------------------------
  def login_handler(self, values, extra=None):
    """Internal callback function to do logins over https
    """
    if self.proto=='http':
      err_msg("This client only supports HTTPS (SSL) connections")
    elif self.proto=='https':
      return self.https_login_handler(values,extra)

  #-----------------------------------------------------------------------------
  def https_login_handler(self, values, extra=None):
    """Internal callback function to do handle result from the
    system.auth2() method call
    """
    server_cert, user_cert, new_passwd=values
    self.conn_passwd=new_passwd
    client_registry[str(id(self))]=self.debug

  #-----------------------------------------------------------------------------
  def error_handler(self, source, exc):
    """Internal error handler callback
    """
    if hasattr(self,"err_callback"):
      return self.err_callback(self, source, exc, self.err_callback_args)
    else:
      return None

  #-----------------------------------------------------------------------------
  def set_error_callback(self, func, args):
    """Set the error callback function
    """
    if self.client:
      self.client.setOnErr(self.error_handler)
    self.err_callback=func
    self.err_callback_args=args

  #-----------------------------------------------------------------------------
  def set_writefunction(self,cb):
    """
    NOT IMPLEMENTED USE set_file_download instead

    Set the function to be called with data that is returned by the server,
    e.g. the write method of a file object

    Example usage:

    f=open("myfile.dat","w")
    myclient.set_writefunction(f.write)
    myclient.file.read("/index.html",0,-1)
    f.close()

    This will download the remote file /index.html and write the result into
    the file myfile.dat
    """
    self.writefunction=cb
    self.filename=None

  #-----------------------------------------------------------------------------
  def set_file_download(self, filename):
    """
    Sets a file name to download the output of a remote method to

    (string) filename: the filename of the file on the local filesystem to
    store the output in

    Example:
    myclient.set_file_download("myfile.html")
    myclient.file.read("/index.html",0,-1)

    This will download the remote file /index.html and write the result into
    the file myfile.html
    """

    self.deserialize=0
    self.filename=filename
    fname=os.path.split(filename)[1]
    self.writefunction=None
    if not self.filename:
      raise IOError("%s is a directory!"%filename)

  def disable_deserialize(self):
    """Disable serialization of data returned by the server in response to
    a method call

    Invocation of the method via client.execute() or "magic method substitution"
    will directly return the data to the caller.

    Example:
    myclient.disable_deserialize()
    data=myclient.file.read("/index.html",0,-1)

    The object "data" will contain the contents of the remote file /index.html

    Use with care! If an error occurs on the server, the returned data will
    be the raw XML or JSON return value from the server
    """

    self.deserialize=0

  def enable_deserialize(self):
    self.deserialize=1
    self.file_obj = StringIO.StringIO()
    self.writefunction=None
    self.filename=None

  #-----------------------------------------------------------------------------
  def file_progress(self, dltotal, dlnow, ultotal, ulnow):
    """An internal callback function to show a progress bar
    """
    k=1024
    M=k*1024
    G=M*1024

    post='bytes'
    v=dlnow
    vt=dltotal
    if dltotal>=k and dlnow<M:
      v=dlnow/k
      vt=dltotal/k
      post='k'
    elif dlnow>=M and dlnow<G:
      v=dlnow/M
      vt=dltotal/M
      post='M'
    elif dlnow>=G:
      v=dlnow/G
      vt=dltotal/M
      post='G'
    sys.stdout.write("\r %2.1f %s"%(v,post))
    sys.stdout.flush()

  #-----------------------------------------------------------------------------
  def set_progress_callback(self,cb):
    """NOT IMPLEMENTED
    Registers a callback function to be called by client periodically to show
    progress
    """
    self.progress_cb=cb

  #-----------------------------------------------------------------------------
  def passwd(self,v):
    """Internal password callback_
    """
    if self.priv_passwd==None:
      self.priv_passwd=self.pwcallback(v)
    return self.priv_passwd

  #-----------------------------------------------------------------------------
  def passwd_set(self,passwd=None):
    """Sets the password to be used to decrypt the user's public key
    """
    self.priv_passwd=passwd

  #-----------------------------------------------------------------------------
  def get_url(self):
    """Returns the url associated to the client object
    """
    return self.url

  #-----------------------------------------------------------------------------
  def get_session_id(self):
    """Returns a tuple cosisting of the temporary username and password
    negotiated for the current session
    """
    return self.conn_user,self.conn_passwd()

  #-----------------------------------------------------------------------------
  def upload_file(self,filename,remotename, timeout=5):
    """Uploads a file to a remote server

    Arguments:
    (string) filename  : name of the local file to upload
    (string) remotename: the name of the remote file, as it would appear to
    the remote file service
    """
    statinfo=os.stat(filename)
    selector=path_join([self.server_path,remotename])

    connected=0
    count=0
    while not connected and count<4:
      try:
        if self.conn.sock==None:
          self.conn.connect()
        if self.debug:
          err_msg("sending request...")
        # Start sending the request and headers
        self.conn.putrequest('PUT', selector)
        self.conn.putheader("User-Agent", "ClarensDpe.py")
        self.conn.putheader("AUTHORIZATION", "Basic %s" % string.replace(
                   encodestring("%s:%s" % (self.conn_user, self.conn_passwd)),"\012", ""))
        self.conn.putheader('Content-Length', statinfo[6])
        self.conn.endheaders()
        connected=1
      except Exception,v:
        raise
        if self.debug:
          err_msg("state = %s"%self.conn._HTTPConnection__state)
        connected=0
        count=count+1
        continue

      # Now send the file
      bytes_read=0
      fo=open(filename)
      while 1:
        data=fo.read(1048576)
        if len(data):
          try:
            bytes_read=bytes_read+len(data)
            self.conn.sock.send(data)
          except socket.error,v:
            if self.debug:
              err_msg("socket error: %s (%s) args=%s"%(v.args[1],v.args[0]))
              err_msg("attempting to reconnect...")
            self.conn.close()
            self.conn.sock=None
            self.conn.connect()
            connected=0
            count=count+1
            break
        else:
          break
      if connected:
        break

    # Now get the result
    self.result_obj=None
    count=0
    while not self.result_obj and count<7:
      try:
        self.result_obj=self.get_result()
        if self.debug:
          print "result_obj =",self.result_obj
        if self.result_obj: break
        time.sleep(1)
      except httplib.CannotSendRequest,v:
        err_msg(repr(v)+"\n"+str(dir(v)))
        err_msg("Could not connect. Make sure certificate is still valid")
        connected=0
        return
      except httplib.ResponseNotReady:
        pass
      count=count+1

    # Return parsed response
    retval = parse_response_xmlrpc(self.result_obj, self.conn, self.debug)
    return retval[0]

  def upload(self,remotename,filename, timeout=5):
    return self.upload_file(filename, remotename, timeout)

  #-----------------------------------------------------------------------------
  def __del__(self):
    """Destructor
    The client will attempt to log out of the server when the object is destroyed
    """
    if self.debug:
      err_msg("Logging out")

    obj_id=str(id(self))
    if not client_registry.has_key(obj_id): return
    debug=client_registry[obj_id]
    try:
      logout=self.execute("system.logout",[])
      if self.debug:
        err_msg("Logout returned %s\n"%logout)
    except:
      if debug:
        raise
      else:
        pass

    del client_registry[obj_id]

  #-----------------------------------------------------------------------------
  def test(self,reps=1000):
    """Test the response speed of a server, printing the time a certain number of calls
       took to execute

       Input: number of repetitions (optional)

       Output: None
       """
    starttime=time.time()
    for i in xrange(reps):
      self.execute("echo.echo",["Hello"])
    endtime=time.time()

    print "Elapsed time is ",endtime-starttime,"s, ",reps/(endtime-starttime),\
      " calls/s for ",reps," calls"    
      

