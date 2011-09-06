#!/bin/sh

# For now play nice with the old fermi PSACCT package
# So we assume it is working and we do not break it.
# We also assume that for a given date we run after runacct

_date=`date +%m%d`
_adm=${ACCTDIR:-/var/adm}
_nite=${_adm}/acct/nite
_currentfile=${_nite}/spacct${_date}

_gratia_dir=/usr/share/gratia
_gratia_data_dir=${_gratia_dir}/var/data
test -e "${_currentfile}" && cp "${_currentfile}" "${_gratia_data_dir}"

# Now run gratia
python "${_gratia_dir}/psacct/PSACCTProbe"

