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

__version__ = '0.1'
__title__ = 'System Tray Status Service'
__doc__ = ""

# StdLib
import sys
import os
import getopt
import signal

# Local
from base.g import *
from base import utils
from prnt import cups


USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-systray [OPTIONS]", "", "summary", True),
         utils.USAGE_OPTIONS,
         ("Force Qt3:", "--qt3 (default)", "option", False),
         ("Force Qt4:", "--qt4", "option", False),
         ("Startup even if no hplip CUPS queues are present:", "-x or --force-startup", "option", False),
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
        ]


def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hpssd.py', __version__)
    sys.exit(0)



if __name__ == '__main__':
    log.set_module('hp-systray(init)')

    prop.prog = sys.argv[0]
    force_qt3 = False
    force_qt4 = False
    force_startup = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'l:hgx', 
            ['level=', 'help', 'help-man', 'help-rest', 'help-desc',
            'qt3', 'qt4', 'force-startup'])

    except getopt.GetoptError, e:
        log.error(e.msg)
        usage()

    if os.getenv("HPLIP_DEBUG"):
        log.set_level('debug')

    for o, a in opts:
        if o in ('-l', '--logging'):
            log_level = a.lower().strip()
            if not log.set_level(log_level):
                usage()

        elif o == '-g':
            log.set_level('debug')

        elif o in ('-h', '--help'):
            usage()

        elif o == '--help-rest':
            usage('rest')

        elif o == '--help-man':
            usage('man')

        elif o == '--help-desc':
            print __doc__,
            sys.exit(0)

        elif o == '--qt3':
            force_qt3 = True
            force_qt4 = False

        elif o == '--qt4':
            force_qt4 = True
            force_qt3 = False
            
        elif o in ('-x', '--force-startup'):
            force_startup = True


    utils.log_title(__title__, __version__) 
    
    if os.getuid() == 0:
        log.error("hp-systray cannot be run as root. Exiting.")
        sys.exit(1)

    if not force_startup:
        # Check for any hp: or hpfax: queues. If none, exit
        if not utils.any([p.device_uri for p in cups.getPrinters()], lambda x : x.startswith('hp')):
            log.warn("No hp: or hpfax: devices found in any installed CUPS queue. Exiting.")
            sys.exit(1)
    
    ok, lock_file = utils.lock_app('hp-systray')
    if not ok:
        sys.exit(1)
    
    r, w = os.pipe()
    parent_pid = os.getpid()
    log.debug("Parent PID=%d" % parent_pid)
    child_pid = os.fork()

    if child_pid:
        # parent (UI)
        os.close(w)

        try:
            if force_qt3 or (not force_qt3 and not force_qt4):
                from ui import systemtray_qt3
                systemtray_qt3.run(r, child_pid)
    
            elif force_qt4:
                from ui import systemtray_qt4
                systemtray_qt4.run(r, child_pid)
        
        finally:
            if child_pid:
                log.debug("Killing child systray process (pid=%d)..." % child_pid)
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except OSError, e:
                    log.debug("Failed: %s" % e.message)
                
            utils.unlock(lock_file)

                
    else:
        # child (dbus)
        os.close(r)

        try:
            import hpssd
            hpssd.run(w, parent_pid)
        finally:
            if parent_pid:
                log.debug("Killing parent systray process (pid=%d)..." % parent_pid)
                try:
                    os.kill(parent_pid, signal.SIGKILL)
                except OSError, e:
                    log.debug("Failed: %s" % e.message)

            utils.unlock(lock_file)
    

