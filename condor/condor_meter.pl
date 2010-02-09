#!/usr/bin/perl
#
# condor_meter.pl - Prototype for an OSG Accouting 'meter' for Condor
#       By Ken Schumacher <kschu@fnal.gov> Began 5 Nov 2005
# $Id$
# Full Path: $HeadURL$
#
# Revision History:
#     5 Nov 2005 - Initial concept
#    14 Apr 2006 - Rewrite to send one accounting record per job

# The name of one or more condor log files should be passed as
# parameters.  This script will parse the log and generate records which
# include the grid accounting data.

#==================================================================
# Globl Variable definitions
#==================================================================

use English;                    # For readability
use strict 'refs', 'subs';
use FileHandle;
use File::Basename;
#use XML::Parser;

sub create_unique_id(\%);

my $progname = "condor_meter.pl";
my $prog_version = '%%%RPMVERSION%%%';
my $prog_revision = '$Revision$ '; # SVN Version number
$prog_revision =~ s&\$Revision(?::\s*)?(.*?)\s*\$$&$1&;
$prog_revision or $prog_revision = "unknown";

#$true = 1; $false = 0;
$verbose = 1;

#==================================================================
#  condor_meter.pl - Main program block
#==================================================================
autoflush STDERR 1; autoflush STDOUT 1;

# Initialization and Setup.
use Getopt::Std;

$opt_d = $opt_l = $opt_r = $opt_v = $opt_x = 0;

# Get command line arguments
unless (getopts('c:df:lrs:vx')) {
  Usage_message();
  exit 1;
}

$constraint_attr = $constraint_value = undef;
if (defined($opt_c)) {
  ($constraint_attr, $constraint_value) = split("=", $opt_c, 2);
  unless (defined($constraint_value)) {
    die "ERROR: constraint must be of form <attr>=<value>";
  }
}

if (defined($opt_s)) {          # State file
  $gram_log_state_file = $opt_s;
}

$delete_flag = ($opt_d == 1);
$gratia_config = $opt_f;
$report_results = ($opt_l == 1);
$reprocess_flag = ($opt_r == 1);
$verbose = ($opt_v == 1);
$debug_mode = ($opt_x == 1);
$max_batch_size = 500; # Max records in one python file.

# After we have stripped off switches, there needs to be at least one
# directory or file name passed as an argument
if (! defined @ARGV) {
  print STDERR "No directories or filenames supplied.\n\n";
  Usage_message();
  exit 1;
}

if ($verbose) {
  print "$progname version $prog_version ($prog_revision)\n";
  if ($debug_mode) {
    print "Running in verbose mode with debugging enabled.\n";
  } else {
    print "Running in verbose mode.\n";
  }
} elsif ($debug_mode) {
  #print "$progname version $prog_version ($prog_revision)\n";
  print "Running in debugging  mode.\n";
}

# Directory to which to write stubs is first writable directory in arg
# list.
my ($stub_dir) = (grep { -d $_ and -w $_ } @ARGV);

#------------------------------------------------------------------
# Locate and verify the path to the condor_history executable
use Env qw(CONDOR_LOCATION PATH GLOBUS_LOCATION); #Import only the Env variables we need
@path = split(/:/, $PATH);
push(@path, "/usr/local/bin");
$condor_history = '';
$condor_hist_cmd = '';

if (( $CONDOR_LOCATION ) && ( -x "$CONDOR_LOCATION/bin/condor_history" )) {
  # This is the most obvious place to look
  $condor_history = "$CONDOR_LOCATION/bin/condor_history";
} else {
  foreach $path_dir (@path) {
    unless ( $condor_history ) {
      if (-x "$path_dir/condor_history") {
        $condor_history = "$path_dir/condor_history";
      }
    }
  }
}

unless ( -x $condor_history ) {
  warn "The 'condor_history' program was not found.\n";
  exit 2;
}

$condor_version = $condor_history;
$condor_version =~ s/history$/version/;

if ($condor_version and -x $condor_version) {
  $condor_version = `$condor_version 2>/dev/null`;
  $condor_version =~ s&^\$CondorVersion:\s*(.*)\s*\$\n\$CondorPlatform:\s*(.*)\s*\$\n&$1 / $2&;
} else {
  undef $condor_version;
}

if ($verbose) {
  print "Condor_history at $condor_history\n";
  print "Condor version is $condor_version\n";
}

$condor_hist_cmd = $condor_history;

open(CONDOR_HISTORY_HELP, "$condor_hist_cmd -help|")
  or die "Unable to open condor_history pipe\n";
my @condor_history_help_text = <CONDOR_HISTORY_HELP>;
close CONDOR_HISTORY_HELP;
chomp @condor_history_help_text;
grep /-backwards\b/, @condor_history_help_text and
  $condor_hist_cmd = "$condor_hist_cmd -backwards";
grep /-match\b/, @condor_history_help_text and
  $condor_hist_cmd = "$condor_hist_cmd -match 1";

$condor_config_val_cmd = sprintf("%s/condor_config_val", dirname($condor_history));
$condor_hist_file = `$condor_config_val_cmd HISTORY`;
chomp $condor_hist_file;

my $global_gram_log =
  `grep -e '^log_path' "$ENV{GLOBUS_LOCATION}/etc/globus-condor.conf" 2>/dev/null`;
chomp $global_gram_log;
$global_gram_log =~ s&^log_path=&&;

if ($global_gram_log and -r $global_gram_log) {
  if ($verbose) {
    print "Global GRAM log found at $global_gram_log\n";
    print "Generating gram stub files for terminated WS-GRAM jobs\n";
  }
  generate_ws_stubs($global_gram_log);
} else {
  print "INFO: Unable to find global GRAM log via globus-condor.conf: some WS jobs may not be accounted.";
}

my $condor_pm_file = "$ENV{GLOBUS_LOCATION}/lib/perl/Globus/GRAM/JobManager/condor.pm";
my $managedfork_pm_file = "$ENV{GLOBUS_LOCATION}/lib/perl/Globus/GRAM/JobManager/managedfork.pm";
my $have_GratiaJobOrigin_in_JobManagers = 1;

my $have_condor_pm_file = (-e $condor_pm_file);
my $have_managedfork_pm_file = (-e $managedfork_pm_file);

# Change logic so that we're tolerant of the situation where condor.pm
# does not exist; but managedfork.pm does.
if ($have_condor_pm_file and
    system("grep -e 'GratiaJobOrigin' \"$condor_pm_file\" >/dev/null 2>&1") != 0) {
  print sprintf("%s%s",
               "INFO: Condor JobManager ($condor_pm_file) exists but does not have expected addition of GratiaJobOrigin ClassAd.\n",
               "INFO: Identification of local jobs disabled.");
  $have_GratiaJobOrigin_in_JobManagers = 0;
}

if ($managedfork_pm_file and
    system("grep -e 'GratiaJobOrigin' \"$managedfork_pm_file\" >/dev/null 2>&1") != 0) {
  print sprintf("%s%s",
               "INFO: Managedfork JobManager ($managedfork_pm_file) exists but does not have expected addition of GratiaJobOrigin ClassAd.\n",
               "INFO: Identification of local jobs disabled.");
  $have_GratiaJobOrigin_in_JobManagers = 0;
}

#------------------------------------------------------------------
# Build a list of file names.  Add individual files given as command
# line arguments or select names from a directory specified.
my @logfiles = @processed_logfiles = ();
foreach $name_arg (@ARGV) {
  if ( -f $name_arg && -s _ ) {
    # This argument is a non-empty plain file
    push(@logfiles, $name_arg);
  } elsif ( -d $name_arg ) {
    # This argument is a directory name
    opendir(DIR, $name_arg)
      or die "Could not open the directory $name_arg.";
    while ($file = readdir(DIR)) {
      next unless (-f "$name_arg/$file" and -s "$name_arg/$file");
      if ($file =~ /^(?:gram|gratia)_condor_log\./ or # One of our or GRAM's log stubs
          $file =~ /^history\.(?:.*?\#)?\d+\.\d+/ # A ClassAd
# Deactivate certinfo files as expensive -- we should get
# a history or globus log file now for everything (even WS events).
#          $file =~ /^gratia_certinfo_(?:condor|managedfork)/ # A certinfo file
         ) {
        if ($verbose) {
          print "Adding $name_arg/$file to list of files to examine\n";
        }
        push(@logfiles, "$name_arg/$file");
      }
    }
    closedir(DIR);
  }
}

# Remove old temporary files (if still there) used for debugging
my $gram_log_dir = dirname($gram_log_state_file);
foreach $tmp_file ( $gram_log_dir."/tmp.out", $gram_log_dir."/tmp_in.py") {
  if ( -e $tmp_file ) {
    unlink($tmp_file)
      or warn "Unable to delete old file: $tmp_file\n";
  }
}

#------------------------------------------------------------------
# Open the pipe to the Gratia meter library process
open_new_py();

$count_submit = 0;

$logs_found = scalar @logfiles;
if ($logs_found == 0) {
  exit 0;
} else {
  if ($verbose) {
    print "Number of log files found: $logs_found\n";
  }
}


my @logfiles_sorted = ();
# Order logfiles by type:
foreach my $file_regex ('m&^history\.(?:.*?\#)?\d+\.\d+&',
                        'm&^(?:gram|gratia)_condor_log\.&',
                        'm&^gratia_certinfo_(?:condor|managedfork)&') {
  my @tmp_array = grep { my $basename = basename $_; eval "\$basename =~ $file_regex" } @logfiles;
  push @logfiles_sorted, @tmp_array;
}

@logfiles = @logfiles_sorted;

#------------------------------------------------------------------
# Get source file name(s)

my $count_orig = $count_orig_004 = $count_orig_005 = $count_orig_009 = 0;
my $count_orig_ignore_004 = $count_orig_ignore_005 = 0;
my $count_xml = $count_xml_004 = $count_xml_005 = $count_xml_009 = 0;
my $count_xml_ignore_004 = $count_xml_ignore_005 = 0;
my $count_history = 0;
my $count_stub_writes = 0;
my $ctag_depth = 0;

foreach $logfile (@logfiles) {

  if ($verbose) {
    print "Processing file: $logfile\n";
  }

  $logfile_errors = 0;
  $logfile_constrained = 0;

  my $basename = basename($logfile);

  # See if the file is a per-job history file (a ClassAd)
  if ($basename =~ /^history.(\d+)\.(\d+)/) {
    my $clusterId = $1;
    my $procId = $2;
    ++$count_history;
    print "Processing condor history file $logfile for $clusterId.$procId\n" if ($verbose);
    # get the class ad from the file
    %condor_data_hash = Read_ClassAd($logfile);
    # check to see we got something
    if (! %condor_data_hash) {
      ++$logfile_errors;
    } else {
      # add-in UniqGlobalJobId
      if ($condor_hist_data{'GlobalJobId'}) {
        $condor_hist_data{'UniqGlobalJobId'} =
          'condor.' . $condor_hist_data{'GlobalJobId'};
      }
      # check constraint then hand off data to gratia
      if (!Check_Constraint(%condor_data_hash)) {
        $logfile_constrained = 1;
      } elsif (!Feed_Gratia(%condor_data_hash)) {
        ++$logfile_errors;
      }
      # Make sure we don't reprocess any duplicate information in other
      # forms (globus stub, etc)
      setSeenLocalJobId($clusterId, $condor_data_hash{ProcId});
    }
  } elsif ($basename =~ /^history\.(?:.*?\#)?(\d+)\.(\d+)/) {
    # This file should be ignored, per Condor experts: just clean it up.
  } elsif ($basename =~/^gratia_certinfo_(?:condor|managedfork)_(\d+)(?:\.(\d+))?/) {
    my ($clusterId, $procId) = ($1, ($2 || 0));
    # File is a certinfo stub.
    if (checkSeenLocalJobId($clusterId, $procId)) {
      # Seen (eg) the history file already.
      print "Ignoring certinfo file $logfile for $clusterId.$procId\n" if ($verbose);
      next;
    } else {
      print "Processing certinfo file $logfile for $clusterId.$procId\n" if ($verbose);
    }

    my %condor_data_hash = Query_Condor_History($clusterId, $procId);
    # Job may not be complete yet (no history)
    if ($condor_data_hash{'GlobalJobId'}) {
      # add-in UniqGlobalJobId
      if ($condor_hist_data{'GlobalJobId'}) {
        $condor_hist_data{'UniqGlobalJobId'} =
          'condor.' . $condor_hist_data{'GlobalJobId'};
      }
      # check constraint then hand off data to gratia
      if (!Check_Constraint(%condor_data_hash)) {
        $logfile_constrained = 1;
      } elsif (!Feed_Gratia(%condor_data_hash)) {
        ++$logfile_errors;
      }
      # Make sure we don't reprocess any duplicate information in other
      # forms (globus stub, etc)
      setSeenLocalJobId($clusterId, $procId);
    }
    next;                       # Never remove these files as they are needed later
  } else {
    my $clusterId;
    # Otherwise, get the first record to test format of the file
    print "Processing condor event log file $logfile\n" if $verbose;
    open(LOGF, $logfile)
      or die "Unable to open logfile: $logfile\n";

    $record_in = <LOGF>;

    # Clear the variables for each new event processed
    %condor_data_hash = ();
    #%logfile_hash = ();  @logfile_clusterids = ();

    if ($record_in =~ /\<c\>/) {
      print "Processing $logfile as an XML format logfile.\n" if $verbose;
      ++$count_xml;             # This is counting XML log files (not records)
      my $last_was_c = 0;       # To work around a bug in the condor xml generation

      $event_hash = {};  $ctag_depth=1;
      # Parse the XML log file
      while (<LOGF>) {
        # See fngp-osg:/export/osg/grid/globus/lib/perl/Globus/GRAM
        # And the JobManger/condor.pm module - under sub poll()

        # I adapted the code the Globus condor JobManager uses. While
        # it lacks some error handling, it will work as well or
        # better than the GRAM job manager.

        if (/<c>/) {            # Open tag --------------------
          # allow for more than one open tag in a row (known condor
          # xml format error).

          if ($last_was_c != 1) {
            ++$ctag_depth;
          }
          if ($ctag_depth > 1) {
            warn "$logfile: Improperly formatted XML records, missing \<c/\>\n";
            ++$logfile_errors;  # An error means we won't delete this log file
          }
          $event_hash = {};
          $last_was_c = 1;
        } else {
          $last_was_c = 0;
        }
        if (/<a n="([^\"]+)">/) { # Attribute line --------------------
          my $attr = $1;

          # In the XML version of log files, the Cluster ID was
          # labeled just 'Cluster' rather than ClusterId' as it is in
          # the original format and in Condor_History
          $attr = 'ClusterId' if ($attr =~ /^Cluster$/);
          $attr = 'ProcId' if ($attr =~ /^Proc$/);

          if (/<s>([^<]+)<\/s>/) {
            $event_hash{$attr} = "'''".$1."'''";
          } elsif (/<i>([^<]+)<\/i>/) {
            $event_hash{$attr} = int($1);
          } elsif (/<b v="([tf])"\/>/) {
            $event_hash{$attr} = ($1 eq 't');
          } elsif (/<r>([^<]+)<\/r>/) {
            $event_hash{$attr} = $1;
          }
        } elsif (/<\/c>/) {     # Close tag --------------------
          if ($event_hash{'ClusterId'}) {
            $clusterId = $event_hash{'ClusterId'};
            $procId = $event_hash{'ProcId'} || 0;
            # I now "fix" this when setting this attribute (above)
            #$event_hash{'ClusterId'} = $event_hash{'Cluster'};

            # All events have an these "standard" elements: MyType,
            #    EventTypeNumber, EventTime, Cluster, Proc, and Subproc
            # Process the events that report CPU usage
            if ($event_hash{'EventTypeNumber'} == 0) { # Job submitted
              # SubmitEvent: has Std and a SubmitHost IP
              #if (%condor_data_hash = 
              #       Query_Condor_History($event_hash{'ClusterId'})) {
              # push @logfile_clusterids, $event_hash{'ClusterId'};
              #} else {
              # warn "No Condor History found - Logfile: " . 
              #   basename($logfile) . " ClusterId: $event_hash{'Cluster'}\n";
              # #Not sure if this case should be considered "fatal"
              # ++$logfile_errors; # An error means we won't delete this log file
              #}
            } elsif ($event_hash{'EventTypeNumber'} == 1) { # Job began exectuting
              # ExecuteEvent: has Std and an ExecuteHost IP
            } elsif ($event_hash{'EventTypeNumber'} == 4) { # Job was Evicted
              print "Identified event type 4 in $logfile\n" if $verbose;
              if (not checkSeenLocalJobId($clusterId, $procId)) {
                ++$count_xml_004;
                if (%condor_data_hash = Query_Condor_History($clusterId, $procId)) {
                  if (!Check_Constraint(%condor_data_hash)) {
                    $logfile_constrained = 1;
                  } elsif (!Feed_Gratia(%condor_data_hash)) {
                    warn "Failed to feed XML 004 event to Gratia\n";
                    ++$logfile_errors; # An error means we won't delete this log file
                  }
                  # Make sure we don't reprocess any duplicate information
                  # in other forms (globus stub, etc)
                  setSeenLocalJobId($clusterId, $procId);
                } else {
                  warn "No Condor History found (XML-5) - Logfile: " .
                    basename($logfile) . " ClusterId: $event_hash{'ClusterId'}\n";
                }
              } else {
                print "Ignoring event type 4 for $clusterId.$procId: already seen\n" if $verbose;
                ++$count_xml_ignore_004;
              }
            } elsif ($event_hash{'EventTypeNumber'} == 5) { # Job finished
              print "Identified event type 5 in $logfile\n" if $verbose;
              if (not checkSeenLocalJobId($clusterId, $procId)) {
                # JobTerminatedEvent: has Std and several others
                ++$count_xml_005;
                if (%condor_data_hash = Query_Condor_History($clusterId, $procId)) {
                  if (!Check_Constraint(%condor_data_hash)) {
                    $logfile_constrained = 1;
                  } elsif (!Feed_Gratia(%condor_data_hash)) {
                    warn "Failed to feed XML 005 event to Gratia\n";
                    ++$logfile_errors; # An error means we won't delete this log file
                  }
                  # Make sure we don't reprocess any duplicate information
                  # in other forms (globus stub, etc
                  setSeenLocalJobId($clusterId, $procId);
                } else {
                  warn "No Condor History found (XML-5) - Logfile: " .
                    basename($logfile) . " ClusterId: $event_hash{'ClusterId'}\n";
                }
              } else {
                print "Ignoring event type 5 for $clusterId.$procId: already seen\n" if $verbose;
                ++$count_xml_ignore_005;
              }
            } elsif ($event_hash{'EventTypeNumber'} == 6) { # Image Size
              # JobImageSizeEvent: has Std and a Size
            } elsif ($event_hash{'EventTypeNumber'} == 9) { # Job Aborted
              # JobAbortedEvent: has Std and Reason (string)
              ++$count_xml_009;
              # I think it is helpful to count these,
              # but there is no data in them worth reporting to Gratia
            }
          } else {
            warn "I have an XML event record with no Cluster Id.\n";
            ++$logfile_errors;  # An error means we won't delete this log file
          }
          $ctag_depth--;
        }                       # End of close tag
      }
    } else {                    # Non-XML format
      print "Processing $logfile as a non-XML format logfile.\n" if $verbose;
      #This is the original condor log file format
      ++$count_orig;            # This is counting 005 files
      @event_records = ();
      push @event_records, $record_in;

      while ($record_in = <LOGF>) {
        if ($verbose && $debug_mode) {
          print "Next input record: " . $record_in . "\n";
        }
        push @event_records, $record_in;

        if ($record_in =~ /^\.\.\./) { # Terminates this event
          if ($event_records[0] =~ /^000 /) {
            if ($verbose) {
              print "Original format 000 record\n";
            }
          } elsif ($event_records[0] =~ /^001 /) {
            if ($verbose) {
              print "Original format 001 record\n";
            }
          } elsif ($event_records[0] =~ /^004 /) {
            # Is this a '004 Job was Evicted' event?
            print "Identified event type 4 in $logfile\n" if $verbose;
            ++$count_orig_004;
            if (%condor_data_hash = Process_004($logfile, @event_records)) {
              if ($verbose) {
                print "Process_004 returned Cluster_id of $condor_data_hash{'ClusterId'}\n";
              }
              if (!checkSeenLocalJobId($condor_data_hash{'ClusterId'},
                                       $condor_data_hash{'ProcId'})) {
                if (!Check_Constraint(%condor_data_hash)) {
                  $logfile_constrained = 1;
                } elsif (!Feed_Gratia(%condor_data_hash)) {
                  ++$logfile_errors;
                }
                # Make sure we don't reprocess any duplicate information
                # in other forms (globus stub, etc)
                setSeenLocalJobId($condor_data_hash{'ClusterId'},
                                  $condor_data_hash{'ProcId'});
              } else {
                print "Ignoring event type 4 for $clusterId.$procId: already seen\n" if $verbose;
                ++$count_orig_ignore_004;
              }
            } else {
              if ($verbose) {
                warn "No Condor History found (Orig-004) - Logfile: " .
                  basename($logfile) . "\n";
                ++$logfile_errors; # An error means we won't delete this log file
              }
            }
          } elsif ($event_records[0] =~ /^005 /) {
            # Is this a '005 Job Terminated' event?
            print "Identified event type 5 in $logfile\n" if $verbose;
            ++$count_orig_005;
            if (%condor_data_hash = Process_005($logfile, @event_records)) {
              if ($verbose) {
                print "Process_005 returned Cluster_id of $condor_data_hash{'ClusterId'}\n";
              }
              if (!checkSeenLocalJobId($condor_data_hash{'ClusterId'},
                                       $condor_data_hash{'ProcId'})) {
                if (!Check_Constraint(%condor_data_hash)) {
                  $logfile_constrained = 1;
                } elsif (!Feed_Gratia(%condor_data_hash)) {
                  ++$logfile_errors;
                }
                # Make sure we don't reprocess any duplicate information
                # in other forms (globus stub, etc)
                setSeenLocalJobId($condor_data_hash{'ClusterId'},
                                  $condor_data_hash{'ProcId'});
              } else {
                print "Ignoring event type 5 for $clusterId.$procId: already seen\n" if $verbose;
                ++$count_orig_ignore_005;
              }
            } else {
              if ($verbose) {
                warn "No Condor History found (Orig-005) - Logfile: " .
                  basename($logfile) . "\n";
                ++$logfile_errors; # An error means we won't delete this log file
              }
            }
          } elsif ($event_records[0] =~ /^009 /) {
            ++$count_orig_009;
            # While I think it is helpful to count these,
            # but there is no data in them worth reporting to Gratia
          }
          # Reset array to capture next event
          @event_records = ();
        }
      }
    }
    close(LOGF);
  }

  if ($delete_flag) {
    if ($logfile_errors != 0) {
      warn "Logfile ($logfile) was not removed due to errors ($logfile_errors)\n";
    } elsif ($logfile_constrained) {
      warn "Logfile ($logfile) was not removed due to unprocessed data (from -c)\n";
    } else {
      print "Scheduling $logfile for removal\n" if $verbose;
      push @processed_logfiles, $logfile;
    }
  }
}                               # End of the 'foreach $logfile' loop.

# Close Python pipe to Gratia.py
close_py_and_cleanup();


#------------------------------------------------------------------
# Wrap up and report results

$count_total = $count_orig + $count_xml + $count_history;
if (($count_total > 1) && ($verbose || $report_results)) {
  print "Condor probe is done processing log files.\n";
  if ($count_stub_writes) {
    print "Number of logs extracted from\n";
    print "                globus-condor.log: $count_stub_writes\n";
  }
  print " Number of ClassAd files processed: $count_history\n" if ($count_history);
  print "   Number of original format files: $count_orig\n"  if ($count_orig);
  print "# of original 004 events processed: $count_orig_004\n"  if ($count_orig_004);
  print "  # of original 004 events ignored: $count_orig_ignore_004\n"  if ($count_orig_ignore_004);
  print "# of original 005 events processed: $count_orig_005\n"  if ($count_orig_005);
  print "  # of original 005 events ignored: $count_orig_ignore_005\n"  if ($count_orig_ignore_005);
  print "          # of original 009 events: $count_orig_009\n"  if ($count_orig_009);
  print "  Number of XML format files found: $count_xml\n"   if ($count_xml);
  print "     # of XML 004 events processed: $count_xml_004\n"  if ($count_xml_004);
  print "       # of XML 004 events ignored: $count_xml_ignore_004\n"  if ($count_xml_ignore_004);
  print "     # of XML 005 events processed: $count_xml_005\n"  if ($count_xml_005);
  print "       # of XML 005 events ignored: $count_xml_ignore_005\n"  if ($count_xml_ignore_005);
  print "     # of XML 009 events processed: $count_xml_009\n"  if ($count_xml_009);
  print "         Total number of log files: $count_total\n\n";
  print "  # of records submitted to Gratia: $count_submit\n" if ($count_submit);
}

if ($verbose) {
  print "\nEnd of program: $progname\n";
}

1;

#==================================================================
# Subroutine Definitions
#==================================================================

#------------------------------------------------------------------
# Subroutine NumSeconds ($time_string, $num_seconds)
#   This routine will convert a string (ie. 0 05:50:41) to a number of
#   seconds.
#
# I may add the reverse conversion here.  If I pass a null $time_string
# I could create a similar format time string from the passed
# $num_seconds.
# ------------------------------------------------------------------
sub NumSeconds {
  my $time_string = $_[0];
  my $num_seconds = $_[1];
  my $num_hours = $num_mins = 0;
  my $days = $hours = $mins = $secs = 0;

  if ($time_string =~ /(\d) (\d{2}):(\d{2}):(\d{2})/) {
    $days = $1;  $hours = $2;  $mins = $3; $secs = $4;
    $num_hours = ($days * 24) + $hours;
    $num_mins = ($num_hours * 60) + $mins;
    $num_seconds = ($num_mins * 60) + $secs;

    return $num_seconds
  } else {
    warn "Invalid time string: $time_string\n";
    return -1;
  }
}                               # End of subroutine NumSeconds

#------------------------------------------------------------------
# Subroutine Check_Constraint
#   This routine takes a hash of Condor ClassAd data and checks
# whether the contraint given on the command line (if one was
# given at all) applies to this ad. Returns 1 if the given hash
# should be processed, 0 if not.
# -----------------------------------------------------------------
sub Check_Constraint {
  my %hash = @_;
  if (defined($constraint_attr) &&	
      ($hash{$constraint_attr} ne $constraint_value)) {
    if ($verbose) {
      my $id = $hash{'ClusterId'};
      if (!defined($id)) {
        $id = "<unknown>";
      }
      print "ClassAd with cluster $id " .
        "skipped due to constraint\n";
    }
    return 0;
  }
  return 1;
}

#------------------------------------------------------------------
# Subroutine PythonStringLiteral
#   This routine takes a string as an argument and escapes it
#   properly for safe usage in Python.
# -----------------------------------------------------------------
sub PythonStringLiteral {
    my $s = shift;
	
    $s =~ s/\\/\\\\/g;   # escape \'s first, MUST be done first
    $s =~ s/'/\\'/g;     #        single quotes
    $s =~ s/\n/\\n/g;    #        new-lines, and everything next
    $s =~ s/([^[:print:]])/sprintf("\\x%02x", ord $1)/eg;

    return "$s" ;
}

# -----------------------------------------------------------------
# Subroutine Create_Try_Except($function_call, $value (supposedly
# numerical), $description)
# Creates the try.. catch Python block for making sure that
# $value is numerical; otherwise it will be annotated by  
# "possible malicious content". 
#------------------------------------------------------------------
sub Create_Try_Except {
  my $fun = shift;
  my $value = shift;
  my $description = shift;
  my $block = qq/try: $fun(float(\"%s\"%\"/. $value.qq/\"), \"$description\")\n/;
  $block = $block.qq/except: $fun(0, \"$description\", "possible malicious content")\n/;
  return $block
}


#------------------------------------------------------------------
# Subroutine Feed_Gratia ($hash_ref)
#   This routine will take a hash of condor log data and push that
# data out to Gratia. Returns 1 if a record was successfully sent,
# 0 if not.
#------------------------------------------------------------------
sub Feed_Gratia {
  my %hash = @_ ;

  if (! defined ($hash{'ClusterId'})) {
    warn "Feed_Gratia has no data to process.\n";
    return 0;
  } else {
    if ($verbose) {
      print "Feed_Gratia was passed Cluster_id of $hash{'ClusterId'}\n";
    }
  }

  print $py "# initialize and populate r\n";
  my $resource_type = ($hash{'GridMonitorJob'} and
                       $hash{'GridMonitorJob'} =~ /(?:t|true|1)/i)?
                         'GridMonitor':
                           'Batch';
  
  print $py "r = Gratia.UsageRecord(\"$resource_type\")\n";

  # 2.1 RecordIdentity must be set by Philippe's module?
  # RecordIdentity is a required string which must be unique

  # 2.2 GlobalJobId - optional, string
  # Sample: GlobalJobId = "fngp-osg.fnal.gov#1126868442#6501.0"
  print $py qq/r.GlobalJobId(\"/ . $hash{'UniqGlobalJobId'} . qq/\")\n/;

  # 2.3 LocalJobId - optional, string
  if ($hash{'ClusterId'}) {
    # Sample: ClusterId = 6501
    print $py qq/r.LocalJobId(\"/ . $hash{'ClusterId'} . qq/\")\n/;
  }

  # 2.4 ProcessId - optional, integer
  # I'll have to parse this out of 'LastClaimId'
  #      sample: LastClaimId = "<131.225.167.210:32806>#1121113508#5671"
  if ( defined ($hash{'LastClaimId'})) {
    if ($hash{'LastClaimId'} =~ /<.*:(\d*)>/) {
      $condor_process_id = $1;
    } else {
      $condor_process_id = 0;
    }
    if ($verbose) {
      print "From ($hash{'LastClaimId'})" .
        "I got process id ($condor_process_id)\n";
    }
    print $py qq/r.ProcessId(/ . $condor_process_id . qq/)\n/;
  }

  # 2.5 LocalUserId - optional, string
  if ( defined ($hash{'Owner'})) {
    # Sample: Owner = "cdf"
    print $py qq/r.LocalUserId(\"/ . $hash{'Owner'} . qq/\")\n/;
  }

  # 2.6 GlobalUsername - such as the distinguished name from the certificate
  if ( defined ($hash{'User'})) {
    # sample: User = "sdss@fnal.gov"
    print $py qq/r.GlobalUsername(\"/ . $hash{'User'} . qq/\")\n/;
    #print $py qq/r.AdditionalInfo(\"GlobalUsername\", \"/
    #  . $hash{'User'} . qq/\")\n/;
  }

  # Sample values for x509userproxysubject:
  #   "/C=CH/O=CERN/OU=GRID/CN=Sami Lehti 5217"
  #   "/DC=gov/DC=fnal/O=Fermilab/OU=People/CN=Philippe G. Canal/UID=pcanal"

  if ( defined ($hash{'x509userproxysubject'})) {
      my ($dn, $fqan, $vo) = ( $hash{'x509userproxysubject'} =~ m&^(.*?)(?::(/([^/]*).*?))*$& );
      # DN gets converted to slash format if necessary in Gratia.py
      print $py qq/r.DN("$dn")\n/ if $dn;
      print $py qq/r.VOName("$fqan")\n/ if $fqan;
      print $py qq/r.ReportableVOName("$vo")\n/ if $vo;
  }

  # 2.7 JobName - Condors name? for this job? - optional, string
  # The $condor_submit_host is used in 2.14 & 2.16 below
  # ??? Should I set this default, or leave it undefined if I can't set it ???
  $condor_submit_host = "unknown submit host";
  if ( defined ($hash{'GlobalJobId'})) {
    # Sample: GlobalJobId = "fngp-osg.fnal.gov#1126868442#6501.0"
    print $py qq/r.JobName(\"/ . $hash{'GlobalJobId'} . qq/\")\n/;

    if ($hash{'GlobalJobId'} =~ /(.*)\#\d*\#.*/) {
      $condor_submit_host = "$1";
    }
  }

  # 2.8 Charge - optional, integer, site dependent

  # 2.9 Status - optional, integer, exit status
  if ( defined ($hash{'ExitStatus'})) {
    # Sample: ExitStatus = 0
    print $py qq/r.Status(\"/ . $hash{'ExitStatus'} .
      qq/\", "Condor Exit Status")\n/;
  }

  # 2.10 WallDuration - "Wall clock time that elpased while the job was running."
  if ( defined ($hash{'RemoteWallClockTime'})) {
    # Sample: RemoteWallClockTime = 10251.000000
    print $py qq/r.WallDuration(int(float(/ . $hash{'RemoteWallClockTime'} .
                                          qq/)),\"Was entered in seconds\")\n/;
  }

  # TimeDuration - According to Gratia.py, "an additional measure
  #    of time duration that is relevant to the reported usage." type
  #    can be 'submit', 'connect', 'dedicated', or 'other'
  # NOTE: First I will submit the time durations that I found, then I
  #       set the ones that were not found to zero so later math does
  #       not fail due to an undefined value.
  if ( defined ($hash{'RemoteUserCpu'})) {
    # Sample: RemoteUserCpu = 9231.000000
    print $py Create_Try_Except("r.TimeDuration", $hash{'RemoteUserCpu'}, "RemoteUserCpu");
  } else {
    $hash{'RemoteUserCpu'} = 0;
  }
  if ( defined ($hash{'LocalUserCpu'})) {
    # Sample: LocalUserCpu = 0.000000
    print $py Create_Try_Except("r.TimeDuration", $hash{'LocalUserCpu'}, "LocalUserCpu");
  } else {
    $hash{'LocalUserCpu'} = 0;
  }
  if ( defined ($hash{'RemoteSysCpu'})) {
    # Sample: RemoteSysCpu = 36.000000
    print $py Create_Try_Except("r.TimeDuration", $hash{'RemoteSysCpu'}, "RemoteSysCpu");
  } else {
    $hash{'RemoteSysCpu'} = 0;
  }
  if ( defined ($hash{'LocalSysCpu'})) {
    # Sample: LocalSysCpu = 0.000000
    print $py Create_Try_Except("r.TimeDuration", $hash{'LocalSysCpu'}, "LocalSysCpu");
  } else {
    $hash{'LocalSysCpu'} = 0;
  }

  if ( defined ($hash{'CumulativeSuspensionTime'})) {
    # Sample: CumulativeSuspensionTime = 0
    print $py Create_Try_Except("r.TimeDuration", $hash{'CumulativeSuspensionTime'}, "CumulativeSuspensionTime");
  }
  if ( defined ($hash{'CommittedTime'})) {
    # Sample: CommittedTime = 0
    print $py Create_Try_Except("r.TimeDuration", $hash{'CommittedTime'}, "CommittedTime");
  }

  # 2.11 CpuDuration - "CPU time used, summed over all processes in the job"
  $hash{'SysCpuTotal'} = $hash{'RemoteSysCpu'} + $hash{'LocalSysCpu'};
  print $py qq/r.CpuDuration(int(float(/ . $hash{'SysCpuTotal'} .
    qq/)), "system", "Was entered in seconds")\n/;
  $hash{'UserCpuTotal'} = $hash{'RemoteUserCpu'} + $hash{'LocalUserCpu'};
  print $py qq/r.CpuDuration(int(float(/ . $hash{'UserCpuTotal'} .
    qq/)), "user", "Was entered in seconds")\n/;

  # 2.12 EndTime - "The time at which the job completed"
  if ( (defined($hash{'CompletionDate'})) &&
       ($hash{'CompletionDate'} != 0) )
  {
    # Sample: CompletionDate = 1126898099
    print $py qq/r.EndTime(/ . int($hash{'CompletionDate'}) .
      qq/,\"Was entered in seconds\")\n/;
  }

  # 2.13 StartTime - The time at which the job started"
  if ( defined ($hash{'JobStartDate'})) {
    # Sample: JobStartDate = 1126887848
    print $py qq/r.StartTime(/ . int($hash{'JobStartDate'}) .
      qq/,\"Was entered in seconds\")\n/;
  }

  # ?.?? TimeInstant - According to Gratia.py, "a discrete time that
  #    is relevant to the reported usage time." Type can be 'submit',
  #      'connect', or 'other'

  # I parse the Submit hostname up in 2.7 out of the GlobalJobId
  #      sample: GlobalJobId = "fngp-osg.fnal.gov#1124148654#4713.0"
  if ( defined ($condor_submit_host)) {
    # 2.14 MachineName - can be host name or the sites name for a cluster
    print $py qq/r.MachineName(\"/ . $condor_submit_host . qq/\")\n/;
    # 2.16 SubmitHost - hostname where the job was submitted
    print $py qq/r.SubmitHost(\"/ . $condor_submit_host . qq/\")\n/;
  }

  # 2.15 Host - hostname where the job ran and boolean for Primary
  # Host must be type DomainName so I must strip any reference to a
  #   virtual machine (which MIGHT be present)
  #      sample: LastRemoteHost = "vm1@fnpc210.fnal.gov"
  if ( defined ($hash{'LastRemoteHost'})) {
    # Sample: LastRemoteHost = "fnpc212.fnal.gov"
    if ($hash{'LastRemoteHost'} =~ /vm\d+?\@(.*)/) {
      $fqdn_last_rem_host = "$1";
    } else {
      $fqdn_last_rem_host = $hash{'LastRemoteHost'};
    }

    print $py qq/r.Host(\"/ . $fqdn_last_rem_host . qq/\",True)\n/;
  }

  # 2.17 - Queue - string, name of the queue from which job executed
  #    I have a field called JobUniverse under Condor
  #      sample: JobUniverse = 5
  if ( defined ($hash{'JobUniverse'})) {
    print $py qq/r.Queue(\"/ . $hash{'JobUniverse'} . 
      qq/\", \"Condor\'s JobUniverse field\")\n/;
  }

  # 2.18 - ProjectName - optional, effective GID (string)
  # I am unsure if this should be the AccountingGroup below ###

  # 2.19 - Network - optional, integer
  #        Can have storageUnit, phaseUnit, metric, description
  #        Metric should be one of 'total','average','max','min'

  # 2.20 - Disk - optional, integer, disk storage used, may have 'type'
  #        Type can be one of scratch or temp

  # 2.21 - Memory - optional, integer, mem use by all concurrent processes

  # 2.22 - Swap - optional, integer

  # 2.23 - NodeCount - optional, positive integer - physical nodes
  if ( defined ($hash{'MaxHosts'})) {
    # Sample: MaxHosts = 1
    print $py qq/r.NodeCount(\"/ . $hash{'MaxHosts'} . qq/\", "max", )\n/;
  }

  # 2.24 - Processors - optional, positive integer - processors used/requested

  # 2.25 - ServiceLevel - optional, string (referred to as record identity?)
    
  # To use r.AddAdditionalInfo: record.AddAdditionalInfo("name",value)
  #    where value can be a string or number
  if ( defined ($hash{'MyType'})) {
    # Sample: MyType = "Job"
    print $py qq/r.AdditionalInfo(\"CondorMyType\", \"/,
      $hash{'MyType'}, qq/\")\n/;
  }
  if ( defined ($hash{'AccountingGroup'})) {
    # Sample: AccountingGroup = "group_sdss.sdss"
    print $py qq/r.AdditionalInfo(\"AccountingGroup\", \"/,
      $hash{'AccountingGroup'}, qq/\")\n/;
  }
  if ( defined ($hash{'ExitBySignal'})) {
    # Sample: ExitBySignal = FALSE
    print $py qq/r.AdditionalInfo(\"ExitBySignal\", \"/,
      $hash{'ExitBySignal'}, qq/\")\n/;
  }
  if ( defined ($hash{'ExitSignal'})) {
    print $py qq/r.AdditionalInfo(\"ExitSignal\", \"/,
      $hash{'ExitSignal'}, qq/\")\n/;
  }
  if ( defined ($hash{'ExitCode'})) {
    # Sample: ExitCode = 0
    print $py qq/r.AdditionalInfo(\"ExitCode\", \"/,
      $hash{'ExitCode'}, qq/\")\n/;
  }
  if ( defined ($hash{'JobStatus'})) {
    # Sample: JobStatus = 4
    print $py qq/r.AdditionalInfo(\"condor.JobStatus\", \"/,
      $hash{'JobStatus'}, qq/\")\n/;
  }
  if ($have_GratiaJobOrigin_in_JobManagers) {
    if ($hash{'GratiaJobOrigin'} and
        $hash{'GratiaJobOrigin'} eq 'GRAM') {
      # If this exists, we have a real grid record
      print $py q/r.Grid("OSG", "GratiaJobOrigin = GRAM")/, "\n";
    } else {                      # Non-GRAM job
      print $py q/r.Grid("Local", "GratiaJobOrigin not GRAM")/, "\n";
    }
  }
  #print $py qq/r.AdditionalInfo(\"\", \"/ . $hash{''} . qq/\")\n/;
  # Sample:

  print $py "Gratia.Send(r)\n";
  print $py "#\n";
  ++$count_submit;
  if (($count_submit % $max_batch_size) == 0) {
    open_new_py();
  }
  return 1;

  # Moved to outer block
  # $py->close;
}                               # End of subroutine Feed_Gratia

#------------------------------------------------------------------
# Subroutine Read_ClassAd
#   This routine will read in a ClassAd from the given
# file name and return a hash containing the data.
#------------------------------------------------------------------
sub Read_ClassAd {

  my $filename = shift;

  unless (open(FH, $filename)) {
    warn "error opening $filename: $!\n";
    return ();
  }

  my %condor_hist_data;
  while ($line = <FH>) {
    chomp $line;

    # Most lines look something like:  MyType = "Job"
    if ($line =~ /(\S+) = (.*)/) {

      $element = $1;  $value=$2;

      # Strip double quotes where needed
      if ($value =~ /"(.*)"/) {
        $value = $1;
      }

      # Place attribute in the hash and escape it properly
      $condor_hist_data{$element} = PythonStringLiteral($value);
    } elsif ($line =~ /\S+/) {
      warn "Invalid line in ClassAd: $line\n";
      return ();
    }
  }

  create_unique_id(%condor_hist_data);

  return %condor_hist_data;
}

#------------------------------------------------------------------
# Subroutine Query_Condor_History
#   This routine will call 'condor_history' to gather additional
# data needed to report this job's accounting data.
#------------------------------------------------------------------
sub Query_Condor_History {
  my $cluster_id = shift;
  my $proc_id = shift || 0;
  my $record_in;
  my %condor_hist_data = ();
  my $fh = new FileHandle;

  my $current_condor_hist_cmd = "$condor_hist_cmd";

  my %seen_history_list = ( ${condor_hist_file} => 1);

 HISTORY_SEARCH:
  {
    if ($cluster_id) {
      $fh->open("$current_condor_hist_cmd -l $cluster_id.$proc_id |")
        or die "Unable to open condor_history pipe\n";
    } else {
      warn "Tried to call condor_history with no cluster_id data.\n";
      return ();
    }

    #unless (defined ($header = <CHIST>)) {
    #    warn "The condor_history pipe returned empty?  (ClusterID: $cluster_id)\n";
    #    return ();
    #  }

    #Test the first line returned to be sure the history command worked
    #unless ($header =~ /\(ClusterId == (\d+)\)/ && $cluster_id == $1) {
    #  warn "Unexpected first line of condor history returned ($header)\n";
    #}

    #Load the remaining lines into a hash
    my $record_seen;
    my $record_not_found;
    while ($record_in = <$fh>) {
      $record_seen = 1;
      # Most lines look something like:  MyType = "Job"
      if ($record_in =~ /(\S+) = (.*)/) {
        $element = $1;  $value=$2;
          
        # Strip double quotes where needed
        if ($value =~ /"(.*)"/) {
          $value = $1;
        }
        $condor_hist_data{$element} = $value;
      } elsif ($record_in =~ /-- Quill/) {
        # Quill header looks like:
        #    -- Quill: quill@fngp-osg.fnal.gov : <fngp-osg.fnal.gov:5432> : quill
        if ($verbose && $debug_mode) { 
          print "Query_Condor_History got Quill history data\n";
          print $record_in;
        }
      } elsif ($record_in =~ /No historical jobs in the database match your query/) {
        $record_not_found = 1;
        last;
      } elsif ($record_in =~ /\S+/) {
        warn "Could not parse: $record_in (skipping)\n";
      }
    }
    $fh->close();
    if ($record_not_found or not $record_seen) {
      undef $record_seen;
      undef $record_not_found;
      # Look in other places
      # Don't do the glob until now just in case there's a race on.
      my @condor_history_file_list = glob("${condor_hist_file}*");
      my $next_history_file;
      while ($next_history_file = shift @condor_history_file_list and
             exists $seen_history_list{$next_history_file}) {
      }
      if ($next_history_file) {
        $current_condor_hist_cmd = "$condor_hist_cmd -f $next_history_file";
        $seen_history_list{$next_history_file} = 1;
        redo HISTORY_SEARCH;
      }
      if ($verbose) {
        warn "Query_Condor_History found no record of this job\n";
      }
      return ();
    }
  }
  if ($condor_hist_data{'GlobalJobId'}) {
    create_unique_id(%condor_hist_data);
    return %condor_hist_data;
  } else {
    if ($verbose) {
      warn "Query_Condor_History could not locate a GlobalJobId.\n";
      return ();
    }
  }
}                               # End of subroutine Query_Condor_History

#------------------------------------------------------------------
# Subroutine create_unique_id
#   Handle creation of a unique ID based on the job's GlobalJobId, if it
# has one.
#------------------------------------------------------------------
sub create_unique_id(\%) {
  my ($condor_hist_data) = @_;

  if ($condor_hist_data->{'GlobalJobId'}) {
	if ($condor_hist_data->{'GlobalJobId'} =~ /"(.*)"/) {
        $condor_hist_data->{'GlobalJobId'} = $1;

      }
    $condor_hist_data->{'UniqGlobalJobId'} =
      'condor.' . $condor_hist_data->{'GlobalJobId'};
    if ($verbose && $debug_mode) {
      print "Unique ID: $condor_hist_data->{'UniqGlobalJobId'}\n";
    }
  }
}

#------------------------------------------------------------------
# Subroutine Process_004
#   This routine will process a type 004 eviction record. A hash
#   of data describing the job is returned.
#
# Sample '004 Job was evicted' event record
# 004 (16110.000.000) 10/31 11:46:13 Job was evicted.
#   (0) Job was not checkpointed.
#     Usr 0 00:00:00, Sys 0 00:00:00  -  Run Remote Usage
#     Usr 0 00:00:00, Sys 0 00:00:00  -  Run Local Usage
#   0  -  Run Bytes Sent By Job
#   0  -  Run Bytes Received By Job
# ...
#------------------------------------------------------------------
sub Process_004 {
  my $filename = shift;
  my @term_event = @_;          # A Job evicted (004) event
  my $next_line = "";
  my $return_value = 0;
  my %condor_history = ();

  # Extract values from the ID line --------------------------------
  $id_line = shift @term_event;

  unless ($id_line =~ /004\s(\S+)\s(\S+)\s(\S+)/) {
    warn "Error parsing the 'Job was evicted' record:\n$id_line";
    return ();
  }
  $job_id = $1;                 # $end_date = $2; $end_time = $3;
  #if ($verbose) {
  #  print "(Process_004) From $id_line: I got id $job_id which ended $end_date at $end_time\n";
  #}

  if ($job_id =~ /\((\d+)\.(\d+)\.(\d+)\)/) {
    $cluster_id = $1;           # $cluster_field2 = $2; $cluster_field3 = $3;
    $proc_id = $2 || 0;
    if ($verbose) {
      print "(Process_004) From $job_id: I got ClusterId $cluster_id, ProcId $proc_id\n";
    }
  } else {
    warn "(Process_004) Error parsing the 'Job id' field: $job_id";
    return ();
  }

  # Next line indicates if the job checkpointed --------------
  $next_line = shift @term_event;
  if ($next_line =~ /was not checkpointed/) {
    if ($verbose) {
      print "\n" . basename($filename) . 
        ": Cluster_Id $cluster_id was evicted but did not checkpoint.\n";
    }
  }

  # The next two lines have CPU usage data ------------------------
  $next_line = shift @term_event;
  if ($next_line =~ /Usr (\d ..:..:..), Sys (\d ..:..:..).*Run Remote/) {
    $rem_usr_cpu = $1;  $rem_sys_cpu = $2;
    $rem_usr_cpusecs = NumSeconds($rem_usr_cpu);
    $rem_sys_cpusecs = NumSeconds($rem_sys_cpu);
  }

  $next_line = shift @term_event;
  if ($next_line =~ /Usr (\d ..:..:..), Sys (\d ..:..:..).*Run Local/) {
    $lcl_usr_cpu = $1;  $lcl_sys_cpu = $2;
    $lcl_usr_cpusecs = NumSeconds($lcl_usr_cpu);
    $lcl_sys_cpusecs = NumSeconds($lcl_sys_cpu);
  }

  $rem_cpusecs = $rem_usr_cpusecs + $rem_sys_cpusecs;
  $lcl_cpusecs = $lcl_usr_cpusecs + $lcl_sys_cpusecs;
  # Now print only the significant results
  if ($verbose) {
    print "   Remote task CPU Duration: $rem_cpusecs seconds"
      . "($rem_usr_cpusecs/$rem_sys_cpusecs)\n"
        if ($rem_cpusecs);

    print    "Local task CPU Duration: $lcl_cpusecs seconds"
      . "($lcl_usr_cpusecs/$lcl_sys_cpusecs)\n" 
        if ($lcl_cpusecs);
  }
  unless ($cluster_id) {
    die "Somehow we got here without getting a cluster id"
  }

  if (checkSeenLocalJobId($cluster_id, $proc_id)) {
    print "Process_004 ignoring already-seen job $cluster_id.$proc_id\n"
      if $verbose;
    return ( ClusterId => $cluster_id,
             ProcId => $proc_id );
  }

  unless ( (%condor_history = Query_Condor_History($cluster_id, $proc_id)) &&
           (defined ($condor_history{'GlobalJobId'})) ) {
    warn "This job ($cluster_id) had no record in Condor History.\n";
    return ();                  # Failure - return an empty hash
  }

  if ($verbose) {
    print "Query_Condor_History returned GlobalJobId of " .
      $condor_history{'GlobalJobId'} . "\n";
  }

  return %condor_history;
}                               # End of Subroutine Process_004 --------------------

#------------------------------------------------------------------
# Subroutine Process_005
#   This routine will process a type 005 termination record. A hash
#   of data describing the job is returned.
#
# Sample '005 Job terminated' event record
# 005 (10078.000.000) 10/18 17:47:49 Job terminated.
#         (1) Normal termination (return value 1)
#                 Usr 0 05:50:41, Sys 0 00:00:11  -  Run Remote Usage
#                 Usr 0 00:00:00, Sys 0 00:00:00  -  Run Local Usage
#                 Usr 0 05:50:41, Sys 0 00:00:11  -  Total Remote Usage
#                 Usr 0 00:00:00, Sys 0 00:00:00  -  Total Local Usage
#         0  -  Run Bytes Sent By Job
#         0  -  Run Bytes Received By Job
#         0  -  Total Bytes Sent By Job
#         0  -  Total Bytes Received By Job
# ...
#------------------------------------------------------------------
sub Process_005 {
  my $filename = shift;
  my @term_event = @_;          # A Terminate (005) event
  my $next_line = "";
  my $return_value = 0;
  my %condor_history = ();

  # Extract values from the ID line --------------------------------
  $id_line = shift @term_event;

  unless ($id_line =~ /005\s(\S+)\s(\S+)\s(\S+)/) {
    warn "Error parsing the 'Job terminated' record:\n$id_line";
    return ();
  }
  $job_id = $1;                 # $end_date = $2; $end_time = $3;
  #if ($verbose) {
  #  print "(Process_005) From $id_line: I got id $job_id which ended $end_date at $end_time\n";
  #}

  if ($job_id =~ /\((\d+)\.(\d+)\.(\d+)\)/) {
    $cluster_id = $1;           # $cluster_field2 = $2; $cluster_field3 = $3;
    $proc_id = $2 || 0;
    if ($verbose) {
      print "(Process_005) From $job_id: I got ClusterId $cluster_id, ProcId $proc_id\n";
    }
  } else {
    warn "(Process_005) Error parsing the 'Job id' field: $job_id";
    return ();
  }

  # Next line indicates what job termination returned --------------
  $next_line = shift @term_event;
  if ($next_line =~ /Normal termination/) {
    # This was a Normal termination event
    if ($next_line =~ /return value (\d*)/) {
      $return_value = $1;
      if ($verbose) {
        print "\n" . basename($filename) . 
          ": Cluster_Id $cluster_id had return value: $return_value\n";
      }
    } else {
      warn "Malformed termination record:\n";
      warn "$next_line";
    }
  } else {
    warn "Event was not a Normal Termination\n";
    warn "$next_line";
  }

  # The next four lines have CPU usage data ------------------------
  $next_line = shift @term_event;
  if ($next_line =~ /Usr (\d ..:..:..), Sys (\d ..:..:..).*Run Remote/) {
    $rem_usr_cpu = $1;  $rem_sys_cpu = $2;
    $rem_usr_cpusecs = NumSeconds($rem_usr_cpu);
    $rem_sys_cpusecs = NumSeconds($rem_sys_cpu);
  }

  $next_line = shift @term_event;
  if ($next_line =~ /Usr (\d ..:..:..), Sys (\d ..:..:..).*Run Local/) {
    $lcl_usr_cpu = $1;  $lcl_sys_cpu = $2;
    $lcl_usr_cpusecs = NumSeconds($lcl_usr_cpu);
    $lcl_sys_cpusecs = NumSeconds($lcl_sys_cpu);
  }

  $rem_cpusecs = $rem_usr_cpusecs + $rem_sys_cpusecs;
  $lcl_cpusecs = $lcl_usr_cpusecs + $lcl_sys_cpusecs;

  $next_line = shift @term_event;
  if ($next_line =~ /Usr (\d ..:..:..), Sys (\d ..:..:..).*Total Remote/) {
    $rem_usr_cpu_total = $1;  $rem_sys_cpu_total = $2;
    $rem_usr_cpusecs_total = NumSeconds($rem_usr_cpu_total);
    $rem_sys_cpusecs_total = NumSeconds($rem_sys_cpu_total);
  }

  $next_line = shift @term_event;
  if ($next_line =~ /Usr (\d ..:..:..), Sys (\d ..:..:..).*Total Local/) {
    $lcl_usr_cpu_total = $1;  $lcl_sys_cpu_total = $2;
    $lcl_usr_cpusecs_total = NumSeconds($lcl_usr_cpu_total);
    $lcl_sys_cpusecs_total = NumSeconds($lcl_sys_cpu_total);
  }

  $rem_cpusecs_total = $rem_usr_cpusecs_total + $rem_sys_cpusecs_total;
  $lcl_cpusecs_total = $lcl_usr_cpusecs_total + $lcl_sys_cpusecs_total;

  # Now print only the significant results
  if ($verbose) {
    print "   Remote task CPU Duration: $rem_cpusecs seconds"
      . "($rem_usr_cpusecs/$rem_sys_cpusecs)\n"
        if ($rem_cpusecs && $rem_cpusecs != $rem_cpusecs_total);
    print    "Local task CPU Duration: $lcl_cpusecs seconds"
      . "($lcl_usr_cpusecs/$lcl_sys_cpusecs)\n" 
        if ($lcl_cpusecs && $lcl_cpusecs != $lcl_cpusecs_total);
    print "   Remote CPU Duration: $rem_cpusecs_total seconds"
      . "($rem_usr_cpusecs_total/$rem_sys_cpusecs_total)\n";
    print "   Local CPU Duration: $lcl_cpusecs_total seconds"
      . "($lcl_usr_cpusecs_total/$lcl_sys_cpusecs_total)\n"
        if ($lcl_cpusecs_total);
  }
  unless ($cluster_id) {
    die "Somehow we got here without getting a cluster id"
  }

  if (checkSeenLocalJobId($cluster_id, $proc_id)) {
    print "Process_005 ignoring already-seen job $cluster_id.$proc_id\n"
      if $verbose;
    return ( ClusterId => $cluster_id,
             ProcId => $proc_id );
  }

  unless ((%condor_history = Query_Condor_History($cluster_id)) &&
          (defined ($condor_history{'GlobalJobId'})) ) {
    warn "This job ($cluster_id) had no record in Condor History.\n";
    return ();                  # Failure - return an empty hash
  }
  if ($verbose) {
    print "Query_Condor_History returned GlobalJobId of " .
      $condor_history{'GlobalJobId'} . "\n";
  }

  $condor_history{'RemCpuSecsTotal'} = $rem_cpusecs_total;
  $condor_history{'JobCpuSecsTotal'} = $rem_cpusecs_total + $lcl_cpusecs_total;

  return %condor_history;
}                               # End of Subroutine Process_005 --------------------

#------------------------------------------------------------------
# Subroutine Usage_message
#   This routine prints the standard usage message.
#------------------------------------------------------------------
sub Usage_message {
  print "$progname version $prog_version ($prog_revision)\n\n";
  print "USAGE: $0 \\\n";
  print "          [-c <constraint>] \\\n";
  print "          [-f <filename>] \\\n";
  print "          [-s <filename>] \\\n";
  print "          [-dlrvx] \\\n";
  print "          <directoryname | filename> ...\n";
  print "\n";
  print "where -c gives a constraint (<attr>=<value>) " .
    "for which ads to process\n";
  print "      -d enables deletion of processed log files\n";
  print "      -f specifies a Gratia configuration file to use\n";
  print "      -l outputs a listing of what was done\n";
  print "      -r forces reprocessing of pending transmissions\n";
  print "      -s gives a state file in which to save the last job processed\n";
  print "          from the globus-condor.log file\n";
  print "      -v causes verbose output\n";
  print "      -x enters debug mode\n\n";

  return;
}                               # End of Subroutine Usage_message  --------------------

#------------------------------------------------------------------
# Subroutine generate_ws_stubs
#   This routine generates GRAM log files for previously unprocessed
#   jobs.
#------------------------------------------------------------------
sub generate_ws_stubs {
  my $gram_log = shift; # Log file
  return unless ($gram_log_state_file and $stub_dir and (-d $stub_dir));
  # Check state file
  my $gram_state = `grep -m 1 -e "^$gram_log"'	' "$gram_log_state_file" 2>/dev/null`;
  chomp $gram_state;
  $gram_state =~ s&^$gram_log\t&&;
  my ($last_clusterId, $last_proc, $last_subproc, $last_event_type) = split /\t/, $gram_state;
  my ($latest_clusterId, $latest_proc, $latest_subproc, $latest_event_type);
  # Read log backwards
  open(GRAM_LOG, "tac $gram_log|") or do {
    warn "WARNING: unable to open $gram_log_state_file";
    return;
  };
  my %event_hash = ();
  my $in_proc;
  while (<GRAM_LOG>) {
    chomp;
    if (m&^</c>$&) {            # Begin record (reading backwards, remember)
      %event_hash = ();
      $in_proc = 1;
      $record_buffer = "";
      next;
    }
    if (m&^\s*<a\s+n="([^\"]+)">&) { # Attribute line
      my $attr = $1;
      $attr = 'ClusterId' if ($attr =~ /^Cluster$/);
      if (/<s>([^<]+)<\/s>/) {
        $event_hash{$attr} = $1;
      } elsif (/<i>([^<]+)<\/i>/) {
        $event_hash{$attr} = int($1);
      } elsif (/<b v="([tf])"\/>/) {
        $event_hash{$attr} = ($1 eq 't');
      } elsif (/<r>([^<]+)<\/r>/) {
        $event_hash{$attr} = $1;
      }
      next;
    }
    if (m&^<c>$&) {             # End record (reading backwards)
      next unless $in_proc;     # Never saw the open
      undef $in_proc;
      unless (defined $latest_clusterId) { # For next entry into state file
        $latest_clusterId = $event_hash{'ClusterId'};
        $latest_proc = $event_hash{'Proc'};
        $latest_subproc = $event_hash{'Subproc'};
        $latest_event_type = $event_hash{'EventTypeNumber'};
      }
      last if                   # Check if we're done.
        $last_clusterId == $event_hash{'ClusterId'} and
          $last_proc == $event_hash{'Proc'} and
            $last_subproc == $event_hash{'Subproc'} and
              $last_event_type == $event_hash{'EventTypeNumber'};
      # If we have a real terminate event, write the stub file.
      if ($event_hash{'EventTypeNumber'} == 4 or
          $event_hash{'EventTypeNumber'} == 5) {
        ++$count_stub_writes;
        print "Writing stub for ", $event_hash{'ClusterId'}, ".", $event_hash{'Proc'},
          " event type ", $event_hash{'EventTypeNumber'}, "\n" if $verbose;
        my $stub_file = "gratia_condor_log.$event_hash{'ClusterId'}.$event_hash{'Proc'}.log";
        open(GRAM_STUB, ">$stub_dir/$stub_file") or die
          "Unable to open $stub_dir/$stub_file for write!";
        print GRAM_STUB "$_\n$record_buffer"; # Don't forget the record opener
        close GRAM_STUB;
      }
      next;
    }
  } continue {
    $record_buffer = "$_\n${record_buffer}"; # Needs to be forward
  }
  close GRAM_LOG;
  my $gram_state_line =
    "$gram_log\t$latest_clusterId\t$latest_proc\t$latest_subproc\t$latest_event_type\n";
  if (-e $gram_log_state_file) {
    # Remove our line quickly. Yes, I know.
    system("perl -wni.bak -e 'm&^\Q$gram_log\E\\t& or print;' \"$gram_log_state_file\"");
  }
  # Write our new state line to the end of the file.
  open (GRAM_STATE, ">>$gram_log_state_file") or
    die "Unable to open $gram_log_state_file for write";
  print GRAM_STATE $gram_state_line;
  close GRAM_STATE;
}

sub job_identifier {
  my @identifiers = @_;
  if (@identifiers == 1) {      # Only ClusterId (maybe)
    @identifiers = split /\./, join(".", @identifiers);
  }
  @identifiers = @identifiers[0 .. 2];
  for (my $loop = 0; $loop < 2; ++$loop) {
    $identifiers[$loop] = 0 unless $identifiers[$loop];
  }
  my $job_id = join(".", map { sprintf "%d", ($_ || 0); } @identifiers );
  print "job_identifier returning $job_id\n" if $verbose;
  return $job_id;
}

my %seenLocalJobIds = ();
sub setSeenLocalJobId {
  my $job_id = job_identifier(@_);
  $seenLocalJobIds{$job_id} = 1;
  print "setSeenLocalJobId recording job ", $job_id, "\n" if $verbose;
}

sub checkSeenLocalJobId {
  my $job_id = job_identifier(@_);
  my $result = (exists $seenLocalJobIds{$job_id} and $seenLocalJobIds{$job_id});
  print "checkSeenLocalJobId returning ", $result,
    " for job ", $job_id, "\n" if $verbose;
  return $result;
}

sub close_py_and_cleanup {
  $py->close() if $py;
  # Now we have closed the Python pipe, I can delete the log files that
  # were just processed.
  if ($delete_flag) {
    foreach $plog (@processed_logfiles) {
      if (unlink ($plog)) {
        if ($verbose) {
          print "Removed logfile ($plog)\n";
        }
      } else {
        warn "Unable to remove logfile ($plog)\n"
      }
    }
  }
  @processed_logfiles = (); # Reset
}

sub open_new_py {
  close_py_and_cleanup();
  $py = new FileHandle;
  # Temporary file for debug purposes only.
  my $tmp_py = $debug_mode?printf("tee \"%s/tmp.py\" |",
                                  dirname($gram_log_state_file)):"";
  my $py_out = $debug_mode?printf(">\"%s/py.out\" 2>&1",
                                  dirname($gram_log_state_file)):">/dev/null 2>&1";
  $py->open("|$tmp_py python -u $py.out");
  autoflush $py 1;
  print $py "import Gratia\n\n";
  print $py "Gratia.RegisterReporter(\"condor_meter.pl\", \"",
    $prog_revision, " (tag ", $prog_version, ")\")\n";
  if ($condor_version) {
    print $py "Gratia.RegisterService(\"Condor\", \"",
      $condor_version, "\")\n";
  }
  print $py "Gratia.setProbeBatchManager(\"condor\")\n";
  if (defined($gratia_config)) {
    print $py "Gratia.Initialize(\"$gratia_config\")\n";
  } else {
    print $py "Gratia.Initialize()\n";
  }
  if ( $reprocess_flag ) {
    # I should probably add a test here to see if there are files waiting
    print $py "Gratia.Reprocess()\n";

    # If someone uses the '-r' option to reprocess working files, should
    #   the program end here?  If one is sending new data, the '-r' is 
    #   redundant as we will reprocess any left over files when we start
    #   sending this data.
    exit 0;
  }
  return;
}

#==================================================================
#==================================================================
# End of Program - condor_meter-pl
#==================================================================


# Variables defined for EMACS editor usage
# Local Variables:
# mode:perl
# comment-start: "# "
# eval: (setq perl-continued-brace-offset -2 perl-continued-statement-offset 2 perl-indent-level 2 perl-label-offset -1)
# End:

