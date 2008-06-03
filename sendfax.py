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
# Thanks to Henrique M. Holschuh <hmh@debian.org> for various security patches
#

__version__ = '8.1'
__title__ = 'PC Sendfax Utility'
__doc__ = "Allows for sending faxes from the PC using HPLIP supported multifunction printers." 

# Std Lib
import sys
import os
import os.path
import getopt
import signal
import time

# Local
from base.g import *
import base.utils as utils
from base import device, tui

log.set_module('hp-sendfax')

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-sendfax [PRINTER|DEVICE-URI] [OPTIONS] [MODE] [FILES]", "", "summary", True),
         utils.USAGE_ARGS,
         ("To specify a fax-URI:", "-d<device-uri> or --device=<device-uri>", "option", False),
         ("To specify a CUPS fax:", "--fax=<fax>", "option", False),
         utils.USAGE_SPACE,
         ("[MODE]", "", "header", False),
         ("Enter graphical UI mode:", "-u or --gui (Default)", "option", False),
         ("Run in non-interactive mode (batch mode):", "-n or --non-interactive", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         ("Specify the fax number(s):", "-f<number(s)> or --faxnum=<number(s)> (-n only)", "option", False),
         ("Specify the recipient(s):", "-r<recipient(s)> or --recipient=<recipient(s)> (-n only)", "option", False), 
         ("Specify the groups(s):", "-g<group(s)> or --group=<group(s)> (-n only)", "option", False), 
         utils.USAGE_BUS1, utils.USAGE_BUS2,         
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2,
         ("Run in debug mode:", "--gg (same as option: -ldebug)", "option", False),
         utils.USAGE_LANGUAGE,
         utils.USAGE_HELP,
         ("[FILES]", "", "header", False),
         ("A list of files to add to the fax job.", "(Required for -n, optional for -u)", "option", True),
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1,
         ("2. If --fax=\* is specified, the default CUPS fax (printer queue) will be used.", "", "note", False),
         ("3. Coversheets are not supported in non-interactive mode (-n)", "", "note", False),
         ("4. Fax numbers and/or recipients should be listed in comma separated lists (-n only).", "", "note", False),
         utils.USAGE_SPACE,
         utils.USAGE_SEEALSO,
         ("hp-fab", "", "seealso", False),
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-sendfax', __version__)
    sys.exit(0)



prop.prog = sys.argv[0]

device_uri = None
printer_name = None
username = prop.username
mode = GUI_MODE
mode_specified = False
faxnum_list = []
recipient_list = []
group_list = []
bus = device.DEFAULT_PROBE_BUS
prettyprint = False
loc = None

try:
    opts, args = getopt.getopt(sys.argv[1:],'l:hz:d:b:g:unf:r:tq:', 
        ['device=', 'fax=', 'level=', 
         'help', 'help-rest', 'lang=',
         'help-man', 'logfile=', 'bus=',
         'gui', 'non-interactive', 'logging=',
         'faxnum=', 'recipients=',
         'gg', 'group=', 'help-desc'])

except getopt.GetoptError, e:
    log.error(e.msg)
    sys.exit(1)


if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    if o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '--gg':
        log.set_level('debug')

    elif o in ('-z', '--logfile'):
        log.set_logfile(a)
        log.set_where(log.LOG_TO_CONSOLE_AND_FILE)

    elif o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-d', '--device'):
        device_uri = a

    #elif o in ('-p', '--printer'):
    elif o == '--fax':
        printer_name = a

    elif o in ('-b', '--bus'):
        bus = [x.lower().strip() for x in a.split(',')]
        if not device.validateBusList(bus):
            usage()

    elif o in ('-n', '--non-interactive'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-n or -u).")
            sys.exit(1)

        mode = NON_INTERACTIVE_MODE
        mode_specified = True

    elif o in ('-u', '--gui'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-n or -u).")
            sys.exit(1)

        mode = GUI_MODE
        mode_specified = True

    elif o in ('-f', '--faxnum'):
        faxnum_list.extend(a.split(','))

    elif o in ('-r', '--recipient'):
        recipient_list.extend(a.split(','))

    elif o in ('-g', '--group'):
        group_list.extend(a.split(','))

    elif o in ('-q', '--lang'):
        if a.strip() == '?':
            tui.show_languages()
            sys.exit(0)

        loc = utils.validate_language(a.lower())



utils.log_title(__title__, __version__)

# Security: Do *not* create files that other users can muck around with
os.umask (0037)

if not prop.fax_build:
    log.error("Fax is disabled (turned off during build). Exiting")
    sys.exit(1)

if mode == GUI_MODE:
    if not utils.canEnterGUIMode():
        mode = NON_INTERACTIVE_MODE

if mode == GUI_MODE:
    app = None
    sendfax = None

    from qt import *

    # UI Forms
    from ui.faxsendjobform import FaxSendJobForm

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
            
            
    if os.geteuid() == 0:
        log.error("You must not be root to run this utility.")

        QMessageBox.critical(None, 
                             "HP Device Manager - Send Fax",
                             "You must not be root to run hp-sendfax.",
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)

        sys.exit(1)
            


    sendfax = FaxSendJobForm(device_uri,  
                             printer_name, 
                             args) 

    app.setMainWidget(sendfax)

    pid = os.getpid()
    log.debug('pid=%d' % pid)

    sendfax.show()

    #signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    try:
        log.debug("Starting GUI loop...")
        app.exec_loop()
    except KeyboardInterrupt:
        pass




else: # NON_INTERACTIVE_MODE
    if os.getuid() == 0:
        log.error("hp-sendfax cannot be run as root.")
        sys.exit(1)
    
    try:
        import struct, Queue

        from prnt import cups
        from base import magic

        try:
            from fax import fax
        except ImportError:
            # This can fail on Python < 2.3 due to the datetime module
            log.error("Fax address book disabled - Python 2.3+ required.")
            sys.exit(1)    

        db =  fax.FaxAddressBook() # FAB instance

        try:
            import dbus
        except ImportError:
            log.error("PC send fax requires dbus and python-dbus")
            sys.exit(1)

        dbus_avail, service = device.init_dbus()

        phone_num_list = []

        log.debug("Faxnum list = %s" % faxnum_list)
        faxnum_list = utils.uniqueList(faxnum_list)
        log.debug("Unique list=%s" % faxnum_list)

        for f in faxnum_list:
            for c in f:
                if c not in '0123456789-(+) *#':
                    log.error("Invalid character in fax number '%s'. Only the characters '0123456789-(+) *#' are valid." % f)
                    sys.exit(1)

        log.debug("Group list = %s" % group_list)
        group_list = utils.uniqueList(group_list)
        log.debug("Unique list=%s" % group_list)

        for g in group_list:
            entries = db.group_members(g)
            if not entries:
                log.warn("Unknown group name: %s" % g)
            else:
                for e in entries:
                    recipient_list.append(e)

        log.debug("Recipient list = %s" % recipient_list)
        recipient_list = utils.uniqueList(recipient_list)
        log.debug("Unique list=%s" % recipient_list)

        for r in recipient_list:
            if db.get(r) is None:
                log.error("Unknown fax recipient '%s' in the recipient list." % r)
                all_entries = db.get_all_records()
                log.info(log.bold("\nKnown recipients (entries):"))

                for a in all_entries:
                    aa = db.get(a)
                    print "%s (fax number: %s)" % (a, aa['fax'])

                print
                sys.exit(1)

        for p in recipient_list:
            a = db.get(p)
            phone_num_list.append(a)
            log.debug("Name=%s Number=%s" % (a['name'], a['fax']))

        for p in faxnum_list:
            phone_num_list.append({'fax': p, 'name': u'Unknown'})
            log.debug("Number=%s" % p)

        log.debug("Phone num list = %s" % phone_num_list)

        if not phone_num_list:
            log.error("No recipients specified. Please use -f, -r, and/or -g to specify recipients.")
            usage()

        allowable_mime_types = cups.getAllowableMIMETypes()
        allowable_mime_types.append("application/hplip-fax")
        allowable_mime_types.append("application/x-python")

        for f in args:
            path = os.path.realpath(f)
            log.debug(path)

            if os.path.exists(path):
                mime_type = magic.mime_type(path)
                log.debug(mime_type)
            else:
                log.error("File '%s' does not exist." % path)
                sys.exit(1)

            if mime_type not in allowable_mime_types:
                log.error("File '%s' has a non-allowed mime-type of '%s'" % (path, mime_type))
                sys.exit(1)

        if printer_name:
            printer_list = cups.getPrinters()
            found = False
            for p in printer_list:
                if p.name == printer_name:
                    device_uri = p.device_uri
                    found = True
                    break

            if not found:
                log.error("Unknown printer name: %s" % printer_name)
                sys.exit(1)

            if not p.device_uri.startswith('hpfax:/'):
                log.error("You must specify a printer that has a device URI in the form 'hpfax:/'")
                sys.exit(1)

        if device_uri and not printer_name:
            cups_printers = cups.getPrinters()

            max_printer_size = 20
            printers = []
            for p in cups_printers:
                try:
                    back_end, is_hp, bus, model, serial, dev_file, host, port = \
                        device.parseDeviceURI(p.device_uri)
                except Error:
                    continue

                if back_end == 'hpfax' and p.device_uri == device_uri:
                    printers.append((p.name, p.device_uri))
                    max_printer_size = max(len(p.name), max_printer_size)

            if not printers:
                log.error("No CUPS queue found for device %s" % device_uri)
                sys.exit(1)

            elif len(printers) == 1:
                printer_name = printers[0][0]

            else:
                log.info(log.bold("\nChoose printer (fax queue) from installed printers in CUPS:\n"))

                formatter = utils.TextFormatter(
                        (
                            {'width': 4},
                            {'width': max_printer_size, 'margin': 2},
                        )
                    )

                log.info(formatter.compose(("Num.", "CUPS Printer (queue)")))
                log.info(formatter.compose(('-'*4, '-'*(max_printer_size), )))

                i = 0
                for p in printers:
                    log.info(formatter.compose((str(i), p[0])))
                    i += 1

                ok, x = tui.enter_range("\nEnter number 0...%d for printer (q=quit) ?" % (i-1), 0, (i-1))

                if not ok: 
                    sys.exit(0)

                printer_name = printers[x][0]

        if not device_uri and not printer_name:
            cups_printers = cups.getPrinters()
            log.debug(cups_printers)

            printers = []
            max_deviceid_size, max_printer_size = 0, 0

            for p in cups_printers:
                try:
                    back_end, is_hp, bus, model, serial, dev_file, host, port = \
                        device.parseDeviceURI(p.device_uri)
                except Error:
                    continue

                if back_end == 'hpfax':
                    printers.append((p.name, p.device_uri))
                    max_deviceid_size = max(len(p.device_uri), max_deviceid_size)
                    max_printer_size = max(len(p.name), max_printer_size)

            if not printers:
                log.error("No devices found.")
                sys.exit(1)

            if len(printers) == 1:
                printer_name, device_uri = printers[0]

            else:
                log.info(log.bold("\nChoose printer (fax queue) from installed printers in CUPS:\n"))

                formatter = utils.TextFormatter(
                        (
                            {'width': 4},
                            {'width': max_printer_size, 'margin': 2},
                            {'width': max_deviceid_size, 'margin': 2},
                        )
                    )

                log.info(formatter.compose(("Num.", "CUPS Printer", "Device URI")))
                log.info(formatter.compose(('-'*4, '-'*(max_printer_size), '-'*(max_deviceid_size))))

                i = 0
                for p in printers:
                    log.info(formatter.compose((str(i), p[0], p[1])))
                    i += 1

                ok, x = tui.enter_range("\nEnter number 0...%d for printer (q=quit) ?" % (i-1), 0, (i-1))

                if not ok: 
                    sys.exit(0)

                printer_name, device_uri = printers[x]


        log.info(log.bold("Using printer %s (%s)" % (printer_name, device_uri)))

        ppd_file = cups.getPPD(printer_name)

        if ppd_file is not None and os.path.exists(ppd_file):
            if file(ppd_file, 'r').read(8192).find('HP Fax') == -1:
                log.error("Fax configuration error. The CUPS fax queue for '%s' is incorrectly configured. Please make sure that the CUPS fax queue is configured with the 'HP Fax' Model/Driver." % printer_name)
                sys.exit(1)

        if not args:
            log.error("No files specfied to send. Please specify the file(s) to send on the command line.")
            usage()

        file_list = []

        for f in args:

            #
            # Submit each file to CUPS for rendering by hpijsfax
            #
            path = os.path.realpath(f)
            log.debug(path)
            mime_type = magic.mime_type(path)

            if mime_type == 'application/hplip-fax': # .g3
                log.info("\nPreparing fax file %s..." % f)
                fax_file_fd = file(f, 'r')
                header = fax_file_fd.read(fax.FILE_HEADER_SIZE)
                fax_file_fd.close()

                mg, version, pages, hort_dpi, vert_dpi, page_size, \
                    resolution, encoding, reserved1, reserved2 = struct.unpack(">8sBIHHBBBII", header)

                if mg != 'hplip_g3':
                    log.error("%s: Invalid file header. Bad magic." % f)
                    sys.exit(1)

                file_list.append((f, mime_type, "", "", pages))

            else:
                all_pages = True 
                page_range = ''
                page_set = 0
                nup = 1

                cups.resetOptions()

                if mime_type in ["application/x-cshell",
                                 "application/x-perl",
                                 "application/x-python",
                                 "application/x-shell",
                                 "text/plain",] and prettyprint:

                    cups.addOption('prettyprint')

                if nup > 1:
                    cups.addOption('number-up=%d' % nup)

                cups_printers = cups.getPrinters()
                printer_state = cups.IPP_PRINTER_STATE_STOPPED
                for p in cups_printers:
                    if p.name == printer_name:
                        printer_state = p.state

                log.debug("Printer state = %d" % printer_state)

                if printer_state == cups.IPP_PRINTER_STATE_IDLE:
                    log.debug("Printer name = %s file = %s" % (printer_name, path))
                    sent_job_id = cups.printFile(printer_name, path, os.path.basename(path))
                    log.info("\nRendering file '%s' (job %d)..." % (path, sent_job_id))
                    log.debug("Job ID=%d" % sent_job_id)
                else:
                    log.error("The CUPS queue for '%s' is in a stopped or busy state. Please check the queue and try again." % printer_name)
                    sys.exit(1)

                cups.resetOptions()

                #
                # Wait for fax to finish rendering
                #

                end_time = time.time() + 120.0 
                while time.time() < end_time:
                    log.debug("Waiting for fax...")
                    try:
                        result = list(service.CheckForWaitingFax(device_uri, prop.username, sent_job_id))
                        print result
                    except dbus.exceptions.DBusException:
                        log.error("Cannot communicate with hp-systray. Canceling...")
                        cups.cancelJob(sent_job_id)
                        sys.exit(1)

                    fax_file = str(result[7])
                    print fax_file

                    if fax_file:
                        log.debug("Fax file=%s" % fax_file)
                        title = str(result[5])
                        break

                    time.sleep(1)

                else:
                    log.error("Timeout waiting for rendering. Canceling job #%d..." % sent_job_id)
                    cups.cancelJob(sent_job_id)
                    sys.exit(1)

                # open the rendered file to read the file header
                f = file(fax_file, 'r')
                header = f.read(fax.FILE_HEADER_SIZE)

                if len(header) != fax.FILE_HEADER_SIZE:
                    log.error("Invalid fax file! (truncated header or no data)")
                    sys.exit(1)

                mg, version, total_pages, hort_dpi, vert_dpi, page_size, \
                    resolution, encoding, reserved1, reserved2 = \
                    struct.unpack(">8sBIHHBBBII", header[:fax.FILE_HEADER_SIZE])

                log.debug("Magic=%s Ver=%d Pages=%d hDPI=%d vDPI=%d Size=%d Res=%d Enc=%d" %
                          (mg, version, total_pages, hort_dpi, vert_dpi, page_size, resolution, encoding))

                file_list.append((fax_file, mime_type, "", title, total_pages))
                f.close()

        #
        # Insure that the device is in an OK state
        #

        dev = None

        log.debug("\nChecking device state...")
        try:
            dev = fax.getFaxDevice(device_uri, printer_name)

            try:
                dev.open()
            except Error, e:
                log.warn(e.msg)

            try:
                dev.queryDevice(quick=True)
            except Error, e:
                log.error("Query device error (%s)." % e.msg)
                dev.error_state = ERROR_STATE_ERROR

            if dev.error_state > ERROR_STATE_MAX_OK and \
                dev.error_state not in (ERROR_STATE_LOW_SUPPLIES, ERROR_STATE_LOW_PAPER):

                log.error("Device is busy or in an error state (code=%d). Please wait for the device to become idle or clear the error and try again." % dev.error_state)
                sys.exit(1)

            user_cfg.last_used.device_uri = dev.device_uri

            log.debug("File list:")

            for f in file_list:
                log.debug(str(f))

            service.SendEvent(device_uri, printer_name, EVENT_START_FAX_JOB, prop.username, 0, '')

            update_queue = Queue.Queue()
            event_queue = Queue.Queue()

            log.info("\nSending fax...")

            if not dev.sendFaxes(phone_num_list, file_list, "", 
                                 "", None, False, printer_name,
                                 update_queue, event_queue):

                log.error("Send fax is active. Please wait for operation to complete.")
                service.SendEvent(device_uri, printer_name, EVENT_FAX_JOB_FAIL, prop.username, 0, '')
                sys.exit(1)

            try:
                cont = True
                while cont:
                    while update_queue.qsize():
                        try:
                            status, page_num, phone_num = update_queue.get(0)
                        except Queue.Empty:
                            break

                        if status == fax.STATUS_IDLE:
                            log.debug("Idle")

                        elif status == fax.STATUS_PROCESSING_FILES:
                            log.info("\nProcessing page %d" % page_num)

                        elif status == fax.STATUS_DIALING:
                            log.info("\nDialing %s..." % phone_num)

                        elif status == fax.STATUS_CONNECTING:
                            log.info("\nConnecting to %s..." % phone_num)

                        elif status == fax.STATUS_SENDING:
                            log.info("\nSending page %d to %s..." % (page_num, phone_num))

                        elif status == fax.STATUS_CLEANUP:
                            log.info("\nCleaning up...")

                        elif status in (fax.STATUS_ERROR, fax.STATUS_BUSY, fax.STATUS_COMPLETED):
                            cont = False

                            if status  == fax.STATUS_ERROR:
                                log.error("Fax send error.")
                                service.SendEvent(device_uri, printer_name, EVENT_FAX_JOB_FAIL, prop.username, 0, '')

                            elif status == fax.STATUS_BUSY:
                                log.error("Fax device is busy. Please try again later.")
                                service.SendEvent(device_uri, printer_name, EVENT_FAX_JOB_FAIL, prop.username, 0, '')

                            elif status == fax.STATUS_COMPLETED:
                                log.info("\nCompleted successfully.")
                                service.SendEvent(device_uri, printer_name, EVENT_END_FAX_JOB, prop.username, 0, '')

                    update_spinner()
                    time.sleep(2)

                cleanup_spinner()

            except KeyboardInterrupt:
                event_queue.put((fax.EVENT_FAX_SEND_CANCELED, '', '', ''))
                service.SendEvent(device_uri, printer_name, EVENT_FAX_JOB_CANCELED, prop.username, 0, '')
                log.error("Cancelling...")

        finally:
            log.debug("Waiting for send fax thread to exit...")
            if dev is not None:
                dev.waitForSendFaxThread()
                log.debug("Closing device...")
                dev.close()

    except KeyboardInterrupt:
        log.error("User exit")    

log.info("")
log.info("Done.")




