#===============================================================================
# This is a temporary class to read information stored in query_one log
#===============================================================================
import time
import sys
import traceback
from VMRecord import VMRecord

class OneReader:
    def __init__(self,fn):
        self.fn=fn
        self.vms={}
        self.start=time.time()
    def readFile(self):
        fd=None
        #checks if file exists
        try:
            fd=open(self.fn,'r')
        except:
            etype,value,trace=sys.exc_info()
            print traceback.format_exception_only(etype, value)[0]
            return 1
        tmp=eval(fd.read())
        for key,value in tmp.items():
            vm=VMRecord(key,value)
            self.vms[key]=vm
            print key
    def getRecords(self):
        return self.vms       

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage python %s file_name" % (sys.argv[0],)
        sys.exit(1)
    reader=OneReader(sys.argv[1])
    if reader.readFile()!=0:
        sys.exit(1)
    sys.exit(0)
            
            
        
