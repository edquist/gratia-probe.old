#!/bin/bash
#
# sge_meter.cron.sh - Shell script used with cron to parse sge log 
#   files for OSG accounting data collection.

# $Id: sge_meter.cron.sh,v 1.3 2007-05-25 23:34:56 greenc Exp $
# Full Path: $Source: /var/tmp/move/gratia/probe/sge/sge_meter.cron.sh,v $

Logger='/usr/bin/logger -s -t sge_meter'

# NOTE: some of the comments in this script indicate work still to be done.
#   The places that still require attention are marked with '###'.  Questions
#   still to be answered also include '???'.

# To direct the e-mail that may be output by this script, enter the crontab
#    entry where MAILTO is the destination address, in a form like:
# MAILTO=root
# 3,13,23,33,43,53 * * * *  $VDT_LOCATION/gratia/sge_meter.cron.sh
#    and using the full path of the VDT location rather than an Env Variable 

# These values were used during testing
#sgeLog_Dir='/export/osg/grid/globus/tmp/gram_job_state'  # on fngp-osg
#sgeLog_Dir='/usr/local/vdt-1.3.6/globus/tmp/gram_job_state'  # on fermigrid1
#sgeLog_Dir='/usr/local/vdt-1.3.9/globus/tmp/gram_job_state'  # on fermigrid1

Meter_BinDir=$(dirname $0)

[[ -n "$1" ]] && sge_log_file="$1"

# Setup the proper Grid environment
# I need to know a default location to find this setup.sh script ??? ###
eval `grep VDTSetupFile ${Meter_BinDir}/ProbeConfig`
for Setupsh in ${VDTSetupFile} '/root/setup.sh'
do
  if [[ -f ${Setupsh} && -r ${Setupsh} ]]; then
    # Should the output of this be directed to /dev/null?
    . ${Setupsh} >/dev/null
    break
  fi
done

# Need to be sure there is not one of these running already
#   This may not be the best way to test this for the long term ??? ###
NCMeter=`ps -ef | grep sge_meter.py | grep -v grep | wc -l`
if [ ${NCMeter} -eq 0 ]; then
  
  # Set the working directory, where we expect to find the following
  #    necessary files.
  if [ -d ${Meter_BinDir} ]; then
    cd ${Meter_BinDir}
  else
    ${Logger} "No such directory ${Meter_BinDir}"
    exit -1
  fi
  
  # We need to locate the sge probe script and it must be executable
  if [ ! -x sge_meter.py ]; then
    ${Logger} "The sge_meter.py file is not in this directory: $(pwd)"
    exit -2
  fi
  
  # We need to locate these files and they must be readable
  for Needed_File in ProbeConfig
  do
    if [ ! -f ${Needed_File} ]; then
      ${Logger} \
       "The ${Needed_File} file is not in this directory: $(pwd)"
      exit -3
    fi
  done
  
  # This is what we expect in a normal Gratia install
  pp_dir=$(cd "$Meter_BinDir/../common"; pwd)
  if test -n "$PqYTHONPATH" ; then
    if echo "$PYTHONPATH" | grep -e ':$' >/dev/null 2>&1; then
      PYTHONPATH="${PYTHONPATH}${pp_dir}:"
    else
      PYTHONPATH="${PYTHONPATH}:${pp_dir}"
    fi
  else
    PYTHONPATH="${pp_dir}"
  fi
  export PYTHONPATH

	enabled=`${pp_dir}/GetProbeConfigAttribute.py EnableProbe`
	if [[ -n "$enabled" ]] && [[ "$enabled" == "0" ]]; then
    ${pp_dir}/DebugPrint.py -l 0 "Probe is not enabled: check $Meter_BinDir/ProbeConfig."
		exit 1
	fi

  # Note: location of accounting file should be specified in ProbeConfig
  ./sge_meter.py -c
  ExitCode=$?
  # If the probe ended in error, report this in Syslog and exit
  if [ $ExitCode != 0 ]; then
    ${Logger} "ALERT: $0 exited abnormally with [$ExitCode]"
    exit $ExitCode
  fi
    
  # Possibly loop to see if there are any new files before exiting. ??? ###
    
  # The following debug statement needs to be removed after testing. ###
  # ls -ltrAF /tmp/py*
else
  ${Logger} "There is a 'sge_meter.py' task running already."
fi

exit 0

#==================================================================
# CVS Log
# $Log: not supported by cvs2svn $
# Revision 1.2  2007/03/08 18:24:34  greenc
# Match VDT renaming of sge.py to sge_meter.py.
#
# Revision 1.1  2007/01/30 19:32:13  greenc
# New probe for SGE. Related changes to package and build scripts.
#
