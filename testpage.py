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

__version__ = '4.1'
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
from base import device, utils
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
    opts, args = getopt.getopt(sys.argv[1:], 'p:d:hl:b:gx',
                               ['printer=', 'device=', 'help', 'help-rest', 
                                'help-man', 'logging=', 'bus=', 'help-desc'])
except getopt.GetoptError:
    usage()

printer_name = None
device_uri = None
bus = 'cups'
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
        printer_name = a

    elif o in ('-d', '--device'):
        device_uri = a

    elif o in ('-b', '--bus'):
        bus = a.lower().strip()
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

if device_uri and printer_name:
    log.error("You may not specify both a printer (-p) and a device (-d).")
    usage()

utils.log_title(__title__, __version__)

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

    if len(d.cups_printers) == 0:
        log.error("No printer queues found for device.")
        sys.exit(1)

    elif len(d.cups_printers) > 1:
        log.info("\nMultiple printers (queues) found in CUPS for device.")
        log.info(utils.bold("\nPlease choose the printer (queue) to use for the test page:\n"))

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

        while 1:
            user_input = raw_input(utils.bold("\nEnter number 0...%d for printer (q=quit) ?" % (x-1)))

            if user_input == '':
                log.warn("Invalid input - enter a numeric value or 'q' to quit.")
                continue

            if user_input.strip()[0] in ('q', 'Q'):
                sys.exit(0)

            try:
                i = int(user_input)
            except ValueError:
                log.warn("Invalid input - enter a numeric value or 'q' to quit.")
                continue

            if i < 0 or i > (x-1):
                log.warn("Invalid input - enter a value between 0 and %d or 'q' to quit." % (x-1))
                continue

            break

        printer_name = d.cups_printers[i]

    else:
        printer_name = d.cups_printers[0]

    log.info("")

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

log.info("Done.")
