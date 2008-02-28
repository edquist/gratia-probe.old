Instructions for configuring the dCache Transfer Probe as installed from
an RPM or VDT package.

Edit the ProbeConfig file in this directory; you need to verify the values of:

SOAPHost             The host running your local gratia repository.
DBHostName           The fully qualified SRM DB Host name
DBLoginName          The login name for the SRM DB.
DBPassword           The password for the SRM DB
DCacheServerHost     The fully qualified hostname of your dCache server.
EmailServerHost      For problem emails -- SMTP server.
EmailFromAddress     For problem emails -- from address.
EmailToList          For problem emails -- recipient list.
DcacheLogLevel       Probe-specific logging level.
EnableProbe          Set to 1 to enable the probe.

If no password is needed, use the empty string.

If installed via RPM, activate the probe using:

  chkconfig --add gratia-dcache-transfer-probe
  service start gratia-dcache-transfer-probe

If installed via VDT, configure-osg.sh should activate the probe;
otherwise ensure configuration with:

$VDT_LOCATION/vdt/setup/configure_gratia --probe dcache-transfer \
--report-to <reporting-host> --site-name <OSG_SE_NAME> --probe-cron

vdt-control --on gratia-dcache-transfer

------------------------------------
2008/02/25 Chris Green <greenc@fnal.gov>
