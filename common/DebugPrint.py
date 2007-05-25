#!/usr/bin/env python

import sys
import Gratia
import getopt
import string

def usage():
    print """usage: DebugPrint [-h|--help]
       DebugPrint [-l #|--level=#] [-c <probeconfig>|--conf=<probeconfig>] <message>""" 

def main():
    level = 0
    customConfig = None;
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:l:", ["help", "conf=" , "level="])

    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
            sys.exit()
                
        if o in ["-c", "--conf"]:
            customConfig = a

        if o in ["-l", "--level"]:
            level = a

    Gratia.quiet = 1

    if customConfig:
        Config = Gratia.ProbeConfiguration(customConfig)
    else:
        Config = Gratia.ProbeConfiguration()

    Gratia.quiet = 0

    Gratia.DebugPrint(level, string.join(args, " "))

if __name__ == "__main__":
    main()
