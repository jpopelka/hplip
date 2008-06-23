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

__version__ = '5.1'
__title__ = 'Testpage Print Utility'
__doc__ = "Print a tespage to a printer. Prints a summary of device information and shows the printer's margins."


# Std Lib
import sys
import os
import getopt
import re
import time

# Local
from base.g import *
from base import device, utils, tui
from prnt import cups

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-testpage [PRINTER|DEVICE-URI] [OPTIONS]", "", "summary", True),
         utils.USAGE_ARGS,
         utils.USAGE_DEVICE,
         utils.USAGE_PRINTER,
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         utils.USAGE_BUS1, utils.USAGE_BUS2,
         ("Don't wait for printout to complete:", "-x", "option", True),
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1, utils.USAGE_STD_NOTES2, 
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-testpage', __version__)
    sys.exit(0)


log.set_module('hp-testpage')
try:
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'p:d:hl:b:gx',
                                   ['printer=', 'device=', 'help', 'help-rest', 
                                    'help-man', 'logging=', 'bus=', 'help-desc'])
    except getopt.GetoptError, e:
        log.error(e.msg)
        usage()

    printer_name = None
    device_uri = None
    bus = ['cups']
    log_level = logger.DEFAULT_LOG_LEVEL
    wait_for_printout = True

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

        elif o in ('-p', '--printer'):
            if a.startswith('*'):
                printer_name = cups.getDefaultPrinter()
                log.debug(printer_name)
                
                if printer_name is not None:
                    log.info("Using CUPS default printer: %s" % printer_name)
                else:
                    log.error("CUPS default printer is not set.")
                
            else:
                printer_name = a

        elif o in ('-d', '--device'):
            device_uri = a

        elif o in ('-b', '--bus'):
            bus = [x.lower().strip() for x in a.split(',')]
            if not device.validateBusList(bus):
                usage()

        elif o in ('-l', '--logging'):
            log_level = a.lower().strip()
            if not log.set_level(log_level):
                usage()

        elif o == '-g':
            log.set_level('debug')

        elif o == '-x':
            wait_for_printout = False


    if device_uri and printer_name:
        log.error("You may not specify both a printer (-p) and a device (-d).")
        usage()

    utils.log_title(__title__, __version__)
    
    if os.getuid() == 0:
        log.warn("hp-testpage should not be run as root.")

    if not device_uri and not printer_name:
        try:
            device_uri = device.getInteractiveDeviceURI(bus)
            if device_uri is None:
                sys.exit(0)
        except Error:
            log.error("Error occured during interactive mode. Exiting.")
            sys.exit(0)

    try:
        d = device.Device(device_uri, printer_name)
    except Error, e:
        log.error("Device error (%s)." % e.msg)
        sys.exit(1)

    if d.device_uri is None and printer_name:
        log.error("Printer '%s' not found." % printer_name)
        sys.exit(1)

    if d.device_uri is None and device_uri:
        log.error("Malformed/invalid device-uri: %s" % device_uri)
        sys.exit(1)

    user_cfg.last_used.device_uri = d.device_uri

    try:
        try:
            d.open()
        except Error:
            log.error("Unable to print to printer. Please check device and try again.")
            sys.exit(1)

        if not printer_name:
            if len(d.cups_printers) == 0:
                log.error("No printer queues found for device.")
                sys.exit(1)
        
            elif len(d.cups_printers) > 1:
                log.info("\nMultiple printers (queues) found in CUPS for device.")
                log.info(log.bold("\nPlease choose the printer (queue) to use for the test page:\n"))
        
                max_name = 24
                for q in d.cups_printers:
                    max_name = max(max_name, len(q))
        
                formatter = utils.TextFormatter(
                    (
                        {'width': 4, 'margin': 2},
                        {'width': max_name, 'margin': 2},
                    )
                )
        
                log.info(formatter.compose(("Num.", "CUPS printer (queue)")))
                log.info(formatter.compose(('-'*4, '-'*(max_name))))
        
                x = 0
                for q in d.cups_printers:
                    log.info(formatter.compose((str(x), d.cups_printers[x])))
                    x += 1
        
                ok, i = tui.enter_range("\nEnter number 0...%d for printer (q=quit) ?" % (x-1), 0, (x-1))
                if not ok: sys.exit(0)
                printer_name = d.cups_printers[i]
        
            else:
                printer_name = d.cups_printers[0]
            
        else:
            if printer_name not in d.cups_printers:
                log.error("Invalid printer name: %s" % printer_name)
                sys.exit(1)

        log.info("")
        
        # TODO: Fix the wait for printout stuff... can't get device ID
        # while hp: backend has device open in printing mode...
        wait_for_printout = False
        
        if d.isIdleAndNoError():
            d.close()
            log.info( "Printing test page to printer %s..." % printer_name)
            try:
                d.printTestPage(printer_name)
            except Error, e:
                if e.opt == ERROR_NO_CUPS_QUEUE_FOUND_FOR_DEVICE:
                    log.error("No CUPS queue found for device. Please install the printer in CUPS and try again.")
                else:
                    log.error("An error occured (code=%d)." % e.opt)
            else:
                if wait_for_printout:
                    log.info("Test page has been sent to printer. Waiting for printout to complete...")

                    time.sleep(5)
                    i = 0

                    while True:
                        time.sleep(5)

                        try:
                            d.queryDevice(quick=True)
                        except Error, e:
                            log.error("An error has occured.")

                        if d.error_state == ERROR_STATE_CLEAR:
                            break

                        elif d.error_state == ERROR_STATE_ERROR:
                            cleanup_spinner()
                            log.error("An error has occured (code=%d). Please check the printer and try again." % d.status_code)
                            break

                        elif d.error_state == ERROR_STATE_WARNING:
                            cleanup_spinner()
                            log.warning("There is a problem with the printer (code=%d). Please check the printer." % d.status_code)

                        else: # ERROR_STATE_BUSY
                            update_spinner()

                        i += 1

                        if i > 24:  # 2min
                            break

                    cleanup_spinner()

                else:
                    log.info("Test page has been sent to printer.")

        else:
            log.error("Device is busy or in an error state. Please check device and try again.")
            sys.exit(1)


    finally:
        d.close()

        log.info("")
        log.notice("If an error occured, or the test page failed to print, refer to the HPLIP website")
        log.notice("at: http://hplip.sourceforge.net for troubleshooting and support.")
        log.info("")

except KeyboardInterrupt:
    log.error("User exit")

log.info("")
log.info("Done.")
