#!/bin/sh
set -x
export PATH=$PATH:/usr/bin:/usr/local/bin/

_gratia_dir=/usr/share/gratia
_gratia_data_dir=/var/lib/gratia/data
_currentfile=${_gratia_data_dir}/query_one.log
test -e "${_currentfile}" && cp "${_currentfile}" "${_currentfile}".`date +%s`

echo "Start onevm dump " `date`
/sbin/runuser - oneadmin -c ${_gratia_dir}/onevm/query_one.rb > "${_currentfile}"
echo "End onevm dump " `date`
python ${_gratia_dir}/onevm/VMProbe ${_currentfile}
exit $?



