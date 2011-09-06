#!/bin/bash
#
# glexec_meter.cron.sh - Shell script used with cron to parse glexec
#   files for OSG accounting data collection.
#      By Chris Green <greenc@fnal.gov>  Began 5 Sept 2006
# $Id$
# Full Path: $HeadURL$
###################################################################
PGM=$(basename $0)
Logger="/usr/bin/logger -s -t $PGM"

Meter_BinDir=$(dirname $0)
if [ "x$1" != "x" ] ; then
   probeconfig_loc=$1
else
   probeconfig_loc=/etc/gratia/glexec/ProbeConfig
fi

# Set the working directory, where we expect to find the following
#    necessary files.
if [ -d ${Meter_BinDir} ]; then
  cd ${Meter_BinDir}
else
  ${Logger} "No such directory ${Meter_BinDir}"
  exit -1
fi

# We need to locate the probe script and it must be executable
if [ ! -x ./glexec_meter ]; then
  ${Logger} "The glexec_meter file is not in this directory: $(pwd)"
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

# glexec probe has its own lock file checking.

enabled=`${pp_dir}/GetProbeConfigAttribute -c $probeconfig_loc EnableProbe`
(( status = $? ))
if (( $status != 0 )); then
  echo "ERROR checking probe configuration!" 1>&2
  exit $status
fi
if [[ -n "$enabled" ]] && [[ "$enabled" == "0" ]]; then
  ${pp_dir}/DebugPrint -c $probeconfig_loc -l -1 "Probe is not enabled: check $Meter_BinDir/ProbeConfig."
  exit 1
fi

#--- run the probes ----
./glexec_meter --nodaemon 2>&1 | ${pp_dir}/DebugPrint -c $probeconfig_loc -l 1

ExitCode=$?

# If the probe ended in error, report this in Syslog and exit
if [ $ExitCode != 0 ]; then
  ${pp_dir}/DebugPrint -c $probeconfig_loc -l -1 "ALERT: $0 exited abnormally with [$ExitCode]"
  exit $ExitCode
fi
  
exit 0


