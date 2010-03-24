
step=3600

class DictRecordAggregator:
    def __init__(self,aggFields,sumFields):
       self.aggFields = aggFields
       self.sumFields = sumFields

    def equal(self,item1,item2):
      try:
        for aggField in self.aggFields:
           if ( item1[aggField] != item2[aggField] ):
              return 0
        return 1
      except KeyError,ex:
        pass

      return 0

    def add(self,item1,item2):
        for sumField in self.sumFields:
            item1[sumField] = item1[sumField] + item2[sumField]

class Bin:

    def __init__(self,tm,aggregator):
        self.tracks = []
        self.aggregator = aggregator
        self.tm = tm;

    def add(self,item):
        item["tm"] = self.tm
        for t in self.tracks:
           if ( self.aggregator.equal(t,item) ): # can be optimized to use hash keys for specific field names, etc. not critical here
                t = self.aggregator.add(t,item)
                return
        self.tracks.append(item)

    def list(self):
        return self.tracks

class TimeBinRange:

    def __init__(self,agg):
        self.agg = agg
        self.bins = {}

    def add(self,tm,item):
       
       allignedTm = int(tm/step)*step
       if ( self.bins.has_key(allignedTm) ):
           self.bins[allignedTm].add(item)
       else:
           b = Bin(allignedTm,self.agg);
           b.add(item);
           self.bins[allignedTm] = b

    def list(self):
       result = []
       tms =  self.bins.keys()
       tms.sort()
       for tm in tms:
          result = result + self.bins[tm].list()

       return result

def test():

    r1 = { 'status': 1 , 'source' : 'a', 'jobs' : 1 , 'transferred' : 1 }
    r2 = { 'status': 1 , 'source' : 'a', 'jobs' : 1 , 'transferred' : 2 }

    r3 = { 'status': 0 ,  'source' : 'a', 'jobs' : 1 , 'transferred' : 0 }
    r4 = { 'status': 0 ,  'source' : 'a', 'jobs' : 1 , 'transferred' : 0 }

    r5 = { 'status': 0 ,  'source' : 'a', 'jobs' : 1 , 'transferred' : 0 }
    r6 = { 'status': 0 ,  'source' : 'b', 'jobs' : 1 , 'transferred' : 0 }

    tr = TimeBinRange(DictRecordAggregator(['status','source'],['jobs','transferred']))

    tr.add(0,r1)
    tr.add(0,r2)
    tr.add(0,r3)
    tr.add(0,r4)
    tr.add(10000,r5)
    tr.add(10000,r6)


    for l in tr.list():
       print l

