# -*- coding: utf-8 -*-
#
# (c) Copyright 2002-2007 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
# Authors: Doug Deprenger, Don Welch
#

# Std Lib
import sys, thread, syslog, traceback, string, os

identity = string.maketrans('','')
unprintable = identity.translate(identity, string.printable)

def printable(s):
    return s.translate(identity, unprintable)


DEFAULT_LOG_LEVEL = 'info'

class Logger(object):

    LOG_LEVEL_NONE = 99
    LOG_LEVEL_FATAL = 6
    LOG_LEVEL_ERROR = 5
    LOG_LEVEL_WARN = 4
    LOG_LEVEL_INFO = 3
    LOG_LEVEL_DEBUG = 2
    LOG_LEVEL_DBG = 2

    logging_levels = {'none' : LOG_LEVEL_NONE,
                       'fata' : LOG_LEVEL_FATAL,
                       'fatal' : LOG_LEVEL_FATAL,
                       'erro' : LOG_LEVEL_ERROR,
                       'error' : LOG_LEVEL_ERROR,
                       'warn' : LOG_LEVEL_WARN,
                       'info' : LOG_LEVEL_INFO,
                       'debu' : LOG_LEVEL_DEBUG,
                       'debug' : LOG_LEVEL_DEBUG}


    LOG_TO_DEV_NULL = 0
    LOG_TO_CONSOLE = 1
    LOG_TO_SCREEN = 1
    LOG_TO_FILE = 2
    LOG_TO_CONSOLE_AND_FILE = 3
    LOG_TO_BOTH = 3


    def __init__(self, module='', level=LOG_LEVEL_INFO, where=LOG_TO_CONSOLE_AND_FILE,
                 log_datetime=False, log_file=None):

        self.set_level(level)
        self._where = where
        self._log_file = log_file
        self._log_datetime = log_datetime
        self._lock = thread.allocate_lock()
        self.module = module
        self.pid = os.getpid()

    def set_level(self, level):
        if isinstance(level,str):
            level = level[:4].lower()

            if level in Logger.logging_levels.keys():
                self._level = Logger.logging_levels.get(level, Logger.LOG_LEVEL_INFO)
                return True
            else:
                self.error("Invalid logging level: %s" % level)
                return False

        elif isinstance(level,int):
            if Logger.LOG_LEVEL_DEBUG <= level <= Logger.LOG_LEVEL_FATAL:
                self._level = level
            else:
                self.error("Invalid logging level: %d" % level)
                return False

        else:
            return False

    def set_module(self, module):
        self.module = module


    def set_logfile(self, log_file):
        self._log_file = log_file
        try:
            self._log_file_f = file(self._log_file, 'w')
        except IOError:
            self._log_file = None
            self._log_file_f = None
            self._where = Logger.LOG_TO_SCREEN

    def set_where(self, where):
        self._where = where

    def get_level(self):
        return self._level

    def is_debug(self):
        return self._level == Logger.LOG_LEVEL_DEBUG

    level = property(get_level, set_level)


    def log(self, message, level):
        if self._where in (Logger.LOG_TO_CONSOLE, Logger.LOG_TO_CONSOLE_AND_FILE):
            try:
                self._lock.acquire()
                if level >= Logger.LOG_LEVEL_WARN:
                    out = sys.stderr
                else:
                    out = sys.stdout
                out.write(message)
                out.write('\n')
            finally:
                self._lock.release()

    def log_to_file(self, message):
        try:
            self._lock.acquire()
            self._log_file_f.write(message.replace('\x1b', ''))
            self._log_file_f.write('\n')

        finally:
            self._lock.release()

    def stderr(self, message):
        try:
            self._lock.acquire()
            sys.stderr.write("%s: %s\n" % (self.module, message))
        finally:
            self._lock.release()

    def debug(self, message, fmt=True):
        if self._level <= Logger.LOG_LEVEL_DEBUG:
            if fmt:
                self.log("%s%s[%d]: debug: %s%s" % ('\x1b[34;01m', self.module, self.pid, message, '\x1b[0m'), Logger.LOG_LEVEL_DEBUG)
            else:
                self.log("%s[%d]: debug: %s" % (self.module, self.pid, message), Logger.LOG_LEVEL_DEBUG)

            syslog.syslog(syslog.LOG_DEBUG, "%s[%d]: debug: %s" % (self.module, self.pid, message))
            
            if self._log_file is not None and \
                self._where in (Logger.LOG_TO_FILE, Logger.LOG_TO_CONSOLE_AND_FILE):
                
                self.log_to_file("%s[%d]: debug: %s" % (self.module, self.pid, message))

    dbg = debug

    def debug_block(self, title, block, fmt=False):
        if self._level <= Logger.LOG_LEVEL_DEBUG:
            if fmt:
                self.log("%s%s[%d]: debug: %s:%s" % ('\x1b[34;01m', self.module,  self.pid, title, '\x1b[0m'), Logger.LOG_LEVEL_DEBUG)
                self.log("%s%s%s" % ('\x1b[34;01m', block, '\x1b[0m'), Logger.LOG_LEVEL_DEBUG)
            else:
                self.log("%s[%d]: debug: :%s" % (self.module, self.pid, title), Logger.LOG_LEVEL_DEBUG)
                self.log(block, Logger.LOG_LEVEL_DEBUG)
                
            if self._log_file is not None and \
                self._where in (Logger.LOG_TO_FILE, Logger.LOG_TO_CONSOLE_AND_FILE):
                
                self.log_to_file("%s[%d]: debug: :%s" % (self.module, self.pid, title))
                self.log_to_file(block)


    printable = """ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~  """

    def log_data(self, data, width=16, fmt=False):
        if self._level <= Logger.LOG_LEVEL_DEBUG:
            index, line = 0, data[0:width]
            while line:
                txt = ' '.join(['%04x: ' % index, ' '.join(['%02x' % ord(d) for d in line]), ' '*(width*3-3*len(line)), ''.join([('.', i)[i in Logger.printable] for i in line])])
                if fmt:
                    self.log("%s%s[%d]: debug: %s:%s" % ('\x1b[34;01m', self.module,  self.pid, txt, '\x1b[0m'), Logger.LOG_LEVEL_DEBUG)
                else:
                    self.log("%s[%d]: debug: :%s" % (self.module, self.pid, txt), Logger.LOG_LEVEL_DEBUG)

                index += width
                line = data[index:index+width]                

    def info(self, message, fmt=True):
        if self._level <= Logger.LOG_LEVEL_INFO:
            self.log(message, Logger.LOG_LEVEL_INFO)
            
            if self._log_file is not None and \
                self._where in (Logger.LOG_TO_FILE, Logger.LOG_TO_CONSOLE_AND_FILE):
                
                self.log_to_file("%s[%d]: info: :%s" % (self.module, self.pid, message))

    information = info

    def warn(self, message, fmt=True):
        if self._level <= Logger.LOG_LEVEL_WARN:
            if fmt:
                self.log("%swarning: %s%s" % ('\x1b[35;06m', message, '\x1b[0m'), Logger.LOG_LEVEL_WARN)
            else:
                self.log("warning: %s" % message, Logger.LOG_LEVEL_WARN)

            syslog.syslog(syslog.LOG_WARNING, "%s[%d]: warning: %s" % (self.module, self.pid, message))
            
            if self._log_file is not None and \
                self._where in (Logger.LOG_TO_FILE, Logger.LOG_TO_CONSOLE_AND_FILE):
                
                self.log_to_file("%s[%d]: warn: :%s" % (self.module, self.pid, message))

    warning = warn

    def note(self, message, fmt=True):
        if self._level <= Logger.LOG_LEVEL_WARN:
            if fmt:
                self.log("%snote: %s%s" % ('\x1b[32;01m', message, '\x1b[0m'), Logger.LOG_LEVEL_WARN)
            else:
                self.log("note: %s" % message, Logger.LOG_LEVEL_WARN)

            syslog.syslog(syslog.LOG_WARNING, "%s[%d]: note: %s" % (self.module, self.pid, message))
            
            if self._log_file is not None and \
                self._where in (Logger.LOG_TO_FILE, Logger.LOG_TO_CONSOLE_AND_FILE):
                
                self.log_to_file("%s[%d]: note: :%s" % (self.module, self.pid, message))

    notice = note

    def error(self, message, fmt=True):
        if self._level <= Logger.LOG_LEVEL_ERROR:
            if fmt:
                self.log("%serror: %s%s" % ('\x1b[31;01m', message, '\x1b[0m'), Logger.LOG_LEVEL_ERROR)
            else:
                self.log("error: %s" % message, Logger.LOG_LEVEL_ERROR)

            syslog.syslog(syslog.LOG_ALERT, "%s[%d] error: %s" % (self.module, self.pid, message))
            
            if self._log_file is not None and \
                self._where in (Logger.LOG_TO_FILE, Logger.LOG_TO_CONSOLE_AND_FILE):
                
                self.log_to_file("%s[%d]: error: :%s" % (self.module, self.pid, message))
            

    def fatal(self, message, fmt=True):
        if self._level <= Logger.LOG_LEVEL_FATAL:
            if fmt:
                self.log("%sfatal error: %s%s" % ('\x1b[31;01m', message, '\x1b[0m'), Logger.LOG_LEVEL_DEBUG)
            else:
                self.log("fatal error: %s" % message, Logger.LOG_LEVEL_DEBUG)

            syslog.syslog(syslog.LOG_ALERT, "%s[%d]: fatal: %s" % (self.module, self.pid, message))
            
            if self._log_file is not None and \
                self._where in (Logger.LOG_TO_FILE, Logger.LOG_TO_CONSOLE_AND_FILE):
                
                self.log_to_file("%s[%d]: fatal: :%s" % (self.module, self.pid, message))
            

    def exception(self):
        typ, value, tb = sys.exc_info()
        body = "Traceback (innermost last):\n"
        lst = traceback.format_tb(tb) + traceback.format_exception_only(typ, value)
        body = body + "%-20s %s" % (''.join(lst[:-1]), lst[-1],)
        self.fatal(body)
