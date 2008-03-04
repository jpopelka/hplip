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

__version__ = '3.4'
__title__ = 'Device Information Utility'
__doc__ = "Query a printer for both static model information and dynamic status."

# Std Lib
import sys, getopt, time

# Local
from base.g import *
from base import device, status, utils
from prnt import cups

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-info [PRINTER|DEVICE-URI] [OPTIONS]", "", "summary", True),
         utils.USAGE_ARGS,
         utils.USAGE_DEVICE,
         utils.USAGE_PRINTER,
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         ("Device ID mode:", "-i or --id (prints device ID only and exits)", "option", False),
         utils.USAGE_BUS1, utils.USAGE_BUS2,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1, utils.USAGE_STD_NOTES2, 
         utils.USAGE_SEEALSO,
         ("hp-toolbox", "", "seealso", False),

         ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-info', __version__)
    sys.exit(0)


log.set_module('hp-info')


try:
    opts, args = getopt.getopt(sys.argv[1:], 'p:d:hl:b:ig',
        ['printer=', 'device=', 'help', 'help-rest', 'help-man', 
         'help-desc', 'logging=', 'id', 'bus='])

except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

printer_name = None
device_uri = None
log_level = logger.DEFAULT_LOG_LEVEL
bus = "cups,par,usb"
devid_mode = False

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
            log.info("Using CUPS default printer: %s" % printer_name)
            log.debug(printer_name)
        else:
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

    elif o in ('-i', '--id'):
        devid_mode = True


if device_uri and printer_name:
    log.error("You may not specify both a printer (-p) and a device (-d).")
    usage()

if not devid_mode:
    utils.log_title(__title__, __version__)

if not device_uri and not printer_name:
    try:
        device_uri = device.getInteractiveDeviceURI(bus)
        if device_uri is None:
            sys.exit(1)
    except Error:
        log.error("Error occured during interactive mode. Exiting.")
        sys.exit(1)
        

try:
    d = device.Device(device_uri, printer_name)
except Error:
    log.error("Error opening device. Exiting.")
    sys.exit(1)

if d.device_uri is None and printer_name:
    log.error("Printer '%s' not found." % printer_name)
    sys.exit(1)

if d.device_uri is None and device_uri:
    log.error("Malformed/invalid device-uri: %s" % device_uri)
    sys.exit(1)

if not devid_mode:
    log.info("")
    log.info(log.bold(d.device_uri))
    log.info("")

user_cfg.last_used.device_uri = d.device_uri

try:
    d.open()
    d.queryDevice()
except Error, e:
    log.error("Error opening device (%s). Exiting." % e.msg)
    sys.exit(1)

if not devid_mode:
    formatter = utils.TextFormatter(
                    (
                        {'width': 28, 'margin' : 2},
                        {'width': 58, 'margin' : 2},
                    )
                )

if devid_mode:
    try:
        print d.dq['deviceid']
    except KeyError:
        log.error("Device ID not available.")
else:
    dq_keys = d.dq.keys()
    dq_keys.sort()

    log.info(log.bold("Device Parameters (dynamic data):"))
    log.info(log.bold(formatter.compose(("Parameter", "Value(s)"))))
    log.info(formatter.compose(('-'*28, '-'*58)))

    for key in dq_keys:
        log.info(formatter.compose((key, str(d.dq[key]))))

    log.info(log.bold("\nModel Parameters (static data):"))
    log.info(log.bold(formatter.compose(("Parameter", "Value(s)"))))
    log.info(formatter.compose(('-'*28, '-'*58)))

    mq_keys = d.mq.keys()
    mq_keys.sort()

    for key in mq_keys:
        log.info(formatter.compose((key, str(d.mq[key]))))

    formatter = utils.TextFormatter(
                    (
                        {'width': 20, 'margin' : 2}, # date/time
                        {'width': 5, 'margin' : 2}, # code
                        {'width': 40, 'margin' : 2}, # desc
                        {'width': 8, 'margin' : 2}, # user
                        {'width': 8, 'margin' : 2}, # job id
                    )
                )


    log.info(log.bold("\nStatus History (most recent first):"))
    log.info(log.bold(formatter.compose(("Date/Time", "Code", "Status Description", "User", "Job ID"))))
    log.info(formatter.compose(('-'*20, '-'*5, '-'*40, '-'*8, '-'*8)))

    hq = d.queryHistory()

    for h in hq:
        if h[9]:
            j = str(h[9])
        else:
            j = ''
        log.info(formatter.compose((time.strftime("%x %H:%M:%S", h[:9]),  str(h[11]), h[12], h[10], j)))

    log.info("")

d.close()
sys.exit(0)
