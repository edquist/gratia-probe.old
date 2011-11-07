// copyright 2004-2006, EGEE project, see LICENSE file

#include <stdlib.h>
#include <time.h>
#include <sstream>
#include "urwg.h"
#include "xmlUtil.h"
#include "int2string.h"

urwg_UsageRecord::urwg_UsageRecord(){}

urwg_UsageRecord::urwg_UsageRecord(string &xml)
{
	node nodeBuff;
	bool goOn = true;
	while ( goOn )
	{
		string tag = "UsageRecord";
		nodeBuff = parse(&xml, tag, "urwg");
		if ( nodeBuff.status != 0 )
		{
			//in case it is a JobUsageRecord Node
			tag = "JobUsageRecord";
			nodeBuff = parse(&xml, tag, "urwg" );
			if ( nodeBuff.status != 0 )
			{
				goOn = false;
			}
		}
		parseRecordIdentity(xml);
		parseJobIdentity(xml);
		parseUserIdentity(xml);
		parseJobName(xml);
		parseCharge(xml);
		parseStatus(xml);
		parseWallDuration(xml);
		parseCpuDuration(xml);
		parseEndTime(xml);
		parseStartTime(xml);
		parseMachineName(xml);
		parseHost(xml);
		parseSubmitHost(xml);
		parseQueue(xml);
		parseProjectName(xml);
		parseNetwork(xml);
		parseDisk(xml);
		parseMemory(xml);
		parseSwap(xml);
		parseNodeCount(xml);
		parseProcessors(xml);
		parseTimeDuration(xml);
		parseTimeInstant(xml);
		parseServiceLevel(xml);
		parseResourceExtension(xml);
		nodeBuff.release();
	}
}

string urwg_UsageRecord::xml()	
{
	string outBuff;
	outBuff = "<UsageRecord xmlns=\"http://www.gridforum.org/2003/ur-wg\" xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.gridforum.org/2003/ur-wg file:///u:/OSG/urwg-schema.11.xsd\">\n";
	outBuff += composeRecordIdentity();
	outBuff += composeJobIdentity();
	outBuff += composeUserIdentity();
	outBuff += composeJobName();
	outBuff += composeCharge();
	outBuff += composeStatus();
	outBuff += composeWallDuration();
	outBuff += composeCpuDuration();
	outBuff += composeEndTime();
	outBuff += composeStartTime();
	outBuff += composeMachineName();
	outBuff += composeHost();
	outBuff += composeSubmitHost();
	outBuff += composeQueue();
	outBuff += composeProjectName();
	outBuff += composeNetwork();
	outBuff += composeDisk();
	outBuff += composeMemory();
	outBuff += composeSwap();
	outBuff += composeNodeCount();
	outBuff += composeProcessors();
	outBuff += composeTimeDuration();
	outBuff += composeTimeInstant();
	outBuff += composeServiceLevel();
	
	outBuff +=composeResourceExtension();
	outBuff += "</UsageRecord>";
	return outBuff;
}

bool urwg_UsageRecord::parseRecordIdentity(string &xml)
{
		#ifdef DEBUG
		 cerr << "urwg_UsageRecord::parseRecordIdentity(string &xml)" << endl;
		#endif
		node tagBuff = parse(&xml, "RecordIdentity", "urwg");
		if ( tagBuff.status == 0 )
		{
			#ifdef DEBUG
			 cerr << "urwg_UsageRecord::parseRecordIdentity(string &xml):Status 0" << endl;
			#endif
			attrType attributes;
			attributes = tagBuff.getAttributes();
			recordIdentity.recordId = 
				parseAttribute ("urwg:recordId", attributes);
			recordIdentity.createTime =
				parseAttribute ("urwg:createTime", attributes);
			#ifdef DEBUG
			 cerr << "urwg_UsageRecord::parseRecordIdentity(string &xml):Return true" << endl;
			#endif
			return true;
		}
		#ifdef DEBUG
		 cerr << "urwg_UsageRecord::parseRecordIdentity(string &xml):return false" << endl;
		#endif
		return false;
}

bool urwg_UsageRecord::parseJobIdentity(string &xml)
{
		node tagBuff;
		tagBuff = parse(&xml, "JobIdentity", "urwg");
		if ( tagBuff.status == 0 )
		{
			node tagBuff;
			tagBuff = parse(&xml, "GlobalJobId" , "urwg");
			if ( tagBuff.status == 0 )
			{
				jobIdentity.GlobalJobId = tagBuff.text;
			}
			tagBuff = parse(&xml, "LocalJobId" , "urwg");
			if ( tagBuff.status == 0 )
			{
				jobIdentity.LocalJobId = tagBuff.text;
			}
			bool goOn = true;
			while (goOn)
			{
				tagBuff = parse(&xml, "ProcessId", "urwg");
				if ( tagBuff.status == 0 )
				{
					jobIdentity.ProcessId.push_back(
							tagBuff.text);
					tagBuff.release();
				}
				else
				{
					goOn = false;
				}
			}
		}
		else
		{
			return false;
		}
		return true;
}

bool urwg_UsageRecord::parseUserIdentity(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "UserIdentity", "urwg");
	if ( tagBuff.status == 0 )
	{
		node tagBuff;
		tagBuff = parse(&xml, "LocalUserId", "urwg");
		if ( tagBuff.status == 0 )
		{
			userIdentity.LocalUserId = tagBuff.text;
		}
		tagBuff = parse(&xml, "KeyInfo" , "ds");
		if ( tagBuff.status == 0 )
		{
			userIdentity.KeyInfo = tagBuff.text;
		}
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseJobName(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "JobName", "urwg");
	if ( tagBuff.status == 0 )
	{
		jobName.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		jobName.Description = 
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseCharge(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "Charge", "urwg");
	if ( tagBuff.status == 0 )
	{
		charge.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		charge.Description = 
			parseAttribute ("urwg:description", attributes);
		charge.Unit =
			parseAttribute ("urwg:unit", attributes);
		charge.Formula =
			parseAttribute ("urwg:formula", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseStatus(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "Status", "urwg");
	if ( tagBuff.status == 0 )
	{
		status.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		status.Description = 
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseWallDuration(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "WallDuration", "urwg");
	if ( tagBuff.status == 0 )
	{
		wallDuration.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		wallDuration.Description =
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseCpuDuration(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "CpuDuration", "urwg");
	if ( tagBuff.status == 0 )
	{
		cpuDuration.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		cpuDuration.Description =
			parseAttribute ("urwg:description", attributes);
		cpuDuration.UsageType =
			parseAttribute ("urwg:usageType", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseEndTime(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "EndTime", "urwg");
	if ( tagBuff.status == 0 )
	{
		endTime.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		endTime.Description = 
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseStartTime(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "StartTime", "urwg");
	if ( tagBuff.status == 0 )
	{
		startTime.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		startTime.Description =
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseMachineName(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "MachineName", "urwg");
	if ( tagBuff.status == 0 )
	{
		machineName.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		machineName.Description = 
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseHost(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "Host", "urwg");
	if ( tagBuff.status == 0 )
	{
		host.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		host.Description = 
			parseAttribute ("urwg:description", attributes);
		if ( parseAttribute ("urwg:primary", attributes) == "true" )
		{
			host.primary = true;
		}
		else
		{
			host.primary = false;
		}
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseSubmitHost(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "SubmitHost", "urwg");
	if ( tagBuff.status == 0 )
	{
		submitHost.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		submitHost.Description =
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseQueue(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "Queue", "urwg");
	if ( tagBuff.status == 0 )
	{
		queue.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		queue.Description =
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseProjectName(string &xml)
{
	node tagBuff;
	tagBuff = parse(&xml, "ProjectName", "urwg");
	if ( tagBuff.status == 0 )
	{
		projectName.Value = tagBuff.text;
		attrType attributes;
		attributes = tagBuff.getAttributes();
		projectName.Description = 
			parseAttribute ("urwg:description", attributes);
	}
	else
	{
		return false;
	}
	return true;
}

bool urwg_UsageRecord::parseNetwork(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "Network", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			Network buffer;
			buffer.Value = atoi((tagBuff.text).c_str());
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description = 
				parseAttribute ("urwg:description", attributes);
			buffer.IntervallicVolume.storage = 
				parseAttribute ("urwg:storageUnit", attributes);
			buffer.IntervallicVolume.phase = 
				parseAttribute ("urwg:phaseUnit", attributes);
			buffer.Metric = 
				parseAttribute ("urwg:metric", attributes);
			network.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;
}

bool urwg_UsageRecord::parseDisk(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "Disk", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			Disk buffer;
			buffer.Value = atoi((tagBuff.text).c_str());
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description =
				parseAttribute ("urwg:description", attributes);
			buffer.IntervallicVolume.storage =
				parseAttribute ("urwg:storageUnit", attributes);
			buffer.IntervallicVolume.phase =
				parseAttribute ("urwg:phaseUnit", attributes);
			buffer.Metric =
				parseAttribute ("urwg:metric", attributes);
			buffer.Type = 
				parseAttribute ("urwg:type", attributes);
			disk.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;
}

bool urwg_UsageRecord::parseMemory(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "Memory", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			Memory buffer;
			buffer.Value = atoi((tagBuff.text).c_str());
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description =
				parseAttribute ("urwg:description", attributes);
			buffer.IntervallicVolume.storage =
				parseAttribute ("urwg:storageUnit", attributes);
			buffer.IntervallicVolume.phase =
			buffer.Metric =
				parseAttribute ("urwg:phaseUnit", attributes);
			buffer.Metric =
				parseAttribute ("urwg:metric", attributes);
			buffer.Type = 
				parseAttribute ("urwg:type", attributes);
			memory.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;
}

bool urwg_UsageRecord::parseSwap(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "Swap", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			Swap buffer;
			buffer.Value = atoi((tagBuff.text).c_str());
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description =
				parseAttribute ("urwg:description", attributes);
			buffer.IntervallicVolume.storage =
				parseAttribute ("urwg:storageUnit", attributes);
			buffer.IntervallicVolume.phase =
				parseAttribute ("urwg:phaseUnit", attributes);
			buffer.Metric =
				parseAttribute ("urwg:metric", attributes);
			buffer.Type = 
				parseAttribute ("urwg:type", attributes);
			swap.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;

}

bool urwg_UsageRecord::parseNodeCount(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "NodeCount", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			NodeCount buffer;
			buffer.Value = atoi((tagBuff.text).c_str());
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description =
				parseAttribute ("urwg:description", attributes);
			buffer.Metric =
				parseAttribute ("urwg:metric", attributes);
			nodeCount.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;
}

bool urwg_UsageRecord::parseProcessors(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "Processors", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			Processors buffer;
			buffer.Value = atoi((tagBuff.text).c_str());
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description =
				parseAttribute ("urwg:description", attributes);
			buffer.Metric =
				parseAttribute ("urwg:metric", attributes);
			buffer.ConsumptionRate =
				atof((parseAttribute(
					"urwg:consumptionRate", attributes)).c_str());
			processors.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;
}

bool urwg_UsageRecord::parseTimeDuration(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "TimeDuration", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			TimeDuration buffer;
			buffer.Value = tagBuff.text;
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description =
				parseAttribute ("urwg:description", attributes);
			buffer.Type =
				parseAttribute ("urwg:type", attributes);
			timeDuration.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;
}

bool urwg_UsageRecord::parseTimeInstant(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "TimeInstant", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			TimeInstant buffer;
			buffer.Value = tagBuff.text;
			attrType attributes;
			attributes = tagBuff.getAttributes();
			buffer.Description =
				parseAttribute ("urwg:description", attributes);
			buffer.Type =
				parseAttribute ("urwg:type", attributes);
			timeInstant.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;

}

bool urwg_UsageRecord::parseServiceLevel(string &xml)
{
	bool retValue = false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "ServiceLevel", "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue = true;
			ServiceLevel buffer;
			attrType attributes;
			buffer.Value = tagBuff.text;
			attributes = tagBuff.getAttributes();
			buffer.Type =
				parseAttribute ("urwg:type", attributes);
			serviceLevel.push_back(buffer);
			tagBuff.release();
		}
		else
		{
			goOn = false;
		}
	}
	return retValue;
}

bool urwg_UsageRecord::parseResourceExtension(string &xml)
{
	bool retValue =false;
	bool goOn = true;
	node tagBuff;
	while ( goOn )
	{
		tagBuff = parse(&xml, "Resource" , "urwg");
		if ( tagBuff.status == 0 )
		{
			retValue =true;
			attrType attributes;
			attributes = tagBuff.getAttributes();
			string buffer = 
				parseAttribute ("urwg:description", attributes);
			if ( buffer == "ResPriceAuthorityContact" )
			{
				resourceExtension.ResPriceAuthorityContact =
					tagBuff.text;
			}
			if ( buffer == "ResAccountingServerContact" )
			{
				resourceExtension.ResAccountingServerContact =
					tagBuff.text;
			}
			if ( buffer == "UserAccountingServerContact" )
			{
				resourceExtension.UserAccountingServerContact =
					tagBuff.text;
			}
			if ( buffer == "LocalUserGroup" )
			{
				resourceExtension.LocalUserGroup =
					tagBuff.text;
			}
			if ( buffer == "UserVOName" )
			{
				resourceExtension.UserVOName =
					tagBuff.text;
			}
			if ( buffer == "UserFQAN" )
			{
				resourceExtension.UserFQAN =
					tagBuff.text;
			}
			if ( buffer == "ResourceIdentity" )
			{
				resourceExtension.ResourceIdentity =
					tagBuff.text;
			}
			if ( buffer == "ResourceKeyInfo" )
			{
				resourceExtension.ResourceKeyInfo =
					tagBuff.text;
			}
			if ( buffer == "SubmitTime" )
			{
				resourceExtension.SubmitTime =
					tagBuff.text;
			}
			if ( buffer == "ResRequiresEconomicAccounting" )
			{
				if ( tagBuff.text == "true" )
				{
					resourceExtension.ResRequiresEconomicAccounting = true;
				}
				else
				{
					resourceExtension.ResRequiresEconomicAccounting = false;
				}
			}
			tagBuff.release();
		}
		else
		{
			cerr << "Should exit!" << endl;
			goOn = false;
		}
	}
	return retValue;
}

string urwg_UsageRecord::composeRecordIdentity()
{
	vector<attribute> attributes;
	if ( recordIdentity.createTime != "" )
	{
		attribute attrBuff = {"urwg:createTime", recordIdentity.createTime};
		attributes.push_back(attrBuff);
	}
	if ( recordIdentity.recordId  != "" )
	{
		attribute attrBuff = {"urwg:recordId", recordIdentity.recordId};
		attributes.push_back(attrBuff);
	}
	string tagBuff = "urwg:RecordIdentity";
	string valueBuff = "";
	return tagAdd (tagBuff, valueBuff, attributes);
}

string urwg_UsageRecord::composeJobIdentity()
{
	string buff;
	buff = "<urwg:JobIdentity>\n";
	buff += tagAdd("urwg:GlobalJobId", jobIdentity.GlobalJobId);
	buff += tagAdd("urwg:LocalJobId", jobIdentity.LocalJobId);
	vector<string>::const_iterator it = jobIdentity.ProcessId.begin();
	while ( it != jobIdentity.ProcessId.end() )
	{
		buff += tagAdd("urwg:ProcessId", *it );
		it++;
	}	
	buff +="</urwg:JobIdentity>\n";
	return buff;
}

string urwg_UsageRecord::composeUserIdentity()
{
	string buff;
	buff = "<urwg:UserIdentity>\n";
	buff += tagAdd("urwg:LocalUserId", userIdentity.LocalUserId);
       vector<attribute> attributes;
       attribute attrBuff = {"xmlns:ds","http://www.w3.org/2000/09/xmldsig#"};        
       attributes.push_back(attrBuff);
	buff += tagAdd("ds:KeyInfo", userIdentity.KeyInfo,attributes);
	buff +="</urwg:UserIdentity>\n";
	return buff;
}

string urwg_UsageRecord::composeJobName()
{
	vector<attribute> attributes;
	if ( jobName.Description != "" )
	{
		attribute attrBuff = {"description", jobName.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:JobName",jobName.Value, attributes);
}

string urwg_UsageRecord::composeCharge()
{
	vector<attribute> attributes;
	if ( charge.Description != "" )
	{
		attribute attrBuff = {"description", charge.Description};
		attributes.push_back(attrBuff);
	}
	if ( charge.Unit != "" )
	{
		attribute attrBuff = {"unit", charge.Unit};
		attributes.push_back(attrBuff);
	}
	if ( charge.Formula != "" )
	{
		attribute attrBuff = {"formula", charge.Formula};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:Charge", charge.Value, attributes );
}

string urwg_UsageRecord::composeStatus()
{
	vector<attribute> attributes;
	if ( status.Description != "" )
	{
		attribute attrBuff = {"description", status.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:Status", status.Value, attributes );
}

string urwg_UsageRecord::composeWallDuration()
{
	vector<attribute> attributes;
	if ( wallDuration.Description != "" )
	{
		attribute attrBuff = {"description", wallDuration.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:WallDuration", wallDuration.Value, attributes );
}

string urwg_UsageRecord::composeCpuDuration()
{
	vector<attribute> attributes;
	if ( cpuDuration.Description != "" )
	{
		attribute attrBuff = {"description", cpuDuration.Description};
		attributes.push_back(attrBuff);
	}
	if ( cpuDuration.UsageType != "" )
	{
		attribute attrBuff = {"usageType", cpuDuration.UsageType};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:CpuDuration", cpuDuration.Value, attributes );
}

string urwg_UsageRecord::composeEndTime()
{
	vector<attribute> attributes;
	if ( endTime.Description != "" )
	{
		attribute attrBuff = {"description", endTime.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:EndTime", endTime.Value, attributes );
}

string urwg_UsageRecord::composeStartTime()
{
	vector<attribute> attributes;
	if ( startTime.Description != "" )
	{
		attribute attrBuff = {"description", startTime.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:StartTime", startTime.Value, attributes );
}

string urwg_UsageRecord::composeMachineName()
{
	vector<attribute> attributes;
	if ( machineName.Description != "" )
	{
		attribute attrBuff = {"description", machineName.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:MachineName", machineName.Value, attributes );
}

string urwg_UsageRecord::composeHost()
{
	vector<attribute> attributes;
	if ( host.Description != "" )
	{
		attribute attrBuff = {"description", host.Description};
		attributes.push_back(attrBuff);
	}
	if ( host.primary == true ) 
	{
		attribute attrBuff = {"primary", "true"};
		attributes.push_back(attrBuff);
	}
	else 
	{
		attribute attrBuff = {"primary", "false"};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:Host", host.Value, attributes );
}

string urwg_UsageRecord::composeSubmitHost()
{
	vector<attribute> attributes;
	if ( submitHost.Description != "" )
	{
		attribute attrBuff = {"description", submitHost.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:SubmitHost", submitHost.Value, attributes );
}

string urwg_UsageRecord::composeQueue()
{
	vector<attribute> attributes;
	if ( queue.Description != "" )
	{
		attribute attrBuff = {"description", queue.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:Queue", queue.Value, attributes );
}

string urwg_UsageRecord::composeProjectName()
{
	vector<attribute> attributes;
	if ( projectName.Description != "" )
	{
		attribute attrBuff = {"description", projectName.Description};
		attributes.push_back(attrBuff);
	}
	return tagAdd ("urwg:ProjectName", projectName.Value, attributes );
}

string urwg_UsageRecord::composeNetwork()
{
	string buff = "";
	vector<Network>::const_iterator it = network.begin();
	while ( it != network.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.storage != "" )
		{
			attribute attrBuff = {"storageUnit", 
				(*it).IntervallicVolume.storage};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.phase != "" )
		{
			attribute attrBuff = {"phaseUnit",
				(*it).IntervallicVolume.phase};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Metric != "" )
		{
			attribute attrBuff = {"metric", (*it).Metric};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:Network", int2string((*it).Value), attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeDisk()
{
	string buff = "";
	vector<Disk>::const_iterator it = disk.begin();
	while ( it != disk.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.storage != "" )
		{
			attribute attrBuff = {"storageUnit",
				(*it).IntervallicVolume.storage};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.phase != "" )
		{
			attribute attrBuff = {"phaseUnit",
				(*it).IntervallicVolume.phase};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Metric != "" )
		{
			attribute attrBuff = {"metric", (*it).Metric};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Type != "" )
		{
			attribute attrBuff = {"type", (*it).Type};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:Disk", int2string((*it).Value), attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeMemory()
{
	string buff = "";
	vector<Memory>::const_iterator it = memory.begin();
	while ( it != memory.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.storage != "" )
		{
			attribute attrBuff = {"storageUnit",
				(*it).IntervallicVolume.storage};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.phase != "" )
		{
			attribute attrBuff = {"phaseUnit",
				(*it).IntervallicVolume.phase};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Metric != "" )
		{
			attribute attrBuff = {"metric", (*it).Metric};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Type != "" )
		{
			attribute attrBuff = {"type", (*it).Type};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:Memory", int2string((*it).Value), attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeSwap()
{
	string buff = "";
	vector<Swap>::const_iterator it = swap.begin();
	while ( it != swap.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.storage != "" )
		{
			attribute attrBuff = {"storageUnit",
				(*it).IntervallicVolume.storage};
			attributes.push_back(attrBuff);
		}
		if ( (*it).IntervallicVolume.phase != "" )
		{
			attribute attrBuff = {"phaseUnit",
				(*it).IntervallicVolume.phase};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Metric != "" )
		{
			attribute attrBuff = {"metric", (*it).Metric};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Type != "" )
		{
			attribute attrBuff = {"type", (*it).Type};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:Swap", int2string((*it).Value), attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeNodeCount()
{
	string buff = "";
	vector<NodeCount>::const_iterator it = nodeCount.begin();
	while ( it != nodeCount.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Metric != "" )
		{
			attribute attrBuff = {"metric", (*it).Metric};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:NodeCount", int2string((*it).Value), attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeProcessors()
{
	string buff = "";
	vector<Processors>::const_iterator it = processors.begin();
	while ( it != processors.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Metric != "" )
		{
			attribute attrBuff = {"metric", (*it).Metric};
			attributes.push_back(attrBuff);
		}
		attribute attrBuff = {"consumptionRate", 
			(float2string((*it).ConsumptionRate))};
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Processors", int2string((*it).Value), attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeTimeDuration()
{
	string buff = "";
	vector<TimeDuration>::const_iterator it = timeDuration.begin();
	while ( it != timeDuration.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Type != "" )
		{
			attribute attrBuff = {"type", (*it).Type};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:TimeDuration", (*it).Value, attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeTimeInstant()
{
	string buff = "";
	vector<TimeInstant>::const_iterator it = timeInstant.begin();
	while ( it != timeInstant.end())
	{
		vector<attribute> attributes;
		if ((*it).Description != "" )
		{
			attribute attrBuff = {"description", (*it).Description};
			attributes.push_back(attrBuff);
		}
		if ( (*it).Type != "" )
		{
			attribute attrBuff = {"type", (*it).Type};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:TimeInstant", (*it).Value, attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeServiceLevel()
{
	string buff = "";
	vector<ServiceLevel>::const_iterator it = serviceLevel.begin();
	while ( it != serviceLevel.end())
	{
		vector<attribute> attributes;
		if ( (*it).Type != "" )
		{
			attribute attrBuff = {"type", (*it).Type};
			attributes.push_back(attrBuff);
		}
		buff += tagAdd ("urwg:ServiceLevel", (*it).Value, attributes );
		it++;
	}
	return buff;
}

string urwg_UsageRecord::composeResourceExtension()
{
	string	buff = "";
	vector<attribute> attributes;
	if ( resourceExtension.ResPriceAuthorityContact != "" )
	{
		attribute attrBuff = {"urwg:description", "ResPriceAuthorityContact" };
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Resource", resourceExtension.ResPriceAuthorityContact, attributes);
	}
	if ( resourceExtension.ResAccountingServerContact != "" )
	{
		attributes.clear();
		attribute attrBuff = {"urwg:description", "ResAccountingServerContact" };
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Resource", resourceExtension.ResAccountingServerContact, attributes);
	}
	if ( resourceExtension.UserAccountingServerContact != "" )
	{
		attributes.clear();
		attribute attrBuff = {"urwg:description", "UserAccountingServerContact" };
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Resource", resourceExtension.UserAccountingServerContact, attributes);
	}
	if ( resourceExtension.ResRequiresEconomicAccounting )
	{
		attributes.clear();
		attribute attrBuff = {"urwg:description", "ResRequiresEconomicAccounting" };
		attributes.push_back(attrBuff);
		
		buff += tagAdd ("urwg:Resource", "true", attributes);
	}
	if ( resourceExtension.LocalUserGroup != "" )
	{
		attributes.clear();
		attribute attrBuff = {"urwg:description", "LocalUserGroup" };
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Resource", resourceExtension.LocalUserGroup, attributes);
	}
	if ( resourceExtension.UserVOName != "" )
        {
                attributes.clear();
                attribute attrBuff = {"urwg:description", "UserVOName" };
                attributes.push_back(attrBuff);
                buff += tagAdd ("urwg:Resource", resourceExtension.UserVOName, attributes);
        }
	if ( resourceExtension.UserFQAN != "" )
        {
                attributes.clear();
                attribute attrBuff = {"urwg:description", "UserFQAN" };
                attributes.push_back(attrBuff);
                buff += tagAdd ("urwg:Resource", resourceExtension.UserFQAN, attributes);
        }
	if ( resourceExtension.ResourceIdentity != "" )
	{
		attributes.clear();
		attribute attrBuff = {"urwg:description", "ResourceIdentity" };
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Resource", resourceExtension.ResourceIdentity, attributes);
	}
	if ( resourceExtension.ResourceKeyInfo != "" )
	{
		attributes.clear();
		attribute attrBuff = {"urwg:description", "ResourceKeyInfo" };
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Resource", resourceExtension.ResourceKeyInfo, attributes);
	}
	if ( resourceExtension.SubmitTime != "" )
	{
		attributes.clear();
		attribute attrBuff = {"urwg:description", "SubmitTime" };
		attributes.push_back(attrBuff);
		buff += tagAdd ("urwg:Resource", resourceExtension.SubmitTime, attributes);
	}
	return buff;
}
