// copyright 2004-2006 EGEE project (see LICENSE file)

#ifndef XMLUTIL_H
#define XMLUTIL_H
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include "hlr_prot_errcode.h"

using namespace std;


inline string float2string(float f)
{
        ostringstream ost;
        ost << f;
        return ost.str();
}

typedef map<string,string> attrType;

struct attribute
{
        string key;
        string value;
};

string timeStamp2ISO8601 (time_t t);
time_t ISO86012timeStamp (string &t);
string seconds2ISO8601  (int s);
int ISO86012seconds (string s);

class node {
	public:

	node ( string *_mainDoc = NULL, int _status = 0, string _tag = "", string _text = "", int _startPos = 0, int _endPos = 0, bool _valid = false ):
		mainDoc(_mainDoc),
		status(_status),
		tag(_tag),
		text(_text),
		startPos(_startPos),
		endPos(_endPos),
		valid(_valid){;};
	
		//retrieve the info in the node delimited by "tag"
	node friend parse(string *xmlInput, string _tag);
            //retrieve the info in the node delimited by "tag" OR
                // "space:tag"
        node friend parse(string *xmlInput, string _tag, string space);
        node friend parseImpl(string *xmlInput, string _tag);
	string friend tagAdd(string tag, string content);
	string friend tagAdd(string tag, string content, vector<attribute> );
	string friend tagAdd(string tag, int content);
	string friend parseAttribute ( string a, map<string,string>& m);
	
	
		//remove the node from the xml;
	int release();
	attrType getAttributes();
	
	private:
	string * mainDoc;
	
	public:	
	int status;
	
	private:
	string tag;
	
	public:	
	string text;
	
	private:
	int startPos;
	int endPos;	
	bool valid;



	
};

node parse(string *xmlInput, string _tag);
node parse(string *xmlInput, string _tag, string space);
node parseImpl(string *xmlInput, string _tag);
string tagAdd(string tag, string content);
string tagAdd(string tag, string content, vector<attribute> );
string tagAdd(string tag, int content);
string parseAttribute ( string a, map<string,string>& m);

#endif
