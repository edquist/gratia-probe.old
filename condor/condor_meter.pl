#!/usr/bin/env perl
#
# condor_meter.pl - Prototype for an OSG Accouting 'meter' for Condor
#       By Ken Schumacher <kschu@fnal.gov> Began 5 Nov 2005
# $Id: condor_meter.pl,v 1.19 2008-05-07 19:57:24 greenc Exp $
# Full Path: $Source: /var/tmp/move/gratia/probe/condor/condor_meter.pl,v $
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

use English;   # For readability
use strict 'refs', 'subs';
use FileHandle;
use File::Basename;
#use XML::Parser;

sub create_unique_id(\%);

my $progname = "condor_meter.pl";
my $prog_version = '$Name: not supported by cvs2svn $';
$prog_version =~ s&\$Name(?::\s*)?(.*)\$$&$1&;
$prog_version or $prog_version = "unknown";
my $prog_revision = '$Revision: 1.19 $ ';   # CVS Version number
#$true = 1; $false = 0;
$verbose = 1;

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
	    ($hash{$constraint_attr} ne $constraint_value))
	{
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
  print $py "r = Gratia.UsageRecord(\"Batch\")\n";
  
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

  # Philippe asked if I could strip the first '/' and change all other
  # '/' (used as seperators) to ', '  (that's comma and space)
  if ( defined ($hash{'x509userproxysubject'})) {
    if ($hash{'x509userproxysubject'} =~ m%^/(.*)%) {
      ($uki = $1) =~ s(/) (, )g;
      print $py qq/r.UserKeyInfo("$uki")\n/;
    } else {
      print $py qq/r.UserKeyInfo("$hash{'x509userproxysubject'}")\n/;
    }
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
    print $py qq/r.WallDuration(int(/ . $hash{'RemoteWallClockTime'} .
      qq/),\"Was entered in seconds\")\n/;
  }

  # TimeDuration - According to Gratia.py, "an additional measure
  #    of time duration that is relevant to the reported usage." type
  #    can be 'submit', 'connect', 'dedicated', or 'other'
  # NOTE: First I will submit the time durations that I found, then I
  #       set the ones that were not found to zero so later math does
  #       not fail due to an undefined value.
  if ( defined ($hash{'RemoteUserCpu'})) {
    # Sample: RemoteUserCpu = 9231.000000
    print $py qq/r.TimeDuration(/ . $hash{'RemoteUserCpu'} .
      qq/, \"RemoteUserCpu\")\n/;
  } else {
    $hash{'RemoteUserCpu'} = 0;
  }
  if ( defined ($hash{'LocalUserCpu'})) {
    # Sample: LocalUserCpu = 0.000000
    print $py qq/r.TimeDuration(/ . $hash{'LocalUserCpu'} .
      qq/, \"LocalUserCpu\")\n/;
  } else {
    $hash{'LocalUserCpu'} = 0;
  }
  if ( defined ($hash{'RemoteSysCpu'})) {
    # Sample: RemoteSysCpu = 36.000000
    print $py qq/r.TimeDuration(/  . $hash{'RemoteSysCpu'} .
      qq/, \"RemoteSysCpu\")\n/;
  } else {
    $hash{'RemoteSysCpu'} = 0;
  }
  if ( defined ($hash{'LocalSysCpu'})) {
    # Sample: LocalSysCpu = 0.000000
    print $py qq/r.TimeDuration(/  . $hash{'LocalSysCpu'} .
      qq/, \"LocalSysCpu\")\n/;
  } else {
    $hash{'LocalSysCpu'} = 0;
  }

  if ( defined ($hash{'CumulativeSuspensionTime'})) {
    # Sample: CumulativeSuspensionTime = 0
    print $py qq/r.TimeDuration(/ . $hash{'CumulativeSuspensionTime'} .
      qq/, \"CumulativeSuspensionTime\")\n/;
  }
  if ( defined ($hash{'CommittedTime'})) {
    # Sample: CommittedTime = 0
    print $py qq/r.TimeDuration(/ . $hash{'CommittedTime'} .
      qq/, \"CommittedTime\")\n/;
  }

  # 2.11 CpuDuration - "CPU time used, summed over all processes in the job"
  $hash{'SysCpuTotal'} = $hash{'RemoteSysCpu'} + $hash{'LocalSysCpu'};
  print $py qq/r.CpuDuration(int(/ . $hash{'SysCpuTotal'} .
    qq/), "system", "Was entered in seconds")\n/;
  $hash{'UserCpuTotal'} = $hash{'RemoteUserCpu'} + $hash{'LocalUserCpu'};
  print $py qq/r.CpuDuration(int(/ . $hash{'UserCpuTotal'} .
    qq/), "user", "Was entered in seconds")\n/;

  # 2.12 EndTime - "The time at which the job completed"
  if ( defined ($hash{'CompletionDate'})) {
    # Sample: CompletionDate = 1126898099
    print $py qq/r.EndTime(/ . $hash{'CompletionDate'} .
      qq/,\"Was entered in seconds\")\n/;
  }

  # 2.13 StartTime - The time at which the job started"
  if ( defined ($hash{'JobStartDate'})) {
    # Sample: JobStartDate = 1126887848
    print $py qq/r.StartTime(/ . $hash{'JobStartDate'} .
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
      qq/\", \"Condor's JobUniverse field\")\n/;
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
    print $py qq/r.AdditionalInfo(\"CondorMyType\", \"/
      . $hash{'MyType'} . qq/\")\n/;
  }
  if ( defined ($hash{'AccountingGroup'})) {
    # Sample: AccountingGroup = "group_sdss.sdss"
    print $py qq/r.AdditionalInfo(\"AccountingGroup\", \"/
      . $hash{'AccountingGroup'} . qq/\")\n/;
  }
  if ( defined ($hash{'ExitBySignal'})) {
    # Sample: ExitBySignal = FALSE
    print $py qq/r.AdditionalInfo(\"ExitBySignal\", \"/
      . $hash{'ExitBySignal'} . qq/\")\n/;
  }
  if ( defined ($hash{'ExitCode'})) {
    # Sample: ExitCode = 0
    print $py qq/r.AdditionalInfo(\"ExitCode\", \"/
      . $hash{'ExitCode'} . qq/\")\n/;
  }
  if ( defined ($hash{'JobStatus'})) {
    # Sample: JobStatus = 4
    print $py qq/r.AdditionalInfo(\"condor.JobStatus\", \"/
      . $hash{'JobStatus'} . qq/\")\n/;
  }
  #print $py qq/r.AdditionalInfo(\"\", \"/ . $hash{''} . qq/\")\n/;
  # Sample: 

  print $py "Gratia.Send(r)\n";
  print $py "#\n";
  $count_submit++;

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

      # Place attribute in the hash
      $condor_hist_data{$element} = $value;
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
  my $cluster_id = $_[0];
  my $record_in;
  my %condor_hist_data = ();
  my $fh = new FileHandle;

  my $current_condor_hist_cmd = "$condor_hist_cmd";

  my %seen_history_list = ( ${condor_hist_file} => 1);

 HISTORY_SEARCH:
  {
    if ($cluster_id) {
      $fh->open("$current_condor_hist_cmd -l $cluster_id |")
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
    if ($verbose) {
      print "(Process_004) From $job_id: I got ClusterId $cluster_id\n";
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

  unless ( (%condor_history = Query_Condor_History($cluster_id)) &&
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
    if ($verbose) {
      print "(Process_005) From $job_id: I got ClusterId $cluster_id\n";
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
  print "          [-dlrvx] \\\n";
  print "          <directoryname | filename> ...\n";
  print "\n";
  print "where -c gives a constraint (<attr>=<value>) " .
            "for which ads to process\n";
  print "      -d enables deletion of processed log files\n";
  print "      -f specifies a Gratia configuration file to use\n";
  print "      -l outputs a listing of what was done\n";
  print "      -r forces reprocessing of pending transmissions\n";
  print "      -v causes verbose output\n";
  print "      -x enters debug mode\n\n";

  return;
}                               # End of Subroutine Usage_message  --------------------

#==================================================================
#==================================================================
#  condor_meter.pl - Main program block
#==================================================================
autoflush STDERR 1; autoflush STDOUT 1;

# Initialization and Setup.
use Getopt::Std;

$opt_d = $opt_l = $opt_r = $opt_v = $opt_x = 0;

# Get command line arguments
unless (getopts('c:df:lrvx')) {
  Usage_message;
  exit 1;
}

$constraint_attr = $constraint_value = undef;
if (defined($opt_c)) {
	($constraint_attr, $constraint_value) = split("=", $opt_c, 2);
	unless (defined($constraint_value)) {
		die "ERROR: constraint must be of form <attr>=<value>";
	}
}

$delete_flag = ($opt_d == 1);
$gratia_config = $opt_f;
$report_results = ($opt_l == 1);
$reprocess_flag = ($opt_r == 1);
$verbose = ($opt_v == 1);
$debug_mode = ($opt_x == 1);

# After we have stripped off switches, there needs to be at least one 
#   directory or file name passed as an argument
if (! defined @ARGV) {
  print STDERR "No directories or filenames supplied.\n\n";
  Usage_message;
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

#------------------------------------------------------------------
# Locate and verify the path to the condor_history executable
use Env qw(CONDOR_LOCATION PATH); #Import only the Env variables we need
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

if ($verbose) {
  print "Condor_history at $condor_history\n";
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

#------------------------------------------------------------------
# Build a list of file names.  Add individual files given as command
# line arguments or select names from a directory specified.
my @logfiles = @processed_logfiles = ();  $logs_found=0;
foreach $name_arg (@ARGV) {
  if ( -f $name_arg && -s _ ) {
    # This argument is a non-empty plain file
    push(@logfiles, $name_arg); $logs_found++;
  } elsif ( -d $name_arg ) {
    # This argument is a directory name
    opendir(DIR, $name_arg)
      or die "Could not open the directory $name_arg.";
    while (defined($file = readdir(DIR))) {
      if ($file =~ /gram_condor_log\./ && -f "$name_arg/$file" && -s _ ) {
        # This plain, non-empty file looks like one of our log files
        push(@logfiles, "$name_arg/$file"); $logs_found++;
      }
      if ($file =~ /history\.\d+\.\d+/ && -f "$name_arg/$file" && -s _ ) {
        # This plain, non-empty file looks like a ClassAd
        push(@logfiles, "$name_arg/$file"); $logs_found++;
      }
    }
    closedir(DIR);
  }
}

# Remove old temporary files (if still there) used for debugging
foreach $tmp_file ( "/tmp/py.in", "/tmp/py.out" ) {
  if ( -e $tmp_file ) {
    unlink $tmp_file
      or warn "Unable to delete old file: $tmp_file\n";
  }
}

#------------------------------------------------------------------
# Open the pipe to the Gratia meter library process
$py = new FileHandle;
$py->open("| tee /tmp/py.in | python -u >/tmp/py.out 2>&1");
autoflush $py 1;
$count_submit = 0;

print $py "import Gratia\n";

if (defined($gratia_config)) {
	print $py "Gratia.Initialize(\"$gratia_config\")\n";
}
else {
	print $py "Gratia.Initialize()\n";
}

if ($logs_found == 0) {
  exit 0;
} else {
  if ($verbose) {
    print "Number of log files found: $logs_found\n";
  }
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

#------------------------------------------------------------------
# Get source file name(s)

my $count_orig = $count_orig_004 = $count_orig_005 = $count_orig_009 = 0;
my $count_xml = $count_xml_004 = $count_xml_005 = $count_xml_009 = 0;
my $ctag_depth = 0;

foreach $logfile (@logfiles) {

  open(LOGF, $logfile)
    or die "Unable to open logfile: $logfile\n";

  if ($verbose) {
    print "Processing file: $logfile\n";
  }

  $logfile_errors = 0;
  $logfile_constrained = 0;

  # See if the file is a per-job history file (a ClassAd)
  if ($logfile =~ /history.(\d+).(\d+)/) {

    # get the class ad from the file
    %condor_data_hash = Read_ClassAd($logfile);

    # check to see we got something
    if (! %condor_data_hash) {
      $logfile_errors++;
    }
    else {

      # add-in UniqGlobalJobId
      if ($condor_hist_data{'GlobalJobId'}) {
        $condor_hist_data{'UniqGlobalJobId'} =
          'condor.' . $condor_hist_data{'GlobalJobId'};
      }

      # check constraint then hand off data to gratia
      if (!Check_Constraint(%condor_data_hash)) {
        $logfile_constrained = 1;
      }
      elsif (!Feed_Gratia(%condor_data_hash)) {
        $logfile_errors++;
      }
    }
  }

  # Otherwise, get the first record to test format of the file
  elsif (defined ( $record_in = <LOGF> )) {
    # Clear the variables for each new event processed
    %condor_data_hash = ();
    #%logfile_hash = ();  @logfile_clusterids = ();

    if ($record_in =~ /\<c\>/) {
      #if ($debug_mode) { print "Processing as an XML format logfile.\n" }
      $count_xml++;             # This is counting XML log files (not records)
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
            $ctag_depth++;
          }
          if ($ctag_depth > 1) {
            warn "$logfile: Improperly formatted XML records, missing \<c/\>\n";
            $logfile_errors++;  # An error means we won't delete this log file
          }
          $event_hash = {};
          $last_was_c = 1;
        } else {
          $last_was_c = 0;
        }
        if (/<a n="([^"]+)">/) { # Attribute line --------------------
          my $attr = $1;

          # In the XML version of log files, the Cluster ID was
          # labeled just 'Cluster' rather than ClusterId' as it is in
          # the original format and in Condor_History
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
        } elsif (/<\/c>/) {     # Close tag --------------------
          if ($event_hash{'ClusterId'}) {
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
              # $logfile_errors++; # An error means we won't delete this log file
              #}
            } elsif ($event_hash{'EventTypeNumber'} == 1) { # Job began exectuting
              # ExecuteEvent: has Std and an ExecuteHost IP
            } elsif ($event_hash{'EventTypeNumber'} == 4) { # Job was Evicted
              $count_xml_004++;
              if (%condor_data_hash = 
                  Query_Condor_History($event_hash{'ClusterId'})) {
                if (!Check_Constraint(%condor_data_hash)) {
                  $logfile_constrained = 1;
                }
                elsif (!Feed_Gratia(%condor_data_hash)) {
                  warn "Failed to feed XML 004 event to Gratia\n";
                  $logfile_errors++; # An error means we won't delete this log file
                }
              } else {
              }
            } elsif ($event_hash{'EventTypeNumber'} == 5) { # Job finished
              # JobTerminatedEvent: has Std and several others
              $count_xml_005++;
              if (%condor_data_hash = 
                  Query_Condor_History($event_hash{'ClusterId'})) {
                if (!Check_Constraint(%condor_data_hash)) {
                  $logfile_constrained = 1;
                }
                elsif (!Feed_Gratia(%condor_data_hash)) {
                  warn "Failed to feed XML 005 event to Gratia\n";
                  $logfile_errors++; # An error means we won't delete this log file
                }
              } else {
                warn "No Condor History found (XML-5) - Logfile: " . 
                  basename($logfile) . " ClusterId: $event_hash{'ClusterId'}\n";
              }
            } elsif ($event_hash{'EventTypeNumber'} == 6) { # Image Size
              # JobImageSizeEvent: has Std and a Size
            } elsif ($event_hash{'EventTypeNumber'} == 9) { # Job Aborted
              # JobAbortedEvent: has Std and Reason (string)
              $count_xml_009++;
              # I think it is helpful to count these,
              # but there is no data in them worth reporting to Gratia
            }
          } else {
            warn "I have an XML event record with no Cluster Id.\n";
            $logfile_errors++;  # An error means we won't delete this log file
          }
          $ctag_depth--;
        }                       # End of close tag
      }
    } else {                    # Non-XML format
      #if ($debug_mode) {print "Processing as a non-XML format logfile.\n"} 
      #This is the original condor log file format
      $count_orig++;            # This is counting 005 files
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
            $count_orig_004++;
            if (%condor_data_hash =
                Process_004($logfile, @event_records)) {
              if ($verbose) {
                print "Process_004 returned Cluster_id of $condor_data_hash{'ClusterId'}\n";
              }
              if (!Check_Constraint(%condor_data_hash)) {
                $logfile_constrained = 1;
              }
              elsif (!Feed_Gratia(%condor_data_hash)) {
                $logfile_errors++;
              }
            } else {
              if ($verbose) {
                warn "No Condor History found (Orig-004) - Logfile: " .
                  basename($logfile) . "\n";
                $logfile_errors++; # An error means we won't delete this log file
              }
            }
          } elsif ($event_records[0] =~ /^005 /) {
            # Is this a '005 Job Terminated' event?
            $count_orig_005++;
            if (%condor_data_hash =
                Process_005($logfile, @event_records)) {
              if ($verbose) {
                print "Process_005 returned Cluster_id of $condor_data_hash{'ClusterId'}\n";
              }
              if (!Check_Constraint(%condor_data_hash)) {
                $logfile_constrained = 1;
              }
              elsif (!Feed_Gratia(%condor_data_hash)) {
                $logfile_errors++;
              }
            } else {
              if ($verbose) {
                warn "No Condor History found (Orig-005) - Logfile: " .
                  basename($logfile) . "\n";
                $logfile_errors++; # An error means we won't delete this log file
              }
            }
          } elsif ($event_records[0] =~ /^009 /) {
            $count_orig_009++;
            # While I think it is helpful to count these,
            # but there is no data in them worth reporting to Gratia
          }
          # Reset array to capture next event
          @event_records = ();
        }
      }
    }
  }
  close(LOGF);

  if ($delete_flag) {
    if ($logfile_errors != 0) {
      warn "Logfile ($logfile) was not removed due to errors ($logfile_errors)\n";
    } elsif ($logfile_constrained) {
      warn "Logfile ($logfile) was not removed due to unprocessed data (from -c)\n";
    }
    else {
      push @processed_logfiles, $logfile;
    }
  }                             # End of the 'foreach $logfile' loop.
}

# Close Python pipe to Gratia.py
$py->close;

# Now we have closed the Python pipe, I can delete the log files that
#    were just processed.
if ($delete_flag) {
  foreach $plog (@processed_logfiles) {
    if (unlink ($plog)) {
      if ($verbose) {
        print "Removed logfile ($plog)\n";
      }
    }
    else {
      warn "Unable to remove logfile ($plog)\n"
    }
  }
}

#------------------------------------------------------------------
# Wrap up and report results

$count_total = $count_orig + $count_xml;
if (($count_total > 1) && ($verbose || $report_results)) {
  print "Condor probe is done processing log files.\n";
  print "  Number of original format files: $count_orig\n"  if ($count_orig);
  print "         # of original 004 events: $count_orig_004\n"  if ($count_orig_004);
  print "         # of original 005 events: $count_orig_005\n"  if ($count_orig_005);
  print "         # of original 009 events: $count_orig_009\n"  if ($count_orig_009);
  print "       Number of XML format files: $count_xml\n"   if ($count_xml);
  print "              # of XML 004 events: $count_xml_004\n"  if ($count_xml_004);
  print "              # of XML 005 events: $count_xml_005\n"  if ($count_xml_005);
  print "              # of XML 009 events: $count_xml_009\n"  if ($count_xml_009);
  print "        Total number of log files: $count_total\n\n";
  print " # of records submitted to Gratia: $count_submit\n" if ($count_submit);
}

if ($verbose) {
  print "\nEnd of program: $progname\n";
}

exit 0;

#==================================================================
# End of Program - condor_meter-pl
#==================================================================

#==================================================================
# CVS Log
# $Log: not supported by cvs2svn $
# Revision 1.18  2008/05/06 21:53:04  greenc
# Apply Greg Quinn's contributed patch for constraint application.
#
# Revision 1.17  2008/05/01 13:13:59  greenc
# Retract erroneously committed (incomplete) changes to condor_meter.pl.
#
# Revision 1.15  2007/10/10 18:02:13  greenc
# Correct handling of ClassAd records.
#
# Revision 1.14  2007/09/24 21:41:09  greenc
# Remove dangerous behavior during use of debug flag.
#
# Revision 1.13  2007/09/04 17:15:55  pcanal
# Send a ping to Gratia even if there is no data to process
#
# Revision 1.12  2007/08/06 18:34:05  greenc
# /bin/env -> /usr/bin/env to satisfy Linux filesystem hierarchy standard.
#
# Revision 1.11  2007/05/18 20:40:58  greenc
# Fix problems discovered with new features during testing.
#
# Revision 1.10  2007/02/13 22:37:47  greenc
# Forward-looking improvement of embedded version (needs accompanying
# change to build script).
#
# Fix creatiion of UniqGlobalJobId to be appropriate for condor 6.9 and
# above.
#
# Revision 1.9  2007/02/13 22:32:05  greenc
# Copy of condor_meter.pl as provided by Greg Quinn, only altered to
# include differences between version upon which his was based (1.6) and
# current HEAD version (1.8).
#
# Revision 1.6  2007/01/04 18:05:21  greenc
# As Burt notes, <> should be <CONDOR_HISTORY_HELP>.
#
# Revision 1.5  2007/01/04 17:47:30  pcanal
# fix typo
#
# Revision 1.4  2006/10/24 14:42:29  greenc
# Only use -backwards and -match options if they are supported.
#
# Revision 1.3  2006/09/19 21:57:33  pcanal
# use faster condor_history lookup
#
# Revision 1.2  2006/08/22 18:04:25  pcanal
# use /bin/env
#
# Revision 1.1  2006/08/21 21:10:02  greenc
# Probe areas reorganized to facilitate RPM building and new
# probes.
#
# README files in probe/condor and probe/common still need to be
# updated.
#
# Probe tarball creation removed from build script per discussion with Greg. Please see probe/build/README.
#
# RPM building commissioned and will be tested shortly.
#
# Revision 1.6  2006/08/14 17:08:27  pcanal
# fix a couple of perl warning seen in the cms-t2 installation
#
# Revision 1.5  2006/07/25 22:14:51  pcanal
# accept to <c> in a row
#
# Revision 1.4  2006/07/20 14:41:48  pcanal
# permissions
#
# Revision 1.3  2006/07/20 14:38:53  pcanal
# change permisssion
#
# Revision 1.2  2006/06/16 15:57:37  glr01
# glr: reset condor-probe to contents from gratia-proto
#
# Revision 1.14  2006/05/03 18:32:08  kschu
# Generates no output unless there is an error
#
# Revision 1.13  2006/04/27 21:49:37  pcanal
# support 2 durations
#
# Revision 1.12  2006/04/21 15:49:19  kschu
# There is now no output, unless there is a problem, or you use the -v flag
#
# Revision 1.11  2006/04/20 15:33:41  kschu
# Corrected syntax error
#
# Revision 1.10  2006/04/19 21:59:05  kschu
# Removes log files after closing Python pipe
#
# Revision 1.9  2006/04/19 16:50:04  kschu
# Code in place and tested to remove logs after submitting to Gratia
#
# Revision 1.8  2006/04/17 22:23:50  kschu
# Added command line option to delete log files after processing.
#
# Revision 1.7  2006/04/13 15:55:34  kschu
# Processes filenames or directory as arguments
#
# Revision 1.6  2006/04/10 22:18:48  kschu
# Two small syntax errors, missing double quotes, fixed
#
# Revision 1.5  2006/04/10 20:35:46  pcanal
# fix TimeDuration calling sequence
#
# Revision 1.4  2006/04/10 19:52:30  kschu
# Refined data submission after code review
#
# Revision 1.3  2006/04/05 18:11:32  kschu
# Now processes XML log files as well as original format
#
# Revision 1.2  2006/03/06 18:09:11  kschu
# used to generate first set of test data
#
# Revision 1.1  2006/02/03 17:22:14  kschu
# First prototype - kschu@fnal.gov
#

# Variables defined for EMACS editor usage
# Local Variables:
# mode:perl
# comment-start: "# "
# End:

