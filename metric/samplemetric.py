
import gratia.common.Gratia as Gratia
import gratia.metric.Metric as Metric

if __name__ == '__main__':
        Gratia.Initialize()
        r = Metric.MetricRecord()

        r.MetricName("LFC-READ")
        r.MetricStatus("OK")
        r.Timestamp("2009-01-02T15:48:39Z") # Or could enter it as seconds since epoch

        print Gratia.Send(r)
