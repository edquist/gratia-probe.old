#!/bin/env python

import Gratia, sys

if __name__ == '__main__':
        Gratia.Initialize()
	if hasattr(sys,'argv') and sys.argv[1]:
		print Gratia.SendXMLFiles(sys.argv[1], True)
#		print Gratia.SendXMLFiles(sys.argv[1], False)
	else:
		print "No records directory specified"
