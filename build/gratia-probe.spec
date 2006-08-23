Name: gratia-probe
Summary: Gratia OSG accounting system probes
Group: Applications/System
Version: 0.9b
Release: 1
License: GPL
Group: Applications/System
URL: http://sourceforge.net/projects/gratia/
Packager: Chris Green <greenc@fnal.gov>
Vendor: The Open Science Grid <http://www.opensciencegrid.org/>

Source0: %{name}-common-%{version}.tar.bz2
Source1: %{name}-condor-%{version}.tar.bz2
Source2: %{name}-psacct-%{version}.tar.bz2

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch

Prefix: /usr
Prefix: /opt/vdt/gratia

%define template_marker <!-- Temporary RPM-generated template marker -->

%prep
%setup -q -c
%setup -q -D -T -a 1
%setup -q -D -T -a 2

%build

%install
# Setup
rm -rf "$RPM_BUILD_ROOT"
mkdir -p "$RPM_BUILD_ROOT/opt/vdt/gratia/probe"

# Obtain files
cp -pR . "$RPM_BUILD_ROOT/opt/vdt/gratia/probe"

# Set up var area
cd "$RPM_BUILD_ROOT/opt/vdt/gratia"
mkdir -p var/{data,logs,tmp}
chmod -R 1777 var/data

# Get uncustomized ProbeConfigTemplate files (see post below)
for probe_config in \
    "$RPM_BUILD_ROOT/opt/vdt/gratia/probe/condor/ProbeConfig" \
    "$RPM_BUILD_ROOT/opt/vdt/gratia/probe/psacct/ProbeConfig"; do
  cp -p "$RPM_BUILD_ROOT/opt/vdt/gratia/probe/common/ProbeConfigTemplate" \
        "$probe_config"
  echo "%{template_marker}" >> "$probe_config"
done

# install psacct startup script.
install -d "$RPM_BUILD_ROOT/etc/rc.d/init.d/"
install -m 755 "$RPM_BUILD_ROOT/opt/vdt/gratia/probe/psacct/gratia-psacct" \
"$RPM_BUILD_ROOT/etc/rc.d/init.d/"

%clean
rm -rf "${RPM_BUILD_ROOT}"

%description
Probes for the Gratia OSG accounting system

%package common
Summary: Common files for Gratia OSG accounting system probes
Group: Applications/System
Requires: python >= 2.2

%description common
Common files and examples for Gratia OSG accounting system probes.

%package psacct
Summary: A ps-accounting probe
Group: Applications/System
Requires: python >= 2.2
Requires: psacct
Requires: %{name}-common = %{version}

%description psacct
The psacct probe for the Gratia OSG accounting system.

%package condor
Summary: A Condor probe
Group: Applications/System
Requires: python >= 2.2
Requires: %{name}-common = %{version}

%description condor
The condor probe for the Gratia OSG accounting system.

%files common
%defattr(-,root,root,-)
/opt/vdt/gratia/var
%doc /opt/vdt/gratia/probe/common/README
%doc /opt/vdt/gratia/probe/common/samplemeter.pl
%doc /opt/vdt/gratia/probe/common/samplemeter.py
%doc /opt/vdt/gratia/probe/common/ProbeConfigTemplate
/opt/vdt/gratia/probe/common/Clarens.py
/opt/vdt/gratia/probe/common/Gratia.py
/opt/vdt/gratia/probe/common/RegisterProbe.py

# Anything marked "config" is something that is going to be changed in
# post or by the end user.
%files psacct
%defattr(-,root,root,-)
%doc /opt/vdt/gratia/probe/psacct/README
%config /opt/vdt/gratia/probe/psacct/facct-catchup
%config /opt/vdt/gratia/probe/psacct/facct-turnoff.sh
%config /opt/vdt/gratia/probe/psacct/psacct_probe.cron.sh
%config /opt/vdt/gratia/probe/psacct/gratia-psacct
/opt/vdt/gratia/probe/psacct/PSACCTProbeLib.py
/opt/vdt/gratia/probe/psacct/PSACCTProbe.py      
%config(noreplace) /opt/vdt/gratia/probe/psacct/ProbeConfig
/etc/rc.d/init.d/gratia-psacct

%post psacct
# /usr -> "${RPM_INSTALL_PREFIX0}"
# /opt/vdt/gratia -> "${RPM_INSTALL_PREFIX1}"
cat <<EOF | while read config_file; do
`grep -le '%{template_marker}' \
"${RPM_INSTALL_PREFIX1}"/probe/psacct/ProbeConfig{,.rpmnew} \
2>/dev/null`
${RPM_INSTALL_PREFIX1}/probe/psacct/facct-catchup
${RPM_INSTALL_PREFIX1}/probe/psacct/facct-turnoff.sh
${RPM_INSTALL_PREFIX1}/probe/psacct/psacct_probe.cron.sh
${RPM_INSTALL_PREFIX1}/probe/psacct/gratia-psacct
EOF
perl -wni.orig -e \
'
s&MAGIC_VDT_LOCATION/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
s&/opt/vdt/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
m&%{template_marker}& or print;' \
"$config_file"
done

# Configure boot-time activation of accounting.
/sbin/chkconfig --add gratia-psacct
/sbin/chkconfig --level 35 gratia-psacct on

# Configure crontab entry
if grep -re 'psacct_probe.cron\.sh' -e 'PSACCTProbe\.py' \
        /etc/crontab /etc/cron.* >/dev/null 2>&1; then
  echo "WARNING: non-standard entry for psacct probe in \
/etc/crontab or /etc/cron.*" 1>&2
  echo "         Please check and remove to avoid clashes \
with root's crontab" 1>&2
fi

tmpfile=`mktemp /tmp/gratia-probe-psacct-post.XXXXXXXXXX`
crontab -l 2>/dev/null | \
grep -v -e 'psacct_probe.cron\.sh' \
        -e 'PSACCTProbe\.py' > "$tmpfile" 2>/dev/null
cat >>"$tmpfile" <<EOF
$(( $RANDOM % 60 )) $(( $RANDOM % 24 )) * * * \
"${RPM_INSTALL_PREFIX1}/probe/psacct/psacct_probe.cron.sh" > \
"${RPM_INSTALL_PREFIX1}/var/logs/gratia-probe-psacct.log" 2>&1
EOF

# Inform user of next step.
crontab "$tmpfile" >/dev/null 2>&1
rm -f "$tmpfile"

  echo "After configuring ${RPM_INSTALL_PREFIX1}/probe/psacct/ProbeConfig
invoke

/etc/rc.d/init.d/gratia-psaccct start

to start process accounting" 1>&2

# Deal with legacy Fermilab psacct configuration:

if grep -e 'fiscal/monacct\.log' >/dev/null 2>&1; then
  tmpfile=`mktemp /tmp/gratia-probe-psacct-post.XXXXXXXXXX`
  crontab -l 2>/dev/null | \
grep -v -e 'nite/acct\.log' \
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
# Remove crontab entry
tmpfile=`mktemp /tmp/gratia-probe-psacct-post.XXXXXXXXXX`
crontab -l 2>/dev/null | \
grep -v -e 'psacct_probe.cron\.sh' \
        -e 'PSACCTProbe\.py' > "$tmpfile" 2>/dev/null
if test -s "$tmpfile"; then
  crontab "$tmpfile" >/dev/null 2>&1
else
  crontab -r
fi
rm -f "$tmpfile"

%files condor
%defattr(-,root,root,-)
%doc /opt/vdt/gratia/probe/condor/README
/opt/vdt/gratia/probe/condor/gram_mods
/opt/vdt/gratia/probe/condor/condor_meter.cron.sh
/opt/vdt/gratia/probe/condor/condor_meter.pl
%config(noreplace) /opt/vdt/gratia/probe/condor/ProbeConfig

%post condor
# /usr -> "${RPM_INSTALL_PREFIX0}"
# /opt/vdt/gratia -> "${RPM_INSTALL_PREFIX1}"
cat <<EOF | while read config_file; do
`grep -le '%{template_marker}' \
"${RPM_INSTALL_PREFIX1}"/probe/condor/ProbeConfig{,.rpmnew} \
2>/dev/null`
EOF
perl -wni.orig -e \
'
s&MAGIC_VDT_LOCATION/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
s&/opt/vdt/gratia(/?)&$ENV{RPM_INSTALL_PREFIX1}${1}&;
m&%{template_marker}& or print;' \
"$config_file"
done

# Configure GRAM perl modules
if ! grep -e 'log_to_gratia' \
"${RPM_INSTALL_PREFIX1}../globus/lib/perl/Globus/GRAM/JobManager/condor.pm" \
>/dev/null 2>&1; then
  echo "WARNING: check that
\${VDT_LOCATION}/globus/lib/perl/Globus/GRAM/JobManager/condor.pm 
and managedfork.pm contain the line, 'sub log_to_gratia'. If not, please patch
using the diff files in:

${RPM_INSTALL_PREFIX1}/probe/condor/gram_mods/

or see ${RPM_INSTALL_PREFIX1}/probe/condor/README for more information." 1>&2
fi


# Configure crontab entry
if grep -re 'condor_meter.cron\.sh' -e 'condor_meter\.pl' \
        /etc/crontab /etc/cron.* >/dev/null 2>&1; then
  echo "WARNING: non-standard installation of condor probe in /etc/crontab or /etc/cron.*" 1>&2
  echo "         Please check and remove to avoid clashes with root's crontab" 1>&2
fi

tmpfile=`mktemp /tmp/gratia-probe-condor-post.XXXXXXXXXX`
crontab -l 2>/dev/null | \
grep -v -e 'condor_meter.cron\.sh' 
        -e 'condor_meter\.pl' > "$tmpfile" 2>/dev/null
cat >>"$tmpfile" <<EOF
$(( $RANDOM % 60 )) $(( $RANDOM % 24 )) * * * \
"${RPM_INSTALL_PREFIX1}/probe/condor/condor_meter.cron.sh" > \
"${RPM_INSTALL_PREFIX1}/var/logs/gratia-probe-condor.log" 2>&1
EOF

crontab "$tmpfile" >/dev/null 2>&1
rm -f "$tmpfile"

%preun condor
# Remove crontab entry
tmpfile=`mktemp /tmp/gratia-probe-condor-post.XXXXXXXXXX`
crontab -l 2>/dev/null | \
grep -v -e 'condor_meter.cron\.sh' \
        -e 'condor_meter\.pl' > "$tmpfile" 2>/dev/null
if test -s "$tmpfile"; then
  crontab "$tmpfile" >/dev/null 2>&1
else
  crontab -r
fi
rm -f "$tmpfile"

%changelog
* Tue Aug 15 2006  <greenc@fnal.gov> - 0.9a-1
- Initial build.

