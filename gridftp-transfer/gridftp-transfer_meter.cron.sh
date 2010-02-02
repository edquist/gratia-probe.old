#!/bin/bash
#
# gridftp-transfer_meter.cron.sh - Shell script used with cron to parse dcache-storage
#   files for OSG accounting data collection.
#      By Chris Green <greenc@fnal.gov>  Began 5 Sept 2006
# $Id: gridftp-transfer_meter.cron.sh,v 1.1 2008/11/19 19:40:17 greenc Exp $
# Full Path: $Source: /cvs/ols/dcache/gratia/gridftp-transfer/gridftp-transfer_meter.cron.sh,v $
###################################################################
PGM=$(basename $0)
Logger="/usr/bin/logger -s -t $PGM"

Meter_BinDir=$(dirname $0)

eval `grep VDTSetupFile ${Meter_BinDir}/ProbeConfig`
for Setupsh in ${VDTSetupFile} '/opt/vdt/setup.sh' '/opt/osg-ce/setup.sh'
do
  if [[ -f ${Setupsh} && -r ${Setupsh} ]]; then
    # Should the output of this be directed to /dev/null?
    . ${Setupsh} >/dev/null
    break
  fi
done

# Set the working directory, where we expect to find the following
#    necessary files.
if [ -d ${Meter_BinDir} ]; then
  cd ${Meter_BinDir}
else
  ${Logger} "No such directory ${Meter_BinDir}"
  exit -1
fi

# Need to be sure there is not one of these running already
NCMeter=`ps -ef | grep GridftpTransferProbeDriver.py | grep -v grep | wc -l`
eval `grep WorkingFolder ./ProbeConfig`
if [ ${NCMeter} -ne 0 -a -e ${WorkingFolder}/gridftp-transfer_meter.cron.pid ]; then
  # We might have a condor_meter.pl running, let's verify that we 
  # started it.
  
  otherpid=`cat ${WorkingFolder}/gridftp-transfer_meter.cron.pid`
  NCCron=`ps -ef | grep ${otherpid} | grep gridftp-transfer_meter.cron | wc -l`
  if [ ${NCCron} -ne 0 ]; then 
 
    ${Logger} "There is a GridftpTransferProbeDriver.py running already"
    exit 1
  fi
fi

# We need to locate the probe script
if [ ! -r ./GridftpTransferProbeDriver.py ]; then
  ${Logger} "The GridftpTransferProbeDriver.py file is not in this directory: $(pwd)"
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

pp_dir=$(cd "$Meter_BinDir/.."; pwd)
arch_spec_dir=`echo "${pp_dir}/lib."*`
if test -n "$PYTHONPATH" ; then
  if echo "$PYTHONPATH" | grep -e ':$' >/dev/null 2>&1; then
    PYTHONPATH="${PYTHONPATH}${pp_dir}/common:${arch_spec_dir}:"
  else
    PYTHONPATH="${PYTHONPATH}:${pp_dir}/common:${arch_spec_dir}"
  fi
else
  PYTHONPATH="${pp_dir}/common:${pp_dir}/common:${arch_spec_dir}"
fi
export PYTHONPATH

enabled=`${pp_dir}/common/GetProbeConfigAttribute.py EnableProbe`
(( status = $? ))
if (( $status != 0 )); then
  echo "ERROR checking probe configuration!" 1>&2
  exit $status
fi
if [[ -n "$enabled" ]] && [[ "$enabled" == "0" ]]; then
  ${pp_dir}/common/DebugPrint.py -l 0 "Probe is not enabled: check $Meter_BinDir/ProbeConfig."
  exit 1
fi

WorkingFolder=`${pp_dir}/common/GetProbeConfigAttribute.py WorkingFolder`
if [ ! -d ${WorkingFolder} ]; then
  if [ "x${WorkingFolder}" != "x" ] ; then 
    mkdir -p ${WorkingFolder}
  else
    ${Logger} "There is no WorkingFolder directory defined in $Meter_BinDir/ProbeConfig."
    exit -4
  fi
fi

echo $$ > ${WorkingFolder}/gridftp-transfer_meter.cron.pid
(( status = $? ))
if (( $status != 0 )); then
   ${Logger} "gridftp-transfer_meter.cron.sh failed to store the pid in  ${WorkingFolder}/gridftp-transfer_meter.cron.pid"
   exit -2
fi

#--- run the probe ----
python ./GridftpTransferProbeDriver.py

ExitCode=$?

# If the probe ended in error, report this in Syslog and exit
if [ $ExitCode != 0 ]; then
  ${pp_dir}/common/DebugPrint.py -l -1 "ALERT: $0 exited abnormally with [$ExitCode]"
  exit $ExitCode
fi
  
exit 0

#==================================================================
# CVS Log
# $Log: gridftp-transfer_meter.cron.sh,v $
# Revision 1.1  2008/11/19 19:40:17  greenc
# Improve version reporting.
#
# cron wrapper script for environment.
#
