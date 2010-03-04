// copyright 2004-2006 EGEE project (see LICENSE file)

#include "xmlUtil.h"
#include "int2string.h"
#include <iostream>

inline string stripWhite ( string &input )
{
	size_t startPos = input.find_first_not_of(" \n\0");
	if ( startPos == string::npos )
		return "";
	size_t endPos = input.find_last_not_of(" \n\0");
	if ( endPos == string::npos )
		return "";
	return input.substr( startPos, endPos - startPos +1 );
}


node parse (string *xmlInput, string _tag)
{
        node nodeBuff;
        int pos = xmlInput->find("<" + _tag);
        if ( pos == string::npos )
        {
                node nodeBuff(xmlInput, atoi(E_PARSE_ERROR));
                return nodeBuff;
        }
        int pos2 = xmlInput->find_first_of(">", pos);
	if ( pos2 != string::npos )
	{
		if ( xmlInput->substr(pos2-1,1) == "\\" )
		{
                	xmlInput->erase(pos2-1, 1);
	                string insertBuff = "</" + _tag + ">";
        	        xmlInput->insert(pos2, insertBuff);
                	nodeBuff = parseImpl(xmlInput, _tag);
	                return nodeBuff;
        	        //\> type tag
		}
        	else
	        {
        	        nodeBuff = parseImpl(xmlInput, _tag);
                	return nodeBuff;
	        }
        }
	else
	{
		node nodeBuff(xmlInput, atoi(E_PARSE_ERROR));
		return nodeBuff;
	}
}

node parseImpl(string *xmlInput, string _tag)
{
        string * _mainDoc = xmlInput;
        size_t pos;
        pos = xmlInput->find("<" + _tag);
        if ( pos == string::npos )
        {
                node nodeBuff(_mainDoc, atoi(E_PARSE_ERROR));
                return nodeBuff;
        }
        string starttag = xmlInput->substr(pos,
                        xmlInput->find_first_of(">",pos)-pos+1);
        string endtag = "</" + _tag + ">";
        string buffer;
        pos = xmlInput->find( starttag );
        if ( pos == string::npos )
        {
                node nodeBuff(_mainDoc, atoi(E_PARSE_ERROR));
                return nodeBuff;
        }
        else
        {
                size_t _startPos = pos;
                size_t textStart = pos + starttag.size();
                pos = xmlInput->find( endtag );
                if ( pos == string::npos )
                {
                        node nodeBuff(_mainDoc, atoi(E_PARSE_ERROR));
                        return nodeBuff;
                }
                else
                {
                        size_t _endPos = pos + endtag.size();
                        size_t textEnd = pos;
                        string _text = xmlInput->substr(
                                        textStart,
                                        textEnd-textStart);
                        _text = stripWhite(_text);
                        node nodeBuff(_mainDoc,
                                        0,
                                        _tag,
                                        _text,
                                        _startPos,
                                        _endPos,
                                        true );
                        return nodeBuff;

                }

        }

}

node parse (string *xmlInput, string _tag, string space)
{
        node nodeBuff;
        nodeBuff = parseImpl(xmlInput, _tag);
        string tag2 = "";
        tag2 += space + ":" + _tag;
        if (nodeBuff.status != 0)
                nodeBuff = parse(xmlInput, tag2);
        return nodeBuff;
}

attrType node::getAttributes()
{
	attrType attributes;
	if (valid)
	{
		size_t pos = startPos + tag.size() +1;	
		string buffer;
		buffer = mainDoc->substr(pos,
				mainDoc->find_first_of(">",pos) - pos);
		bool goOn = true;
		while ( goOn )
		{
			pos = buffer.find_first_not_of(" ,");
			if ( pos == string::npos )
			{
				goOn = false;
				break;
			}
			size_t pos1 = buffer.find_first_of("=");
			string param = buffer.substr(pos,
					pos1 - pos);
			param = stripWhite(param);
			buffer.erase(0, pos1 +1);
			pos = buffer.find_first_of('\"');
			pos1 = buffer.find_first_of('\"',pos+1);
			string value = buffer.substr(pos+1, 
					pos1 - pos -1);
			value = stripWhite(value);
			buffer.erase(0, pos1 +1);
			attributes.insert(
					attrType::
					value_type(param,value)
					);
		}
		if ( attributes.size() == 0 )
		{
			status = atoi(E_NO_ATTRIBUTES);
			return attributes;
		}
		return attributes;
		
	}
	else
	{
		status = atoi(E_PARSE_ERROR);
		
	}
	return attributes;
}

int node::release()
{
	if (valid)
	{
		mainDoc->erase(startPos, endPos-startPos);
		valid = false;
		return 0;
	}
	else
	{
		return atoi(E_PARSE_ERROR);
	}
}


string tagAdd(string tag, string content)
{
        string buff;
        buff = "<" + tag + ">" + content + "</" +tag+ ">\n";
        return buff;
}

string tagAdd(string tag, string content, vector<attribute> attributes)
{
        if ( content == "" && attributes.size() == 0 )
        {
                return "";
        }
        string buff;
        buff = "<" + tag;
        vector<attribute>::const_iterator it = attributes.begin();
        while ( it != attributes.end() )
        {
                buff += " " + (*it).key +"="+"\"" + (*it).value + "\"";
                it++;
                if ( it != attributes.end() )
                {
                        buff += "\n";
                }
        }
        if ( content == "" )
        {
                //no Element value attached, end with />
                buff += "/>\n";
        }
        else
        {
                //Element Value is present 
                buff +=">" + content + "</" +tag+ ">\n";
        }
        return buff;
}

string tagAdd(string tag, int content)
{
        string buff;
        buff = "<" + tag + ">" + int2string(content) + "</" +tag+ ">\n";
        return buff;
}

string timeStamp2ISO8601 (time_t t)
{
        struct tm * tmBuff = new(struct tm);
        if ( tmBuff != NULL )
        {
                tmBuff = localtime_r (&t, tmBuff);
        }
        char charBuff[23];
        strftime (charBuff, sizeof(charBuff), "%Y-%m-%dT%T%Z", tmBuff);
        cerr << "DEBUG:" << charBuff << endl;
        string strBuff(charBuff);
        cerr << "DEBUG:" << strBuff << endl;
        if ( tmBuff != NULL )
                delete tmBuff;
        return strBuff;
}

time_t ISO86012timeStamp (string &t)
{
        struct tm * tmBuff = new(struct tm);
        if ( tmBuff != NULL )
        {
                strptime (t.c_str(), "%Y-%m-%dT%T%Z", tmBuff);
        }
        strptime (t.c_str(), "%Y-%m-%dT%T%Z", tmBuff);
        time_t tsBuff = mktime (tmBuff);
        if ( tmBuff != NULL)
                delete tmBuff;
        cerr << "DEBUG:" << tsBuff << endl;
        return tsBuff;
}

string seconds2ISO8601  (int s)
{
        div_t result;
        //compute days
        result = div (s, 86400);
        int days= result.quot;
        result = div (result.rem, 3600);
        int hours= result.quot;
        result = div (result.rem, 60);
        int minutes = result.quot;
        int seconds = result.rem;
        string buffer = "P";
        if ( days != 0 )
                buffer += int2string(days) + "D";
        buffer += "T";
        if ( hours != 0 )
                buffer += int2string(hours) + "H";
        if ( minutes != 0 )
                buffer += int2string(minutes) + "M";
        buffer += int2string(seconds) + "S";
        return buffer;
}

int ISO86012seconds (string s)
{
        unsigned int endMark = string::npos;
        unsigned int beginMark = string::npos;
        size_t buffer = 0;
        if ( s.find("P") == string::npos || s.find("T") == string::npos )
        {
                return 0;
        }
        endMark = s.find("S");
        if ( endMark != string::npos )
        {
                beginMark = s.find_last_of("THM");
                buffer += atoi((s.substr(beginMark+1,
                                endMark-beginMark-1)).c_str());
                endMark = string::npos;
                beginMark = string::npos;
        }
        endMark = s.find("M");
        if ( endMark != string::npos )
        {
                beginMark = s.find_last_of("TH");
                buffer += (atoi((s.substr(beginMark+1,
                                endMark-beginMark-1)).c_str()))*60;
                endMark = string::npos;
                beginMark = string::npos;
        }
        endMark = s.find("H");
        if ( endMark != string::npos )
        {
                beginMark = s.find_last_of("T");
                buffer += (atoi((s.substr(beginMark+1,
                                endMark-beginMark-1)).c_str()))*3600;
                endMark = string::npos;
                beginMark = string::npos;
        }
        endMark = s.find("D");
        if ( endMark != string::npos )
        {
                beginMark = s.find_last_of("P");
                buffer += (atoi((s.substr(beginMark+1,
                                endMark-beginMark-1)).c_str()))*86400;
                endMark = string::npos;
                beginMark = string::npos;
        }
        return buffer;
}

string parseAttribute ( string a, attrType& m)
{
        string buff = "";
        string attr;            
        unsigned int pos = a.find_first_of(":");
        if ( pos != string::npos )
        {
                //there's a ':' scope delimiter
                buff = m[a];
                if ( buff == "" )
                {
                        attr = a.substr(pos+1,a.length()-pos);
                        buff = m[attr];
                }
        }
	else
	{
		buff = m[a];
	}
        return buff;
}

