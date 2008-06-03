#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
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
# Author: Don Welch
#

__version__ = '3.3'
__title__ = 'HPLIP Installer'
__doc__ = "Installer for HPLIP tarball."


# Std Lib
import getopt
import os
import os.path
import sys
import time
import re
import platform

# Local
from base.g import *
from base import utils


USAGE = [(__doc__, "", "name", True),
         ("Usage: sh ./hplip-install [MODE] [OPTIONS]", "", "summary", True),
         utils.USAGE_SPACE,
         ("[MODE]", "", "header", False),
         ("Enter browser (web) GUI mode:", "-u or --gui or -w or --web or --browser", "option", False),
         ("Run in interactive (text) mode:", "-t or --text or -i or  --interactive (Default)", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         ("Automatic mode (chooses the most common options):", "-a or --auto (text mode only)", "option", False),
         ("Dependency installation retries:", "-r <retries> or --retries=<retries> (default is 3)", "option", False),
         ("Assume network connection present:", "-n or --network", "option", False),
         ("Force install of all dependencies (FOR TESTING ONLY):", "-x (text mode only)", "option", False),
         ("Unknown distro mode (FOR TESTING ONLY):", "-d (text mode only)", "option", False),
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hplip-install', __version__)
    sys.exit(0)        


log.set_module("hplip-install")

log.debug("euid = %d" % os.geteuid())
mode = INTERACTIVE_MODE #INTERACTIVE_MODE   #BROWSER_MODE
auto = False
test_depends = False
test_unknown = False
language = None
assume_network = False
max_retries = 3

try:
    opts, args = getopt.getopt(sys.argv[1:], 'hl:giawutxdq:nr:', 
        ['help', 'help-rest', 'help-man', 'help-desc', 'gui', 'lang=',
        'logging=', 'interactive', 'auto', 'web', 'browser', 'text', 
        'network', 'retries=']) 

except getopt.GetoptError, e:
    log.error(e.msg)
    usage()
    sys.exit(1)

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    if o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')
        
    elif o in ('-q', '--lang'):
        language = a.lower()

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-i', '--interactive', '--text', '-t'):
        mode = INTERACTIVE_MODE

    elif o in ('-a', '--auto'):
        auto = True

    elif o in ('-u', '-w', '--browser', '--web', '--gui'):
        mode = BROWSER_MODE
        
    elif o == '-x':
        log.warn("Install all depends (-x) is for TESTING ONLY")
        test_depends = True

    elif o == '-d':
        log.warn("Unknown distro (-d) is for TESTING ONLY")
        test_unknown = True
        
    elif o in ('-n', '--network'):
        assume_network = True
        
    elif o in ('-r', '--retries'):
        try:
            max_retries = int(a)
        except ValueError:
            log.error("Invalid value for retries. Set to default of 3.")
            max_retries = 3
        
        
if os.getuid() == 0:
    log.error("hplip-install should not be run as root.")

log_file = os.path.normpath('./hplip-install_%s.log' % time.strftime("%a-%d-%b-%Y_%H:%M:%S"))

if os.path.exists(log_file):
    os.remove(log_file)

log.set_logfile(log_file)
log.set_where(log.LOG_TO_CONSOLE_AND_FILE)

log.debug("Log file=%s" % log_file)

ac_init_pat = re.compile(r"""AC_INIT\(\[(.*?)\], *\[(.*?)\], *\[(.*?)\], *\[(.*?)\] *\)""", re.IGNORECASE)
try:
    config_in = open('./configure.in', 'r')
except IOError:
    prop.version = 'x.x.x'
else:
    for c in config_in:
        if c.startswith("AC_INIT"):
            match_obj = ac_init_pat.search(c)
            prop.version = match_obj.group(2)
            break

    config_in.close()

utils.log_title(__title__, __version__, True)

log.info("Installer log saved in: %s" % log.bold(log_file))
log.info("")

if mode == BROWSER_MODE:
    if platform.system() != 'Darwin':
        if not os.getenv('DISPLAY'):
            log.warn("No display found.")
            mode = INTERACTIVE_MODE
        
    if utils.find_browser() is None:
        log.warn("No browser found.")
        mode = INTERACTIVE_MODE

if mode == BROWSER_MODE:
    if test_depends or test_unknown:
        log.error("Test modes -x and -d are not implemented with GUI mode.")
    from installer import web_install
    log.debug("Starting web browser installer...")
    web_install.start(language)

elif mode == INTERACTIVE_MODE:

    try:
        from installer import text_install
        log.debug("Starting text installer...")
        text_install.start(language, auto, test_depends, test_unknown, assume_network, max_retries)
    except KeyboardInterrupt:
        log.error("User exit")

else:
    log.error("Invalid mode. Please use '-i', '-t', '-u' or '-w' to select the mode.")
    sys.exit(1)

