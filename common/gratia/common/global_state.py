
"""
This is the "dirty secrets" module for gratia.common

This holds all of the global state which I was unable to disentangle from the
rest of the system
"""

import os

bundle_size = 0
CurrentBundle = None
RecordPid = os.getpid()
collector__wantsUrlencodeRecords = 1

estimatedServiceBacklog = 0

def getEstimatedServiceBacklog():
    return estimatedServiceBacklog

def RegisterEstimatedServiceBacklog(count):
    """Register the estimated amount of data that the probe still have to process.
    It should be the number of records/jobs for which Send is still to be called.
    """
    global estimatedServiceBacklog
    estimatedServiceBacklog = count

