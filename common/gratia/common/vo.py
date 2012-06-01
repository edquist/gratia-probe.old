
import re
import fileinput

from gratia.common.debug import DebugPrint, DebugPrintTraceback
import gratia.common.config as config

__UserVODictionary = {}
__voiToVOcDictionary = {}
__dictionaryErrorStatus = False


def __InitializeDictionary__():
    global __dictionaryErrorStatus
    if __dictionaryErrorStatus:
        return None
    mapfile = config.Config.get_UserVOMapFile()
    if mapfile == None:
        return None
    __voi = []
    __VOc = []
    DebugPrint(4, 'DEBUG: Initializing (voi, VOc) lookup table')
    for line in fileinput.input([mapfile]):
        try:
            mapMatch = re.match(r'#(voi|VOc)\s', line)
            if mapMatch:
                locals()["__" + mapMatch.group(1)] = re.split(r'\s*', line[mapMatch.end(0):])
            if re.match(r'\s*#', line):
                continue
            mapMatch = re.match('\s*(?P<User>\S+)\s*(?P<voi>\S+)', line)
            if mapMatch:
                if not len(__voiToVOcDictionary) and len(__voi) and len(__VOc):
                    try:
                        for index in xrange(0, len(__voi) - 1):
                            __voiToVOcDictionary[__voi[index]] = __VOc[index]
                            if __voiToVOcDictionary[__voi[index]] == None or __voiToVOcDictionary[__voi[index]] \
                                == r'':
                                DebugPrint(0, 'WARNING: no VOc match for voi "' + __voi[index]
                                           + '": not entering in (voi, VOc) table.')
                                del __voiToVOcDictionary[__voi[index]]
                    except IndexError, _:
                        DebugPrint(0, 'WARNING: VOc line does not have at least as many entries as voi line in '
                                    + mapfile + ': truncating')
                __UserVODictionary[mapMatch.group('User')] = {'VOName': mapMatch.group('voi'),
                        'ReportableVOName': __voiToVOcDictionary[mapMatch.group('voi')]}
        except KeyError, e:
            DebugPrint(0, 'WARNING: voi "' + str(e.args[0]) + '" listed for user "' + mapMatch.group('User')
                       + '" not found in (voi, VOc) table')
        except IOError, e:
            DebugPrint(0, 'IO error exception initializing osg-user-vo-map dictionary ' + str(e))
            DebugPrintTraceback()
            __dictionaryErrorStatus = True
        except Exception, e:
            DebugPrint(0, 'Unexpected exception initializing osg-user-vo-map dictionary ' + str(e))
            __dictionaryErrorStatus = True


def VOc(voi):
    if len(__UserVODictionary) == 0:

        # Initialize dictionary

        __InitializeDictionary__()
    return __voiToVOcDictionary.get(voi, voi)


def VOfromUser(user):
    ''' Helper function to obtain the voi and VOc from the user name via the reverse gridmap file'''

    if len(__UserVODictionary) == 0:

        # Initialize dictionary

        __InitializeDictionary__()
    return __UserVODictionary.get(user, None)

