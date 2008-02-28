Instructions for configuring the dCache Storage Probe as installed from
an RPM or VDT package.

Edit the ProbeConfig file in this directory; you need to verify the values of:

SOAPHost             The host running your local gratia repository.
DBHostName           The fully qualified SRM DB Host name
DBLoginName          The login name for the SRM DB.
DBPassword           The password for the SRM DB
DCacheServerHost     The fully qualified hostname of your dCache server.
AdminSvrPort         The admin server port.
AdminSvrLogin        The admin server login.
AdminSvrPassword     The admin server password.
DcacheLogLevel       Probe-specific logging level.
EnableProbe          Set to 1 to enable the probe.

If no password is needed, use the empty string.

If installed via RPM, no further action should be necessary.

If installed via VDT, configure-osg.sh should activate the probe;
otherwise ensure configuration with:

$VDT_LOCATION/vdt/setup/configure_gratia --probe dcache-storage \
--report-to <reporting-host> --site-name <OSG_SE_NAME>  --probe-cron

vdt-control --on gratia-dcache-storage

------------------------------------
2008/02/25 Chris Green <greenc@fnal.gov>
