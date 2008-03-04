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

__version__ = '1.0'
__title__ = 'Firmware Download Utility'
__doc__ = "Download firmware to a device."

# Std Lib
import sys
import getopt
import gzip
import operator
import time

# Local
from base.g import *
from base import device, status, utils
from prnt import cups

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-firmware [PRINTER|DEVICE-URI] [OPTIONS]", "", "summary", True),
         utils.USAGE_ARGS,
         utils.USAGE_DEVICE,
         utils.USAGE_PRINTER,
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         ("Use USB IDs to specify printer:", "-s bbb:ddd, where bbb is the USB bus ID and ddd is the USB device ID. The ':' and all leading zeroes must be present.", "option", False),
         ("Seconds to delay before download:", "-y<secs> or --delay=<secs> (float value, e.g. 0.5)", "option", False),
         utils.USAGE_BUS1, utils.USAGE_BUS2,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1, utils.USAGE_STD_NOTES2, 
         utils.USAGE_SPACE,
         utils.USAGE_SEEALSO,
         ("hp-toolbox", "", "seealso", False),

         ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-info', __version__)
    sys.exit(0)


log.set_module('hp-firmware')


try:
    opts, args = getopt.getopt(sys.argv[1:], 'p:d:hl:b:gs:y:',
        ['printer=', 'device=', 'help', 'help-rest', 'help-man', 
         'help-desc', 'logging=', 'bus=', 'delay='])

except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

printer_name = None
device_uri = None
log_level = logger.DEFAULT_LOG_LEVEL
bus = "cups,par,usb"
usb_bus_node = None
usb_bus_id = None
usb_device_id = None
silent = False
delay = 0.0

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
        
    elif o == '-s':
        silent = True
        try:
            usb_bus_id, usb_device_id = a.split(":", 1)
            log.debug("USB bus ID: %s" % usb_bus_id)
            log.debug("USB device ID: %s" % usb_device_id)
        except ValueError:
            log.error("Invalid USB IDs: %s" % a)
            sys.exit(1)
            
        if len(usb_bus_id) != 3 or len(usb_device_id) != 3:
            log.error("Invalid USB IDs: %s" % a)
            sys.exit(1)
            
        usb_bus_node = a
        
    elif o in ('-y', '--delay'):
        try:
            delay = float(a)
        except ValueError:
            log.error("Invalid delay value. Must be numeric (float) value. Setting delay to 0.0")
            delay = 0.0


if device_uri and printer_name:
    log.error("You may not specify both a printer (-p) and a device (-d).")
    usage()

utils.log_title(__title__, __version__)

if silent:
    # called by .rules file with -s bbb.ddd
    printer_name = None
    
    if usb_bus_node is not None:
        log.debug("USB bus node: %s" % usb_bus_node)
        device_uri, sane_uri, fax_uri = device.makeURI(usb_bus_node, 1)
        
        if not device_uri:
            log.error("Invalid USB IDs: %s" % usb_bus_node)
            sys.exit(1)
    
else:
    if not device_uri and not printer_name:
        try:
            device_uri = device.getInteractiveDeviceURI(bus, 
                filter={'fw-download' : (operator.gt, 0)})
                
            if device_uri is None:
                sys.exit(1)
        except Error:
            log.error("Error occured during interactive mode. Exiting.")
            sys.exit(1)
    
if delay:
    time.sleep(delay)

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

user_cfg.last_used.device_uri = d.device_uri
    
   
try:
    d.open()
    d.queryModel()
except Error, e:
    log.error("Error opening device (%s). Exiting." % e.msg)
    sys.exit(1)

fw_download = d.mq.get('fw-download', 0)

if fw_download:
    if d.downloadFirmware(usb_bus_id, usb_device_id):
        if not silent:
            log.info("Done.")
else:
    log.error("Device %s does not support or require firmware download." % device_uri)


d.close()
sys.exit(0)
