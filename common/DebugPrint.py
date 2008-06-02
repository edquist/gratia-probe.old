#!/usr/bin/env python

import sys
import Gratia
import getopt
import string

def usage():
    print """usage: DebugPrint.py [-h|--help]
       DebugPrint.py [-l #|--level=#] [-c <probeconfig>|--conf=<probeconfig>] <message>
       cat message.txt | DebugPrint.py [-l #|--level=#] [-c <probeconfig>|--conf=<probeconfig>]"""

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
            level = int(a)

    Gratia.quiet = 1

    if customConfig:
        Gratia.Config = Gratia.ProbeConfiguration(customConfig)
    else:
        Gratia.Config = Gratia.ProbeConfiguration()

    Gratia.Config.loadConfiguration()
    Gratia.quiet = 0

    if len(args) > 0:
        Gratia.DebugPrint(level, string.join(args, " ").rstrip())
    else:
        while 1:
            try:
                line = raw_input();
            except EOFError, e:
                break
            Gratia.DebugPrint(level, line.rstrip())


if __name__ == "__main__":
    main()
