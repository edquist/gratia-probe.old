#!/usr/bin/env python

import Gratia, sys

if __name__ == '__main__':
        Gratia.Initialize()
	if hasattr(sys,'argv') and sys.argv[1]:
		print Gratia.SendXMLFiles(sys.argv[1], True, "Batch")
#		print Gratia.SendXMLFiles(sys.argv[1], False, "Batch")
	else:
		print "No records directory specified"
