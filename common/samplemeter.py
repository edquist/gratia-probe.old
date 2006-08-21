
import Gratia

class Simple:
        "A simple example class"
        i = 12345
        def f(self):
                return 'hello world'

if __name__ == '__main__':
        Gratia.Initialize()
        r = Gratia.UsageRecord()

        r.LocalUserId("cmsuser000")
        r.GlobalUsername("john ainsworth")
        r.UserKeyInfo("CN=john ainsworth, L=MC, OU=Manchester, O=eScience, C=UK")

        r.LocalJobId("PBS.1234.0bad")
        r.LocalJobId("PBS.1234.0")        # overwrite the previous entry

        r.JobName("cmsreco","this is not a real job name")
        r.Charge("1240")
        r.Status("4")
        r.Status(4)

        r.Njobs(3,"Aggregation over 10 days")

        r.Network(3.5,"Gb",30,"total")
        #r.Disk(3.5,"Gb",13891,"max")
        #r.Memory(650000,"KB","min")
        #r.Swap(1.5,"GB","max")
        r.ServiceLevel("BottomFeeder","QOS")

        r.TimeDuration(24,"submit")
        r.TimeInstant("2005-11-02T15:48:39Z","submit")

        r.WallDuration(3600*25+63*60+21.2,"Was entered in seconds")
        r.CpuDuration("PT23H12M1.75S","user","Was entered as text")
        r.CpuDuration("PT12M1.75S","sys","Was entered as text")
        r.NodeCount(3) # default to total
        r.Processors(3,.75,"total")
        r.StartTime(1130946550,"Was entered in seconds")
        r.EndTime("2005-11-03T17:52:55Z","Was entered as text")
        r.MachineName("flxi02.fnal.gov")
        r.SubmitHost("patlx7.fnal.gov")
        r.Host("flxi02.fnal.gov",True)
        r.Queue("CepaQueue")

        r.ProjectName("cms reco")


        r.AdditionalInfo("RemoteWallTime",94365)
        r.Resource("RemoteCpuTime","PT23H")
        #
        # populate r
        print Gratia.Send(r)
