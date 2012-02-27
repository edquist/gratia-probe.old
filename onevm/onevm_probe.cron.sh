#!/bin/sh
#set -x
export PATH=$PATH:/usr/bin:/usr/local/bin/

_gratia_dir=/usr/share/gratia
_gratia_data_dir=/var/lib/gratia/data
_currentfile=${_gratia_data_dir}/query_one.log
test -e "${_currentfile}" && cp "${_currentfile}" "${_currentfile}".`date +%s`

echo "Start onevm dump " `date`
#version
_version=`/sbin/runuser - oneadmin -c "onevm --version|grep ^OpenNebula|cut -d' ' -f2"`
#_version=2.0.0
echo "OpenNebula version $_version"
if [ x${_version} == "x" ]
then
	_version=3.0.0
fi
_version=`echo ${_version%.*}`
options=""
if [ ${_version} == "3.0" ]
then
	#check if chkpt_vm_DoNotDelete exists
	if [ ! -f ${_gratia_data_dir}/chkpt_vm_DoNotDelete ]
	then
		#we will start from the beginig
		options="-a"
	else
		ct=`date +%s`
		let delta=${ct}-`cat ${_gratia_data_dir}/chkpt_vm_DoNotDelete`
		options="-t ${ct} -d ${delta}"
	fi
	/sbin/runuser - oneadmin ${options} -c ${_gratia_dir}/onevm/query_one_lite.rb -c ${_gratia_data_dir} -o "${_currentfile}"
else
	#get the latest vmid
	_vmid=`/sbin/runuser - oneadmin -c "onevm list -l id|sort -n|tail -1"`
	/sbin/runuser - oneadmin -c ${_gratia_dir}/onevm/query_one_2.0.0 ${_vmid} >  "${_currentfile}"
fi
	
echo "End onevm dump " `date`
${_gratia_dir}/onevm/VMGratiaProbe  -f ${_currentfile} -V ${_version} 
exit $?
