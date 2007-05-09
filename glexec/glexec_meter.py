#
# Gratia plugin for gLExec-GUMS 
#

import os,os.path,sys,time,string,pwd
import socket
import popen2
import gratia_glexec_parser
sys.path.append("../common")
import Gratia

#
# Handle lock
#

def get_lock_name(data_dir):
    return os.path.join(data_dir,'glexec_plugin.lck')

def create_lock(data_dir):
    lock_name=get_lock_name(data_dir)
    if os.path.exists(lock_name):
        verify_lock(data_dir)

    fd = open(lock_name,"w")
    try:
        fd.write("%i\n"%os.getpid());
    finally:
        fd.close()
    return

def verify_lock(data_dir):
    lock_name=get_lock_name(data_dir)
    fd=open(lock_name,"r")
    try:
        lock_str=string.strip(fd.read())
    finally:
        fd.close()

    if os.path.exists(os.path('/proc',lock_str)):
        raise RuntimeError,"Another copy running as PID %s"%lock_str

    os.unlink(lock_name)
    return
    
def remove_lock(data_dir):
    lock_name=get_lock_name(data_dir)
    os.unlink(lock_name)

#
# Process transactions
#
def get_check_fname(data_dir):
    return os.path.join(data_dir,'glexec_plugin.chk')

def load_last_check(data_dir):
    check_fname=get_check_fname(data_dir)
    if os.path.exists(check_fname):
        fd=open(check_fname,"r")
        try:
            last_check_str=string.strip(fd.read())
        finally:
            fd.close()
        return long(last_check_str)
    else:
        return 0 #never done anything

def save_last_check(data_dir,last_check):
    check_fname=get_check_fname(data_dir)
    fd = open(check_fname,"w")
    try:
        fd.write("%il\n"%last_check);
    finally:
        fd.close()
    return

#
# Process data
#

def getCE(vdtsetup,host_proxy):
    cmd="source '%s'; grid-proxy-info -f '%s'"%(vdtsetup,host_proxy)
    cmd_el=popen2.Popen3(cmd,1)
    cmd_el.tochild.close() # no input
    exit_code=cmd_el.wait()
    stderr=cmd_el.childerr.read()
    stdout=cmd_el.fromchild.read()
    cmd_el.childerr.close()
    cmd_el.fromchild.close()
    
    if exit_code!=0:
        raise RuntimeError, "Failed to query host proxy: "+stderr

    return string.split(stdout,"/CN=",2)[1]


# a cached way to convert uid to name
UID_DICT={}
def uid2name(uid):
    global UID_DICT
    if not UID_DICT.has_key(uid):
        try:
            UID_DICT[uid]=pwd.getpwuid(uid)[0]
        except:
            UID_DICT[uid]="uid%i"%uid
    return UID_DICT[uid]

def get_host():
    network_interface=socket.gethostbyname(socket.gethostname())
    local_hostname = socket.gethostbyaddr(network_interface)[0]
    return local_hostname[0:]

def send_one(el,
             host, # uname -n
             cename):
    r=Gratia.UsageRecord()
    r.ProbeName("glexec:%s"%host)
    r.MachineName(cename)
    r.Host(host)
    r.LocalUserId(uid2name(el['jobuid'])) # uid number
    if el.has_key("DN"):
        r.UserKeyInfo(el["DN"])
    if el.has_key("VO"):
        r.VOName(el["VO"])
    r.WallDuration(el['end']-el['start'])
    r.CpuDuration(el['usercpu'],'user')
    r.CpuDuration(el['syscpu'],'sys')
    r.StartTime(el['start'])
    r.EndTime(el['end'])
    print Gratia.Send(r)
    #print host,r

#
# Main
#

def main():
    Gratia.Initialize()
    sitename=Gratia.Config.get_SiteName()
    if sitename=="generic Site":
        raise RuntimeError,"SiteName unconfigured"
    cename=getCE(Gratia.Config._ProbeConfiguration__getConfigAttribute('VDTSetupFile'),Gratia.Config.get_CertificateFile())
    data_dir=Gratia.Config.get_DataFolder()
    logfile=Gratia.Config._ProbeConfiguration__getConfigAttribute('gLExecMonitorLog')
    #logfile="/var/log/glexec/glexec_monitor.log"
    create_lock(data_dir)
    try:
        last_check=load_last_check(data_dir)
        host=get_host()
        glexec_data=gratia_glexec_parser.parse_log(logfile,last_check+1)
        # find out only finished jobs
        ids=[]
        for id in glexec_data.keys():
            el=glexec_data[id]
            if el.has_key('end'):
                ids.append(id)

        # sort by termination time
        ids.sort(lambda e1,e2:cmp(glexec_data[e1]['end'],glexec_data[e2]['end']))

        max_end=last_check
        for id in ids:
            el=glexec_data[id]
            send_one(el,host,cename)
            if el['end']>max_end:
                max_end=el['end']
                save_last_check(data_dir,max_end)
    finally:
        remove_lock(data_dir)

    
if __name__== '__main__':
    main()
