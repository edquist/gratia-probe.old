package Globus::GRAM::JobManagerGratia;

use strict;
require Exporter;

use Globus::Core::Paths;
use XML::Simple;

use vars qw(@ISA @EXPORT);

@ISA = qw(Exporter);
@EXPORT = qw(&gratia_save_cert_info);

my $xmls = new XML::Simple();

my $grid_info_cmd = sprintf("%s/grid-proxy-info",
                                  $Globus::Core::Paths::bindir);
my $proxy_info_cmd = $grid_info_cmd;
my $backup_proxy_info_cmd = join(" ", map { "$_" }
                         ($grid_info_cmd, '-identity'));
$proxy_info_cmd =~ s&/grid-proxy-info$&/voms-proxy-info&o;
$proxy_info_cmd =~ s&/globus/&/glite/&o;
if (-x $proxy_info_cmd) {
  $proxy_info_cmd = join(" ", map { "$_" }
                         ($proxy_info_cmd, qw(-acsubject -vo -fqan)));
} else {
  $proxy_info_cmd = $backup_proxy_info_cmd;
}

1;

sub gratia_save_cert_info {
  return unless $proxy_info_cmd;
  my ($jobmanager, $job_id) = @_;
  $job_id = job_identifier($job_id);
  my $batchmanager_name = ref $jobmanager;
  $batchmanager_name =~ s&^.*::&&;
  return if $batchmanager_name eq 'fork'; # Don't save info for non-managed fork jobs.
  my $env = "$ENV{VDT_LOCATION}";
  unless ($env) {
    $env = "$ENV{GLOBUS_LOCATION}";
    $env = ($env)?"$env/..":($ENV{TMPDIR} || "/var/tmp");
  }
  my $log_dir = sprintf("%s/%s",
                        $env,
                        "gratia/var/data/");
  my $gratia_filename = sprintf("gratia_certinfo_%s_%s",
                                $batchmanager_name,
                                $job_id);
  open(GRATIA_CERTINFO, ">$log_dir$gratia_filename") or return;
  binmode(GRATIA_CERTINFO, ':utf8');
  print GRATIA_CERTINFO '<?xml version="1.0" encoding="UTF-8"?>', "\n";
  printf GRATIA_CERTINFO "<GratiaCertInfo>\n";
#  print GRATIA_CERTINFO '  <DebugInfo>',
#    $xmls->escape_value(scalar `$grid_info_cmd -path 2>/dev/null`), "  </DebugInfo>\n";
#  print GRATIA_CERTINFO '  <DebugInfo>',
#    $xmls->escape_value(scalar `$grid_info_cmd -all 2>/dev/null`), "  </DebugInfo>\n";
  my $description  = $jobmanager->{JobDescription};
  my @proxy_info = split /\n/, `$proxy_info_cmd 2>/dev/null`;
  my ($identity, $vo, $fqan) = ('', '', '');
  if (scalar @proxy_info) {
    $identity = $proxy_info[1] || "";
    $vo = $proxy_info[0] || "";
    $fqan = $proxy_info[2] || "";
  } else { # Try grid proxy instead
    @proxy_info = split /\n/, `$backup_proxy_info_cmd 2>/dev/null`;
    $identity = $proxy_info[0] || "";
  }
  $identity =~ s&(?:/CN=proxy)+$&&; # Don't want proxy information.
#  print GRATIA_CERTINFO '  <DebugInfo>',
#    $xmls->escape_value(join("\n", @proxy_info)), "</DebugInfo>\n";
  printf GRATIA_CERTINFO "  <BatchManager>%s</BatchManager>\n",
    $xmls->escape_value($batchmanager_name);
  printf GRATIA_CERTINFO "  <UniqID>%s</UniqID>\n",
    $xmls->escape_value($description->uniq_id());
  printf GRATIA_CERTINFO
    "  <LocalJobId>%s</LocalJobId>\n",
      $job_id;
  printf GRATIA_CERTINFO
    "  <DN>%s</DN>\n",
      $xmls->escape_value($identity) if $identity;
  printf GRATIA_CERTINFO
    "  <VO>%s</VO>\n",
      $xmls->escape_value($vo) if $vo;
  printf GRATIA_CERTINFO
    "  <FQAN>%s</FQAN>\n",
      $xmls->escape_value($fqan) if $fqan;
  print GRATIA_CERTINFO "</GratiaCertInfo>\n";
  close(GRATIA_CERTINFO);
}

sub job_identifier {
  my @identifiers = @_;
  if (@identifiers == 1) {      # Only ClusterId (maybe)
    if ($identifers[0] =~ m&\.&) {
      @identifiers = split /\./, join(".", @identifiers);
    } else {
      # Don't do anything for the simple case (non-Condor?)
      return $identifers[0];
    }
  }
  @identifiers = @identifiers[0 .. 2];
  for (my $loop = 0; $loop < 2; ++$loop) {
    $identifiers[$loop] = 0 unless $identifiers[$loop];
  }
  my $job_id = join(".", map { sprintf "%d", ($_ || 0); } @identifiers );
  return $job_id;
}
