import time
import TimeBinRange
import random
import datetime


def collapse(records,agg):

  tr = TimeBinRange.TimeBinRange(agg)

  for r in records:
     recordTime = int(time.mktime( r['datestamp'].timetuple() ))
     r['njobs'] = 1
     tr.add(recordTime,r)
      
  result = tr.list()
  for r in result:
      makeTransaction(r,agg)

  while 1:
      if ( len(result) > 0  and result[-1]['tm'] > int(time.time()) - 2*TimeBinRange.step):
         del result[-1]
      else:
         break

  return result

def makeTransaction(record,agg):
   
   transaction = str(record['tm']/TimeBinRange.step)
   hashCode = 0
   for aggField in agg.aggFields:
      tupl = (hashCode, hash(record[aggField]))
      hashCode = hash(tupl)

   record['transaction'] = transaction + str(hashCode)
 
   record['datestamp'] = datetime.datetime.fromtimestamp(record['tm'])

def generateResult():

  aggFields = { 'initiator' : [ 'I1' ,'I2','I3' ], 'client' : [  'C2' ,'C1','C3'] , 'protocol' : [ 'P1' ] , 'errorcode' :  [ 0 ] , 'isnew' : [ 0 ] }

  startTime = time.time() - 24*3600
  now = time.time() - 1
  results = []

  while startTime < now:
     r = {}
     r['datestamp'] =  datetime.datetime.fromtimestamp(startTime)
     for aggField in aggFields.keys():
        rN = random.randint(0,10000)
        aggFieldVal = aggFields[aggField][rN%len(aggFields[aggField])]
        r[aggField] = aggFieldVal

     r['njobs'] = 1
     r['transfersize'] = 1
     r['connectiontime'] = 1
     results.append(r)
     rN = random.randint(0,10000)
     startTime = startTime + 3+(rN%300)

  return results

def test():

   preResult = generateResult()
   result = collapse(preResult,TimeBinRange.DictRecordAggregator(['initiator','client', 'protocol','errorcode','isnew' ],['njobs','transfersize','connectiontime']))
   return result

if __name__ == "__main__":
   print "AAAA"
   for r in test():
      print r
