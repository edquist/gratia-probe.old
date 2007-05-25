#!/usr/bin/env python

import sys
import Gratia
import getopt

def usage():
    print """usage: GetProbeConfigAttribute [-h|--help]
       GetProbeConfigAttribute [-c <probeconfig>|--conf=<probeconfig>] <attribute> ...""" 

def main():
    Gratia.quiet = 1

    customConfig = None;
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:l:", ["help", "conf="])

    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
            sys.exit()
                
        if o in ["-c", "--conf"]:
            customConfig = a

    if customConfig:
        Config = Gratia.ProbeConfiguration(customConfig)
    else:
        Config = Gratia.ProbeConfiguration()
    
    for attribute in args:
        print Config.getConfigAttribute(attribute)


if __name__ == "__main__":
    main()
