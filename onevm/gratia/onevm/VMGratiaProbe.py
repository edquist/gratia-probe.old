import gratia.common.Gratia as Gratia
import gratia.common.GratiaCore as GratiaCore
import sys
import logging
import VMGratiaProbeConfig
import os
import time
import traceback
from Checkpoint import Checkpoint 
from OneReader import OneReader

class VMGratiaProbe:
    def __init__(self,config,logger):
        self._dataFolder=config.get_DataFolder()
        self._log=logger
        #self._maxAge = should get from Config
        self._maxAge =365
        vmChkptFN = 'chkpt_vm_DoNotDelete'
        if  self._dataFolder != None:
            vmChkptFN = os.path.join(self._dataFolder, vmChkptFN)
        self._lastChkpt = Checkpoint(vmChkptFN, self._maxAge)
        self.resourceType="FermiCloud-OneVM"
        self.project="FERMICLOUD"
    def setVersion(self,version):
	self.version=version
    def getVersion(self,version):
	return self.version
    def setResourceType(self):
	self.resourceType=self.resourceType+self.version[0:self.version.rfind(".")]
    #check when was the last time we have run - if timestamp exist
    #if it exists 
    #send all jobs that are currently running (started and endtime=Now) 
    #send all finished jobs that since then
    def process(self,records):
	self.setResourceType()
        current_time=time.time()
        for key,vmr in records.items():
            print key,vmr.getMachineName()
            if not vmr.isValid():
                   print "The machine didn't really started for some reason"
                   continue
            recs=vmr.getRecords()    
            for i in range(len(recs)):   
                if (recs[i].getEndTime() != None) and (0 < float(recs[i].getEndTime()) < self._lastChkpt.getLastCheckPoint()):
		    print "Skipping VM "+key+"["+repr(i)+"]"
                    continue # we have already reported that VM
                r = Gratia.UsageRecord()
                r.LocalUserId(vmr.getLocalUserId())
                keyInfo=vmr.getUserKeyInfo()
                if vmr.getMachineName():
                    r.MachineName(vmr.getMachineName())
                if  keyInfo:
                    r.UserKeyInfo(vmr.getUserKeyInfo())
                r.LocalJobId(vmr.getLocalJobId())
                r.GlobalJobId(vmr.getLocalJobId()+"#"+repr(time.time()))
                r.JobName(vmr.getJobName())
		status,description=recs[i].getStatus()
                r.Status(status,description)
                r.Njobs(1,"")
                r.Memory(vmr.getMemory(),"KB")
                r.NodeCount(1) # default to total
                r.Processors(vmr.getNumberOfCPU(),0,"total")
                stime=self._lastChkpt.getLastCheckPoint()
		print "check point", time.gmtime(stime)
                if recs[i].isRunning():
		    print " VM "+key+"["+repr(i)+"] is running"
                    #this is actively running VM
                    if float(recs[i].getStartTime()) >stime:
                        stime=float(recs[i].getStartTime()) #VM started after we ran
                else:
		    print " VM "+key+"["+repr(i)+"] is done"
                    if float(recs[i].getStartTime()) >stime:
                        stime=float(recs[i].getStartTime()) #VM started after we ran
                
                r.StartTime(GratiaCore.TimeToString(time.gmtime(stime)))
                etime=current_time
                if float(recs[i].getEndTime())>0:
                    etime=float(recs[i].getEndTime())
                r.EndTime(GratiaCore.TimeToString(time.gmtime(etime)))
                r.WallDuration(etime-stime)
                r.CpuDuration(etime-stime,'user')
                r.CpuDuration(0,'system')
                r.SubmitHost(recs[i].getSubmitHost())
                r.ProjectName(self.project)
                r.ResourceType(self.resourceType)
                print Gratia.Send(r)
        self._lastChkpt.createCheckPoint(current_time)
if __name__ == '__main__':
    logger = logging.getLogger("VMGratiaProbe")
    probe_config="ProbeConfig"
    records={}
    try:
        reader=OneReader(sys.argv[1])
        reader.readFile()
        records=reader.getRecords()
    except:
        etype,value,trace=sys.exc_info()
        print traceback.format_exception_only(etype, value)[0]
        sys.exit(1)
    
    if (len(sys.argv) > 3):
        probe_config=sys.argv[3]
    print probe_config
    #config=VMGratiaProbeConfig.VMGratiaProbeConfig(probe_config)
    Gratia.Initialize(probe_config)
    vmProbe=VMGratiaProbe(Gratia.Config,logger)
    vmProbe.setVersion(sys.argv[2])
    vmProbe.process(records)
    
    
