Name: gratia-probe
Summary: Gratia OSG accounting system probes
Group: Applications/System
Version: 0.9g
Release: 2
License: GPL
Group: Applications/System
URL: http://sourceforge.net/projects/gratia/
Packager: Chris Green <greenc@fnal.gov>
Vendor: The Open Science Grid <http://www.opensciencegrid.org/>

%define ProbeConfig_template_marker <!-- Temporary RPM-generated template marker -->
%define pbs_lsf_template_marker # Temporary RPM-generated template marker
%define urCollector_version 2006-06-13
%define itb_suffix -itb

%{?config_itb: %define maybe_itb_suffix %{itb_suffix}}
%{?config_itb: %define itb_soaphost_config s&^(\\s*SOAPHost\\s*=\\s*).*$&${1}"gratia-osg.fnal.gov:8881"&;}

%{?vdt_loc: %define vdt_loc_set 1}
%{!?vdt_loc: %define vdt_loc /opt/vdt}
%{!?default_prefix: %define default_prefix %{vdt_loc}/gratia}

%define osg_attr %{vdt_loc}/monitoring/osg-attributes.conf
%define site_name "$( ( if [[ -r \"%{osg_attr}\" ]]; then . \"%{osg_attr}\" ; echo \"${OSG_SITE_NAME}\"; else echo \"Generic Site\"; fi ) )"

Source0: %{name}-common-%{version}.tar.bz2
Source1: %{name}-condor-%{version}.tar.bz2
Source2: %{name}-psacct-%{version}.tar.bz2
Source3: %{name}-pbs-lsf-%{version}.tar.bz2
Source4: urCollector-%{urCollector_version}.tgz
Patch0: urCollector-2006-06-13-pcanal-fixes-1.patch
Patch1: urCollector-2006-06-13-gratia-addin-1.patch
Patch2: urCollector-2006-06-13-greenc-fixes-1.patch
Patch3: urCollector-2006-06-13-createTime-timezone.patch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

Prefix: /usr
Prefix: %{default_prefix}

%prep
%setup -q -c
%setup -q -D -T -a 1
%setup -q -D -T -a 2
%ifnarch noarch
%setup -q -D -T -a 3
%setup -q -D -T -a 4
cd urCollector-%{urCollector_version}
%patch -P 0 -p1 -b .pcanal-fixes-1
%patch -P 1 -b .gratia-addin-1
%patch -P 2 -b .greenc-fixes-1
%patch -P 3 -b .createTime-timezone-1
%endif

%build
%ifnarch noarch
cd urCollector-%{urCollector_version}
%{__make} clean
%{__make}
cd -
%endif

%install
# Setup
%{__rm} -rf "${RPM_BUILD_ROOT}"
%{__mkdir_p} "${RPM_BUILD_ROOT}%{default_prefix}/probe"

%ifarch noarch
  # Obtain files
  %{__cp} -pR {common,condor,psacct} "${RPM_BUILD_ROOT}%{default_prefix}/probe"

  # Get uncustomized ProbeConfigTemplate files (see post below)
  for probe_config in \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/condor/ProbeConfig" \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/psacct/ProbeConfig" \
      ; do
    %{__cp} -p "common/ProbeConfigTemplate" "$probe_config"
    echo "%{ProbeConfig_template_marker}" >> "$probe_config"
  done

%else
  %{__cp} -pR pbs-lsf "${RPM_BUILD_ROOT}%{default_prefix}/probe"

  # Get uncustomized ProbeConfigTemplate file (see post below)
  for probe_config in \
      "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/ProbeConfig" \
      ; do
    %{__cp} -p "common/ProbeConfigTemplate" \
          "$probe_config"
    echo "%{ProbeConfig_template_marker}" >> "$probe_config"
  done

  # Get urCollector software
  cd urCollector-%{urCollector_version}
  %{__cp} -p urCreator urCollector.pl \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf"
  %{__cp} -p urCollector.conf-template \
  "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/urCollector.conf"
  echo "%{pbs_lsf_template_marker}" >> \
       "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf/urCollector.conf"

  cd "${RPM_BUILD_ROOT}%{default_prefix}/probe/pbs-lsf"
  %{__ln_s} . etc
  %{__ln_s} . libexec
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
%package pbs-lsf%{?maybe_itb_suffix}
Summary: Gratia OSG accounting system probe for PBS and LSF batch systems.
Group: Application/System
Requires: %{name}-common = %{version}
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
%{default_prefix}/probe/pbs-lsf/pbs-lsf.py
%{default_prefix}/probe/pbs-lsf/pbs-lsf_meter.cron.sh
%{default_prefix}/probe/pbs-lsf/urCreator
%{default_prefix}/probe/pbs-lsf/urCollector.pl
%{default_prefix}/probe/pbs-lsf/etc
%{default_prefix}/probe/pbs-lsf/libexec
%config(noreplace) %{default_prefix}/probe/pbs-lsf/urCollector.conf
%config(noreplace) %{default_prefix}/probe/pbs-lsf/ProbeConfig

%post pbs-lsf%{?maybe_itb_suffix}
# /usr -> "${RPM_INSTALL_PREFIX0}"
# %{default_prefix} -> "${RPM_INSTALL_PREFIX1}"

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

# Configure ProbeConfig
%{__cat} <<EOF | while read config_file; do
`%{__grep} -le '^%{ProbeConfig_template_marker}$' \
"${RPM_INSTALL_PREFIX1}"/probe/pbs-lsf/ProbeConfig{,.rpmnew} \
2>/dev/null`
EOF
test -n "$config_file" || continue
%{__perl} -wni.orig -e \
'
s&MAGIC_VDT_LOCATION/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
%{?vdt_loc_set: s&MAGIC_VDT_LOCATION&%{vdt_loc}&;}
s&/opt/vdt/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
%{?itb_soaphost_config}
s&(MeterName\s*=\s*)\"[^\"]*\"&${1}"pbs-lsf:'`uname -n`'"&;
s&(SiteName\s*=\s*)\"[^\"]*\"&${1}"'%{site_name}'"&;
m&%{ProbeConfig_template_marker}& or print;
' \
"$config_file" >/dev/null 2>&1
done

# Configure crontab entry
if %{__grep} -re 'pbs-lsf_meter.cron\.sh' \
        /etc/crontab /etc/cron.* >/dev/null 2>&1; then
%{__cat} <<EOF 1>&2

WARNING: non-standard installation of probe in /etc/crontab or /etc/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

tmpfile=`mktemp /tmp/gratia-probe-pbs-lsf-post.XXXXXXXXXX`
crontab -l 2>/dev/null | \
%{__grep} -v -e 'pbs-lsf_meter.cron\.sh' > "$tmpfile" 2>/dev/null
%{__cat} >>"$tmpfile" <<EOF
$(( $RANDOM % 15 ))-59/15 * * * * \
"${RPM_INSTALL_PREFIX1}/probe/pbs-lsf/pbs-lsf_meter.cron.sh" > \
"${RPM_INSTALL_PREFIX1}/var/logs/gratia-probe-pbs-lsf.log" 2>&1
EOF

crontab "$tmpfile" >/dev/null 2>&1
rm -f "$tmpfile"

%preun pbs-lsf%{?maybe_itb_suffix}
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  # Remove crontab entry
  tmpfile=`mktemp /tmp/gratia-probe-pbs-lsf-post.XXXXXXXXXX`
  crontab -l 2>/dev/null | \
  %{__grep} -v -e 'pbs-lsf_meter.cron\.sh' > "$tmpfile" 2>/dev/null
  if test -s "$tmpfile"; then
    crontab "$tmpfile" >/dev/null 2>&1
  else
    crontab -r
  fi
  rm -f "$tmpfile"
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
%doc common/ProbeConfigTemplate
%{default_prefix}/probe/common/README
%{default_prefix}/probe/common/samplemeter.pl
%{default_prefix}/probe/common/samplemeter.py
%{default_prefix}/probe/common/ProbeConfigTemplate
%{default_prefix}/probe/common/Clarens.py
%{default_prefix}/probe/common/Gratia.py
%{default_prefix}/probe/common/RegisterProbe.py

%package psacct
Summary: A ps-accounting probe
Group: Applications/System
Requires: python >= 2.2
Requires: psacct
Requires: %{name}-common = %{version}

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
%{__cat} <<EOF | while read config_file; do
`%{__grep} -le '^%{ProbeConfig_template_marker}$' \
"${RPM_INSTALL_PREFIX1}"/probe/psacct/ProbeConfig{,.rpmnew} \
2>/dev/null`
${RPM_INSTALL_PREFIX1}/probe/psacct/facct-catchup
${RPM_INSTALL_PREFIX1}/probe/psacct/facct-turnoff.sh
${RPM_INSTALL_PREFIX1}/probe/psacct/psacct_probe.cron.sh
${RPM_INSTALL_PREFIX1}/probe/psacct/gratia-psacct
/etc/rc.d/init.d/gratia-psacct
EOF
test -n "$config_file" || continue
%{__perl} -wni.orig -e \
'
s&^(\s*SOAPHost\s*=\s*).*$&${1}"gratia-fermi.fnal.gov:8882"&;
s&gratia-osg\.fnal\.gov$&gratia-fermi.fnal.gov&;
s&MAGIC_VDT_LOCATION/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
%{?vdt_loc_set: s&MAGIC_VDT_LOCATION&%{vdt_loc}&;}
s&/opt/vdt/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
s&(MeterName\s*=\s*)\"[^\"]*\"&${1}"psacct:'`uname -n`'"&;
s&(SiteName\s*=\s*)\"[^\"]*\"&${1}"'%{site_name}'"&;
m&^/>& and print <<EOF;
    PSACCTFileRepository="$ENV{RPM_INSTALL_PREFIX1}/var/account/"
    PSACCTBackupFileRepository="$ENV{RPM_INSTALL_PREFIX1}/var/backup/"
    PSACCTExceptionsRepository="$ENV{RPM_INSTALL_PREFIX1}/logs/exceptions/"
EOF
m&%{ProbeConfig_template_marker}& or print;' \
"$config_file"
done

# Configure boot-time activation of accounting.
/sbin/chkconfig --add gratia-psacct
/sbin/chkconfig --level 35 gratia-psacct on

# Configure crontab entry
if %{__grep} -re 'psacct_probe.cron\.sh' -e 'PSACCTProbe\.py' \
        /etc/crontab /etc/cron.* >/dev/null 2>&1; then
%{__cat} 1>&2 <<EOF


WARNING: non-standard installation of probe in /etc/crontab or /etc/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

tmpfile=`mktemp /tmp/gratia-probe-psacct-post.XXXXXXXXXX`
crontab -l 2>/dev/null | \
%{__grep} -v -e 'psacct_probe.cron\.sh' \
        -e 'PSACCTProbe\.py' > "$tmpfile" 2>/dev/null
%{__cat} >>"$tmpfile" <<EOF
$(( $RANDOM % 60 )) $(( $RANDOM % 24 )) * * * \
"${RPM_INSTALL_PREFIX1}/probe/psacct/psacct_probe.cron.sh" > \
"${RPM_INSTALL_PREFIX1}/var/logs/gratia-probe-psacct.log" 2>&1
EOF

crontab "$tmpfile" >/dev/null 2>&1
rm -f "$tmpfile"

# Inform user of next step.
%{__cat} 1>&2 <<EOF

After configuring ${RPM_INSTALL_PREFIX1}/probe/psacct/ProbeConfig
invoke

/etc/rc.d/init.d/gratia-psacct start

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
  chkconfig --del facct
  echo "

Execute 

${RPM_INSTALL_PREFIX1}/probe/psacct/facct-catchup --enable

to upload remaining information to Gratia. ProbeConfig should be
configured first and gratia-psacct started to avoid gaps in data." 1>&2
fi

rm -f "$tmpfile"

%preun psacct
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  # Remove crontab entry
  tmpfile=`mktemp /tmp/gratia-probe-psacct-post.XXXXXXXXXX`
  crontab -l 2>/dev/null | \
  %{__grep} -v -e 'psacct_probe.cron\.sh' \
          -e 'PSACCTProbe\.py' > "$tmpfile" 2>/dev/null
  if test -s "$tmpfile"; then
    crontab "$tmpfile" >/dev/null 2>&1
  else
    crontab -r
  fi
  rm -f "$tmpfile"
fi

%package condor%{?maybe_itb_suffix}
Summary: A Condor probe
Group: Applications/System
Requires: python >= 2.2
Requires: %{name}-common = %{version}
%{?config_itb:Obsoletes: %{name}-condor}
%{!?config_itb:Obsoletes: %{name}-condor%{itb_suffix}}

%description condor%{?maybe_itb_suffix}
The condor probe for the Gratia OSG accounting system.

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
%{__cat} <<EOF | while read config_file; do
`%{__grep} -le '^%{ProbeConfig_template_marker}$' \
"${RPM_INSTALL_PREFIX1}"/probe/condor/ProbeConfig{,.rpmnew} \
2>/dev/null`
EOF
test -n "$config_file" || continue
%{__perl} -wni.orig -e \
'
s&MAGIC_VDT_LOCATION/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
%{?vdt_loc_set: s&MAGIC_VDT_LOCATION&%{vdt_loc}&;}
s&/opt/vdt/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
%{?itb_soaphost_config}
s&(MeterName\s*=\s*)\"[^\"]*\"&${1}"condor:'`uname -n`'"&;
s&(SiteName\s*=\s*)\"[^\"]*\"&${1}"'%{site_name}'"&;
m&%{ProbeConfig_template_marker}& or print;' \
"$config_file" >/dev/null 2>&1
done

# Configure GRAM perl modules
if ! %{__grep} -e 'log_to_gratia' \
"${RPM_INSTALL_PREFIX1}/../globus/lib/perl/Globus/GRAM/JobManager/condor.pm" \
>/dev/null 2>&1; then
%{__cat} 1>&2 <<EOF

WARNING: check that
\${VDT_LOCATION}/globus/lib/perl/Globus/GRAM/JobManager/condor.pm 
and managedfork.pm contain the line, 'sub log_to_gratia'. If not, please patch
using the diff files in:

${RPM_INSTALL_PREFIX1}/probe/condor/gram_mods/

or see ${RPM_INSTALL_PREFIX1}/probe/condor/README for more information.

EOF
fi


# Configure crontab entry
if %{__grep} -re 'condor_meter.cron\.sh' -e 'condor_meter\.pl' \
        /etc/crontab /etc/cron.* >/dev/null 2>&1; then
%{__cat} <<EOF 1>&2

WARNING: non-standard installation of probe in /etc/crontab or /etc/cron.*
         Please check and remove to avoid clashes with root's crontab

EOF
fi

tmpfile=`mktemp /tmp/gratia-probe-condor-post.XXXXXXXXXX`
crontab -l 2>/dev/null | \
%{__grep} -v -e 'condor_meter.cron\.sh' \
        -e 'condor_meter\.pl' > "$tmpfile" 2>/dev/null
%{__cat} >>"$tmpfile" <<EOF
$(( $RANDOM % 15 ))-59/15 * * * * \
"${RPM_INSTALL_PREFIX1}/probe/condor/condor_meter.cron.sh" > \
"${RPM_INSTALL_PREFIX1}/var/logs/gratia-probe-condor.log" 2>&1
EOF

crontab "$tmpfile" >/dev/null 2>&1
rm -f "$tmpfile"

%preun condor%{?maybe_itb_suffix}
# Only execute this if we're uninstalling the last package of this name
if [ $1 -eq 0 ]; then
  # Remove crontab entry
  tmpfile=`mktemp /tmp/gratia-probe-condor-post.XXXXXXXXXX`
  crontab -l 2>/dev/null | \
  %{__grep} -v -e 'condor_meter.cron\.sh' \
          -e 'condor_meter\.pl' > "$tmpfile" 2>/dev/null
  if test -s "$tmpfile"; then
    crontab "$tmpfile" >/dev/null 2>&1
  else
    crontab -r
  fi
  rm -f "$tmpfile"
fi

%endif

%changelog
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
