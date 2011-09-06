#!/bin/bash
#
# condor_meter.cron.sh - Shell script used with cron to parse Condor log 
#   files for OSG accounting data collection.
#      By Ken Schumacher <kschu@fnal.gov>  Began 5 April 2006
# $Id$
# Full Path: $HeadURL$

Logger='/usr/bin/logger -s -t condor_meter'

# NOTE: some of the comments in this script indicate work still to be done.
#   The places that still require attention are marked with '###'.  Questions
#   still to be answered also include '???'.

# To direct the e-mail that may be output by this script, enter the crontab
#    entry where MAILTO is the destination address, in a form like:
# MAILTO=root
# 3,13,23,33,43,53 * * * *  $VDT_LOCATION/gratia/condor_meter.cron.sh
#    and using the full path of the VDT location rather than an Env Variable 

# These values were used during testing
#CondorLog_Dir='/export/osg/grid/globus/tmp/gram_job_state'  # on fngp-osg
#CondorLog_Dir='/usr/local/vdt-1.3.6/globus/tmp/gram_job_state'  # on fermigrid1
#CondorLog_Dir='/usr/local/vdt-1.3.9/globus/tmp/gram_job_state'  # on fermigrid1

#Meter_BinDir='/home/kschu/src/osg'
Meter_BinDir=$(dirname $0)
if [ "x$1" != "x" ] ; then
   probeconfig_loc=$1
else
   probeconfig_loc=/etc/gratia/condor/ProbeConfig
fi

# Set the working directory, where we expect to find the following
#    necessary files.
if [ -d ${Meter_BinDir} ]; then
  cd ${Meter_BinDir}
else
  ${Logger} "No such directory ${Meter_BinDir}"
  exit -1
fi

# Need to be sure there is not one of these running already
NCMeter=`ps -ef | grep condor_meter.pl | grep -v grep | wc -l`
eval `grep WorkingFolder $probeconfig_loc`
if [ ${NCMeter} -ne 0 -a -e ${WorkingFolder}/condor_meter.cron.pid ]; then
  # We might have a condor_meter.pl running, let's verify that we 
  # started it.
  
  otherpid=`cat ${WorkingFolder}/condor_meter.cron.pid`
  NCCron=`ps -ef | grep ${otherpid} | grep condor_meter.cron | wc -l`
  if [ ${NCCron} -ne 0 ]; then 
 
     ${Logger} "There is a 'condor_meter.pl' task running already."
     exit 0
  fi
fi

# We need to locate the condor probe script and it must be executable
if [ ! -x condor_meter.pl ]; then
  ${Logger} "The condor_meter.pl file is not in this directory: $(pwd)"
  exit -2
fi
  
# We need to locate these files and they must be readable
for Needed_File in $probeconfig_loc
do
  if [ ! -f ${Needed_File} ]; then
    ${Logger} \
     "The ${Needed_File} file is not in this directory: $(pwd)"
    exit -3
  fi
done
  
pp_dir=$(cd "$Meter_BinDir/../common"; pwd)
if test -n "$PYTHONPATH" ; then
  if echo "$PYTHONPATH" | grep -e ':$' >/dev/null 2>&1; then
    PYTHONPATH="${PYTHONPATH}${pp_dir}:"
  else
    PYTHONPATH="${PYTHONPATH}:${pp_dir}"
  fi
else
  PYTHONPATH="${pp_dir}"
fi
export PYTHONPATH

enabled=`${pp_dir}/GetProbeConfigAttribute -c $probeconfig_loc EnableProbe`
(( status = $? ))
if (( $status != 0 )); then
  echo "ERROR checking probe configuration!" 1>&2
  exit $status
fi
if [[ -n "$enabled" ]] && [[ "$enabled" == "0" ]]; then
  ${pp_dir}/DebugPrint -l -1 "Probe is not enabled: check $probeconfig_loc."
  exit 1
fi

# This is what we expect in a normal Gratia install
DataFolder=`${pp_dir}/GetProbeConfigAttribute -c $probeconfig_loc DataFolder`
if [ ! -d ${DataFolder} ]; then
  ${Logger} "There is no ${DataFolder} directory (defined as DataFolder in ProbeConfig)."
  exit -4
fi

WorkingFolder=`${pp_dir}/GetProbeConfigAttribute -c $probeconfig_loc WorkingFolder`
if [ ! -d ${WorkingFolder} ]; then
  ${Logger} "There is no ${WorkingFolder} directory (defined as WorkingFolder in ProbeConfig)."
  exit -4
fi

echo $$ > ${WorkingFolder}/condor_meter.cron.pid
(( status = $? ))
if (( $status != 0 )); then
   ${Logger} "condor_meter.cron.sh failed to store the pid in  ${WorkingFolder}/condor_meter.cron.pid"
   exit -2
fi 

#echo "Begin processing directory ${DataFolder}"
# The '-d' option tells the meter to delete log files after they are
#    reported to Gratia.
# The '-s' option gives the location of the state file for globus-condor.log
./condor_meter.pl \
  -d \
  -v \
  -x \
  -s "${WorkingFolder}/globus-condor-log-state.dat" \
  -f $probeconfig_loc \
  ${DataFolder} | ${pp_dir}/DebugPrint -l 1 -c $probeconfig_loc
ExitCode=$?
# If the probe ended in error, report this in Syslog and exit
if [ $ExitCode != 0 ]; then
  ${pp_dir}/DebugPrint.py -l -1 "ALERT: $0 exited abnormally with [$ExitCode]"
  exit $ExitCode
fi
    
# Possibly loop to see if there are any new files before exiting. ??? ###
    
# The following debug statement needs to be removed after testing. ###
# ls -ltrAF /tmp/py*

exit 0

