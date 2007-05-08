#!/usr/bin/env python

# Filename: sge.py 
# Author: Shreyas Cholia, NERSC-LBL, schola@lbl.gov
# Description: SGE probe for gratia
#
# Usage: sge.py [options]
# options:
#  -h, --help            show this help message and exit
#  -aACCOUNTING, --accounting=ACCOUNTING
#                        SGE accounting file. Default:
#                        $SGE_ROOT/default/common/accounting
#  -mGRIDMAP, --gridmap=GRIDMAP
#                        grid-mapfile. Default: /etc/grid-security/grid-mapfile
#  -d, --debug           print debug output
#  -c, --checkpoint      Only reports records past checkpoint. Default is to
#                        report all records.






import Gratia
import os, copy, pwd, time, sys

if not Gratia.pythonVersionRequire(2,3):
    Gratia.Error("SGE Probe requires python version >= 2.3 (current version " + sys.version + ")")
    sys.exit(1)

# This module requires python v2.3
from optparse import OptionParser

info_level = 0
verbose_level = 0
debug_level = 0

class SGE:
    sgeRecord = {}
    __sgeFields__ = [ "qname",
                      "hostname",
                      "group",
                      "owner",
                      "job_name",
                      "job_number",
                      "account",
                      "priority",
                      "submission_time",
                      "start_time",
                      "end_time",
                      "failed",
                      "exit_status",
                      "ru_wallclock",
                      "ru_utime",
                      "ru_stime",
                      "ru_maxrss",
                      "ru_ixrss",
                      "ru_ismrss",
                      "ru_idrss",
                      "ru_isrss",
                      "ru_minflt",
                      "ru_majflt",
                      "ru_nswap",
                      "ru_inblock",
                      "ru_oublock",
                      "ru_msgsnd",
                      "ru_msgrcv",
                      "ru_nsignals",
                      "ru_nvcsw",
                      "ru_nivcsw",
                      "project",
                      "department",
                      "granted_pe",
                      "slots",
                      "task_number",
                      "cpu",
                      "mem",
                      "io",
                      "category",
                      "iow",
                      "pe_taskid",
                      "maxvmem" ]
    

    def reverseGridMap(self):
        user = self.sgeRecord['owner']
        gridmapfile=open(gridmapFile, "r")

        # read the gridmapfile
        for entry in gridmapfile:
            # strip leading and trailing whitespace
            entry=entry.strip()

            # split on whitespace, for local username
            pieces=entry.split()
            localuser=pieces[len(pieces)-1]

            # rest of the entry (before localuser) is dn
            dn=entry[:entry.rfind(localuser)]
	    dn=dn.strip().strip("\"")
            if localuser==user:
                return dn
        # if not found return empty string
        return ""
        
    def __init__(self, valueList):
        self.sgeRecord = dict(zip(self.__sgeFields__, valueList))

                
    
    def createUsageRecord(self):
   	r=Gratia.UsageRecord("Batch")
        # do a straight mapping where applicable
        dn=self.reverseGridMap()

        # Values map to the Usage Record format recommendation
        # http://www.psc.edu/~lfm/PSC/Grid/UR-WG/UR-Spec-gfd.58-ggf18.pdf


        # 3.1 RecordIdentity is set by Gratia.py on record creation 
        # RecordIdentity is a required string which must be unique
        # RecordIdentity is a required string which must be unique

        # 3.2 GlobalJobId - optional, string
        # format: SGE:hostname:job_number.index
        # eg. SGE:pc1805.nersc.gov:121443.0
        globalJobId="SGE:" + self.sgeRecord['hostname'] + ":" + self.sgeRecord['job_number'] + "." + self.sgeRecord['task_number']
        r.GlobalJobId(globalJobId)

        # 3.3 LocalJobId - optional, string
        # use SGE job_number field
        r.LocalJobId(self.sgeRecord['job_number'])

        # 3.4  ProcessId - optional, integer
        # TBD

        # 3.5 LocalUserId - optional, string
        # local username 
        r.LocalUserId(self.sgeRecord['owner'])

        # 3.6 GlobalUsername -
        #
        # Get the GlobalUserName from pwent
        #
        # get UserKeyInfo from reverse gridmap lookup to get the 
        # distinguished name from the certificate
        try: 
            pwent=pwd.getpwnam(self.sgeRecord['owner'])
            # TBD: If we need to further qualify this use:
            # globalUserName=pwent.pw_gecos + " (" + pwent.pw_name + ":" + `pwent.pw_uid` + ")"
            globalUserName=pwent.pw_gecos
        except KeyError:
            globalUserName=self.sgeRecord['owner']
        r.GlobalUsername(globalUserName) 

        # dn from reverse gridmap lookup
        if dn != "":
            r.UserKeyInfo(dn)

        # 3.7 JobName  - optional, string
        # Use SGE job_name field
        r.JobName(self.sgeRecord['job_name'])
        
        # 3.8 Charge - optional, integer, site dependent
        # TBD

        # 3.9 Status - optional, integer, exit status
        # Use SGE exit_status
        # TBD - May want to do additional error code handling along with "failed"
        r.Status(self.sgeRecord['exit_status'])

        # 3.10 WallDuration -  "Wall clock time that elpased while the job was running."
        # Use SGE ru_wallclock field
        # Use float or int so that Gratia can format it appropriately
        r.WallDuration(float(self.sgeRecord['ru_wallclock']),"was entered in seconds")

        # 3.11 CpuDuration - "CPU time used, summed over all processes in the job
        # SGE ru_utime is the user CpuDuration
        # SGE ru_stime is the sys CpuDuration
        # Use float or int so that Gratia can format it appropriately
        r.CpuDuration(float(self.sgeRecord['ru_utime']),"user","was entered in seconds")
        r.CpuDuration(float(self.sgeRecord['ru_stime']),"sys","was entered in seconds")

        # 3.12  EndTime - "The time at which the job completed"
        # SGE end_time field
        # Use float or int so that Gratia can format it appropriately
        endTime=float(self.sgeRecord['end_time'])
        r.EndTime(endTime,"Was entered in seconds")

        # 3.13 StartTime - The time at which the job started"
        # SGE start_time field
        # Use float or int so that Gratia can format it appropriately
        startTime=float(self.sgeRecord['start_time'])
        r.StartTime(startTime,"Was entered in seconds")

        # 3.14 MachineName - can be host name or the sites name for a cluster
        # SGE hostname field
        # TBD - May want to use a generic cluster name
        # r.MachineName(self.sgeRecord['hostname'])

        # 3.15 Host - hostname on which job was run
        r.Host(self.sgeRecord['hostname'])

        # 3.16 SubmitHost
        # TBD - May want to read contents of $SGE_ROOT/default/common/act_qmaster
        # Optionally - we may want to use Globus GK hostname instead
        # r.SubmitHost(self.sgeRecord['hostname'])

        # 3.17 Queue - string, name of the queue from which job executed
        # SGE qname field
        r.Queue(self.sgeRecord['qname'])

        # 3.18 ProjectName - optional, effective GID (string)
        # SGE project field
        r.ProjectName(self.sgeRecord['project'])


        # 4 Differentiated UsageRecord Properties
        
        # 4.1 Network
        # NA

        # 4.2 Disk
        # NA

        # 4.3 Memory - optional, integer, mem use by all concurrent processe
        # SGE maxvmem field
        r.Memory(float(self.sgeRecord['maxvmem']), "B", description = "maxvmem")

        # 4.4 Swap
        # TBD - we could use ru_nswap - but need to verify if SGE actually sets this
        # What about ru_minflt and ru_majflt

        # 4.5 NodeCount

        # 4.6 Processors

        # 4.7 TimeDuration
        
        # 4.8 TimeInstant - a discrete time that is relevant to the reported usage time.
        # Type can be 'submit','connect', or 'other'
        # SGE submission_time field
        r.TimeInstant(float(self.sgeRecord['submission_time']),"submit", "was entered in seconds")

        # 4.9 Service Level - identifies the quality of service associated with
        # the resource consumption.For example, service level may represent a
        # priority associated with the usage.
        # SGE field - priority

        r.ServiceLevel(self.sgeRecord['priority'], type="string", description="SGE Priority")
        
        # 4.10 Extension
        # TBD lookup grid VO related information and add  it to record

	return r	
	

    def printRecord(self):
        Gratia.DebugPrint(debug_level, "=================================")
        for key in self.__sgeFields__:
            Gratia.DebugPrint(debug_level, key +  " : " + self.sgeRecord[key])
        Gratia.DebugPrint(debug_level, "=================================")
                
            

if __name__ == '__main__':


    sgeRoot = os.getenv("SGE_ROOT", "/common/sge/6.0u4")

    
    gridmapFile = os.getenv("GRIDMAP", "/etc/grid-security/grid-mapfile")


    # parse options

    optParser = OptionParser()

    optParser.add_option("-a", "--accounting",
                         action="store", dest="accounting", type="string",
                         help="SGE accounting file. Default: $SGE_ROOT/default/common/accounting" )
    optParser.add_option("-m", "--gridmap",
                         action="store", dest="gridmap", type="string",
                         default=gridmapFile,
                         help="grid-mapfile. Default: /etc/grid-security/grid-mapfile" )
    optParser.add_option("-d", "--debug",
                         action="store_true", dest="debug",
                         default=False,
                         help="print debug output")
    optParser.add_option("-c", "--checkpoint",
                         action="store_true", dest="checkpoint",
                         default=False,
                         help="Only reports records past checkpoint. Default is to report all records.")    

    
    (opts, args)=optParser.parse_args()

    debug = opts.debug
    gridmapFile = opts.gridmap


    # Initialize Gratia
    Gratia.Initialize()

    # Set the default accounting file per the ProbeConfig file if attribute exists
    defaultAccountingFile = Gratia.Config.getConfigAttribute("SGEAccountingFile")
    if not defaultAccountingFile or not os.path.exists(defaultAccountingFile):
        defaultAccountingFile = sgeRoot+"/default/common/accounting"

    # get the accounting file name

    if opts.accounting:
        accFileName = opts.accounting
    else:
        accFileName = defaultAccountingFile

    

    checkpointFile=os.path.join(Gratia.Config.get_WorkingFolder(), "checkpoint")
    
    if debug:
        info_level = 0
        verbose_level = 0
        debug_level = 0
    else:
        info_level = 1
        verbose_level = 2
        debug_level = 3
    
    Gratia.DebugPrint(info_level, "Using " + checkpointFile)
   

    if opts.checkpoint:	
      # TBD - Do some error checking if file io fails
      if os.path.isfile(checkpointFile):
          CPFILE=open(checkpointFile, "r")
          checkpoint=int(CPFILE.readline())
          CPFILE.close()
      else:
          checkpoint=0
             

    Gratia.DebugPrint(0, "Using Accounting file: " + accFileName)
    Gratia.DebugPrint(0, "Using grid-mapfile: " + gridmapFile)



    linecount=0
    file = open(accFileName, "r")
    for line in file:
        # keep going until we hit the checkpoint
        linecount = linecount + 1
        # TBD Still need to handle file rotation
        if opts.checkpoint:
          if linecount <= checkpoint:
              continue
        # ignore comments
        if line[0] == '#':
            continue

        # break up line into fields
        sgeList = line.rstrip("\r\n").split(":")
        Gratia.DebugPrint(debug_level, sgeList)

        # create sgeRecord
        rec = SGE(sgeList)
        rec.printRecord()

        # convert sgeRecord into Gratia UsageRecord
	gratiaRec = rec.createUsageRecord()

        if debug:
            xmlRec = copy.deepcopy(gratiaRec)
	    xmlRec.XmlCreate()
            Gratia.DebugPrint(debug_level, string.join(" ", xmlRec.XmlData))

        # send UsageRecord
        Gratia.Send(gratiaRec)

        if opts.checkpoint:      
          # Write our checkpoint to a file 
  	  checkpoint = linecount
    	  # Do some error checking if file io fails
    	  CPFILE=open(checkpointFile, "w")
    	  CPFILE.write(str(checkpoint) + "\n")
    	  CPFILE.close()

    # Clean things up
    # Do we need to define a clean exit function?
