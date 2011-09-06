
# Make sure we can resolve all the probes in our path
import os
import sys

for dir in sys.path:
    gratia_dir = os.path.join(dir, 'gratia')
    if os.path.exists(gratia_dir) and (gratia_dir not in __path__): # Try this directory as a probe
        __path__.append(gratia_dir)

