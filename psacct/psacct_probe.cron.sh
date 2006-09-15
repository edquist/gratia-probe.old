#!/bin/sh

# For now play nice with the old fermi PSACCT package
# So we assume it is working and we do not break it.
# We also assume that for a given date we run after runacct

_date=`date +%m%d`
_adm=${ACCTDIR:-/var/adm}
_nite=${_adm}/acct/nite
_currentfile=${_nite}/spacct${_date}

_gratia_dir=/opt/vdt/gratia
_gratia_data_dir=${_gratia_dir}/var/data
test -e "${_currentfile}" && cp "${_currentfile}" "${_gratia_data_dir}"

# Now run gratia

cd "${_gratia_dir}"/probe
if test -n "$PYTHONPATH" ; then
  if echo "$PYTHONPATH" | grep -e ':$' >/dev/null 2>&1; then
    PYTHONPATH="${PYTHONPATH}${_gratia_dir}/probe/common:"
  else
    PYTHONPATH="${PYTHONPATH}:${_gratia_dir}/probe/common"
  fi
else
  PYTHONPATH="${_gratia_dir}/probe/common"
fi
export PYTHONPATH
python "${_gratia_dir}/probe/psacct/PSACCTProbe.py"
