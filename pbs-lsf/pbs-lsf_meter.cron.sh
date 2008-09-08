#!/bin/bash
#
# pbs-lsfr_meter.cron.sh - Shell script used with cron to parse PBS and LSF
#   files for OSG accounting data collection.
#      By Chris Green <greenc@fnal.gov>  Began 5 Sept 2006
# $Id: pbs-lsf_meter.cron.sh,v 1.10 2008-09-08 21:40:51 greenc Exp $
# Full Path: $Source: /var/tmp/move/gratia/probe/pbs-lsf/pbs-lsf_meter.cron.sh,v $
###################################################################
function check_if_running {
  # Need to be sure there is not one of these running already
  # This may not be the best way to test this for the long term ??? ###
  # If one is not running, then we need to remove a lock file that the
  # ./urCollector.pl and ./pbs-lsf_meter.pl processes check for.
  # Note: this lock file gets left behind when either of these processes
  #       ends prematurely like on a system shutdown.
    
  NCMeter=`ps -ef | egrep "\./urCollector.pl|\./pbs-lsf_meter.pl" | grep -v grep | wc -l`
  get_lockfile
  if [ -f $LOCKFILE ];then
    if [ ${NCMeter} -ne 0 ]; then
      return 1 
    else
      rm -f $LOCKFILE
    fi
  else
    mkdir -p `dirname "$LOCKFILE"`
  fi
  return 0
} # end of terminate_if_running
#------------------------
function get_lockfile {
  conf=$URCOLLECTOR_LOCATION/urCollector.conf
  if [ ! -f $conf ];then
    ${Logger} "ERROR: Unable to locate $conf"
    exit -1
  fi
  LOCKFILE=$(perl <<EOF
use urCollector::Configuration;
# Parse configuration file
&parseConf("$conf");
print "\$configValues{collectorLockFileName}";
exit(0);
EOF
)
} # end of get_lockfile
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

# We need to locate the probe script and it must be executable
if [ ! -x urCollector.pl ]; then
  ${Logger} "The urCollector.pl file is not in this directory: $(pwd)"
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

export URCOLLECTOR_LOCATION=`pwd`  

#--- check to see if processes still running --
check_if_running;rtn=$?
if [ $rtn -eq 1 ];then
   ${Logger} "urCollector.pl or pbs-lsf_meter.pl probes still running... exiting"
  exit 0
fi

enabled=`${pp_dir}/GetProbeConfigAttribute.py EnableProbe`
(( status = $? ))
if (( $status != 0 )); then
  echo "ERROR checking probe configuration!" 1>&2
  exit $status
fi
if [[ -n "$enabled" ]] && [[ "$enabled" == "0" ]]; then
  ${pp_dir}/DebugPrint.py -l -1 "Probe is not enabled: check $Meter_BinDir/ProbeConfig."
  exit 1
fi

log_file="`date +'%Y-%m-%d'`.log"

# Remove erroneous log files from probe main area (should be in gratia/var/logs/)
rm -f 2[0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9].log

#--- run the probes ----
./urCollector.pl --nodaemon 2>&1 | ${pp_dir}/DebugPrint.py -l 1
./pbs-lsf_meter.pl 2>&1

ExitCode=$?

# If the probe ended in error, report this in Syslog and exit
if [ $ExitCode != 0 ]; then
  ${pp_dir}/DebugPrint.py -l -1 "ALERT: $0 exited abnormally with [$ExitCode]"
  exit $ExitCode
fi
  
exit 0

#==================================================================
# CVS Log
# $Log: not supported by cvs2svn $
# Revision 1.9  2007/12/10 22:37:05  greenc
# Improve lockfile logic.
#
# Revision 1.8  2007/10/10 18:03:04  greenc
# Make sure lock directory exists.
#
# Revision 1.7  2007/09/10 20:17:14  greenc
# Update SPEC file.
#
# Improve redirection of non-managed output.
#
# Revision 1.6  2007/08/03 17:18:09  greenc
# All output goes to DebugPrint();
#
# Remove erroneously placed logfiles from previous version.
#
# Revision 1.5  2007/06/13 22:09:12  greenc
# Append output of urCollector.pl to log file.
#
# Revision 1.4  2007/05/25 23:34:56  greenc
# New utilities GetProbeConfigAttribute.py and DebugPrint.py.
#
# Cron scripts now check for EnableProbe attribute in config -- if present
# and 0, probe will not be invoked and log entry will be made.
#
# Fix fragility in spec file using "global" macro.
#
# Revision 1.3  2007/03/08 18:25:00  greenc
# John W's changes to forestall lockfile problems.
#
# Revision 1.2  2006/10/09 16:40:26  greenc
# Invoke the perl Gratia wrapper immediately after the urCollector run.
#
# Revision 1.1  2006/09/07 22:20:41  greenc
# Gratia-specific files for pbs-lsf probe.
#
# Revision 1.1  2006/08/21 21:10:03  greenc
# Probe areas reorganized to facilitate RPM building and new
# probes.
#
# README files in probe/condor and probe/common still need to be
# updated.
#
# Probe tarball creation removed from build script per discussion with Greg. Please see probe/build/README.
#
# RPM building commissioned and will be tested shortly.
#
# Revision 1.4  2006/07/20 14:41:48  pcanal
# permissions
#
# Revision 1.3  2006/07/20 14:38:53  pcanal
# change permisssion
#
# Revision 1.2  2006/06/16 15:57:37  glr01
# glr: reset condor-probe to contents from gratia-proto
#
# Revision 1.8  2006/06/06 21:45:16  pcanal
# update following the new directory layout
#
# Revision 1.7  2006/04/21 15:49:58  kschu
# There is now no output, unless there is a problem, updated note re: crontab
#
# Revision 1.6  2006/04/19 22:04:04  kschu
# Updated comment about setting up crontab entry
#
# Revision 1.5  2006/04/19 16:51:16  kschu
# Improved exception handling and comments within the script
#
# Revision 1.4  2006/04/17 22:25:14  kschu
# Gets the log file directory from ProbeConfig file.
#
# Revision 1.3  2006/04/13 15:56:29  kschu
# Uses a directory as probe command-line argument
#
# Revision 1.2  2006/04/10 19:52:30  kschu
# Refined data submission after code review
#
# Revision 1.1  2006/04/05 18:10:25  kschu
# First test version of script to be called by Cron
#
