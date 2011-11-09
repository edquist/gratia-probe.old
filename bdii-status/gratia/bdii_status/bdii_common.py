
import os
import re
import sys
import logging
import optparse
import logging.handlers

default_bdii = 'ldap://is.grid.iu.edu:2170'

import gratia.common.GratiaCore as GratiaCore
import gratia.services.Subcluster as Subcluster
import gratia.services.StorageElement as StorageElement
import gratia.services.StorageElementRecord as StorageElementRecord
import gratia.services.ComputeElement as ComputeElement
import gratia.services.ComputeElementRecord as ComputeElementRecord

log = None

class _hdict(dict): #pylint: disable-msg=C0103
    """
    Hashable dictionary; used to make LdapData objects hashable.
    """
    def __hash__(self):
        items = self.items()
        items.sort()
        return hash(tuple(items))

class LdapData:

    """
    Class representing the logical information in the GLUE entry.
    Given the LDIF GLUE, represent it as an object.

    """

    #pylint: disable-msg=W0105
    glue = {}
    """
    Dictionary representing the GLUE attributes.  The keys are the GLUE entries,
    minus the "Glue" prefix.  The values are the entries loaded from the LDIF.
    If C{multi=True} was passed to the constructor, then these are all tuples.
    Otherwise, it is just a single string.
    """

    objectClass = []
    """
    A list of the GLUE objectClasses this entry implements.
    """

    dn = []
    """
    A list containing the components of the DN.
    """

    def __init__(self, data, multi=False):
        self.ldif = data
        glue = {}
        objectClass = []
        for line in self.ldif.split('\n'):
            if line.startswith('dn: '):
                dn = line[4:].split(',')
                dn = [i.strip() for i in dn]
                continue
            try:
                # changed so we can handle the case where val is none
                #attr, val = line.split(': ', 1)
                p = line.split(': ', 1)
                attr = p[0]
                try:
                    val = p[1]
                except:
                    val = ""
            except:
                print >> sys.stderr, line.strip()
                raise
            val = val.strip()
            if attr.startswith('Glue'):
                if attr == 'GlueSiteLocation':
                    val = tuple([i.strip() for i in val.split(',')])
                if multi and attr[4:] in glue:
                    glue[attr[4:]].append(val)
                elif multi:
                    glue[attr[4:]] = [val]
                else:
                    glue[attr[4:]] = val
            elif attr == 'objectClass':
                objectClass.append(val)
            elif attr.lower() == 'mds-vo-name':
                continue
            else:
                raise ValueError("Invalid data:\n%s" % data)
        objectClass.sort()
        self.objectClass = tuple(objectClass)
        try:
            self.dn = tuple(dn)
        except:
            print >> sys.stderr, "Invalid GLUE:\n%s" % data
            raise
        for entry in glue:
            if multi:
                glue[entry] = tuple(glue[entry])
        self.glue = _hdict(glue)
        self.multi = multi

    def to_ldif(self):
        """
        Convert the LdapData back into LDIF.
        """
        ldif = 'dn: ' + ','.join(self.dn) + '\n'
        for obj in self.objectClass:
            ldif += 'objectClass: %s\n' % obj
        for entry, values in self.glue.items():
            if entry == 'SiteLocation':
                if self.multi:
                    for value in values:
                        ldif += 'GlueSiteLocation: %s\n' % \
                            ', '.join(list(value))
                else:
                    ldif += 'GlueSiteLocation: %s\n' % \
                        ', '.join(list(values))
            elif not self.multi:
                ldif += 'Glue%s: %s\n' % (entry, values)
            else:
                for value in values:
                    ldif += 'Glue%s: %s\n' % (entry, value)
        return ldif

    def __hash__(self):
        return hash(tuple([normalizeDN(self.dn), self.objectClass, self.glue]))

    def __str__(self):
        output = 'Entry: %s\n' % str(self.dn)
        output += 'Classes: %s\n' % str(self.objectClass)
        output += 'Attributes: \n'
        for key, val in self.glue.items():
            output += ' - %s: %s\n' % (key, val)
        return output

    def __eq__(self, ldif1, ldif2):
        if not compareDN(ldif1, ldif2):
            return False
        if not compareObjectClass(ldif1, ldif2):
            return False
        if not compareLists(ldif1.glue.keys(), ldif2.glue.keys()):
            return False
        for entry in ldif1.glue:
            if not compareLists(ldif1.glue[entry], ldif2.glue[entry]):
                return False
        return True

def read_ldap(fp, multi=False):
    """
    Convert a file stream into LDAP entries.

    @param fp: Input stream containing LDIF data.
    @type fp: File-like object
    @keyword multi: If True, then the resulting LdapData objects can have
        multiple values per GLUE attribute.
    @returns: List containing one LdapData object per LDIF entry.
    """
    entry_started = False
    mybuffer = ''
    entries = []
    counter = 0
    for origline in fp.readlines():
        counter += 1
        line = origline.strip()
        if len(line) == 0 and entry_started == True:
            entries.append(LdapData(mybuffer[1:], multi=multi))
            entry_started = False
            mybuffer = ''
        elif len(line) == 0 and entry_started == False:
            pass
        else: # len(line) > 0
            if not entry_started:
                entry_started = True
            if origline.startswith(' '):
                mybuffer += origline[1:-1]
            else:
                mybuffer += '\n' + line
    #Catch the case where we started the entry and got to the end of the file
    #stream
    if entry_started == True:
        entries.append(LdapData(mybuffer[1:], multi=multi))
    return entries

def query_bdii(cp, query="(objectClass=GlueCE)", binding="o=grid"):
    endpoint = cp.get('bdii', 'endpoint')
    r = re.compile('ldap://(.*):([0-9]*)')
    m = r.match(endpoint)
    if not m: 
        raise Exception("Improperly formatted endpoint: %s." % endpoint)
    info = {}
    info['hostname'], info['port'] = m.groups()
    info['query'] = query
    info["binding"] = binding
    #print info
    fp = os.popen('ldapsearch -h %(hostname)s -p %(port)s -xLLL '
        "-b %(binding)s '%(query)s'" % info)
    return fp

def read_bdii(cp, query="", binding="o=grid", multi=False):
    """
    Query a BDII instance, then parse the results.

    @param cp: Site configuration; see L{query_bdii}
    @type cp: ConfigParser
    @keyword query: LDAP query filter to use
    @keyword base: Base DN to query on.
    @keyword multi: If True, then resulting LdapData can have multiple values
        per attribute
    @returns: List of LdapData objects representing the data the BDII returned.
    """
    fp = query_bdii(cp, query=query, binding=binding)
    return read_ldap(fp, multi=multi)

def normalizeDN(dn_tuple):
    """
    Normalize a DN; because there are so many problems with mds-vo-name
    and presence/lack of o=grid, just remove those entries.
    """
    dn = ''
    for entry in dn_tuple:
        if entry.lower().find("mds-vo-name") >= 0 or \
                 entry.lower().find("o=grid") >=0:
            return dn[:-1]
        dn += entry + ','

def join_FK(item, join_list, join_attr, join_fk_name="ForeignKey"):
    if item.multi:
        item_fks = item.glue[join_fk_name]
        for item_fk in item_fks:
            for entry in join_list:
                if entry.multi:
                    for val in entry.glue[join_attr]:
                        test_val = "Glue%s=%s" % (join_attr, val)
                        if test_val == item_fk:
                            return entry
                else:
                    test_val = "Glue%s=%s" % (join_attr, entry.glue[join_attr])
                    if test_val == item_fk:
                        return entry
    else:
        item_fk = item.glue[join_fk_name]
        for entry in join_list:
            if entry.multi:
                for val in entry.glue[join_attr]:
                    test_val = "Glue%s=%s" % (join_attr, val)
                    if test_val == item_fk:
                        return entry
            else:
                test_val = "Glue%s=%s" % (join_attr, entry.glue[join_attr])
                if test_val == item_fk:
                    return entry
    raise ValueError("Unable to find matching entry in list.")

def parse_opts():
    global ProbeConfig

    parser = optparse.OptionParser()
    parser.add_option("-l", "--logfile", help="Log file location.  Defaults " \
        "to the Gratia logging infrastructure.", dest="logfile")
    parser.add_option("-c", "--gratia_config", help="Location of the Gratia " \
        "config; defaults to /etc/gratia/bdii-status/ProbeConfig",
        dest="gratia_config")
    parser.add_option("--bdii", help="BDII to query; defaults to %s" % \
        default_bdii, dest="bdii")
    parser.add_option("-v", "--verbose", help="Enable verbose logging to " \
        "stdout.", default=False, action="store_true", dest="verbose")

    opts, args = parser.parse_args()

    # Expand our input paths:
    if opts.logfile:
        opts.logfile = os.path.expanduser(opts.logfile)
    if opts.gratia_config:
        opts.gratia_config = os.path.expanduser(opts.gratia_config)

    # Initialize logging
    logfile = "/var/log/gratia/bdii-status.log"
    if opts.logfile:
        logfile = opts.logfile
    path, _ = os.path.split(logfile)
    if path and not os.path.exists(path):
        os.makedirs(path)
    has_logfile = True
    try:
        fp = open(logfile, 'w')
        fp.close()
    except Exception, e:
        has_logfile = False
        print >> sys.stderr, ("Could not open bdii-status logfile, %s, for " \
            "write.  Error: %s." % (logfile, str(e)))
        print >> sys.stderr, "Logging will be written to stderr."
    global log
    log = logging.getLogger("BdiiStatus")
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    if has_logfile:
        handler = logging.handlers.RotatingFileHandler(
            logfile, maxBytes=20*1024*1024, backupCount=5)
    else:
        handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    if opts.verbose:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        log.addHandler(handler)

    # Initialize Gratia
    gratia_config = None
    if opts.gratia_config and os.path.exists(opts.gratia_config):
        gratia_config = opts.gratia_config
    else:
        tmp = "/etc/gratia/bdii-status/ProbeConfig"
        if os.path.exists(tmp):
            gratia_config = tmp
    if not gratia_config:
        raise Exception("Unable to find a suitable ProbeConfig to use!")
    GratiaCore.Initialize(gratia_config)
    ProbeConfig = gratia_config

    if opts.verbose:
        GratiaCore.Config.__DebugLevel = 5

    return opts


