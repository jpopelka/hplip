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
__title__ = 'Printer Discovery Utility'
__doc__ = "Discover USB, parallel, and network printers."


# Std Lib
import sys
import getopt
import operator
import os

# Local
from base.g import *
from base import device, utils, tui


USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-probe [OPTIONS]", "", "summary", True),
         utils.USAGE_OPTIONS,
         ("Bus to probe:", "-b<bus> or --bus=<bus>", "option", False),
         ("", "<bus>: cups, usb\*, net, bt, fw, par (\*default) (Note: bt and fw not supported in this release.)", "option", False),
         ("Set Time to Live (TTL):", "-t<ttl> or --ttl=<ttl> (Default is 4).", "option", False),
         ("Set timeout:", "-o<timeout in secs.> or --timeout=<timeout is secs.>", "option", False),
         ("Filter by functionality:", "-e<filter list> or --filter=<filter list>", "option", False),
         ("", "<filter list>: comma separated list of one or more of: scan, pcard, fax, copy, or none\*. (\*none is the default)", "option", False),
         ("Search:", "-s<search re> or --search=<search re>", "option", False),
         ("", "<search re> must be a valid regular expression (not case sensitive)", "option", False),
         ("Network discovery method:", "-m<method> or --method=<method>: <method> is 'slp'* or 'mdns'.", "option", False),
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_SPACE,
         utils.USAGE_EXAMPLES,
         ("Find all devices on the network:", "hp-probe -bnet", "example", False),
         ("Find all devices on USB that support scanning:", "hp-probe -busb -escan", "example", False),
         ("Find all networked devices that contain the name 'lnx' and that support photo cards or scanning:", "hp-probe -bnet -slnx -escan,pcard", "example", False),
         ("Find all devices that have queues installed in CUPS:", "hp-probe -bcups", "example", False),
         ("Find all devices on the USB bus:", "hp-probe", "example", False),
         ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-probe', __version__)
    sys.exit(0)


log.set_module('hp-probe')

try:

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                    'hl:b:t:o:e:s:gm:',
                                    ['help', 'help-rest', 'help-man',
                                      'help-desc',
                                      'logging=',
                                      'bus=',
                                      'event=',
                                      'ttl=',
                                      'timeout=',
                                      'filter=',
                                      'search=',
                                      'method=',
                                    ]
                                  )
    except getopt.GetoptError, e:
        log.error(e.msg)
        usage()

    log_level = logger.DEFAULT_LOG_LEVEL
    bus = None
    align_debug = False
    timeout=10
    ttl=4
    filter = []
    search = ''
    method = 'slp'

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

        elif o == '-g':
            log.set_level('debug')

        elif o in ('-b', '--bus'):
            try:
                bus = [x.lower().strip() for x in a.split(',')]
            except TypeError:
                bus = ['usb']

            if not device.validateBusList(bus):
                usage()

        elif o in ('-l', '--logging'):
            log_level = a.lower().strip()
            if not log.set_level(log_level):
                usage()

        elif o in ('-m', '--method'):
            method = a.lower().strip()

            if method not in ('slp', 'mdns', 'bonjour'):
                log.error("Invalid network search protocol: %s (must be 'slp' or 'mdns')" % method)
                method = 'slp'

            else:
                bus = ['net']

        elif o in ('-t', '--ttl'):
            try:
                ttl = int(a)
            except ValueError:
                ttl = 4
                log.note("TTL value error. TTL set to default of 4 hops.")

        elif o in ('-o', '--timeout'):
            try:
                timeout = int(a)
                if timeout > 45:
                    log.note("Timeout > 45secs. Setting to 45secs.")
                    timeout = 45
            except ValueError:
                timeout = 5
                log.note("Timeout value error. Timeout set to default of 5secs.")

            if timeout < 0:
                log.error("You must specify a positive timeout in seconds.")
                usage()

        elif o in ('-e', '--filter'):
            filter = [x.strip().lower() for x in a.split(',')]
            if not device.validateFilterList(filter):
                usage()

        elif o in ('-s', '--search'):
            search = a.lower().strip()

    utils.log_title(__title__, __version__)
    
    if os.getuid() == 0:
        log.warn("hp-probe should not be run as root.")

    if bus is None:
        x = 1
        ios = {0: ('usb', "Universal Serial Bus (USB)") }
        if sys_cfg.configure['network-build']: 
            ios[x] = ('net', "Network/Ethernet/Wireless (direct connection or JetDirect)")
            x += 1
        if sys_cfg.configure['pp-build']: 
            ios[x] = ('par', "Parallel Port (LPT:)")
            x += 1
        
        if len(ios) > 1:
            tui.header("CHOOSE CONNECTION TYPE")
            f = tui.Formatter()
            f.max_widths = (10, 10, 40)
            f.header = ("Num.", "Connection Type", "Connection Type Description")
            
            for x, data in ios.items():
                if not x:
                    f.add((str(x) + "*", data[0], data[1]))
                else:
                    f.add((str(x), data[0], data[1]))
                
            f.output()
        
            ok, val = tui.enter_range("\nEnter number 0...%d for connection type (q=quit, enter=usb*) ? " % x, 
                0, x, 0)

            if not ok: sys.exit(0)
            
            bus = [ios[val][0]]
        else:
            bus = [ios[0][0]]
            
        log.info("")
        
    tui.header("DEVICE DISCOVERY")

    for b in bus:
        if b == 'net':
            log.info(log.bold("Probing network for printers. Please wait, this will take approx. %d seconds...\n" % timeout))
            
        FILTER_MAP = {'print' : None,
                      'none' : None,
                      'scan': 'scan-type', 
                      'copy': 'copy-type', 
                      'pcard': 'pcard-type',
                      'fax': 'fax-type',
                      }
        
        filter_dict = {}
        for f in filter:
            if f in FILTER_MAP:
                filter_dict[FILTER_MAP[f]] = (operator.gt, 0)
            else:
                filter_dict[f] = (operator.gt, 0)
                
        log.debug(filter_dict)

        devices = device.probeDevices([b], timeout, ttl, filter_dict, search, method)
        cleanup_spinner()

        max_c1, max_c2, max_c3, max_c4 = 0, 0, 0, 0

        if devices:
            for d in devices:
                max_c1 = max(len(d), max_c1)
                max_c3 = max(len(devices[d][0]), max_c3)
                max_c4 = max(len(devices[d][2]), max_c4)

            if b == 'net':
                formatter = utils.TextFormatter(
                            (
                                {'width': max_c1, 'margin' : 2},
                                {'width': max_c3, 'margin' : 2},
                                {'width': max_c4, 'margin' : 2},
                            )
                        )

                log.info(formatter.compose(("Device URI", "Model", "Name")))
                log.info(formatter.compose(('-'*max_c1, '-'*max_c3, '-'*max_c4)))
                for d in devices:
                    log.info(formatter.compose((d, devices[d][0], devices[d][2])))

            elif b in ('usb', 'par', 'cups'):
                formatter = utils.TextFormatter(
                            (
                                {'width': max_c1, 'margin' : 2},
                                {'width': max_c3, 'margin' : 2},
                            )
                        )

                log.info(formatter.compose(("Device URI", "Model")))
                log.info(formatter.compose(('-'*max_c1, '-'*max_c3)))
                for d in devices:
                    log.info(formatter.compose((d, devices[d][0])))

            else:
                log.error("Invalid bus: %s" % b)

            log.info("\nFound %d printer(s) on the '%s' bus.\n" % (len(devices), b))

        else:
            log.warn("No devices found on the '%s' bus. If this isn't the result you are expecting," % b)

            if b == 'net':
                log.warn("check your network connections and make sure your internet")
                log.warn("firewall software is disabled.")
            else:
                log.warn("check to make sure your devices are properly connected and powered on.")

except KeyboardInterrupt:
    log.error("User exit")

log.info("")
log.info("Done.")
