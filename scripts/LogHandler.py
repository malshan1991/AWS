#!/usr/bin/python

import datetime
import errno
import logging
import os
import pprint
import re

#-------------------------------------------------------------------------------
# LOGGING
#-------------------------------------------------------------------------------

TRACE_LEVEL_NUM = 5

class LogHandler:

    def __init__(self, level=None, logfile=None, module=None, script_invocation=None):
        self.script_invocation = script_invocation
        if level is None:
            self.level      = logging.DEBUG
        else:
            self.level      = level

        # get root logger
        self.logger     = logging.getLogger(module)

        logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
        logging.Logger.trace = self.trace

        # set default log level
        self.logger.setLevel(logging.NOTSET)

        if module is None:
            # remove all handlers - should only be one rootLogger
            del self.logger.handlers[:]
            self.createHandlers(level=level, logfile=logfile)


    def createHandlers(self, level=None, logfile=None, module=None):
        self.handlers   = { 'console':  None, }
        if logfile:
            self.handlers[logfile] = None
            if re.search(r'\/', logfile):                   # check if path
                logpath = re.sub(r'\/[^\/]*$', '', logfile) # remove file from path
                try:
                    os.makedirs(logpath)
                except OSError as e:
                    if e.errno == errno.EEXIST and os.path.isdir(logpath):
                        pass
                    else:
                        raise
            else:
                print("{0} is not a path".format(logfile))

        # create formatter
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)-8s] (%(module)-20s) - %(message)s', '%Y%m%d %H:%M:%S')

        # add handles to logger
        for handle in self.handlers.keys():
            handler = self.__createHandler(handle, self.level, formatter)
            if handler:
                self.logger.addHandler(handler)
        self.__displayConfig(self.logger)

        return self.logger


    def __createHandler(self, handleName, level, formatter):
        handler = None

        if handleName == 'console':
            handler = logging.StreamHandler()
        else:
            handler = logging.FileHandler(handleName)
            level   = logging.DEBUG

        if handler:
            handler.setFormatter(formatter)
            handler.setLevel(level)

        return handler


    def __displayConfig(self, logger, debug=False):
        logger.debug("-" * 80)
        if self.script_invocation:
            logger.debug("Invoked as [{0}]".format(' '.join(self.script_invocation)))
        if debug:
            configStr = pprint.pformat(config, indent=4)
            logger.debug("Config CLI:\n" + configStr)


    def getLogger(self):
        return self.logger


    def trace(self, message, *args, **kws):
        if self.logger.isEnabledFor(TRACE_LEVEL_NUM):
            self.logger._log(TRACE_LEVEL_NUM, message, args, **kws)


    def setLevel(level):
        self.logger.setLevel(level)


    @staticmethod
    def addTraceLogLevel():
        # define custom trace level log level
        TRACE_LEVEL_NUM = 5

        def trace(self, message, *args, **kws):
            if self.isEnabledFor(TRACE_LEVEL_NUM):
                self._log(TRACE_LEVEL_NUM, message, args, **kws)

        logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
        logging.Logger.trace = trace
        logging.trace = trace
    

    def giveupthefunc():
        frame = inspect.currentframe(1)
        code  = frame.f_code
        globs = frame.f_globals
        functype = type(lambda: 0)
        funcs = []
        for func in gc.get_referrers(code):
            if type(func) is functype:
                if getattr(func, "__code__", None) is code:
                    if getattr(func, "__globals__", None) is globs:
                        funcs.append(func)
                        if len(funcs) > 1:
                            return None
        return funcs[0] if funcs else None

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

def main():
    print ("This should not be run")


#--------------------------------------------------------------------------------
# only execute main if run as a script
if __name__ == '__main__':
    main()
