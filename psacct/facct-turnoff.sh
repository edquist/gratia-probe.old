#!/bin/sh

PATH=/usr/lib/acct:/bin:/usr/bin:/etc
export PATH
_MIN_BLKS=500
_adm=${ACCTDIR:-/var/adm}
_lib=/usr/lib/acct
_nite=${_adm}/acct/nite
_sum=${_adm}/acct/sum
_fsdev='/var/adm'
_statefile=${_nite}/statefile
_active=${_nite}/active
_lastdate=${_nite}/lastdate
_date="`date +%m%d`"


gratia_dir=/opt/vdt/gratia
gratia_psdir=${gratia_dir}/probe/psacct

# last move
mv /var/log/pacct "${_nite}/spacct${_date}"
    
mkdir -p "${gratia_dir}/var/account"
touch "${gratia_dir}/var/account/pacct"
/usr/sbin/accton  "${gratia_dir}/var/account/pacct"

# Apply patch to root crontab
#cat $gratia_psdir/cron.patch | patch 
