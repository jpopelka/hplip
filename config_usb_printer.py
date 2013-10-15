#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2011-2014 Hewlett-Packard Development Company, L.P.
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
# Author: Amarnath Chitumalla
#

__version__ = '1.1'
__title__ = 'HP device setup using USB'
__mod__ = 'hp-config_usb_printer'
__doc__ = "Udev invokes this tool. Tool configures the USB connected devices (if not configured), detects the plugin, queues issues and notifies to logged-in user."

# Std Lib
import sys
import os
import getopt
import commands
import re
import time

# Local
from base.g import *
from base import device,utils, tui, models,module, services, os_utils
from prnt import cups
from installer import pluginhandler

LPSTAT_PAT = re.compile(r"""(\S*): (.*)""", re.IGNORECASE)
USB_PATTERN = re.compile(r'''serial=(.*)''',re.IGNORECASE)
BACK_END_PATTERN = re.compile(r'''(.*):(.*)''',re.IGNORECASE)
USB_SERIAL_INTERFACE = re.compile(r'''(.*)&interface.*''',re.IGNORECASE)
DBUS_SERVICE='com.hplip.StatusService'
DBUS_AVIALABLE=False

##### METHODS #####

# remove queues using cups API
def remove_queues(arg_queues_list):
    for queue_name in arg_queues_list:
        cups.delPrinter(queue_name)


#Function:  get_queues
#       Returns the HP, Non HP configured queuese list for a given device serial No and backend
def get_queues(arg_serial_no, arg_back_end):
    status, output = utils.run('lpstat -v')
    hp_conf_queues = []
    non_hp_conf_queues = []
    for p in output.splitlines():
        try:
            match = LPSTAT_PAT.search(p)
            printer_name = match.group(1)
            device_uri = match.group(2)
            if device_uri.startswith("cups-pdf:/") or not USB_PATTERN.search(device_uri):
                continue

            back_end = BACK_END_PATTERN.search(device_uri).group(1)
            serial = USB_PATTERN.search(device_uri).group(1)
            if USB_SERIAL_INTERFACE.search(serial):
                serial = USB_SERIAL_INTERFACE.search(serial).group(1)

            log.debug("arg_serial_no[%s] serial[%s] arg_back_end[%s] back_end[%s]"%(arg_serial_no, serial, arg_back_end, back_end))
            if arg_serial_no == serial and (arg_back_end == back_end or back_end == 'usb'):
                if printer_name.find('_') == -1 and printer_name.find('-') != -1:
                    non_hp_conf_queues.append(printer_name)
                else:
                    hp_conf_queues.append(printer_name)

        except AttributeError:
            pass

    log.debug( "serial No [%s] HP Configured Queues [%s] Non HP Configured Queues [%s]"%(arg_serial_no, hp_conf_queues,non_hp_conf_queues))
    return hp_conf_queues, non_hp_conf_queues


def check_cups_process():
    cups_running_sts = False
    sts, output = utils.run('lpstat -r')
    if sts == 0 and ('is running' in output):
        cups_running_sts = True

    return cups_running_sts

# Send dbus event to hpssd on dbus system bus
def send_message(device_uri, printer_name, event_code, username, job_id, title, pipe_name=''):
    if DBUS_AVIALABLE == False:
        return

    log.debug("send_message() entered")
    args = [device_uri, printer_name, event_code, username, job_id, title, pipe_name]
    msg = lowlevel.SignalMessage('/', DBUS_SERVICE, 'Event')
    msg.append(signature='ssisiss', *args)

    SystemBus().send_message(msg)
    log.debug("send_message() returning")


# Usage function
def usage(typ='text'):
    utils.format_text(USAGE, typ, __title__, __mod__, __version__)
    sys.exit(0)

# Systray service. If hp-systray is not running, starts.
def start_systray():
    if DBUS_AVIALABLE == False:
        return False

    Systray_Is_Running=False
    status,output = utils.Is_Process_Running('hp-systray')
    if status is False:
        if os.getuid() == 0:
            log.error(" hp-systray must be running.\n Run \'hp-systray &\' in a terminal. ")
        else:
            log.info("Starting hp-systray service")
            services.run_systray()
            status,output = utils.Is_Process_Running('hp-systray')

    if status == True:
        Systray_Is_Running=True
        log.debug("hp-systray service is running\n")

    return Systray_Is_Running



USAGE = [ (__doc__, "", "name", True),
          ("Usage: %s [OPTIONS] [SERIAL NO.|USB bus:device]" % __mod__, "", "summary", True),
          utils.USAGE_OPTIONS,
          utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
          utils.USAGE_HELP,
          ("[SERIAL NO.|USB bus:device]", "", "heading", False),
          ("USB bus:device :", """"xxx:yyy" where 'xxx' is the USB bus and 'yyy' is the USB device. (Note: The ':' and all leading zeros must be present.)""", 'option', False),
          ("", "Use the 'lsusb' command to obtain this information.", "option", False),
          ("SERIAL NO.:", '"serial no." (future use)', "option", True),
          utils.USAGE_EXAMPLES,
          ("USB, IDs specified:", "$%s 001:002"%(__mod__), "example", False),
          ("USB, using serial number:", "$%s US12345678A"%(__mod__), "example", False),
          utils.USAGE_SPACE,
          utils.USAGE_NOTES,
          ("1. Using 'lsusb' to obtain USB IDs: (example)", "", 'note', False),
          ("   $ lsusb", "", 'note', False),
          ("         Bus 003 Device 011: ID 03f0:c202 Hewlett-Packard", "", 'note', False),
          ("   $ %s 003:011"%(__mod__), "", 'note', False),
          ("   (Note: You may have to run 'lsusb' from /sbin or another location. Use '$ locate lsusb' to determine this.)", "", 'note', True),
        ]


mod = module.Module(__mod__, __title__, __version__, __doc__, USAGE, (INTERACTIVE_MODE,), None, run_as_root_ok=True, quiet=True)
opts, device_uri, printer_name, mode, ui_toolkit, loc = mod.parseStdOpts('gh',['time-out=', 'timeout='],handle_device_printer=False)

LOG_FILE = "%s/hplip_config_usb_printer.log"%prop.user_dir
if os.path.exists(LOG_FILE):
    try:
        os.remove(LOG_FILE)
    except OSError:
        pass

log.set_logfile(LOG_FILE)
log.set_where(log.LOG_TO_CONSOLE_AND_FILE)

try:
    import dbus
    from dbus import SystemBus, lowlevel
except ImportError:
    log.warn("Failed to Import DBUS ")
    DBUS_AVIALABLE = False
else:
    DBUS_AVIALABLE = True

try:
    param = mod.args[0]
except IndexError:
    param = ''

log.debug("param=%s" % param)
if len(param) < 1:
    usage()
    sys.exit()

try:
    # ******************************* MAKEURI
    if param:
        device_uri, sane_uri, fax_uri = device.makeURI(param)
    if not device_uri:
        log.error("This is not a valid device")
        sys.exit(0)

    # ******************************* QUERY MODEL AND CHECKING SUPPORT
    log.debug("\nSetting up device: %s\n" % device_uri)
    back_end, is_hp, bus, model, serial, dev_file, host, zc, port = device.parseDeviceURI(device_uri)

    mq = device.queryModelByURI(device_uri)
    if not mq or mq.get('support-type', SUPPORT_TYPE_NONE) == SUPPORT_TYPE_NONE:
        log.error("Unsupported printer model.")
        sys.exit(1)

    printer_name = ""
    username = prop.username
    job_id = 0
    # ******************************* STARTING CUPS SERVICE, IF NOT RUNNING.
    while check_cups_process() is False:
        log.debug("CUPS is not running.. waiting for 30 sec")
        time.sleep(30)

    # ******************************* RUNNING HP-SETUP, IF QUEUE IS NOT ADDED
    time.sleep(1)
    norm_model = models.normalizeModelName(model).lower()
    if not mq.get('fax-type', FAX_TYPE_NONE) in (FAX_TYPE_NONE, FAX_TYPE_NOT_SUPPORTED):
        fax_queues_list, fax_config_list_non_hp_conf = get_queues(serial, 'hpfax')
        remove_queues(fax_config_list_non_hp_conf)

    print_queues_list, print_queues_list_non_hp_conf = get_queues(serial, back_end)
    remove_queues(print_queues_list_non_hp_conf)     # Removing Queues which are not configured by HPLIP
    if len(print_queues_list) ==0:
        if "SMART_INSTALL_ENABLED" not in device_uri:
            cmd ="hp-setup -i -x -a -q %s"%param
            log.debug("%s"%cmd)
            os_utils.execute(cmd)

        if start_systray():
            if "SMART_INSTALL_ENABLED" in device_uri:
                send_message( device_uri, printer_name, EVENT_DIAGNOSE_PRINTQUEUE, username, job_id,'')
            else:
                send_message( device_uri, printer_name, EVENT_ADD_PRINTQUEUE, username, job_id,'')

    # ******************************* TRIGGERING PLUGIN POP-UP FOR PLUGING SUPPORTED PRINTER'S
    plugin = mq.get('plugin', PLUGIN_NONE)
    if plugin != PLUGIN_NONE:
       pluginObj = pluginhandler.PluginHandle()
       plugin_sts = pluginObj.getStatus()
       if plugin_sts == pluginhandler.PLUGIN_INSTALLED:
          log.info("Device Plugin is already installed")
       elif plugin_sts == pluginhandler.PLUGIN_NOT_INSTALLED :
          log.info("HP Device Plug-in is not found")
       else:
          log.info("HP Device Plug-in version mismatch or some files are corrupted")
    
       if plugin_sts != pluginhandler.PLUGIN_INSTALLED:
           if start_systray():
               send_message( device_uri,  printer_name, EVENT_AUTO_CONFIGURE, username, job_id, "AutoConfig")

       # ******************************* RUNNING FIRMWARE DOWNLOAD TO DEVICE FOR SUPPORTED PRINTER'S
       fw_download_req = mq.get('fw-download', False)
       if fw_download_req:
           fw_cmd = "hp-firmware -y3 -s %s"%param
           log.info(fw_cmd)
           fw_sts, fw_out = utils.run(fw_cmd)
           if fw_sts == 0:
               log.debug("Firmware downloaded to %s "%device_uri)
           else:
               log.warn("Failed to download firmware to %s device"%device_uri)     

    # ******************************* REMOVING CUPS CREATED QUEUE, If any
    i =0
    while i <12:
        time.sleep(2)
        fax_queues_list, fax_queues_list_non_hp_conf = get_queues(serial, 'hpfax')
        remove_queues(fax_queues_list_non_hp_conf)     # Removing Queues which are not configured by HPLIP

        print_queues_list, print_queues_list_non_hp_conf = get_queues(serial, 'hp')
        remove_queues(print_queues_list_non_hp_conf)     # Removing Queues which are not configured by HPLIP

        if i == 0:
            send_message( device_uri, printer_name, EVENT_DIAGNOSE_PRINTQUEUE, username, job_id,"")
        i += 1

except KeyboardInterrupt:
    log.error("User exit")

log.debug("Done.")
