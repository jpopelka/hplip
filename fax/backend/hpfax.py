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

__version__ = '2.7'
__title__ = 'CUPS Fax Backend (hpfax:)'
__doc__ = "CUPS backend for PC send fax. Generally this backend is run by CUPS, not directly by a user. To send a fax as a user, run hp-sendfax."

import sys
import getopt
import ConfigParser
import os.path, os
import socket
import syslog
import time
import operator

CUPS_BACKEND_OK = 0 # Job completed successfully
CUPS_BACKEND_FAILED = 1 # Job failed, use error-policy
CUPS_BACKEND_AUTH_REQUIRED = 2 # Job failed, authentication required
CUPS_BACKEND_HOLD = 3 # Job failed, hold job
CUPS_BACKEND_STOP = 4 #  Job failed, stop queue
CUPS_BACKEND_CANCEL = 5 # Job failed, cancel job

pid = os.getpid()
config_file = '/etc/hp/hplip.conf'
home_dir = ''

if os.path.exists(config_file):
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    try:
        home_dir = config.get('dirs', 'home')
    except:
        syslog.syslog("hpfax[%d]: error: Error setting home directory: home= under [dirs] not found." % pid)
        sys.exit(1)
else:
    syslog.syslog("hpfax[%d]: error: Error setting home directory: /etc/hp/hplip.conf not found." % pid)
    sys.exit(1)

if not home_dir or not os.path.exists(home_dir):
    syslog.syslog("hpfax[%d]: error: Error setting home directory: Home directory %s not found." % (pid, home_dir))
    sys.exit(1)

sys.path.insert( 0, home_dir )

try:
    from base.g import *
    from base.codes import *
    from base import device, utils, msg, service
    from base.service import sendEvent
    from prnt import cups
except ImportError:
    syslog.syslog("hpfax[%d]: error: Error importing HPLIP modules." % pid)
    sys.exit(1)

log.set_module("hpfax")

USAGE = [(__doc__, "", "para", True),
         ("Usage: hpfax [OPTIONS] [job_id] [username] [title] [copies] [options]", "", "summary", True),
         utils.USAGE_OPTIONS,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, title=__title__, crumb='hpfax:')
    sys.exit(CUPS_BACKEND_OK)        


try:
    opts, args = getopt.getopt(sys.argv[1:], 'l:hg', ['level=', 'help', 'help-rest', 'help-man'])

except getopt.GetoptError:
    usage()

for o, a in opts:

    if o in ('-l', '--logging'):
        log_level = a.lower().strip()
        log.set_level(log_level)

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')


if len( args ) == 0:
    cups11 = utils.to_bool(sys_cfg.configure.cups11, False)
    
    try:
        probed_devices = device.probeDevices('usb,par', filter={'fax-type': (operator.gt, 0)})
    except Error:
        log.stderr("hpfax[%d]: error: Unable to contact HPLIP I/O (hpssd)." % pid)
        sys.exit(CUPS_BACKEND_FAILED)

    good_devices = 0
    for uri in probed_devices:
        try:
            back_end, is_hp, bus, model, serial, dev_file, host, port = \
                device.parseDeviceURI(uri)
        except Error:
            continue

        print 'direct %s "HP Fax" "%s HP Fax HPLIP" "MFG:HP;MDL:Fax;DES:HP Fax;"' % \
            (uri.replace("hp:", "hpfax:"), model.replace("_", " "))
            
        good_devices += 1

    if good_devices == 0:
        if cups11:
            print 'direct hpfax:/no_device_found "HP Fax" "no_device_found" ""'
        else:
            print 'direct hpfax "Unknown" "HP Fax (HPLIP)" ""' 

    sys.exit(CUPS_BACKEND_OK)

else:
    # CUPS provided environment
    try:
        device_uri = os.environ['DEVICE_URI']
        printer_name = os.environ['PRINTER']
    except KeyError:
        log.stderr("hpfax[%d]: error: Improper environment: Must be run by CUPS." % pid)
        sys.exit(CUPS_BACKEND_FAILED)

    log.debug(args)

    try:
        job_id, username, title, copies, options = args[0:5]
    except IndexError:
        log.stderr("hpfax[%d]: error: Invalid command line: Invalid arguments." % pid)
        sys.exit(CUPS_BACKEND_FAILED)

    try:
        input_fd = file(args[5], 'r')
    except IndexError:
        input_fd = 0

    try:
        sock = service.startup()
    except Error:
        log.stderr("hpfax[%d]: error: Unable to start hpssd." % pid)
        sys.exit(CUPS_BACKEND_FAILED)

    fax_data = os.read(input_fd, prop.max_message_len)

    if not len(fax_data):
        log.stderr("hpfax[%d]: error: No data!" % pid)

        sendEvent(sock, EVENT_ERROR_NO_DATA_AVAILABLE, 'error',
                  job_id, username, device_uri)

        sock.close()
        sys.exit(CUPS_BACKEND_FAILED)


    sendEvent(sock, EVENT_START_FAX_PRINT_JOB, 'event',
              job_id, username, device_uri)

    while True:
        try:
            fields, data, result_code = \
                msg.xmitMessage(sock, "HPFaxBegin", 
                                     None,
                                     {"username": username,
                                      "job-id": job_id,
                                      "device-uri": device_uri,
                                      "printer": printer_name,
                                      "title": title,
                                     })

        except Error:
            log.stderr("hpfax[%d]: error: Unable to send event to HPLIP I/O (hpssd)." % pid)
            sys.exit(CUPS_BACKEND_FAILED) 

        if result_code == ERROR_GUI_NOT_AVAILABLE:
            # New behavior in 1.6.6a (10sec retry)
            log.stderr("hpfax[%d]: error: You must run hp-sendfax first. Run hp-sendfax now to continue. Fax will resume within 10 seconds." % pid)

            sendEvent(sock, EVENT_ERROR_FAX_MUST_RUN_SENDFAX_FIRST, 'event',
                      job_id, username, device_uri)

        else: # ERROR_SUCCESS
            break

        time.sleep(10)


    bytes_read = 0
    while True:
        if not len(fax_data):
            fields, data, result_code = \
                msg.xmitMessage(sock, "HPFaxEnd", 
                                     None,
                                     {"username": username,
                                      "job-id": job_id,
                                      "printer": printer_name,
                                      "title": title,
                                      "options": options,
                                      "device-uri": device_uri,
                                      "job-size": bytes_read,
                                     })

            break


        bytes_read += len(fax_data) 

        fields, data, result_code = \
            msg.xmitMessage(sock, "HPFaxData", 
                                 fax_data,
                                 {"username": username,
                                  "job-id": job_id,
                                 })

        fax_data = os.read(input_fd, prop.max_message_len)

    os.close(input_fd)
    sock.close()
    sys.exit(CUPS_BACKEND_OK)


