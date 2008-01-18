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

__version__ = '0.2'
__title__ = 'Time/Date Utility'
__doc__ = "Set the time and date on an HP Officejet."

# Std Lib
import sys
import re
import getopt
import struct
import operator

# Local
from base.g import *
from base.codes import *
from base import device, status, utils, pml
from prnt import cups
from fax import fax

USAGE = [(__doc__, "", "name", True),
         ("Usage: timedate.py [PRINTER|DEVICE-URI] [OPTIONS]", "", "summary", True),
         utils.USAGE_ARGS,
         utils.USAGE_DEVICE,
         utils.USAGE_PRINTER,
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         utils.USAGE_BUS1, utils.USAGE_BUS2,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2,
         utils.USAGE_HELP,
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1, utils.USAGE_STD_NOTES2, 
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'timedate.py', __version__)
    sys.exit(0)


PML_ERROR_CODES = {
    pml.ERROR_OK_END_OF_SUPPORTED_OBJECTS: "OK: End of supported objects",
    pml.ERROR_OK_NEAREST_LEGAL_VALUE_SUBSITUTED: "OK: Nearest legal value substituted",
    pml.ERROR_UNKNOWN_REQUEST: "Unknown request",
    pml.ERROR_BUFFER_OVERFLOW: "Buffer overflow",
    pml.ERROR_COMMAND_EXECUTION: "Command execution",
    pml.ERROR_UNKNOWN_OID: "Unknown OID",
    pml.ERROR_OBJ_DOES_NOT_SUPPORT_SPECIFIED_ACTION: "Object does not support action",
    pml.ERROR_INVALID_OR_UNSUPPORTED_VALUE: "Invalid or unsupported value",
    pml.ERROR_PAST_END_OF_SUPPORTED_OBJS: "Past end of supported objects",
    pml.ERROR_ACTION_CANNOT_BE_PERFORMED_NOW: "Action cannot be performed now",
    pml.ERROR_SYNTAX: "Syntax",
}



try:
    opts, args = getopt.getopt(sys.argv[1:],
                                'p:d:hl:b:g',
                                ['printer=',
                                  'device=',
                                  'help',
                                  'help-rest',
                                  'help-man',
                                  'help-desc',
                                  'logging=',
                                  'bus=',
                                ]
                              )
except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

printer_name = None
device_uri = None
bus = device.DEFAULT_PROBE_BUS
log_level = logger.DEFAULT_LOG_LEVEL

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
            printer_name = cups.getDefault()
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

    elif o in ('-v', '--value'):
        print a


if device_uri and printer_name:
    log.error("You may not specify both a printer (-p) and a device (-d).")
    usage()

utils.log_title(__title__, __version__)

if not device_uri and not printer_name:
    try:
        device_uri = device.getInteractiveDeviceURI(bus, filter={'fax-type' : (operator.gt, 0)})
        if device_uri is None:
            sys.exit(1)
    except Error:
        log.error("Error occured during interactive mode. Exiting.")
        sys.exit(0)

#d = fax.FaxDevice(device_uri, printer_name)
d = fax.getFaxDevice(device_uri, printer_name)

if d.device_uri is None and printer_name:
    log.error("Printer '%s' not found." % printer_name)
    sys.exit(1)

if d.device_uri is None and device_uri:
    log.error("Malformed/invalid device-uri: %s" % device_uri)
    sys.exit(1)

user_cfg.last_used.device_uri = d.device_uri

try:
    d.open()
except Error:
    log.error("Unable to open device. Exiting. ")
    sys.exit(1)

try:
    d.setDateAndTime()
except Error:
    log.error("An error occured!")


log.info("")
d.close()
log.info('Done.')
sys.exit(0)
