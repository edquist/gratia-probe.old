Name: gratia-probe
Summary: Gratia OSG accounting system probes
Group: Applications/System
Version: 0.30d
Release: 1
License: GPL
Group: Applications/System
URL: http://sourceforge.net/projects/gratia/
Packager: Chris Green <greenc@fnal.gov>
Vendor: The Open Science Grid <http://www.opensciencegrid.org/>
BuildRequires: python >= 2.3
BuildRequires: python-devel >= 2.3
BuildRequires: postgresql-devel
BuildRequires: gcc-c++

%global sqlalchemy_version 0.4.1
%global psycopg2_version 2.0.6
%global dcache_probe_version 2.0
%global dcache_storage_probe_version 0_1

# RH5 precompiles the python files and produces .pyc and .pyo files.
%define _unpackaged_files_terminate_build 0

%global ProbeConfig_template_marker <!-- Temporary RPM-generated template marker -->
%global pbs_lsf_template_marker # Temporary RPM-generated template marker
%global urCollector_version 2006-06-13

%global osg_collector gratia.opensciencegrid.org
%global fnal_collector gratia-fermi.fnal.gov

%{?config_itb: %global maybe_itb_suffix -itb }
%{?config_itb: %global itb 1}
%{!?config_itb: %global itb 0}

%{!?pexec: %global pexec python }

%if %{itb}
  %global collector_port 8881
  %global metric_collector metric.opensciencegrid.org
  %global metric_port 8881
  %global grid OSG-ITB
%else
  %global collector_port 8880
  %global metric_collector metric.opensciencegrid.org
  %global metric_port 8880
  %global grid OSG
%endif

%{?vdt_loc: %global vdt_loc_set 1}
%{!?vdt_loc: %global vdt_loc /opt/vdt}
%{!?default_prefix: %global default_prefix %{vdt_loc}/gratia}

%global osg_attr %{vdt_loc}/monitoring/osg-attributes.conf

%{!?site_name: %global site_name \$(( if [[ -r \"%{osg_attr}\" ]]; then . \"%{osg_attr}\" ; echo \"${OSG_SITE_NAME}\"; else echo \"Generic Site\"; fi ) )}

%{!?meter_name: %global meter_name `hostname -f`}

%define scrub_root_crontab tmpfile=`mktemp /tmp/gratia-cleanup.XXXXXXXXXX`; crontab -l 2>/dev/null | %{__grep} -v -e 'gratia/probe/' > "$tmpfile" 2>/dev/null; crontab "$tmpfile" 2>/dev/null 2>&1; %{__rm} -f "$tmpfile"

%define final_post_message() [[ "%1" == *ProbeConfig* ]] && echo "IMPORTANT: please check %1 and remember to set EnableProbe = \"1\" to start operation." 1>&2

%define max_pending_files_check() (( mpf=`sed -ne 's/^[ 	]*MaxPendingFiles[ 	]*=[ 	]*\\"\\{0,1\\}\\([0-9]\\{1,\\}\\)\\"\\{0,1\\}.*$/\\1/p' "${RPM_INSTALL_PREFIX1}/probe/%1/ProbeConfig"` )); if (( $mpf < 100000 )); then printf "NOTE: Given the small size of gratia files (<1K), MaxPendingFiles can\\nbe safely increased to 100K or more to facilitate better tolerance of collector outages.\\n"; fi

%define configure_probeconfig_pre(p:d:m:) site_name=%{site_name}; %{__grep} -le '^%{ProbeConfig_template_marker}\$' "${RPM_INSTALL_PREFIX1}/probe/%{-d*}/ProbeConfig"{,.rpmnew} %{*} 2>/dev/null | while read config_file; do test -n "$config_file" || continue; %{__perl} -wni.orig -e 's&MAGIC_VDT_LOCATION/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&; %{?vdt_loc_set: s&MAGIC_VDT_LOCATION&%{vdt_loc}&;} s&/opt/vdt/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&; my $meter_name = %{meter_name}; chomp $meter_name; my $install_host = `hostname -f`; $install_host = "${meter_name}" unless $install_host =~ m&\\.&; chomp $install_host; my $collector_host = ($install_host =~ m&\\.fnal\\.&i)?"%{fnal_collector}":"%{osg_collector}"; my $collector_port = "%{-p*}" || "%{collector_port}"; s&^(\\s*(?:SOAPHost|SSLRegistrationHost)\\s*=\\s*).*$&${1}"${collector_host}:${collector_port}"&; s&^(\\s*SSLHost\\s*=\\s*).*$&${1}""&; s&(MeterName\\s*=\\s*)\\"[^\\"]*\\"&${1}"%{-m*}:${meter_name}"&; s&(SiteName\\s*=\\s*)\\"[^\\"]*\\"&${1}"'"${site_name}"'"&;

%define configure_probeconfig_post(g:) my $grid = "%{-g*}" || "%{grid}"; s&(Grid\\s*=\\s*)\\\"[^\\\"]*\\\"&${1}"${grid}"&; m&%{ProbeConfig_template_marker}& or print; ' "$config_file" >/dev/null 2>&1; %{expand: %final_post_message $config_file }; done

%global setuptools_source setuptools-0.6c3-py2.3.egg
%global dcache_transfer_source gratia-dcache-probe-%{dcache_probe_version}.tar.gz
%global dcache_storage_source dcacheStorageMeter_%{dcache_storage_probe_version}.tar.gz

Source0: %{name}-common-%{version}.tar.bz2
Source1: %{name}-condor-%{version}.tar.bz2
Source2: %{name}-psacct-%{version}.tar.bz2
Source3: %{name}-pbs-lsf-%{version}.tar.bz2
Source4: urCollector-%{urCollector_version}.tgz
Source5: %{name}-sge-%{version}.tar.bz2
Source6: %{name}-glexec-%{version}.tar.bz2
Source7: %{name}-metric-%{version}.tar.bz2
Source8: SQLAlchemy-%{sqlalchemy_version}.tar.gz
Source9: psycopg2-%{psycopg2_version}.tar.gz
Source10: %{name}-dCache-storage-%{version}.tar.bz2
Source11: %{setuptools_source}
Source12: %{dcache_transfer_source}
Source13: %{dcache_storage_source}
Patch0: urCollector-2006-06-13-pcanal-fixes-1.patch
Patch1: urCollector-2006-06-13-greenc-fixes-1.patch
Patch2: urCollector-2006-06-13-createTime-timezone.patch
Patch3: urCollector-2006-06-13-nodect.patch
Patch4: urCollector-2006-06-13-modules-1.patch
Patch5: urCollector-2006-06-13-modules-2.patch
Patch6: urCollector-2006-06-13-xmlUtil.h-gcc4.1-fixes.patch
Patch7: urCollector-2006-06-13-tac-race.patch
Patch8: urCollector-2006-06-13-parser-improve.patch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

Prefix: /usr
Prefix: %{default_prefix}
Prefix: /etc

%prep
%setup -q -c
%setup -q -D -T -a 1
%setup -q -D -T -a 2
%ifnarch noarch
%setup -q -D -T -a 3
%setup -q -D -T -a 4
cd urCollector-%{urCollector_version}
%patch -P 0 -p1 -b .pcanal-fixes-1
%patch -P 1 -b .greenc-fixes-1
%patch -P 2 -b .createTime-timezone-1
%patch -P 3 -b .nodect
%patch -P 4 -b .modules-1
%patch -P 5 -b .modules-2
%patch -P 6 -b .xmlUtil.h-gcc4.1-fixes
%patch -P 7 -b .tac-race
%patch -P 8 -b .parser-improve
%setup -q -D -T -a 9
%endif
%setup -q -D -T -a 5
%setup -q -D -T -a 6
%setup -q -D -T -a 7
%setup -q -D -T -a 8
%{__cp} ${RPM_SOURCE_DIR}/%{setuptools_source} SQLAlchemy-%{sqlalchemy_version}/
mkdir dCache-transfer
%{__tar} zxvf ${RPM_SOURCE_DIR}/%{dcache_transfer_source} -C dCache-transfer/
%{__rm} -rf dCache-transfer/{external,tmp,install.sh} # Not needed by this install.
mkdir dCache-storage
%{__tar} zxvf ${RPM_SOURCE_DIR}/%{dcache_storage_source} -C dCache-storage/
%setup -q -D -T -a 10

%build
%ifnarch noarch
cd urCollector-%{urCollector_version}
%{__make} clean
%{__make}
cd -
cd psycopg2-%{psycopg2_version}
%{pexec} setup.py build
%else
cd SQLAlchemy-%{sqlalchemy_version}
%{pexec} setup.py build
%endif

%install
# Setup
%{__rm} -rf "${RPM_BUILD_ROOT}"
%{__mkdir_p} "${RPM_BUILD_ROOT}%{default_prefix}/probe"

%ifarch noarch
  # Obtain files
  %{__cp} -pR {common,condor,psacct,sge,glexec,metric,dCache-transfer,dCache-storage} "${RPM_BUILD_ROOT}%{default_prefix}/probe"

  # Get uncustomized ProbeConfigTemplate files (see post below)
  for probe_config in \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/condor/ProbeConfig" \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/psacct/ProbeConfig" \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/sge/ProbeConfig" \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/glexec/ProbeConfig" \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/metric/ProbeConfig" \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/dCache-transfer/ProbeConfig" \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/dCache-storage/ProbeConfig" \
      ; do
    %{__cp} -p "common/ProbeConfigTemplate" "$probe_config"
    echo "%{ProbeConfig_template_marker}" >> "$probe_config"
  done

  # dCache init script
  %{__install} -d "${RPM_BUILD_ROOT}/etc/rc.d/init.d/"
  %{__install} -m 755 "${RPM_BUILD_ROOT}%{default_prefix}/probe/dCache-transfer/gratia-dcache-probe" "${RPM_BUILD_ROOT}/etc/rc.d/init.d/gratia-dcache-transfer-probe"
  %{__rm} -f "${RPM_BUILD_ROOT}%{default_prefix}/probe/dCache-transfer/"{gratia-dcache-probe,Gratia.py}

  # dCache-transfer README change
  perl -wani.bak -e 'm&^FILES:$& and print <<EOF;
This README is only intended for beta testers, and to guide those who will
make the RPM distribution of this probe.
If you don'"'"'t understand any of the steps in the instructions, you
probably should wait until the RPM version is available.

EOF
print;
' "${RPM_BUILD_ROOT}%{default_prefix}/probe/dCache-transfer/README"


  # YUM repository install
  install -d "${RPM_BUILD_ROOT}/etc/yum.repos.d"
  %{__mv} -v "${RPM_BUILD_ROOT}%{default_prefix}/probe/common/gratia.repo" "${RPM_BUILD_ROOT}/etc/yum.repos.d/"

  # Get already-built SQLAlchemy software
  %{__cp} -R SQLAlchemy-%{sqlalchemy_version}/build/lib/sqlalchemy \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/common/"

%else

  # PBS / LSF probe install
  %{__cp} -pR pbs-lsf "${RPM_BUILD_ROOT}%{default_prefix}/probe"
  for probe_config in \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/ProbeConfig" \
      ; do
    %{__cp} -p "common/ProbeConfigTemplate" \
          "$probe_config"
    echo "%{ProbeConfig_template_marker}" >> "$probe_config"
  done
  cd "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf"
  %{__ln_s} . etc
  %{__ln_s} . libexec
  cd - >/dev/null

  # Get urCollector software
  cd urCollector-%{urCollector_version}
  %{__cp} -p urCreator urCollector.pl \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf"
  %{__install} -m 0644 LICENSE \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf"
  %{__cp} -p urCollector.conf-template \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/urCollector.conf"
  echo "%{pbs_lsf_template_marker}" >> \
       "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/urCollector.conf"
  %{__mkdir_p} "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/urCollector"
  %{__cp} -p urCollector/Common.pm \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/urCollector"
  %{__cp} -p urCollector/Configuration.pm \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/urCollector"
  cd - >/dev/null

  # Get already-built psycopg2 software
  %{__cp} -R psycopg2-%{psycopg2_version}/build/lib.* \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/"

%endif

cd "${RPM_BUILD_ROOT}%{default_prefix}"

%ifarch noarch
  # Set up var area
  %{__mkdir_p} var/{data,logs,tmp}
  %{__chmod} 1777 var/data

  # install psacct startup script.
  %{__install} -d "${RPM_BUILD_ROOT}/etc/rc.d/init.d/"
  %{__install} -m 755 "${RPM_BUILD_ROOT}%{default_prefix}/probe/psacct/gratia-psacct" \
  "${RPM_BUILD_ROOT}/etc/rc.d/init.d/"
%else
  %{__mkdir_p} var/{lock,tmp/urCollector}
%endif

%clean
%{__rm} -rf "${RPM_BUILD_ROOT}"

%description
Probes for the Gratia OSG accounting system

%ifnarch noarch
%package extra-libs-arch-spec
Summary: Architecture-specific third-party libraries required by some Gratia probes.
Group: Application/System
Requires: postgresql-libs
Requires: python >= 2.3
License: See psycopg2-LICENSE.

%description extra-libs-arch-spec
Architecture-specific third-party libraries required by some Gratia probes.

Currently this consists of the psycopg2 postgresql interface package;
see http://www.initd.org/pub/software/psycopg/ for details.

%files extra-libs-arch-spec
%defattr(-,root,root,-)
%{default_prefix}/probe/lib.*

%package pbs-lsf%{?maybe_itb_suffix}
Summary: Gratia OSG accounting system probe for PBS and LSF batch systems.
Group: Application/System
Requires: %{name}-common >= 0.12f
License: See LICENSE.
%{?config_itb:Obsoletes: %{name}-pbs-lsf}
%{!?config_itb:Obsoletes: %{name}-pbs-lsf%{itb_suffix}}

%description pbs-lsf%{?maybe_itb_suffix}
Gratia OSG accounting system probe for PBS and LSF batch systems.

This product includes software developed by The EU EGEE Project
(http://cern.ch/eu-egee/).

%files pbs-lsf%{?maybe_itb_suffix}
%defattr(-,root,root,-)
%dir %{default_prefix}/var
%dir %{default_prefix}/var/lock
%dir %{default_prefix}/var/tmp
%dir %{default_prefix}/var/tmp/urCollector
%doc urCollector-%{urCollector_version}/LICENSE
%doc urCollector-%{urCollector_version}/urCollector.conf-template
%doc pbs-lsf/README
%{default_prefix}/probe/pbs-lsf/README
%{default_prefix}/probe/pbs-lsf/LICENSE
%{default_prefix}/probe/pbs-lsf/pbs-lsf.py
%{default_prefix}/probe/pbs-lsf/pbs-lsf_meter.cron.sh
%{default_prefix}/probe/pbs-lsf/pbs-lsf_meter.pl
%{default_prefix}/probe/pbs-lsf/urCreator
%{default_prefix}/probe/pbs-lsf/urCollector.pl
%{default_prefix}/probe/pbs-lsf/urCollector/Common.pm
%{default_prefix}/probe/pbs-lsf/urCollector/Configuration.pm
%{default_prefix}/probe/pbs-lsf/etc
%{default_prefix}/probe/pbs-lsf/libexec
%{default_prefix}/probe/pbs-lsf/test/pbs-logdir/
%{default_prefix}/probe/pbs-lsf/test/lsf-logdir/
%config(noreplace) %{default_prefix}/probe/pbs-lsf/urCollector.conf
%config(noreplace) %{default_prefix}/probe/pbs-lsf/ProbeConfig

%post pbs-lsf%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"
# /etc -> "${RPM_INSTALL_PREFIX2}"

# Configure urCollector.conf
%{__cat} <<EOF | while read config_file; do
`%{__grep} -le '^%{pbs_lsf_template_marker}$' \
"${RPM_INSTALL_PREFIX1}"/probe/pbs-lsf/urCollector.conf{,.rpmnew} \
2>/dev/null`
EOF
test -n "$config_file" || continue
%{__perl} -wni.orig -e \
'
s&^\s*(URBox\s*=\s*).*$&${1}"$ENV{RPM_INSTALL_PREFIX1}/var/tmp/urCollector"&;
s&^\s*(collectorLockFileName\s*=\s*).*$&${1}"$ENV{RPM_INSTALL_PREFIX1}/var/lock/urCollector.lock"&;
s&^\s*(collectorLogFileName\s*=\s*).*$&${1}"$ENV{RPM_INSTALL_PREFIX1}/var/logs/urCollector.log"&;
s&^\s*(collectorBufferFileName\s*=\s*).*$&${1}"$ENV{RPM_INSTALL_PREFIX1}/var/tmp/urCollectorBuffer"&;
s&^\s*(jobPerTimeInterval\s*=\s*).*$&${1}"1000"&;
s&^\s*(timeInterval\s*=\s*).*$&${1}"0"&;
m&%{pbs_lsf_template_marker}& or print;
' \
"$config_file" >/dev/null 2>&1
done

%configure_probeconfig_pre -d pbs-lsf -m pbs-lsf
%configure_probeconfig_post

%max_pending_files_check pbs-lsf

# Configure crontab entry
%scrub_root_crontab
if %{__grep} -re 'pbs-lsf_meter.cron\.sh' \
        ${RPM_INSTALL_PREFIX2}/crontab ${RPM_INSTALL_PREFIX2}/cron.??* >/dev/null 2>&1; then
%{__cat} <<EOF 1>&2

WARNING: non-standard installation of probe in ${RPM_INSTALL_PREFIX2}/crontab or ${RPM_INSTALL_PREFIX2}/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

(( min = $RANDOM % 15 ))
%{__cat} >${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-pbs-lsf.cron <<EOF
$min,$(( $min + 15 )),$(( $min + 30 )),$(( $min + 45 )) * * * * root \
"${RPM_INSTALL_PREFIX1}/probe/pbs-lsf/pbs-lsf_meter.cron.sh"
EOF

%preun pbs-lsf%{?maybe_itb_suffix}
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  %{__rm} -f ${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-pbs-lsf.cron
fi

%else

%package common
Summary: Common files for Gratia OSG accounting system probes
Group: Applications/System
Requires: python >= 2.2

%description common
Common files and examples for Gratia OSG accounting system probes.

%files common
%defattr(-,root,root,-)
%dir %{default_prefix}/var
%dir %{default_prefix}/var/logs
%dir %{default_prefix}/var/data
%dir %{default_prefix}/var/tmp
%doc common/README
%doc common/samplemeter.pl
%doc common/samplemeter.py
%doc common/samplemeter_multi.py
%doc common/ProbeConfigTemplate
%{default_prefix}/probe/common/README
%{default_prefix}/probe/common/samplemeter.pl
%{default_prefix}/probe/common/samplemeter.py
%{default_prefix}/probe/common/samplemeter_multi.py
%{default_prefix}/probe/common/ProbeConfigTemplate
%{default_prefix}/probe/common/Gratia.py
%{default_prefix}/probe/common/GetProbeConfigAttribute.py
%{default_prefix}/probe/common/DebugPrint.py
%{default_prefix}/probe/common/RegisterProbe.py
%{default_prefix}/probe/common/test/db-find-job
%config(noreplace) /etc/yum.repos.d/gratia.repo

%package extra-libs
Summary: Third-party libraries required by some Gratia probes.
Group: Application/System
Requires: python >= 2.3
License: See SQLAlchemy-LICENSE.

%description extra-libs
Third-party libraries required by some Gratia probes.

Currently this consists of the SQLAlchemy postgresql interface package;
see http://www.sqlalchemy.org/ for details.

%files extra-libs
%defattr(-,root,root,-)
%{default_prefix}/probe/common/sqlalchemy

%package psacct
Summary: A ps-accounting probe
Group: Applications/System
Requires: python >= 2.2
Requires: psacct
Requires: %{name}-common >= 0.12f

%description psacct
The psacct probe for the Gratia OSG accounting system.

# Anything marked "config" is something that is going to be changed in
# post or by the end user.
%files psacct
%defattr(-,root,root,-)
%doc psacct/README
%{default_prefix}/probe/psacct/README
%config %{default_prefix}/probe/psacct/facct-catchup
%config %{default_prefix}/probe/psacct/facct-turnoff.sh
%config %{default_prefix}/probe/psacct/psacct_probe.cron.sh
%config %{default_prefix}/probe/psacct/gratia-psacct
%{default_prefix}/probe/psacct/PSACCTProbeLib.py
%{default_prefix}/probe/psacct/PSACCTProbe.py      
%config(noreplace) %{default_prefix}/probe/psacct/ProbeConfig
%config /etc/rc.d/init.d/gratia-psacct

%post psacct
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"
# /etc -> "${RPM_INSTALL_PREFIX2}"

%configure_probeconfig_pre -p 8882 -d psacct -m psacct ${RPM_INSTALL_PREFIX1}/probe/psacct/facct-catchup ${RPM_INSTALL_PREFIX1}/probe/psacct/facct-turnoff.sh ${RPM_INSTALL_PREFIX1}/probe/psacct/psacct_probe.cron.sh ${RPM_INSTALL_PREFIX1}/probe/psacct/gratia-psacct ${RPM_INSTALL_PREFIX2}/rc.d/init.d/gratia-psacct
m&^/>& and print <<EOF;
    PSACCTFileRepository="$ENV{RPM_INSTALL_PREFIX1}/var/account/"
    PSACCTBackupFileRepository="$ENV{RPM_INSTALL_PREFIX1}/var/backup/"
    PSACCTExceptionsRepository="$ENV{RPM_INSTALL_PREFIX1}/logs/exceptions/"
EOF
m&^\s*VDTSetupFile\s*=& and next;
%configure_probeconfig_post -g Local

# Configure boot-time activation of accounting.
/sbin/chkconfig --add gratia-psacct
/sbin/chkconfig --level 35 gratia-psacct on

%max_pending_files_check psacct

# Configure crontab entry
%scrub_root_crontab
if %{__grep} -re 'psacct_probe.cron\.sh' -e 'PSACCTProbe\.py' \
        ${RPM_INSTALL_PREFIX2}/crontab ${RPM_INSTALL_PREFIX2}/cron.??* >/dev/null 2>&1; then
%{__cat} 1>&2 <<EOF


WARNING: non-standard installation of probe in ${RPM_INSTALL_PREFIX2}/crontab or ${RPM_INSTALL_PREFIX2}/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

%{__cat} >${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-psacct.cron <<EOF
$(( $RANDOM % 60 )) $(( $RANDOM % 24 )) * * * root \
"${RPM_INSTALL_PREFIX1}/probe/psacct/psacct_probe.cron.sh"
EOF

# Inform user of next step.
%{__cat} 1>&2 <<EOF

After configuring ${RPM_INSTALL_PREFIX1}/probe/psacct/ProbeConfig
invoke

${RPM_INSTALL_PREFIX2}/rc.d/init.d/gratia-psacct start

to start process accounting

EOF

# Deal with legacy Fermilab psacct configuration:
if %{__grep} -e 'fiscal/monacct\.log' >/dev/null 2>&1; then
  tmpfile=`mktemp /tmp/gratia-probe-psacct-post.XXXXXXXXXX`
  crontab -l 2>/dev/null | \
%{__grep} -v -e 'nite/acct\.log' \
        -e 'fiscal/monacct\.log' > "$tmpfile" 2>/dev/null
  crontab "$tmpfile" >/dev/null 2>&1
  echo "Shutting down facct service" 1>&2
  /sbin/chkconfig --del facct
  echo "

Execute 

${RPM_INSTALL_PREFIX1}/probe/psacct/facct-catchup --enable

to upload remaining information to Gratia. ProbeConfig should be
configured first and gratia-psacct started to avoid gaps in data." 1>&2
fi

%{__rm} -f "$tmpfile"

%preun psacct
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  %{__rm} -f ${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-psacct.cron
fi

%package condor%{?maybe_itb_suffix}
Summary: A Condor probe
Group: Applications/System
Requires: python >= 2.2
Requires: %{name}-common >= 0.12f
%{?config_itb:Obsoletes: %{name}-condor}
%{!?config_itb:Obsoletes: %{name}-condor%{itb_suffix}}

%description condor%{?maybe_itb_suffix}
The Condor probe for the Gratia OSG accounting system.

%files condor%{?maybe_itb_suffix}
%defattr(-,root,root,-)
%doc condor/README
%{default_prefix}/probe/condor/README
%{default_prefix}/probe/condor/gram_mods
%{default_prefix}/probe/condor/condor_meter.cron.sh
%{default_prefix}/probe/condor/condor_meter.pl
%config(noreplace) %{default_prefix}/probe/condor/ProbeConfig

%post condor%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"

%configure_probeconfig_pre -d condor -m condor
%configure_probeconfig_post

# Configure GRAM perl modules
vdt_setup_sh=`%{__perl} -ne 's&^\s*VDTSetupFile\s*=\s*\"([^\"]+)\".*$&$1& and print;' \
"${RPM_INSTALL_PREFIX1}/probe/condor/ProbeConfig"`
vdt_location=`dirname "$vdt_setup_sh"`

%{__grep} -e '\$condor_version_number' `%{__grep} -le 'log_to_gratia' \
"${RPM_INSTALL_PREFIX1}/../globus/lib/perl/Globus/GRAM/JobManager/condor.pm" \
"$vdt_location/globus/lib/perl/Globus/GRAM/JobManager/condor.pm" \
2>/dev/null` >/dev/null 2>&1
if (( $? != 0 )); then
%{__cat} 1>&2 <<\EOF

WARNING: please check that
${VDT_LOCATION}/globus/lib/perl/Globus/GRAM/JobManager/{condor,managedfork}.pm
contain *both* lines:
my $condor_version_number = 0;
sub log_to_gratia

If not, please either install VDT:Gratia-Patch using pacman, or see the
notes on the OSG accounting TWiki:

https://twiki.grid.iu.edu/bin/view/Accounting/ProbeConfigCondor#GratiaCondorGramPatch

EOF
fi

condor_pm="${RPM_INSTALL_PREFIX1}/../globus/lib/perl/Globus/GRAM/JobManager/condor.pm"
[[ -f "$condor_pm" ]] || \
condor_pm="$vdt_location/globus/lib/perl/Globus/GRAM/JobManager/condor.pm"

managedfork_pm="${RPM_INSTALL_PREFIX1}/../globus/lib/perl/Globus/GRAM/JobManager/managedfork.pm"
[[ -f "$managedfork_pm" ]] || \
managedfork_pm="$vdt_location/globus/lib/perl/Globus/GRAM/JobManager/managedfork.pm"

# Apply correctional patches
patch_script="${RPM_INSTALL_PREFIX1}/probe/condor/gram_mods/update_pm_in_place"
for jobmanager in "$condor_pm" "$managedfork_pm"; do
	[[ -x "$patch_script" ]] && [[ -w "$jobmanager" ]] && \
        perl -wi.gratia-`date +%Y%m%d` "$patch_script" "$jobmanager"
done

%max_pending_files_check condor

# Configure crontab entry
%scrub_root_crontab
if %{__grep} -re 'condor_meter.cron\.sh' -e 'condor_meter\.pl' \
        ${RPM_INSTALL_PREFIX2}/crontab ${RPM_INSTALL_PREFIX2}/cron.??* >/dev/null 2>&1; then
%{__cat} <<EOF 1>&2

WARNING: non-standard installation of probe in ${RPM_INSTALL_PREFIX2}/crontab or ${RPM_INSTALL_PREFIX2}/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

(( min = $RANDOM % 15 ))
%{__cat} >${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-condor.cron <<EOF
$min,$(( $min + 15 )),$(( $min + 30 )),$(( $min + 45 )) * * * * root \
"${RPM_INSTALL_PREFIX1}/probe/condor/condor_meter.cron.sh"
EOF

%preun condor%{?maybe_itb_suffix}
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  %{__rm} -f ${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-condor.cron
fi

%package sge%{?maybe_itb_suffix}
Summary: An SGE probe
Group: Applications/System
Requires: python >= 2.3
Requires: %{name}-common >= 0.12e
%{?config_itb:Obsoletes: %{name}-sge}
%{!?config_itb:Obsoletes: %{name}-sge%{itb_suffix}}

%description sge%{?maybe_itb_suffix}
The SGE probe for the Gratia OSG accounting system.

%files sge%{?maybe_itb_suffix}
%defattr(-,root,root,-)
%doc sge/README
%{default_prefix}/probe/sge/README
%{default_prefix}/probe/sge/sge_meter.cron.sh
%{default_prefix}/probe/sge/sge_meter.py
%{default_prefix}/probe/sge/test/2007-01-26.log.snippet
%config(noreplace) %{default_prefix}/probe/sge/ProbeConfig

%post sge%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"

%configure_probeconfig_pre -d sge -m sge
m&^/>& and print <<EOF;
    SGEAccountingFile=""
EOF
%configure_probeconfig_post

%max_pending_files_check sge

# Configure crontab entry
%scrub_root_crontab
if %{__grep} -re 'sge_meter.cron\.sh' -e 'sge\.py' \
        ${RPM_INSTALL_PREFIX2}/crontab ${RPM_INSTALL_PREFIX2}/cron.??* >/dev/null 2>&1; then
%{__cat} <<EOF 1>&2

WARNING: non-standard installation of probe in ${RPM_INSTALL_PREFIX2}/crontab or ${RPM_INSTALL_PREFIX2}/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

(( min = $RANDOM % 15 ))
%{__cat} >${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-sge.cron <<EOF
$min,$(( $min + 15 )),$(( $min + 30 )),$(( $min + 45 )) * * * * root \
"${RPM_INSTALL_PREFIX1}/probe/sge/sge_meter.cron.sh"
EOF

%preun sge%{?maybe_itb_suffix}
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  %{__rm} -f ${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-sge.cron
fi

%package glexec%{?maybe_itb_suffix}
Summary: A gLExec probe
Group: Applications/System
Requires: python >= 2.2
Requires: %{name}-common >= 0.12e
%{?config_itb:Obsoletes: %{name}-glexec}
%{!?config_itb:Obsoletes: %{name}-glexec%{itb_suffix}}
Obsoletes: fnal_gratia_glexec_probe

%description glexec%{?maybe_itb_suffix}
The gLExec probe for the Gratia OSG accounting system.

%files glexec%{?maybe_itb_suffix}
%defattr(-,root,root,-)
%doc glexec/README
%{default_prefix}/probe/glexec/README
%{default_prefix}/probe/glexec/glexec_meter.cron.sh
%{default_prefix}/probe/glexec/glexec_meter.py
%{default_prefix}/probe/glexec/gratia_glexec_parser.py
%config(noreplace) %{default_prefix}/probe/glexec/ProbeConfig

%post glexec%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"

%configure_probeconfig_pre -d glexec -m glexec
s&(CertificateFile\s*=\s*)\"[^\"]*\"&${1}"${RPM_INSTALL_PREFIX2}/grid-security/hostproxy.pem"&;
s&(KeyFile\s*=\s*)\"[^\"]*\"&${1}"${RPM_INSTALL_PREFIX2}/grid-security/hostproxykey.pem"&;
m&^/>& and print <<EOF;
    gLExecMonitorLog="/var/log/glexec/glexec_monitor.log"
EOF
%configure_probeconfig_post

%max_pending_files_check glexec

# Configure crontab entry
%scrub_root_crontab
if %{__grep} -re 'glexec_meter.cron\.sh' \
        ${RPM_INSTALL_PREFIX2}/crontab ${RPM_INSTALL_PREFIX2}/cron.??* >/dev/null 2>&1; then
%{__cat} <<EOF 1>&2

WARNING: non-standard installation of probe in ${RPM_INSTALL_PREFIX2}/crontab or ${RPM_INSTALL_PREFIX2}/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

(( min = $RANDOM % 15 ))
%{__cat} >${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-glexec.cron <<EOF
$min,$(( $min + 15 )),$(( $min + 30 )),$(( $min + 45 )) * * * * root \
"${RPM_INSTALL_PREFIX1}/probe/glexec/glexec_meter.cron.sh"
EOF

# End of gLExec post

%preun glexec%{?maybe_itb_suffix}
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  %{__rm} -f ${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-glexec.cron
fi
#   End of glExec preun
# End of gLExec section

%package metric%{?maybe_itb_suffix}
Summary: A probe for OSG metrics
Group: Applications/System
Requires: python >= 2.2
Requires: %{name}-common >= 0.25a
%{?config_itb:Obsoletes: %{name}-metric}
%{!?config_itb:Obsoletes: %{name}-metric%{itb_suffix}}

%description metric%{?maybe_itb_suffix}
The metric probe for the Gratia OSG accounting system.

%files metric%{?maybe_itb_suffix}
%defattr(-,root,root,-)
%doc metric/README
%doc metric/samplemetric.py
%{default_prefix}/probe/metric/README
%{default_prefix}/probe/metric/Metric.py
%{default_prefix}/probe/metric/samplemetric.py
%config(noreplace) %{default_prefix}/probe/metric/ProbeConfig

%post metric%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"

%configure_probeconfig_pre -d metric -m metric
s&(CertificateFile\s*=\s*)\"[^\"]*\"&${1}"${RPM_INSTALL_PREFIX2}/grid-security/hostproxy.pem"&;
s&(KeyFile\s*=\s*)\"[^\"]*\"&${1}"${RPM_INSTALL_PREFIX2}/grid-security/hostproxykey.pem"&;
m&^/>& and print <<EOF;
    metricMonitorLog="/var/log/metric/metric_monitor.log"
EOF
%configure_probeconfig_post

%max_pending_files_check metric

# End of metric post
# End of metric section

%package dCache-transfer%{?maybe_itb_suffix}
Summary: Gratia OSG accounting system probe for dCache billing.
Group: Application/System
Requires: %{name}-common >= 0.30
Requires: %{name}-extra-libs
Requires: %{name}-extra-libs-arch-spec
License: See LICENSE.
Obsoletes: %{name}-dCache
Obsoletes: %{name}-dCache%{itb_suffix}
%{?config_itb:Obsoletes: %{name}-dCache-transfer}
%{!?config_itb:Obsoletes: %{name}-dCache-transfer%{itb_suffix}}

%description dCache-transfer%{?maybe_itb_suffix}
Gratia OSG accounting system probe for dCache transfers.
Contributed by Greg Sharp and the dCache project.

%files dCache-transfer%{?maybe_itb_suffix}
%defattr(-,root,root,-)
/etc/rc.d/init.d/gratia-dcache-transfer-probe
%{default_prefix}/probe/dCache-transfer/README
%{default_prefix}/probe/dCache-transfer/Alarm.py
%{default_prefix}/probe/dCache-transfer/Checkpoint.py
%{default_prefix}/probe/dCache-transfer/CheckpointTest.py
%{default_prefix}/probe/dCache-transfer/DCacheAggregator.py
%{default_prefix}/probe/dCache-transfer/dCacheBillingAggregator.py
%config(noreplace) %{default_prefix}/probe/dCache-transfer/ProbeConfig

%post dCache-transfer%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"
# /etc -> "${RPM_INSTALL_PREFIX2}"

# Configure ProbeConfig
%configure_probeconfig_pre -d dCache-transfer -m dcache-transfer
m&^/>& and print <<EOF;
    UpdateFrequency="120"
    DBHostName="localhost"
    DBLoginName="srmdcache"
    DBPassword="srmdcache"
    StopFileName="stopGratiaFeed"
    DCacheServerHost="BILLING_HOST"
    EmailServerHost="localhost"
    EmailFromAddress="dCacheProbe@localhost"
    EmailToList=""
    AggrLogLevel="warn"
EOF
%configure_probeconfig_post

# Configure init script
perl -wani.bak -e 'if (s&^(PROBE_DIR=).*$&$1'"${RPM_INSTALL_PREFIX1}"'/probe/dCache-transfer&) {
  print;
  print <<'"'"'EOF'"'"';
arch_spec_dir=${PROBE_DIR}/../lib.*
if test -n "$PYTHONPATH" ; then
  if echo "$PYTHONPATH" | grep -e '"'"':$'"'"' >/dev/null 2>&1; then
    PYTHONPATH="${PYTHONPATH}${PROBE_DIR}/../common:${arch_spec_dir}:"
  else
    PYTHONPATH="${PYTHONPATH}:${PROBE_DIR}/../common:${arch_spec_dir}"
  fi
else
  PYTHONPATH="${PROBE_DIR}/../common:${arch_spec_dir}"
fi
export PYTHONPATH
EOF
  next;
}
s&gratia-d?cache-probe&gratia-dcache-transfer-probe&g;
s&python &%{pexec} &g;
print;
' "${RPM_INSTALL_PREFIX2}/rc.d/init.d/gratia-dcache-transfer-probe"

# Activate init script
/sbin/chkconfig --add gratia-dcache-transfer-probe

# Activate it
service gratia-dcache-transfer-probe start

%max_pending_files_check dCache-transfer

# End of dCache-transfer post
# End of dCache-transfer section

%package dCache-storage%{?maybe_itb_suffix}
Summary: Gratia OSG accounting system probe for dCache storage.
Group: Application/System
Requires: %{name}-common >= 0.30
Requires: %{name}-extra-libs
Requires: %{name}-extra-libs-arch-spec
License: See LICENSE.
%{?config_itb:Obsoletes: %{name}-dCache-storage}
%{!?config_itb:Obsoletes: %{name}-dCache-storage%{itb_suffix}}

%description dCache-storage%{?maybe_itb_suffix}
Gratia OSG accounting system probe for available space in dCache.
Contributed by Greg Sharp and the dCache project.

%files dCache-storage%{?maybe_itb_suffix}
%defattr(-,root,root,-)
%{default_prefix}/probe/dCache-storage/README
%{default_prefix}/probe/dCache-storage/dcacheStorageMeter.py
%{default_prefix}/probe/dCache-storage/dCache-storage_meter.cron.sh
%config(noreplace) %{default_prefix}/probe/dCache-storage/ProbeConfig

%post dCache-storage%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"

%configure_probeconfig_pre -d dCache-storage -m dcache-storage
m&^/>& and print <<EOF;
    DBHostName="localhost"
    DBLoginName="srmdcache"
    DBPassword="srmdcache"
    AdminSvrPort="22223"
    AdminSvrLogin="admin"
    AdminSvrPassword="ADMIN_SVR_PASSWORD"
    DCacheServerHost="POSTGRES_HOST"
    DcacheLogLevel="debug"
EOF
%configure_probeconfig_post

perl -wapi.bak -e 's&^python &%{pexec} &g' \
"${RPM_INSTALL_PREFIX1}"/probe/dCache-storage/dCache-storage_meter.cron.sh

%max_pending_files_check dCache-storage

# Configure crontab entry
%scrub_root_crontab
if %{__grep} -re '_meter.cron\.sh' \
        ${RPM_INSTALL_PREFIX2}/crontab ${RPM_INSTALL_PREFIX2}/cron.??* >/dev/null 2>&1; then
%{__cat} <<EOF 1>&2

WARNING: non-standard installation of probe in ${RPM_INSTALL_PREFIX2}/crontab or ${RPM_INSTALL_PREFIX2}/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

(( min = $RANDOM % 60 ))
%{__cat} >${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-dcache-storage.cron <<EOF
$min * * * * root \
"${RPM_INSTALL_PREFIX1}/probe/dCache-storage/dCache-storage_meter.cron.sh"
EOF

# End of dCache-storage post

%preun dCache-storage%{?maybe_itb_suffix}
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  %{__rm} -f ${RPM_INSTALL_PREFIX2}/cron.d/gratia-probe-dcache-storage.cron
fi
#   End of dCache-storage preun
# End of dCache-storage section

%endif

%changelog
* Mon Jan 22 2008 Christopher Green <greenc@fnal.gov> - 0.30d-1
- Parser is a whole lot careful for LSF files, and more efficient for
  both PBS and LSF.
- Re-order unpacking of gratia/probe/dCache-storage vs the provided tar
  file to allow files to be overrwritten.
- Fix version matching in Condor jobmanager patches.

* Mon Jan 14 2008 Christopher Green <greenc@fnal.gov> - 0.30c-1
- Quick fix for last line in file missing newline due to race with batch
  system.

* Mon Jan  7 2008 Christopher Green <greenc@fnal.gov> - 0.30b-3
- Fix crontab removal problems in multiple preun statements.
- Add missing preun to gratia-storage.

* Fri Dec 14 2007 Christopher Green <greenc@fnal.gov> - 0.30b-2
- Remove debug statements from build.

* Fri Dec 14 2007 Christopher Green <greenc@fnal.gov> - 0.30b-1
- Allow for non-standard name of python exec.
- Fix directory problems in dCache-storage_meter.cron.sh.
- Fix cron install for dCache-storage.
- Add disclaimer to README file for dCache-transfer.

* Thu Dec 13 2007 Christopher Green <greenc@fnal.gov> - 0.30a-2
- Upon request, dCache probe is renamed to dCache-transfer.

* Mon Dec 10 2007 Christopher Green <greenc@fnal.gov> - 0.30a-1
- Better code reuse in scriptlets.
- Package dCache probes and associated third party libraries.
- Better method of naming temporary XML files prior to upload.

* Tue Oct 16 2007 Christopher Green <greenc@fnal.gov> - 0.27.5c-1
- Correct handling of suppressed records.

* Thu Oct  4 2007 Christopher Green <greenc@fnal.gov> - 0.27.5b-1
- Fix location of DebugPrint.py for PBS error conditions.

* Mon Sep 24 2007 Christopher Green <greenc@fnal.gov> - 0.27.5a-1
- Remove bad debug message in Gratia.py.
- Fix encoding behavior in Gratia.py.
- Fix dangerous behavior in debug mode in condor_meter.pl.

* Tue Sep 11 2007 Christopher Green <greenc@fnal.gov> - 0.27.3-1
- Match collector version bump.

* Mon Sep 10 2007 Christopher Green <greenc@fnal.gov> - 0.27.2a-1
- Better redirection of non-managed output.

* Mon Sep 10 2007 Christopher Green <greenc@fnal.gov> - 0.27.2-1
- Handshaking facility with collector.
- Gratia.py can handle larger numbers for time durations.
- URLencoding and XML escaping (backward compatible with old collectors).

* Mon Aug  6 2007 Christopher Green <greenc@fnal.gov> - 0.26.2b-1
- /bin/env -> /usr/bin/env in pound-bang line.

* Fri Aug  3 2007 Christopher Green <greenc@fnal.gov> - 0.26.2a-1
- Fix crontab entries to include user.
- Fix and improve DebugPring.py logging utility.
- Fix PBS probe logging.

* Thu Jul 19 2007 Christopher Green <greenc@fnal.gov> - 0.26-2
- Fix Grid assignment for psacct probe.

* Wed Jul 18 2007 Christopher Green <greenc@fnal.gov> - 0.26-1
- Configure Grid attribute appropriately in new ProbeConfig files.
- Fix Metric probe configuration of port.

* Wed Jul 11 2007 Christopher Green <greenc@fnal.gov> - 0.25a-1
- Correct Gratia.py to generate correct XML for Grid attribute.
- Take account of Gratia.py changes in Metric.py.
- Remove unnecessary Obsoletes clause from metric package.

* Tue Jul  3 2007 Christopher Green <greenc@fnal.gov> - 0.25-1
- First release of metric probe.

* Mon Jun 18 2007 Christopher Green <greenc@fnal.gov> - 0.24b-3
- Added define _unpackaged_files_terminate_build 0 to prevent python
-  files being byte-compiled without being put into the files list.

* Mon Jun 18 2007 Christopher Green <greenc@fnal.gov> - 0.24b-2
- Fix patch application.

* Mon Jun 18 2007 Christopher Green <greenc@fnal.gov> - 0.24b-1
- Remove accidental 'percent'global in changelog causing complaints.
- Patch xmlUtil.h to compile under gcc4.1's fixed friend injection rules.

* Fri Jun 15 2007 Christopher Green <greenc@fnal.gov> - 0.24a-1
- Fix problem with sge_meter_cron.sh per Shreyas Cholia

* Thu Jun 14 2007 Christopher Green <greenc@fnal.gov> - 0.24-1
- Sync with service release no.
- Incorporate latest changes to SGE probe from Shreyas.
- Fix URL in probe/sge/README per Shreyas.

* Thu Jun 14 2007 Christopher Green <greenc@fnal.gov> - 0.23b-1
- Extra safety checks on document integrity.
- Correct spelling of metricRecord.

* Wed Jun 13 2007 Christopher Green <greenc@fnal.gov> - 0.23a-1
- Fix various and sundry problems with abstractions of XML checking
 	routines.

* Wed Jun 13 2007 Christopher Green <greenc@fnal.gov> - 0.23-1
- Redirect urCollector.pl output to log file from pbs-lsf_meter.cron.sh.
- Gratia.py handles new "Grid" attribute.
- Updated release no.

* Tue Jun 12 2007 Christopher Green <greenc@fnal.gov> - 0.22d-4
- More variables declared global to fix funny behavior.
- glexec probe does not require python 2.3 -- erroneously copied from SGE.
- final_post_message only prints out if it's a ProbeConfig file.

* Fri May 25 2007 Christopher Green <greenc@fnal.gov> - 0.22d-1
- New utilites GetProbeConfigAttribute.py and DebugPrint.py.
- Cron scripts now check if they are enabled in ProbeConfig before
	running the probe.

* Thu May 24 2007 Christopher Green <greenc@fnal.gov> - 0.22c-1
- Correct minor problems with glexec probe.

* Thu May 24 2007 Christopher Green <greenc@fnal.gov> - 0.22b-2
- Swap to using /etc/cron.d and clean up root's crontab.

* Fri May 18 2007 Christopher Green <greenc@fnal.gov> - 0.22b-1
- Fix condor_meter.pl problems discovered during testing.
- uname -n => hostname -f.
- When installing in FNAL domain, default collector is FNAL.

* Thu May 17 2007 Christopher Green <greenc@fnal.gov> - 0.22a-2
- re-vamp post to handle FNAL-local collector configurations.

* Thu May 17 2007 Christopher Green <greenc@fnal.gov> - 0.22a-1
- Condor probe now looks in old history files if necessary.
- condor_history check only done once per invocation instead of once per job.

* Wed May  9 2007 Christopher Green <greenc@fnal.gov> - 0.20a-1
- Consolidation release.
- Addition of gLExec probe to suite.
- Yum repository config file.

* Wed Apr  4 2007 Christopher Green <greenc@fnal.gov> - 0.12k-0
- Pre-release for testing and emergency deployment only.

* Fri Feb  9 2007 Chris Green <greenc@fnal.gov> - 0.12i-1
- Fix reported problem with PBS probe.
- Make requested change to maximum backoff delay.

* Fri Feb  9 2007 Chris Green <greenc@fnal.gov> - 0.12h-1
- ResetAndRetry mechanism altered to geometric backoff delay up to 1
  hour.
- Suspension of reprocessing on connect failure now works as desired.
- Reprocessing gets re-done on successful re-connect.
- LICENSE file now part of main pbs-lsf directory as well as the docs.
- URL pointers to TWiki updated to new secure URLs.

* Wed Feb  7 2007 Chris Green <greenc@fnal.gov> - 0.12g-1
- Records now have a ResourceType: batch, rawCPU or storage.
- ResetAndRetry mechanism for continuously-running probes.
- Stats now include failed reprocess attempts.
- New naming scheme for backup files distinguishes different probes
  running on the same node.
- Fix minor internal problems with XML prefix parsing.
- VOName and ReportableVOName keys should not be in the XML record if
  they are empty.
- Preserve type of Record.XmlData

* Fri Feb  2 2007 Chris Green <greenc@fnal.gov> - 0.12f-1
- SGE probe requires python v2.3 or better -- put check in code as well
  as RPM requirements.
- SGE probe now uses DebugPrint instead of straight print.
- Use xml.dom for XML parsing where appropriate.
- Cope with multiple usage records in one XML packet.
- Optional suppression of records with no VOName.
- Python version checking and handling of libraries that behave
  differently in different versions.
- Psacct probe now more intelligent about memory use for large
  accounting files.

* Mon Jan 29 2007 Chris Green <greenc@fnal.gov> - 0.12e-1
- Keep track of suppressed, failed and successfully sent records
  separately.
- Better logging and error output.
- Public ProbeConfiguration.getConfigAttribute(attribute) method.
- New probe for SGE batch system.

* Fri Jan  5 2007 Chris Green <greenc@fnal.gov> - 0.12d-1
- Fix problems with user-vo-name lookup under pbs-lsf.
- Try to be more robust against not finding top of VDT distribution.
- Honor request for crontab to not redirect output; and for crontab line
   to be POSIX-compliant (/ notation for stepping is apparently a
   vixie-cron extension).
- Tweak ProbeConfigTemplate to suppress all but real errors in
  stdout/stderr.

* Thu Jan  4 2007 Chris Green <greenc@fnal.gov> - 0.12c-1
- Fix a couple of bugs affecting pbs-lsf.

* Thu Jan  4 2007 Chris Green <greenc@fnal.gov> - 0.12b-1
- README files now mainly vestigial and refer to TWiki.
- Fix various minor bugs in Gratia.py.
- Fix two annoying (but minor) bugs in condor_history capability check.
- Add db-find-job test script to common package.
- Removed unnecessary Clarens.py.
- Removed README-facct-migration (see TWiki docs for this information).

* Wed Dec 20 2006 Chris Green <greenc@fnal.gov> - 0.12a-1
- Upgrade version to match tag.
- Processing of backlog files is now much more efficient.
- Better handling of large backlog and MaxPendingFiles config option.
- New default value of MaxPendingFiles of 100K.
- Eliminate errors if we exit before full initialization.
- Reprocess is now done as part of initialization.

* Wed Dec 13 2006 Chris Green <greenc@fnal.gov> - 0.11f-2
- Better application of GRAM patches where gratia is not installed under
  $VDT_LOCATION.

* Wed Dec 13 2006 Chris Green <greenc@fnal.gov> - 0.11f-1
- Better correction to GRAM patches.

* Tue Dec 12 2006 Chris Green <greenc@fnal.gov> - 0.11e-1
- Correct GRAM patch problem.
- post install now corrects (but does not install) GRAM patches if appropriate.
- Gratia.py now supports automatic user->VO translation for those probes
  which allow Gratia.py routines to construct the XML (if it can find a
  reverse mapfile). This does not apply to probes which upload a pre-made XML
  blob such as the pbs-lsf probe.
- UserVOMapFile key added to ProbeConfigTemplate.
- Correct patch check.
- Probes don't require *exactly* the same version of the gratia-probe-common
  RPM, so this can be upgraded in isolation if necessary.

* Fri Dec  8 2006 Chris Green <greenc@fnal.gov> - 0.11d-1
- GRAM patches tweaked slightly.
- Gratia.py updated to offer VOfromUser(user) function, returning a
  [ voi, VOc ] pair based on a username -- uses a local copy of the
  grid3-user-vo-map.txt file.

* Mon Nov 20 2006 Chris Green <greenc@fnal.gov> - 0.11b-1
- Improve documentation for GRAM script patches.

* Mon Nov 20 2006 Chris Green <greenc@fnal.gov> - 0.11a-1
- New option UseSyslog.
- New option LogRotate.
- condor.pl only uses -backwards and -match options to condor_history if
  they are supported.
- More robust GRAM patches.

* Thu Oct 19 2006 Chris Green <greenc@fnal.gov> - 0.10c-2
- Change escaping of site_name macro internally for more robustness.

* Thu Oct 19 2006 Chris Green <greenc@fnal.gov> - 0.10c-1
- Remove unnecessary VDTSetup line from psacct ProbeConfig file.
- Remove version no. from README files.
- new doc README-facct-migration for psacct.

* Wed Oct 18 2006 Chris Green <greenc@fnal.gov> - 0.10b-2
- meter_name and site_name are now configurable macros.

* Mon Oct 16 2006 Chris Green <greenc@fnal.gov> - 0.10a-1
- Robustness updates for connection handling.

* Wed Oct 11 2006  <greenc@fnal.gov> - 0.10-1
- Make sure that the end time is correct even when processing more than
one day worth of raw data (PSACCTProbeLib.py).

* Fri Oct  6 2006  <greenc@fnal.gov> - 0.9m-1
- Separate routines out of urCollector into Perl Modules, and use them
in a perl Gratia probe for pbs-lsf.
- Remove gratia-addin patch: call Gratia probe from outside
urCollector.pl and use perl modules to read configuration file.

* Wed Oct  4 2006  <greenc@fnal.gov> - 0.9l-2
- Processor count set to 1 if it's not anything else.

* Wed Oct  4 2006  <greenc@fnal.gov> - 0.9l-1
- urCollector now looks at nodect in addition to neednodes.

* Fri Sep 29 2006  <greenc@fnal.gov> - 0.9k-1
- Add method to Gratia.py to set VOName in the record.
- Remove debug statements printing direct to screen in Gratia.py.
- Disconnect at exit using sys.exitfunc in Gratia.py.
- Remove obsolete reference to jclarens in disconnect debug message in
Gratia.py.

* Fri Sep 22 2006  <greenc@fnal.gov> - 0.9j-1
- Fix problem with StartTime / EndTime in ps-accounting probe.

* Fri Sep 22 2006  <greenc@fnal.gov> - 0.9i-1
- Gratia.py had some strange response code logic for non-default
transaction methods: added automatic setting of code based on message if
supplied code is -1.
- Fix thinko in ProbeConfigTemplate.

* Thu Sep 21 2006  <greenc@fnal.gov> - 0.9h-1
- Turn off soap for non-SSL connections.

* Thu Sep 21 2006  <greenc@fnal.gov> - 0.9g-2
- Add patch to fix timezone problem for createTime in urCollector.pl.

* Wed Sep 20 2006  <greenc@fnal.gov> - 0.9g-1
- Update version number for improved condor probe.
- Only replace MAGIC_VDT_LOCATION in VDTSetup.sh if vdt_loc was
explicitly set.

* Tue Sep 19 2006  <greenc@fnal.gov> - 0.9f-3
- SiteName should be pretty (not the node name), so use OSG_SITE_NAME.

* Mon Sep 18 2006  <greenc@fnal.gov> - 0.9f-2
- Allow for build-time setting of VDT location.
- Set MeterName and SiteName in post for fresh installs.

* Fri Sep 15 2006  <greenc@fnal.gov> - 0.9f-1
- Moved psacct-specific items out of ProbeConfigTemplate and into post.
- Fixed sundry minor problems in psacct_probe.cron.sh: missing export of
PYTHONPATH, typo (psaact -> psacct). Also only attempt to copy old
PSACCT admin file if it exists, and assume gratia/var/data already
exists (in common RPM).
- SOAPHost changes in post need enclosing quotes

* Thu Sep 14 2006  <greenc@fnal.gov> - 0.9e-2
- Correct typo in psacct post-install message.

* Wed Sep 13 2006  <greenc@fnal.gov> - 0.9e-1
- Reprocess() and __disconnect() were at the wrong indent level --
should be outside the loop.

* Wed Sep 13 2006  <greenc@fnal.gov> - 0.9d-2
- Split post-install sections for configuring urCollector.conf and
ProbeConfig.
- Changed jobPerTimeInterval and timeInterval to make catching up on a
backlog much faster.

* Mon Sep 11 2006  <greenc@fnal.gov> - 0.9d-1
- ITB-specific RPMS with preconfigured port.
- Updated README files.
- Replaced as many UNIX commands as possible with %%{__cmd} macros
 
* Fri Sep  8 2006  <greenc@fnal.gov> - 0.9c-2
- Patch to urCollector for parsing corner cases (work with Rosario).

* Wed Sep  6 2006  <greenc@fnal.gov> - 0.9c-1
- New patch for urCollector to invoke gratia probe.
- Gratia.py enhancements to handle pre-made XML files.
- Cron script for pbs-lsf probe.
- Fix preun scripts for hysteresis problem during RPM upgrades.

* Wed Aug 30 2006  <greenc@fnal.gov> - 0.9b-4
- Condor probe should run every 15 minutes, not once per day.

* Tue Aug 29 2006  <greenc@fnal.gov> - 0.9b-3
- Revised doc entries and simplified (!) install section.
- Corrected path in log_to_gratia check in condor post.
- Corrected handling of /etc/rc.d/init.d/gratia-psacct in file list and
post.
- Improved description for pbs-lsf probe.

* Mon Aug 28 2006 <greenc@fnal.gov> - 0.9b-2
- Specfile revised for arch-specific pbs-lsf package adapted from EGEE's
urCollector package. NOTE double build now required with and without
"--target noarch" option

* Wed Aug 23 2006  <greenc@fnal.gov> - 0.9b-1
- Documentation updates
- Minor change to condor_meter.pl from Philippe

* Tue Aug 15 2006  <greenc@fnal.gov> - 0.9a-1
- Initial build.
