#!/usr/bin/env python

import Gratia, sys

if __name__ == '__main__':
        rev = Gratia.ExtractCvsRevision("$Revision$");
        tag = "%%%RPMVERSION%%%";
        Gratia.RegisterReporter("pbs-lsf.py", str(rev) + " (tag " + str(tag) + ")")
	if hasattr(sys,'argv') and sys.argv[1]:
                if (len(sys.argv) >= 3 and sys.argv[2]):
                        Gratia.setProbeBatchManager(sys.argv[2])
                if (len(sys.argv) == 4) and sys.argv[2] and sys.argv[3]:
                        Gratia.RegisterService(sys.argv[2], sys.argv[3])
                Gratia.Initialize()
		print Gratia.SendXMLFiles(sys.argv[1], True, "Batch")
	else:
		print "pbs-lsf.py: No records directory specified\n"
