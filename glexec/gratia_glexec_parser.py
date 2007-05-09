#
# This module will parge glexec_monitor log
# files and return gratia related information
#

import os,sys,stat
import time,string

# returns a dictionary
# where keys are (monitor_pid,glexec_uid)
# values are dictionaries
#   'start'            - Start utime
#   'jobuid'           - UID switched to
#   'DN','VO','FQAN'   - Used DN, VO, FQAN (optional)
#   'end'              - End utime (only for terminated jobs)
#   'usercpu','syscpu' - CPU seconds used in User and Kernel mode (only for terminated jobs)
def parse_log(logfile,time_limit):
    out={}

    fd=ReadBackFile(logfile)
    fd.open()
    try:
        while 1:
            try:
                line=fd.readline()
            except EOFError,e:
                break # no more data

            if line=="":
                continue # skip empty lines

            try:
                date,id,message=parse_line(line)
            except:
                continue # skip malformed lines

            if out.has_key(id):
                el=out[id]
            else:
                el={}
                out[id]=el

            try:
                update_element(el,date,message)
            except:
                continue # skip malformed lines

            if el=={}:
                # ignore unrecognized entries
                del out[id]

            if date<time_limit:
                break # reached time limit 

        # remove entries that ended before the time limit
        for id in out.keys():
            el=out[id]
            if el.has_key('end'):
                if el['end']<time_limit:
                    del out[id]

        # nostart will a list of ids without a start section
        nostart=[]
        for id in out.keys():
            if not out[id].has_key("start"):
                nostart.append(id)

        while len(nostart)>0:
            try:
                line=fd.readline()
            except EOFError,e:
                break # no more data
            
            if line=="":
                continue # skip empty lines

            try:
                date,id,message=parse_line(line)
            except:
                continue # skip malformed lines

            if id in nostart:
                try:
                    update_element(out[id],date,message)
                except:
                    continue # skip malformed lines
                if out[id].has_key("start"):
                    nostart.remove(id)

    finally:
        fd.close()

    #remove elements without a start section, if any
    for id in nostart:
        del out[id]


    return out

#####################################################
#
# I N T E R N A L - Do not use
#
#####################################################

# This class mimics a File object
# but reads lines from back to the beginning
# it also automatically moves to filename.0 when
# finished with reading the first file
class ReadBackFile:
    def __init__(self,fname):
        self.fname=fname

    def open(self):
        self.mtime=os.stat(self.fname)[stat.ST_MTIME]
        self.fd=open(self.fname,"r")
        self.fd.seek(0,2) # go to EOF
        self.position=self.fd.tell()
        self.buffer=""

    def close(self):
        self.fd.close()
        del self.buffer

    # return the last line in the file
    def readline(self):
        # check if need to read more data
        if len(self.buffer)<512:
            self.readbuf(4096)
        if self.buffer=="":
            raise EOFError,"No more data"

        # find newline
        newline=self.buffer.rfind("\n")

        # save last line and shorten buffer
        if newline<0:
            # not found, send complete buffer
            out=self.buffer
            self.buffer=""
        else:
            out=self.buffer[(newline+1):]
            self.buffer=self.buffer[:newline]

        # return last line
        return out

    ###########################################
    # internal, read into buffer
    def readbuf(self,size):
        req_size=size
        if self.position>0:
            if size>self.position:
                size=self.position
            self.position=self.position-size
            self.fd.seek(self.position,0) # seek back from current position
            #print "Read at %i"%self.position
            part_buf=self.fd.read(size)
            self.buffer=part_buf+self.buffer

        if len(self.buffer)<size:
            new_name=self.fname+".0"
            #print "About to switch"
            if (os.access(new_name,os.R_OK) and
                (os.stat(new_name)[stat.ST_MTIME]<self.mtime)): # make sure it is an older file
                #print "switched"
                self.close()
                self.fname=new_name
                self.open()
                self.readbuf(req_size) # even if larger,better maintaing same granularity
        return
            
def parse_line(line):
    # looking for [<date>#<monitor_id> <glexec_id>] Msg\n
    if line[0]!='[':
        raise RuntimeError,"Not starting with [ (%s)"%line
    header,message=string.split(line[1:],']',1)
    date,idstr=string.split(header,'#',1)
    mon_str,gl_str=string.split(idstr)

    return (long(date),(int(mon_str),int(gl_str)),message[1:])

def update_element(el,date,msg):
    #print date,msg
    msg7=msg[:7]
    if msg7=="Started":
        el["start"]=date
        if not el.has_key("useruid"):
            # do not overwrite, keep the newer one
            uididx=msg.rfind(" ")+1
            el["jobuid"]=int(msg[uididx:])
    elif msg7=="New uid":
        if not el.has_key("useruid"):
            # do not overwrite, keep the newer one
            uididx=msg.rfind(" ")+1
            el["jobuid"]=int(msg[uididx:])
    elif msg7=="Used DN":
        el["DN"]=msg[10:-1]
    elif msg7=="Used VO":
        el["VO"]=string.split(msg[10:],'"',1)[0]
    elif msg7=="Used FQ":
        el["FQAN"]=msg[12:-1] # if there are many listed, the oldest will prevail
    elif msg7=="Termina":
        el["end"]=date
        el["usercpu"]=1
        sysidx=msg.rfind(" ")+1
        el["syscpu"]=long(msg[sysidx:])
        useridx=msg.rfind(" ",0,sysidx-9)+1
        el["usercpu"]=long(msg[useridx:sysidx-8])
    return
    
