
import re

import gratia.common.global_state as global_state

class Response:

    __responseMatcherURLCheck = re.compile(r'Unknown Command: URL', re.IGNORECASE)
    __responseMatcherErrorCheck = re.compile(r'Error report</title', re.IGNORECASE)
    __BundleProblemMatcher = re.compile(r'Error: Unknown Command: multiupdate', re.IGNORECASE)
    __certRejection = 'Error: The certificate has been rejected by the Gratia Collector!'
    __responseMatcherPostTooLarge = re.compile(r'.*java.lang.IllegalStateException: Post too large.*',
                                               re.IGNORECASE)

    AutoSet = -1
    Success = 0
    Failed = 1
    CollectorError = 2
    UnknownCommand = 3
    ConnectionError = 4
    BadCertificate = 5
    BundleNotSupported = 6
    PostTooLarge = 7

    _codeString = {
        -1: 'UNSET',
        0: 'SUCCESS',
        1: 'FAILED',
        2: 'COLLECTOR_ERROR',
        3: 'UNKNOWN_COMMAND',
        4: 'CONNECTION_ERROR',
        5: 'BAD_CERTIFICATE',
        6: 'BUNDLE_NOT_SUPPORTED',
        7: 'POST TOO LARGE',
        }

    _code = -1
    _message = r''

    def __init__(self, code, message):

        if code == -1:
            if message == 'OK':
                self._code = Response.Success
            elif message == 'Error':

                self._code = Response.CollectorError
            elif message == None:

                self._code = Response.ConnectionError
            elif message == self.__certRejection:

                self._code = Response.BadCertificate
            elif Response.__BundleProblemMatcher.match(message):

                self._code = Response.BundleNotSupported
            elif global_state.collector__wantsUrlencodeRecords == 1 and Response.__responseMatcherURLCheck.search(message):

                self._code = Response.UnknownCommand
            elif Response.__responseMatcherPostTooLarge.search(message):

                self._code = Response.PostTooLarge
            elif Response.__responseMatcherErrorCheck.search(message):

                self._code = Response.ConnectionError
            else:

                self._code = Response.Failed
        else:

            self._code = code
        if message:
            self._message = message

    def __str__(self):
        return '(' + self.getCodeString() + r', ' + self.getMessage() + ')'

    def getCodeString(self):
        return self._codeString[self._code]

    def getCode(self):
        return self._code

    def getMessage(self):
        return str(self._message)

    def setCode(self, code):
        self._code = code

    def setMessage(self, message):
        self._message = message

