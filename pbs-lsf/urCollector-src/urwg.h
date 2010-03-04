// Authors: Andrea Guarise, Rosario Piro <{guarise,piro}@to.infn.it>
// simple implementation of the GGF usage record (UR)
// copyright 2004-2006 EGEE project, see LICENSE file.


#ifndef URWG_H
#define URWG_H
#include <vector>
#include <string>
#include <iostream>
#include <sstream>
#include <map>

using namespace std;

typedef string dateTime;
typedef string description;
typedef string storageUnit;
typedef string phaseUnit;
typedef string metric;
typedef string type;
typedef string unit;
typedef string domainNameType;
typedef string duration;
typedef string ds_KeyInfo;//FIXME 

struct intervallicVolume
{
	storageUnit storage;
	phaseUnit phase;
};

struct RecordIdentity
{
	dateTime createTime;
	string recordId;
	//FIXME add 6.1.3 ds:KeyInfo element
};

struct JobIdentity
{
	string GlobalJobId; //minOccours =0
	string LocalJobId; //minOccours = 0
	vector<string> ProcessId; //minOccours = 0 maxOccours = unbounded
};

struct UserIdentity
{
	string LocalUserId; //minOccours=0 maxOccours=1
	ds_KeyInfo KeyInfo;//minOccours=0 maxOccours=1//FIXME
};

struct JobName
{
	string Value;
	description Description;
	
};

struct Charge
{
	string Value;
	description Description;
	unit Unit;
	string Formula;
};

struct Status
{
	string Value;
	description Description;	
};

struct WallDuration
{
	duration Value;
	description Description;
};

struct CpuDuration
{
	duration Value;
	description Description;	
	string UsageType;//FIXME should be enum type
};

struct EndTime
{
	dateTime Value;
	description Description;
};

struct StartTime
{
	dateTime Value;
	description Description;
};

struct MachineName
{
	domainNameType Value;
	description Description;
};

struct Host
{
	domainNameType Value;
	description Description;
	bool primary;
};

struct SubmitHost
{
	domainNameType Value;
	description Description;
};

struct Queue
{
	string Value;
	description Description;
};

struct ProjectName
{
	string Value;
	description Description;
};

struct  Network
{
	unsigned int Value;
	description Description;
	intervallicVolume IntervallicVolume;
	metric Metric;
};

struct Disk
{
	unsigned int Value;
	description Description;
	intervallicVolume IntervallicVolume;
	metric Metric;
	string Type;//FIXME must become enum
};

struct Memory
{
	unsigned int Value;
	description Description;
	intervallicVolume IntervallicVolume;
	metric Metric;
	string Type;//FIXME must become enum
};

struct Swap
{
	unsigned int Value;
	description Description;
	intervallicVolume IntervallicVolume;
	metric Metric;
	string Type;//FIXME must become enum
};

struct NodeCount
{
	unsigned int Value;
	description Description;
	metric Metric;//FIXME must become enum
};

struct Processors
{
	unsigned int Value;
	description Description;
	metric Metric;
	float ConsumptionRate;	
};

struct TimeDuration
{
	duration Value;
	description Description;
	string Type;
};

struct TimeInstant
{
	dateTime Value;
	description Description;
	string Type;
};

struct ServiceLevel
{
	string Value;
	string Type;
};


/*
 * Example of the XML output:
 * <Resource urwg:description="ResPriceAuthorityContact">paID</Resource>
 * <Resource urwg:description="ResAccountingServerContact">bankID</Resource>
 * */
struct ResourceExtension
{
	// additional stuff fir accounting
	string ResPriceAuthorityContact;//PAID
	string ResAccountingServerContact;//resourceHLRID
	string UserAccountingServerContact;//userHLRID
	bool ResRequiresEconomicAccounting; //default is false
	// additional stuff for user identity:
	string UserVOName; // name of user's VO; different from ProjectName
	string UserFQAN; // VOMS FQAN of user's certificate proxy
	string LocalUserGroup; // UNIX group on resource
	// additional stuff for resource identity:
	string ResourceIdentity;//CeID
        string ResourceKeyInfo; // host certificate subject of resource
	string SubmitTime;//SubmitTime
	
};


class urwg_UsageRecord {
public:
	RecordIdentity recordIdentity;
	JobIdentity jobIdentity;
	UserIdentity userIdentity;
	JobName jobName;
	Charge charge;
	Status status;
	WallDuration wallDuration;
	CpuDuration  cpuDuration;
	EndTime endTime;
	StartTime startTime;
	MachineName machineName;
	Host	host;
	SubmitHost submitHost;
	Queue	queue;
	ProjectName projectName;
	vector<Network> network;
	vector<Disk> disk;
	vector<Memory> memory;
	vector<Swap> swap;
	vector<NodeCount> nodeCount;
	vector<Processors> processors;
	vector<TimeDuration> timeDuration;
	vector<TimeInstant> timeInstant;
	vector<ServiceLevel> serviceLevel;
	
	
	ResourceExtension resourceExtension;
	urwg_UsageRecord();
	urwg_UsageRecord(string &xml);
	string xml();


protected:

private:

bool parseRecordIdentity(string &xml);
bool parseJobIdentity(string &xml);
bool parseUserIdentity(string &xml);
bool parseJobName(string &xml);
bool parseCharge(string &xml);
bool parseStatus(string &xml);
bool parseWallDuration(string &xml);
bool parseCpuDuration(string &xml);
bool parseEndTime(string &xml);
bool parseStartTime(string &xml);
bool parseMachineName(string &xml);
bool parseHost(string &xml);
bool parseSubmitHost(string &xml);
bool parseQueue(string &xml);
bool parseProjectName(string &xml);
bool parseNetwork(string &xml);
bool parseDisk(string &xml);
bool parseMemory(string &xml);
bool parseSwap(string &xml);
bool parseNodeCount(string &xml);
bool parseProcessors(string &xml);
bool parseTimeDuration(string &xml);
bool parseTimeInstant(string &xml);
bool parseServiceLevel(string &xml);
bool parseResourceExtension(string& xml);

string composeRecordIdentity();
string composeJobIdentity();
string composeUserIdentity();
string composeJobName();
string composeCharge();
string composeStatus();
string composeWallDuration();
string composeCpuDuration();
string composeEndTime();
string composeStartTime();
string composeMachineName();
string composeHost();
string composeSubmitHost();
string composeQueue();
string composeProjectName();
string composeNetwork();
string composeDisk();
string composeMemory();
string composeSwap();
string composeNodeCount();
string composeProcessors();
string composeTimeDuration();
string composeTimeInstant();
string composeServiceLevel();
string composeResourceExtension();


};

#endif
