// copyright 2004-2006 EGEE project, see LICENSE file

#include <string>
#include <iostream>
#include <sstream>
#include <getopt.h>
#include <vector>
#include <ctime>
#include "urwg.h"
#include "stringSplit.h"

//#define OPTION_STRING "ho:t:r:g:l:I:u:k:j:J:v:V:U:F:x:X:w:W:c:C:T:e:E:s:S:m:M:y:Y:1z:Z:q:Q:p:P:"
#define OPTION_STRING "hot:r:g:l:I:u:k:j:J:v:V:U:F:x:X:w:W:c:C:T:e:E:s:S:m:M:y:Y:1z:Z:q:Q:p:P:"

using namespace std;

bool needs_help = false;

// we use standard out instead!
// string urFileName = "";

urwg_UsageRecord ur;

vector<string> usage_v;


void help(string myName) {
  cerr << "Authors: Rosario Piro, Andrea Guarise <{piro,guarise@}to.infn.it>" << endl << endl;
  cerr << "Usage:" << endl;
  cerr << myName << " [OPTIONS] [USAGE] [EXTENSIONS]" << endl;
  cerr << "Where OPTIONS are:" << endl;
  cerr << "-h  --help                        Display this help and exit." << endl;
  //cerr << "-o --outfile <filename>           The XML output file (GGF UR)." << endl;
  cerr << "-t --createTime <string>          The createTime string." << endl;
  cerr << "-r --recordId <string>            The recordId string." << endl;
  cerr << "-u --LocalUserId <string>         Local user ID." << endl;
  cerr << "-k --KeyInfo <string>             ds:KeyInfo, user DN (x509 certificate" << endl << "                                  subject)." << endl;
  cerr << "-j --JobName <string>             The name of the job." << endl; 
  cerr << "-J --JobDescription <string>      An arbitrary description of the job." << endl; 
  cerr << "-g --GlobalJobId <string>         The GlobalJobId string." << endl;
  cerr << "-l --LocalJobId <string>          The LocalJobId string." << endl;
  cerr << "-I --ProcessIds <string>          Comma-separated list of process IDs." << endl;
  cerr << "-v --Charge <string>              Charge (cost) for the job." << endl;
  cerr << "-V --ChargeDescription <string>   Arbitrary description of the charge." << endl;
  cerr << "-U --ChargeUnit <string>          Unit of charge (see -c)." << endl;
  cerr << "-F --ChargeFormula <string>       String specifying the formula used to" << endl << "                                  compute the charge (see -c)." << endl;
  cerr << "-x --Status <string>              Status of the job (string)." << endl;
  cerr << "-X --StatusDescription <string>   Arbitrary description of the status." << endl;
  cerr << "-w --WallDuration <string>        Wall duration (wall-clock time) of the job" << endl << "                                  (string)." << endl;
  cerr << "-W --WallDurDescription <string>  Arbitrary description of the wall duration." << endl;
  cerr << "-c --CpuDuration <string>         CPU duration (CPU time) of the job" << endl << "                                  (string)." << endl;
  cerr << "-C --CpuDurDescription <string>   Arbitrary description of the CPU duration." << endl;
  cerr << "-T --CpuUsageType <string>        UsageType for CPU duration (user,system)." << endl;
  cerr << "-e --EndTime <string>             End time for job (string)." << endl;
  cerr << "-E --EndTimeDescription <string>  Arbitrary description of end time." << endl;
  cerr << "-s --StartTime <start_time_string> Start time for job (string)." << endl;
  cerr << "-S --StartTimeDescription <string> Arbitrary description of start time." << endl;
  cerr << "-m --MachineName <string>         Name of the executing resource." << endl;
  cerr << "-M --MachineDescription <string>  Arbitrary description of the MachineName." << endl;
  cerr << "-y --Host <string>                Host name of the executing resource." << endl;
  cerr << "-Y --HostDescription <string>     Arbitrary description of the Host." << endl;
  cerr << "-1 --PrimaryHost                  Host (-y) is referred to the primary" << endl << "                                  executing host (but there are others)." << endl;
  cerr << "-z --SubmitHost <string>          Host name of the submitting machine." << endl;
  cerr << "-Z --SubmitHostDescription <string> Arbitrary description of the SubmitHost." << endl;
  cerr << "-q --Queue <string>               Name of the batch queue on the resource." << endl;
  cerr << "-Q --QueueDescription <string>    Arbitrary description of the batch queue." << endl;
  cerr << "-p --ProjectName <string>         Name of the user's project." << endl;
  cerr << "-P --ProjectDescription <string>  Arbitrary description of the user's project." << endl;
  cerr << endl;
  cerr << "And USAGE can be (each parameter can occur multiple times):" << endl;
  cerr << "  \"Network=<int_value>,<description>,<storageUnit>,<phaseUnit>,<metric>\"" << endl;
  cerr << "  \"Disk=<int_value>,<description>,<storageUnit>,<phaseUnit>,<metric>,<type>\"" << endl;
  cerr << "  \"Memory=<int_value>,<description>,<storageUnit>,<phaseUnit>,<metric>,<type>\"" << endl;
  cerr << "  \"Swap=<int_value>,<description>,<storageUnit>,<phaseUnit>,<metric>,<type>\"" << endl;
  cerr << "  \"NodeCount=<int_value>,<description>,<metric>\"" << endl;
  cerr << "  \"Processors=<int_value>,<description>,<metric>,<consumption_rate>\"" << endl;
  cerr << "  \"TimeDuration=<duration>,<description>,<type>\"" << endl;
  cerr << "  \"TimeInstant=<dateTime>,<description>,<type>\"" << endl;
  cerr << "  \"ServiceLevel=<level>,<type>\"" << endl;
  cerr << "where <int_value> is an integer, <consumption_rate> a float and all other" << endl << "parameters are strings." << endl;
  cerr << endl;
  cerr << "The following EXTENSIONS are parameters that extend the UR by adding" << endl << "non-standard Resource elements:" << endl;
  cerr << "  \"ResPriceAuthorityContact=<PA_contact_string>\"" << endl;
  cerr << "  \"ResAccountingServerContact=<resource_accounting_server_contact_string>\"" << endl;
  cerr << "  \"UserAccountingServerContact=<user_accounting_server_contact_string>\"" << endl;
  cerr << "  \"ResRequiresEconomicAccounting=<true/false>\" (default is false)" << endl;
  cerr << "  \"LocalUserGroup=<local_UNIX_group_on_resource>\"" << endl;
  cerr << "  \"UserVOName=<name_of_user's_VO>\"" << endl;
  cerr << "  \"UserFQAN=<FQAN_of_user's_VOMS_certificate_proxy>\"" << endl;
  cerr << "  \"ResourceIdentity=<Resource_identity_sting>\"" << endl;
  cerr << "  \"ResourceKeyInfo=<host_certificate_subject_of_resource>\"" << endl;
  cerr << "  \"SubmitTime=<job_sumbission_time_string>\"" << endl;
  cerr << endl;
  cerr << "Important note: This tool does not check the validity of the single fields!" << endl;
  cerr << endl;

} // help()

int options ( int argc, char **argv ) {
  int option_char;
  int option_index = 0;

  static struct option long_options[] = {
    //{"outfile",1,0,'o'},//outfile
    {"createTime",1,0,'t'},//createTime
    {"recordId",1,0,'r'},//RecordIdentity
    {"GlobalJobId",1,0,'g'},//GlobalJobId
    {"LocalJobId",1,0,'l'},//LocalJobId
    {"ProcessIds",1,0,'I'},//ProcessIds
    {"LocalUserId",1,0,'u'},//LocalUserId
    {"KeyInfo",1,0,'k'},//KeyInfo
    {"JobName",1,0,'j'},//JobName
    {"JobDescription",1,0,'J'},//JobDescription
    {"Charge",1,0,'v'},//Charge
    {"ChargeDescription",1,0,'V'},//ChargeDescription
    {"ChargeUnit",1,0,'U'},//ChargeUnit
    {"ChargeFormula",1,0,'F'},//ChargeFormula
    {"Status",1,0,'x'},//Status
    {"StatusDescription",1,0,'X'},//StatusDescription
    {"WallDuration",1,0,'w'},//WallDuration
    {"WallDurDescription",1,0,'W'},//WallDurDescription
    {"CpuDuration",1,0,'c'},//CpuDuration
    {"CpuDurDescription",1,0,'C'},//CpuDurDescription
    {"CpuUsageType",1,0,'T'},//CpuUsageType
    {"EndTime",1,0,'e'},//EndTime
    {"EndTimeDescription",1,0,'E'},//EndTimeDescription
    {"StartTime",1,0,'s'},//StartTime
    {"StartTimeDescription",1,0,'S'},//StartTimeDescription
    {"MachineName",1,0,'m'},//MachineName
    {"MachineDescription",1,0,'M'},//MachineDescription
    {"Host",1,0,'y'},//Host
    {"HostDescription",1,0,'Y'},//HostDescription
    {"PrimaryHost",0,0,'1'},//PrimaryHost
    {"SubmitHost",1,0,'z'},//SubmitHost
    {"SubmitHostDescription",1,0,'Z'},//SubmitHostDescription
    {"Queue",1,0,'q'},//Queue
    {"Queue",1,0,'Q'},//QueueDescription
    {"ProjectName",1,0,'p'},//ProjectName
    {"ProjectDescription",1,0,'P'},//ProjectDescription
    {"help",0,0,'h'},
    {0,0,0,0}
  };

  while (( option_char = getopt_long( argc, argv, OPTION_STRING,
				      long_options, &option_index)) != EOF) {
    string *ids;

    switch (option_char) {
      case 'h': needs_help = 1; break;		  
      //case 'o': urFileName = optarg; break;
      case 'r': ur.recordIdentity.recordId = optarg; break;
      case 't': ur.recordIdentity.createTime = optarg; break;
      case 'g': ur.jobIdentity.GlobalJobId = optarg; break;
      case 'l': ur.jobIdentity.LocalJobId = optarg; break;
      case 'I': Split(',', optarg, &ur.jobIdentity.ProcessId); break;
      case 'u': ur.userIdentity.LocalUserId = optarg; break;
      case 'k': ur.userIdentity.KeyInfo = optarg; break;
      case 'j': ur.jobName.Value = optarg; break;
      case 'J': ur.jobName.Description = optarg; break;
      case 'v': ur.charge.Value = optarg; break;
      case 'V': ur.charge.Description = optarg; break;
      case 'U': ur.charge.Unit = optarg; break;
      case 'F': ur.charge.Formula = optarg; break;
      case 'x': ur.status.Value = optarg; break;
      case 'X': ur.status.Description = optarg; break;
      case 'w': ur.wallDuration.Value = optarg; break;
      case 'W': ur.wallDuration.Description = optarg; break;
      case 'c': ur.cpuDuration.Value = optarg; break;
      case 'C': ur.cpuDuration.Description = optarg; break;
      case 'T': ur.cpuDuration.UsageType = optarg; break;
      case 'e': ur.endTime.Value = optarg; break;
      case 'E': ur.endTime.Description = optarg; break;
      case 's': ur.startTime.Value = optarg; break;
      case 'S': ur.startTime.Description = optarg; break;
      case 'm': ur.machineName.Value = optarg; break;
      case 'M': ur.machineName.Description = optarg; break;
      case 'y': ur.host.Value = optarg; break;
      case 'Y': ur.host.Description = optarg; break;
      case '1': ur.host.primary = true; break;
      case 'z': ur.submitHost.Value = optarg; break;
      case 'Z': ur.submitHost.Description = optarg; break;
      case 'q': ur.queue.Value = optarg; break;
      case 'Q': ur.queue.Description = optarg; break;
      case 'p': ur.projectName.Value = optarg; break;
      case 'P': ur.projectName.Description = optarg; break;
      default : break;

    }
  }

  // get additional usage stuff (if any):

  if (optind < argc) {
    while (optind < argc)
      usage_v.push_back(argv[optind++]);
  }


  // parse additional usage stuff:

  vector<Network> netw;
  vector<Disk> dsk;
  vector<Memory> mem;
  vector<Swap> swp;
  vector<Processors> procs;
  vector<NodeCount> nCount;
  vector<TimeDuration> timeDur;
  vector<TimeInstant> timeInst;
  vector<ServiceLevel> servLev;

  for (int i = 0; i < usage_v.size(); i++) {
    vector<string> usage_str;
    Split ('=', usage_v[i], &usage_str);
    if (usage_str.size() >= 2) {

      // recompose what follows the parameter name (the value itself
      // might contain '=')
      string value_str = 
	usage_v[i].substr(usage_str[0].size()+1, string::npos);

      vector<string> usage_values;
      Split (',', value_str, &usage_values);

      // USAGE:
      // a Network element
      if (usage_str[0] == "Network") {
	if (usage_values.size() != 5) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 5, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	Network thisNetw;
	thisNetw.Value = (unsigned int) atoi(usage_values[0].c_str());
	thisNetw.Description = usage_values[1];
	thisNetw.IntervallicVolume.storage = usage_values[2];
	thisNetw.IntervallicVolume.phase = usage_values[3];
	thisNetw.Metric = usage_values[4];
	netw.push_back(thisNetw);
      }
      // a Disk element
      else if (usage_str[0] == "Disk") {
	if (usage_values.size() != 6) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 6, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	Disk thisDsk;
	thisDsk.Value = (unsigned int) atoi(usage_values[0].c_str());
	thisDsk.Description = usage_values[1];
	thisDsk.IntervallicVolume.storage = usage_values[2];
	thisDsk.IntervallicVolume.phase = usage_values[3];
	thisDsk.Metric = usage_values[4];
	thisDsk.Type = usage_values[5];
	dsk.push_back(thisDsk);
      }
      // a Memory element
      else if (usage_str[0] == "Memory") {
	if (usage_values.size() != 6) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 6, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	Memory thisMem;
	thisMem.Value = (unsigned int) atoi(usage_values[0].c_str());
	thisMem.Description = usage_values[1];
	thisMem.IntervallicVolume.storage = usage_values[2];
	thisMem.IntervallicVolume.phase = usage_values[3];
	thisMem.Metric = usage_values[4];
	thisMem.Type = usage_values[5];
	mem.push_back(thisMem);
      }
      // a Swap element
      else if (usage_str[0] == "Swap") {
	if (usage_values.size() != 6) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 6, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	Swap thisSwp;
	thisSwp.Value = (unsigned int) atoi(usage_values[0].c_str());
	thisSwp.Description = usage_values[1];
	thisSwp.IntervallicVolume.storage = usage_values[2];
	thisSwp.IntervallicVolume.phase = usage_values[3];
	thisSwp.Metric = usage_values[4];
	thisSwp.Type = usage_values[5];
	swp.push_back(thisSwp);
      }
      // a NodeCount element
      else if (usage_str[0] == "NodeCount") {
	if (usage_values.size() != 3) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 3, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	NodeCount thisNCount;
	thisNCount.Value = (unsigned int) atoi(usage_values[0].c_str());
	thisNCount.Description = usage_values[1];
	thisNCount.Metric = usage_values[2];
	nCount.push_back(thisNCount);
      }
      // a Processors element
      else if (usage_str[0] == "Processors") {
	if (usage_values.size() != 4) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 4, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	Processors thisProcs;
	thisProcs.Value = (unsigned int) atoi(usage_values[0].c_str());
	thisProcs.Description = usage_values[1];
	thisProcs.Metric = usage_values[2];
	thisProcs.ConsumptionRate = (float) atof(usage_values[3].c_str());
	procs.push_back(thisProcs);
      }
      // a TimeDuration element
      else if (usage_str[0] == "TimeDuration") {
	if (usage_values.size() != 3) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 3, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	TimeDuration thisTimeDur;
	thisTimeDur.Value = usage_values[0];
	thisTimeDur.Description = usage_values[1];
	thisTimeDur.Type = usage_values[2];
	timeDur.push_back(thisTimeDur);
      }
      // a TimeInstant element
      else if (usage_str[0] == "TimeInstant") {
	if (usage_values.size() != 3) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 3, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	TimeInstant thisTimeInst;
	thisTimeInst.Value = usage_values[0];
	thisTimeInst.Description = usage_values[1];
	thisTimeInst.Type = usage_values[2];
	timeInst.push_back(thisTimeInst);
      }
      // a ServiceLevel element
      else if (usage_str[0] == "ServiceLevel") {
	if (usage_values.size() != 2) {
	  cerr << "Error: wrong number of parameters in: " <<  usage_v[i]
	       << endl << "       Expected: 2, found: " << usage_values.size()
	       << endl;
	  exit(1);
	}
	ServiceLevel thisServLev;
	thisServLev.Value = usage_values[0];
	thisServLev.Type = usage_values[1];
	servLev.push_back(thisServLev);
      }
      // EXTENSIONS:
      // a ResPriceAuthorityContact element
      else if (usage_str[0] == "ResPriceAuthorityContact") {
	ur.resourceExtension.ResPriceAuthorityContact = value_str;
      }
      // a ResAccountingServerContact element
      else if (usage_str[0] == "ResAccountingServerContact") {
	ur.resourceExtension.ResAccountingServerContact = value_str;
      }
      // a UserAccountingServerContact element
      else if (usage_str[0] == "UserAccountingServerContact") {
	ur.resourceExtension.UserAccountingServerContact = value_str;
      }
      // a ResRequiresEconomicAccounting element
      else if (usage_str[0] == "ResRequiresEconomicAccounting" &&
	             (value_str == "true" || value_str == "false") ) {
	if (usage_str[1] == "true") 
	  ur.resourceExtension.ResRequiresEconomicAccounting = true;
      }
      // a LocalUserGroup element
      else if (usage_str[0] == "LocalUserGroup") {
        ur.resourceExtension.LocalUserGroup = value_str;
      }
      // a UserVOName element
      else if (usage_str[0] == "UserVOName") {
        ur.resourceExtension.UserVOName = value_str;
      }
      // a UserFQAN element
      else if (usage_str[0] == "UserFQAN") {
        ur.resourceExtension.UserFQAN = value_str;
      }
      // a ResourceIdentity element
      else if (usage_str[0] == "ResourceIdentity") {
	ur.resourceExtension.ResourceIdentity = value_str;
      }
      // a ResourceKeyInfo element
      else if (usage_str[0] == "ResourceKeyInfo") {
	ur.resourceExtension.ResourceKeyInfo = value_str;
      }
      // a SubmitTime element
      else if (usage_str[0] == "SubmitTime") {
	ur.resourceExtension.SubmitTime = value_str;
      }
      else {
	cerr << "Error: Unknown usage information: " << usage_v[i] << endl;
	exit(2);
      }
    }
  }

  ur.network = netw;
  ur.disk = dsk;
  ur.memory = mem;
  ur.swap = swp;
  ur.processors = procs;
  ur.nodeCount = nCount;
  ur.timeDuration = timeDur;
  ur.timeInstant = timeInst;
  ur.serviceLevel = servLev;

  return 0;
} // options()


int initalizeUR() {
  // initialize the data members:
  ur.host.primary = false;
  ur.resourceExtension.ResRequiresEconomicAccounting = false;

  // everything else is of type string and doesn't need to be initialized
  return 0;
}


int main (int argc, char *argv[]) {
  int retVal = 0; // ok

  initalizeUR(); // initialize a few things

  options(argc, argv); // get options from command line

  if (needs_help) {
    help(argv[0]);
    return 0;
  }

  // now print it to standard output:
  cout << ur.xml() << endl;

  return retVal;
}
