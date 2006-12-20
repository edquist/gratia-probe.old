#! /usr/bin/env bash

# Default values.
hostname=gratia-db01.fnal.gov 
username=reader
port=3320 
password=reader 
schema=gratia
LocalJobId=0
ProbeName=%

Meter_BinDir=$(dirname $0)
if test -e ${Meter_BinDir}/ProbeConfig ; then
   eval `grep MeterName ${Meter_BinDir}/ProbeConfig`
   ProbeName=$MeterName
   eval `grep VDTSetupFile ${Meter_BinDir}/ProbeConfig`
fi

while test "x$1" != "x"; do
   case $1 in 
      "-v" ) verbose=x; shift ;;
      "-h" ) help=x; shift ;;
      "-help" ) help=x; shift ;;
      "--help" ) help=x; shift ;;
      "-hostname" ) shift; hostname=$1; shift ;;
      "-port" ) shift; port=$1; shift ;;
      "-username" ) shift; username=$1; shift ;;
      "-password" ) shift; password=$1; shift ;;
      "-schema" ) shift; schema=$1; shift ;;
      "-LocalJobId" ) shift; LocalJobId=$1; shift ;;
      "-ProbeName" ) shift; ProbeName=$1; shift ;;      
      *) echo "Unknown option: $1" ; shift;;
   esac
done

if test "x$help" != "x"; then
    echo "$0 [options]"
    echo "Options:"
    echo "  -LocalJobId : local job id of the known job"
    echo "  -v : verbose"
    echo "  -h : print this help message"
    echo "  -hostname : name of the Gratia Database host"
    echo "  -port : port number of the Gratia Databse"
    echo "  -username : Database username having read access to the Gratia Database"
    echo "  -password : Database password for the given user"
    echo "  -schema : Schema name for the Gratia Database"
    echo "  -ProbeName : name of the probe that sent the data"
fi


#Setup the proper Grid environment
#for Setupsh in ${VDTSetupFile} '/root/setup.sh'
#do
#  if [[ -f ${Setupsh} && -r ${Setupsh} ]]; then
#    # Should the output of this be directed to /dev/null?
#    . ${Setupsh} >/dev/null
#    break
#  fi
#done

#if macosx
#cwhich="type -path"
#else
cwhich="which"
#fi

if `$cwhich mysql > /dev/null 2>&1` ; then
  # we found mysql
  echo > /dev/null
else
  echo "Error: Could not find mysql"
  exit 1
fi

connection_string=" -h $hostname -u $username --port=$port --password=$password $schema "
cmd="select recordId,StartTime,EndTime,WallDuration,LocalJobId,ProbeName from JobUsageRecord where LocalJobId=$LocalJobId and ProbeName like '$ProbeName';"
if test "x$verbose" != "x"; then 
   echo mysql $connection_string -e "$cmd"
fi
mysql $connection_string -e "$cmd" > /var/tmp/quicktest_$pid.out
if test -s /var/tmp/quicktest_$pid.out; then
   result=0
else
   result=1
fi
cat /var/tmp/quicktest_$pid.out
rm /var/tmp/quicktest_$pid.out

exit $result
