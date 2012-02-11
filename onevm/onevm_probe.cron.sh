#!/bin/sh
set -x
export PATH=$PATH:/usr/bin:/usr/local/bin/

_gratia_dir=/usr/share/gratia
_gratia_data_dir=/var/lib/gratia/data
_currentfile=${_gratia_data_dir}/query_one.log
test -e "${_currentfile}" && cp "${_currentfile}" "${_currentfile}".`date +%s`

echo "Start onevm dump " `date`
#version
_version=`onevm --version|grep ^OpenNebula|cut -d' ' -f2`
echo "OpenNebula version $version"
if [ x${_version} == "x" ]
then
	_version=3.0.0
fi
if [ ${_version} == "3.0.0" ]
then
	/sbin/runuser - oneadmin -c ${_gratia_dir}/onevm/query_one.rb > "${_currentfile}"
else
	#get the latest vmid
	_vmid=`onevm list -l id|sort -n|tail -1`
	/sbin/runuser - oneadmin -c ${_gratia_dir}/onevm/query_one_2.0.0 ${_vmid}
fi
	
echo "End onevm dump " `date`
python ${_gratia_dir}/onevm/VMProbe  ${_currentfile} ${_version}
exit $?




#version
version=`onevm --version|grep ^OpenNebula|cut -d' ' -f2`