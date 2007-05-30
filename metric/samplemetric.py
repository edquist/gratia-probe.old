import Gratia
import Metric


if __name__ == '__main__':
        Gratia.Initialize()
        r = Metric.MetricRecord()

        r.MetricName("LFC-READ")
        r.MetricStatus("OK")
        r.Timestamp("2007-11-02T15:48:39Z") # Or could enter it as seconds since epoch

        print Gratia.Send(r)
