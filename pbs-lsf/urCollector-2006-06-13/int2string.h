// copyright 2004-2006 EGEE project, see LICENSE file.

#ifndef INT2STRING_H
#define INT2STRING_H

#include <sstream>
#include <string>

using namespace std;

inline string int2string(int i)
{
	ostringstream ost;
	ost << i;
	return ost.str();
}
	

#endif
