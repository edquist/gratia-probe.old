import Collapse
import datetime
import TimeBinRange
import time
import re
import random

class SimInterrupt:
   def  __init__(self):
      pass

# test clean area
# generate 6 hours worth of records
# aggegated records should overlap between seconds
# parse out query time stamp
# return list of rows sorted by time
# route A: record limit is not hit 
# A1 report total transferred
# A2 aggregate and report transfferrred
# assertion : total transferred should be the same
# route B: record limit is hit
# reshufle sorted list randomly
# interrupt probe at random times
# assertion check - total transferred should be the same as in route A

TEST = 0
StartTime = 1272314919 - 24*3600
EndTime = StartTime + 4*3600 + 700

recordsToSend = []
addedTransactions = {}

def isTest():
   return TEST

def getMaxAge():
   global StartTime
   return  (time.time() - StartTime)/(3600*24)

def getEndDateTime():
    global EndTime
    return datetime.datetime.fromtimestamp(EndTime + 3600)

def sendInterrupt(freq):
   if ( TEST ):
     if ( random.randint(0,freq) == 0 ):
        raise SimInterrupt()

def processRow(dbRow,log):
   global recordsToSend
   global addedTransactions
   if ( not addedTransactions.has_key(dbRow['transaction']) ):
      recordsToSend.append(dbRow)
      addedTransactions[dbRow['transaction']] = 1
   else:
      log.info("Duplicate detected, discarding")
   return dbRow['njobs']


def dumpStatistics(log):
   if ( not TEST ):
      return
   log.info("Overall "+str(countBy(recordsToSend,None,None)))
   log.info("initiator "+str(countBy(recordsToSend,"initiator","I1")))
   log.info("errorcode "+str(countBy(recordsToSend,"errorcode",0)))
   log.info("num records sent "+str(len(recordsToSend)))

def countBy(records,fieldName,fieldValue):

   sum = 0

   for r in records:
      if ( fieldName != None and fieldValue != None):
        if (r[fieldName] == fieldValue ):
          sum = sum + r['transfersize']
      else:
          sum = sum + r['transfersize']

   return sum
     

if __name__ == "__main__":

  recordsToSend = generateTableContent() 
  print "Pre aggregation"
  dumpStatistics()

  recordsToSend = Collapse.collapse(recordsToSend,TimeBinRange.DictRecordAggregator(['initiator','client', 'protocol','errorcode','isnew' ],['njobs','transfersize','connectiontime']))
  print "Post Aggregation"
  dumpStatistics()

