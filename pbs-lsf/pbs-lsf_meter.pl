#!/usr/bin/perl -w
########################################################################
# pbs-lsf_meter.pl
#
# Read the urCollector configuration file for URBox, then invoke the
# "real" probe in the original Klin^H^H^H^HPython.
#
# Chris Green 2006/10/06
#
# (C) 2006 Fermilab. Released under GPL v2.
########################################################################

####################################
# Packages
####################################
use strict;
use POSIX;

use urCollector::Common qw(:DEFAULT :Locking);
use urCollector::Configuration;

sub local_error {
  system("$URCOLLECTOR_LOC/../common/DebugPrint.py", "-l", "-1", @_);
}

####################################
# BEGIN clause
####################################
BEGIN {
  push @INC, $::ENV{URCOLLECTOR_LOCATION} || "/opt/urCollector";
};

####################################
# Initialization / executable code
####################################

# Config file path if specified
if ($ARGV[0]) {
  $configFilePath = shift @ARGV;
}

# Parse configuration file
&parseConf($configFilePath);

my $sigset = POSIX::SigSet ->new();
my $cleanup_action =
  POSIX::SigAction->new("cleanup", $sigset);

POSIX::sigaction(&POSIX::SIGINT, $cleanup_action);
POSIX::sigaction(&POSIX::SIGQUIT, $cleanup_action);
POSIX::sigaction(&POSIX::SIGTERM, $cleanup_action);

if (putLock($configValues{collectorLockFileName}) != 0) {
  local_error("Fatal Error: Couldn't open lock file $configValues{collectorLockFileName}.\n");
};

my $lrms = uc $configValues{lrmsType};

my $lrms_version;
if ($lrms eq "PBS") {
  ($lrms_version) = grep /\bpbs_version\b/, `qmgr -c "print server" 2>/dev/null`;
  $lrms_version =~ s&^.*=\s*(.*)\n$&$1&;
} elsif ($lrms eq "LSF") {
  $lrms_version = `bsub -V 2>&1 1>/dev/null`;
  $lrms_version =~ m&^Platform\s*([^\n]*)(?:.*binary type\s*:\s*(.*))?&s and
    $lrms_version = $2?"$1 / $2":"$1";
}

my $status = system("$URCOLLECTOR_LOC/pbs-lsf.py",
                    "$configValues{URBox}",
                    $lrms,
                    $lrms_version);

if (delLock($configValues{collectorLockFileName}) != 0) {
  local_error("Error removing lock file.\n");
}

exit($status);
####################################
# End of initialization / executable code
####################################
1;


####################################
# Subroutines
####################################
sub cleanup {
  delLock($configValues{collectorLockFileName})
    if $configValues{collectorLockFileName};
}

__END__
