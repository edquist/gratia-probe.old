// copyright 2004-2006 EGEE project, see LICENSE file.

#ifndef STRINGSPLIT_H
#define STRINGSPLIT_H

#include<string>
#include<vector>

using namespace std;

inline void Split (char delim, string& input, vector<string> *output)
{
	size_t pos = 0;
	size_t prev_pos = 0;
	string buffer;
	while (( pos = input.find_first_of(delim, pos))
			!= string::npos )
	{
		if ( pos == 0 )//first character matches delimiter
		{
			prev_pos=++pos;
			continue;
		}
		output->push_back(input.substr(prev_pos, pos-prev_pos));
		prev_pos = ++pos;
	}
	output->push_back ( input.substr( prev_pos, pos - prev_pos ));
}


inline void Split (char delim, char *input, vector<string> *output)
{
        string inp = input;
	Split(delim, inp, output);
}

#endif
