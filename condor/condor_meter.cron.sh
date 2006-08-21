#!/bin/bash
#
# condor_meter.cron.sh - Shell script used with cron to parse Condor log 
#   files for OSG accounting data collection.
#      By Ken Schumacher <kschu@fnal.gov>  Began 5 April 2006
# $Id: condor_meter.cron.sh,v 1.1 2006-08-21 21:10:03 greenc Exp $
# Full Path: $Source: /var/tmp/move/gratia/probe/condor/condor_meter.cron.sh,v $

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
NCMeter=`ps -ef | grep condor_meter.pl | grep -v grep | wc -l`
if [ ${NCMeter} -eq 0 ]; then
  
  # Set the working directory, where we expect to find the following
  #    necessary files.
  if [ -d ${Meter_BinDir} ]; then
    cd ${Meter_BinDir}
  else
    ${Logger} "No such directory ${Meter_BinDir}"
    exit -1
  fi
  
  # We need to locate the condor probe script and it must be executable
  if [ ! -x condor_meter.pl ]; then
    ${Logger} "The condor_meter.pl file is not in this directory: $(pwd)"
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
  CondorLog_Dir="${VDT_LOCATION}/gratia/var/data"
  if [ ! -d ${CondorLog_Dir} ]; then
    ${Logger} "There is no ${CondorLog_Dir} directory"
    exit -4
  fi

  
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
    
  #echo "Begin processing directory ${CondorLog_Dir}"
  # The '-d' option tells the meter to delete log files after they are
  #    reported to Gratia.
  ./condor_meter.pl -d ${CondorLog_Dir}
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
  ${Logger} "There is a 'condor_meter.pl' task running already."
fi

exit 0

#==================================================================
# CVS Log
# $Log: not supported by cvs2svn $
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
