package urCollector::Common;

####################################
# Packages
####################################
use strict;
require Exporter;

####################################
# Global variables used internally
####################################
use vars qw(@ISA @EXPORT @EXPORT_OK %EXPORT_TAGS
	    $URCOLLECTOR_LOC);

####################################
# Symbol export
####################################
@ISA = qw(Exporter);
@EXPORT = qw($URCOLLECTOR_LOC
	     &error);
@EXPORT_OK = qw();
%EXPORT_TAGS =
  (
   Locking => [ qw(&putLock &delLock) ]
  );

Exporter::export_ok_tags('Locking');

####################################
# Initialization / executable code
####################################

# Installation area
$URCOLLECTOR_LOC = $::ENV{URCOLLECTOR_LOCATION} || "/opt/urCollector";

####################################
# End of initialization / executable code
####################################
1;


####################################
# Subroutines
####################################
sub error {
    if (scalar(@_) > 0) {
	print "$_[0]";
    }
    exit(1);
}


sub putLock {
    my $lockName = $_[0];
    open(IN,  "< $lockName") && return 1;
    close(IN);
    open(OUT, "> $lockName") || return 2;
    print OUT  $$;    ## writes pid
    close(OUT);
    return 0;
}


sub delLock {
    my $lockName = $_[0];
    open(IN,  "< $lockName") || return 1;
    close(IN);
    my $status = system("rm -f $lockName");
    return $status;
}


####################################
# Only POD beyond here.
####################################
__END__
