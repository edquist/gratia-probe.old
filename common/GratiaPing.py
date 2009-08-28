#!/bin/env python

#@(#)gratia/probe/common:$HeadURL$:$Id$

import getopt,sys
import Gratia

class UsageError(Exception):
    def __init__(self, msg):
        self.msg = msg

def Usage():
        print" Usage: "+sys.argv[0]+" [-v] [--verbose]"
        print
        print "   -v, --verbose: print the result in human readable form"
        print 
        print " This will attempt to upload a handshake to the server"
        
if __name__ == '__main__':
        verbose = False;
        argv = sys.argv
        try:
                try:
                        opts, args = getopt.getopt(argv[1:], "hv", ["help","verbose"])
                except getopt.error, msg:
                        raise UsageError(msg)
        except UsageError, err:
                print >>sys.stderr, err.msg
                print >>sys.stderr, "for help use --help"
                sys.exit(2)
        for o, a in opts:
                if o in ("-v","--verbose"):
                        verbose = True;
                if o in ("-h","--help"):
                        Usage()
                        sys.exit(0)

        rev = "$Revision$"
        Gratia.RegisterReporter("GratiaPing.py",Gratia.ExtractSvnRevision(rev))

        Gratia.Initialize()

        if (verbose):
                print "Number of successful handshakes: "+str(Gratia.successfulHandshakes)
        sys.exit(0==Gratia.successfulHandshakes)

