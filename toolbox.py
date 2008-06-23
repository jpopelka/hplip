#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2008 Hewlett-Packard Development Company, L.P.
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
# Thanks to Henrique M. Holschuh <hmh@debian.org> for various security patches
#

__version__ = '14.0'
__title__ = 'HP Device Manager'
__doc__ = "The HP Device Manager (aka Toolbox) for HPLIP supported devices. Provides status, tools, and supplies levels."

# Std Lib
import sys
import os
import getopt
import signal

# Local
from base.g import *
import base.utils as utils
from base import status, tui


w = None # write pipe
app = None
toolbox  = None
loc = None
session_bus = None

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-toolbox [OPTIONS]", "", "summary", True),
         utils.USAGE_OPTIONS,
         ("Activate device on startup:", "-d<device_uri> or --device=<device_uri>", "option", False),
         #("Activate printer on startup:", "-p<printer> or --printer=<printer>", "option", False),
         #("Activate function on startup:", "-f<function> or --function=<function>", "option", False),
         ("Disable dbus:", "-x or --disable-dbus", "option", False),
         utils.USAGE_LANGUAGE,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_SEEALSO,
         ("hp-info", "", "seealso", False),
         ("hp-clean", "", "seealso", False),
         ("hp-colorcal", "", "seealso", False),
         ("hp-align", "", "seealso", False),
         ("hp-print", "", "seealso", False),
         ("hp-sendfax", "", "seealso", False),
         ("hp-fab", "", "seealso", False),
         ("hp-testpage", "", "seealso", False),
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-toolbox', __version__)
    sys.exit(0)


def handle_session_signal(*args, **kwds):
    if kwds['interface'] == 'com.hplip.Toolbox' and \
        kwds['member'] == 'Event':

        event = device.Event(*args)

        if event.event_code > EVENT_MAX_EVENT:
            event.event_code = status.MapPJLErrorCode(event.event_code)

        # regular user/device status event
        log.debug("Received event notifier: %d" % event.event_code)

        if w is not None:
            log.debug("Sending event to toolbox UI...")
            try:
                os.write(w, event.pack())
            except OSError:
                log.debug("Failed. Exiting...")
                # if this fails, then hp-toolbox must be killed.
                # No need to continue running...
                sys.exit(1)


log.set_module('hp-toolbox(init)')

try:
    opts, args = getopt.getopt(sys.argv[1:], 'l:hgq:d:x', 
        ['level=', 'help', 'help-rest', 'help-man', 'help-desc', 
        'lang=', 'device=', 'disable-dbus'])

except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

initial_device_uri = None
#initial_printer_name = None
#initial_function = None
disable_dbus = False

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

    elif o in ('-q', '--lang'):
        if a.strip() == '?':
            tui.show_languages()
            sys.exit(0)

        loc = utils.validate_language(a.lower())

    elif o in ('-d', '--device'):
        initial_device_uri = a

    #elif o in ('-f', '--function'):
    #    initial_function = a

    elif o in ('-x', '--disable-dbus'):
        disable_dbus = True



utils.log_title(__title__, __version__)

if os.getuid() == 0:
    log.warn("hp-toolbox should not be run as root.")

ok, lock_file = utils.lock_app('hp-toolbox')
if not ok:
    sys.exit(1)

# UI Forms and PyQt
if not utils.canEnterGUIMode():
    log.error("hp-toolbox requires GUI support. Exiting.")
    sys.exit(1)

try:
    from dbus import SessionBus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gobject import MainLoop

except ImportError:
    log.error("Unable to load dbus - Automatic status updates in HPLIP Device Manager will be disabled.")
    disable_dbus = True    


child_pid, w, r = 0, 0, 0

if not disable_dbus:
    r, w = os.pipe()
    parent_pid = os.getpid()
    log.debug("Parent PID=%d" % parent_pid)
    child_pid = os.fork()

if disable_dbus or child_pid:
    # parent (UI)
    log.set_module("hp-toolbox(UI)")

    if w:
        os.close(w)

    from qt import *
    from ui.devmgr4 import DevMgr4

    # Security: Do *not* create files that other users can muck around with
    os.umask (0037)

    # create the main application object
    app = QApplication(sys.argv)

    if loc is None:
        loc = user_cfg.ui.get("loc", "system")
        if loc.lower() == 'system':
            loc = str(QTextCodec.locale())
            log.debug("Using system locale: %s" % loc)

    if loc.lower() != 'c':    
        e = 'utf8'
        try:
            l, x = loc.split('.')
            loc = '.'.join([l, e])
        except ValueError:
            l = loc
            loc = '.'.join([loc, e])

        log.debug("Trying to load .qm file for %s locale." % loc)
        trans = QTranslator(None)

        qm_file = 'hplip_%s.qm' % l
        log.debug("Name of .qm file: %s" % qm_file)
        loaded = trans.load(qm_file, prop.localization_dir)

        if loaded:
            app.installTranslator(trans)
        else:
            loc = 'c'

    if loc == 'c':
        log.debug("Using default 'C' locale")
    else:
        log.debug("Using locale: %s" % loc)
        QLocale.setDefault(QLocale(loc))
        prop.locale = loc
        try:
            locale.setlocale(locale.LC_ALL, locale.normalize(loc))
        except locale.Error:
            pass

    toolbox = DevMgr4(r, __version__, initial_device_uri, disable_dbus)
    app.setMainWidget(toolbox)

    toolbox.show()

    try:
        try:
            log.debug("Starting GUI loop...")
            app.exec_loop()
        except KeyboardInterrupt:
            sys.exit(0)

    finally:
        if child_pid:
            log.debug("Killing child toolbox process (pid=%d)..." % child_pid)
            try:
                os.kill(child_pid, signal.SIGKILL)
            except OSError, e:
                log.debug("Failed: %s" % e.message)

        utils.unlock(lock_file)
        sys.exit(0)


elif not disable_dbus:
    # dBus
    log.set_module("hp-toolbox(dbus)")

    from base import device

    try:
        # child (dbus connector)
        os.close(r)

        dbus_loop = DBusGMainLoop(set_as_default=True)

        try:
            session_bus = dbus.SessionBus()
        except dbus.exceptions.DBusException, e:
            if os.getuid() != 0:
                log.error("Unable to connect to dbus session bus. Exiting.")
                sys.exit(1)
            else:
                log.error("Unable to connect to dbus session bus (running as root?)")            
                sys.exit(1)

        # Receive events from the session bus
        session_bus.add_signal_receiver(handle_session_signal, sender_keyword='sender',
            destination_keyword='dest', interface_keyword='interface',
            member_keyword='member', path_keyword='path')

        log.debug("Entering main loop...")

        try:
            MainLoop().run()
        except KeyboardInterrupt:
            log.debug("Ctrl-C: Exiting...")

        #print "MainLoop exited!"

    finally:
        if parent_pid:
            log.debug("Killing parent toolbox process (pid=%d)..." % parent_pid)
            try:
                os.kill(parent_pid, signal.SIGKILL)
            except OSError, e:
                log.debug("Failed: %s" % e.message)

        utils.unlock(lock_file)

    sys.exit(0)



