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

__version__ = '2.0'
__title__ = 'HPLIP Installer'
__doc__ = "Installer for HPLIP tarball."


# Std Lib
import getopt, os, os.path, sys, time

# Local
from base.g import *
from base import utils
from installer import core


USAGE = [(__doc__, "", "name", True),
         ("Usage: sh ./hplip-install [MODE] [OPTIONS]", "", "summary", True),
         utils.USAGE_SPACE,
         ("[MODE]", "", "header", False),
         #("Enter browser (web) UI mode:", "-w or --web or --browser", "option", False),
         ("Run in interactive mode:", "-i or --interactive (Default)", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         ("Automatic mode (chooses the most common options):", "-a or --auto", "option", False),
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
mode = INTERACTIVE_MODE
auto = False

try:
    opts, args = getopt.getopt(sys.argv[1:], 'hl:guiaw', 
        ['help', 'help-rest', 'help-man', 'help-desc',
        'logging=', 'interactive', 'auto', 'web', 'browser']) 

except getopt.GetoptError:
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

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-i', '--interactive'):
        mode = INTERACTIVE_MODE

    elif o in ('-a', '--auto'):
        auto = True

    elif o in ('-w', '--browser', '--web'):
        mode = BROWSER_MODE


log_file = os.path.normpath('./hplip-install_%s.log' % time.strftime("%a-%d-%b-%Y_%H:%M:%S"))
#print log_file
if os.path.exists(log_file):
    os.remove(log_file)

log.set_logfile(log_file)
log.set_where(log.LOG_TO_CONSOLE_AND_FILE)

log.debug("Log file=%s" % log_file)

version_description, version_public, version_internal = core.getHPLIPVersion()
log.debug("HPLIP Description=%s Public version=%s Internal version = %s"  % 
    (version_description, version_public, version_internal))

prop.version = version_public
utils.log_title(__title__, __version__)

if mode == BROWSER_MODE:
    from installer import web_install
    log.debug("Starting web browser installer...")
    web_install.start()

elif mode == INTERACTIVE_MODE:
    from installer import text_install
    log.debug("Starting text installer...")
    text_install.start(auto)

else:
    log.error("Invalid mode. Please use '-i' or '-w' to select the mode.")
    sys.exit(1)

