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

__version__ = '3.2'
__title__ = "Make Copies Utility"
__doc__ = "PC initiated make copies on supported HP AiO and MFP devices."

# Std Lib
import sys
import os
import getopt
import re
import socket
import Queue
import time
import operator

# Local
from base.g import *
from base.msg import *
from base import utils, device, pml, service
from copier import copier
from prnt import cups

log.set_module('hp-makecopies')

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-makecopies [PRINTER|DEVICE-URI] [MODE] [OPTIONS]", "", "summary", True),
         utils.USAGE_ARGS,
         utils.USAGE_DEVICE,
         ("To specify a CUPS printer:", "-P<printer>, -p<printer> or --printer=<printer>", "option", False),
         utils.USAGE_SPACE,
         ("[MODE]", "", "header", False),
         ("Enter graphical UI mode:", "-u or --gui (Default)", "option", False),
         ("Run in non-interactive mode (batch mode):", "-n or --non-interactive", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         ("Number of copies:", "-m<num_copies> or --copies=<num_copies> or --num=<num_copies> (1-99)", "option", False),
         ("Reduction/enlargement:", "-r<%> or --reduction=<%> or --enlargement=<%> (25-400%)", "option", False),
         ("Quality:", "-q<quality> or --quality=<quality> (where quality is: 'fast', 'draft', 'normal', 'presentation', or 'best')", "option", False),
         ("Contrast:", "-c<contrast> or --contrast=<contrast> (-5 to +5)", "option", False),
         ("Fit to page (flatbed only):", "-f or --fittopage or --fit (overrides reduction/enlargement)", "option", False),
         utils.USAGE_LANGUAGE2,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1, utils.USAGE_STD_NOTES2, 
         ("3. If any copy parameter is not specified (contrast, reduction, etc), the default values from the device are used.", "", "note", False),
         ]


def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-makecopies', __version__)
    sys.exit(0)


try:
    opts, args = getopt.getopt(sys.argv[1:], 'P:p:d:hl:gm:c:q:r:funb:',
                               ['printer=', 'device=', 'help', 'logging=',
                                'num=', 'copies=', 'contrast=', 'quality=',
                                'reduction=', 'enlargement=', 'fittopage', 
                                'fit', 'gui', 'help-rest', 'help-man',
                                'help-desc', 'non-interactive', 'bus=', 
                                'lang='])
except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

printer_name = None
device_uri = None
log_level = logger.DEFAULT_LOG_LEVEL
bus = 'cups'
num_copies = None
reduction = None
reduction_spec = False
contrast = None
quality = None
fit_to_page = None
mode = GUI_MODE
mode_specified = False
loc = None

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    #print o, a
    if o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-p', '-P', '--printer'):
        printer_name = a

    elif o in ('-d', '--device'):
        device_uri = a

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-m', '--num', '--copies'):
        try:
            num_copies = int(a)
        except ValueError:
            log.warning("Invalid number of copies. Set to default of 1.")
            num_copies = 1

        if num_copies < 1: 
            log.warning("Invalid number of copies. Set to minimum of 1.")
            num_copies = 1

        elif num_copies > 99: 
            log.warning("Invalid number of copies. Set to maximum of 99.")
            num_copies = 99

    elif o in ('-c', '--contrast'):
        try:
            contrast = int(a)
        except ValueError:
            log.warning("Invalid contrast setting. Set to default of 0.")
            contrast = 0

        if contrast < -5: 
            log.warning("Invalid contrast setting. Set to minimum of -5.")
            contrast = -5

        elif contrast > 5: 
            log.warning("Invalid contrast setting. Set to maximum of +5.")
            contrast = 5

        contrast *= 25

    elif o in ('-q', '--quality'):
        a = a.lower().strip()

        if a == 'fast':
            quality = pml.COPIER_QUALITY_FAST

        elif a.startswith('norm'):
            quality = pml.COPIER_QUALITY_NORMAL

        elif a.startswith('pres'):
            quality = pml.COPIER_QUALITY_PRESENTATION

        elif a.startswith('draf'):
            quality = pml.COPIER_QUALITY_DRAFT

        elif a == 'best':
            quality = pml.COPIER_QUALITY_BEST

        else:
            log.warning("Invalid quality. Set to default of 'normal'.")

    elif o in ('-r', '--reduction', '--enlargement'):
        reduction_spec = True
        try:
            reduction = int(a.replace('%', ''))
        except ValueError:
            log.warning("Invalid reduction %. Set to default of 100%.")
            reduction = 100

        if reduction < 25:
            log.warning("Invalid reduction %. Set to minimum of 25%.")
            reduction = 25

        elif reduction > 400:
            log.warning("Invalid reduction %. Set to maximum of 400%.")
            reduction = 400

    elif o in ('-f', '--fittopage', '--fit'):
        fit_to_page = pml.COPIER_FIT_TO_PAGE_ENABLED

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

    elif o in ('-b', '--bus'):
        bus = a.lower().strip()
        if not device.validateBusList(bus):
            usage()
            
    elif o == '--lang':
        if a.strip() == '?':
            utils.show_languages()
            sys.exit(0)
            
        loc = utils.validate_language(a.lower())



if fit_to_page == pml.COPIER_FIT_TO_PAGE_ENABLED and reduction_spec:
    log.warning("Fit to page specfied: Reduction/enlargement parameter ignored.")


utils.log_title(__title__, __version__)

# Security: Do *not* create files that other users can muck around with
os.umask (0037)

if mode == GUI_MODE:
    if not prop.gui_build:
        log.warn("GUI mode disabled in build. Reverting to non-interactive mode.")
        mode = NON_INTERACTIVE_MODE
    
    elif not os.getenv('DISPLAY'):
        log.warn("No display found. Reverting to non-interactive mode.")
        mode = NON_INTERACTIVE_MODE

    elif not utils.checkPyQtImport():
        log.warn("PyQt init failed. Reverting to non-interactive mode.")
        mode = NON_INTERACTIVE_MODE
        
if mode == GUI_MODE:
    app = None
    makecopiesdlg = None

    from qt import *
    from ui.makecopiesform import MakeCopiesForm

    try:
        hpssd_sock = service.startup()
    except Error:
        log.error("Unable to connect to HPLIP I/O (hpssd).")
        sys.exit(1)

    log.debug("Connected to hpssd on %s:%d" % (prop.hpssd_host, prop.hpssd_port))
    
   

    # create the main application object
    app = QApplication(sys.argv)
    
    if loc is None:
        loc = user_cfg.ui.get("loc", "system")
        if loc.lower() == 'system':
            loc = str(QTextCodec.locale())
            log.debug("Using system locale: %s" % loc)
    
    if loc.lower() != 'c':
        log.debug("Trying to load .qm file for %s locale." % loc)
        trans = QTranslator(None)
        qm_file = 'hplip_%s.qm' % loc
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
        try:
            locale.setlocale(locale.LC_ALL, locale.normalize(loc+".utf8"))
            prop.locale = loc
        except locale.Error:
            log.error("Invalid locale: %s" % (loc+".utf8"))
    
    makecopiesdlg = MakeCopiesForm(hpssd_sock, bus, device_uri, printer_name, 
                                   num_copies, contrast, quality, reduction, fit_to_page)

    makecopiesdlg.show()
    app.setMainWidget(makecopiesdlg)

    try:
        log.debug("Starting GUI loop...")
        app.exec_loop()
    except KeyboardInterrupt:
        pass
    except:
        log.exception()

    hpssd_sock.close()

else: # NON_INTERACTIVE_MODE
    if not device_uri and not printer_name:
        try:
            device_uri = device.getInteractiveDeviceURI(bus, 
                filter={'copy-type': (operator.gt, 0)})
                
            if device_uri is None:
                sys.exit(1)
        except Error:
            log.error("Error occured during interactive mode. Exiting.")
            sys.exit(1)

    try:
        hpssd_sock = service.startup()
    except Error:
        log.error("Unable to connect to HPLIP I/O (hpssd).")
        sys.exit(1)

    dev = copier.PMLCopyDevice(device_uri, printer_name, 
                               hpssd_sock)


    if dev.copy_type == COPY_TYPE_NONE:
        log.error("Sorry, make copies functionality is not supported on this device.")
        sys.exit(1)
        
    user_cfg.last_used.device_uri = dev.device_uri

    try:
        dev.open()

        if num_copies is None:
            result_code, num_copies = dev.getPML(pml.OID_COPIER_NUM_COPIES)

        if contrast is None:
            result_code, contrast = dev.getPML(pml.OID_COPIER_CONTRAST)

        if reduction is None:
            result_code, reduction = dev.getPML(pml.OID_COPIER_REDUCTION)

        if quality is None:
            result_code, quality = dev.getPML(pml.OID_COPIER_QUALITY)

        if fit_to_page is None and dev.copy_type == COPY_TYPE_DEVICE:
            result_code, fit_to_page = dev.getPML(pml.OID_COPIER_FIT_TO_PAGE)
        else:
            fit_to_page = pml.COPIER_FIT_TO_PAGE_DISABLED

        result_code, max_reduction = dev.getPML(pml.OID_COPIER_REDUCTION_MAXIMUM)
        result_code, max_enlargement = dev.getPML(pml.OID_COPIER_ENLARGEMENT_MAXIMUM)

    except Error, e:
        log.error(e.msg)
        sys.exit(1)

    scan_style = dev.mq.get('scan-style', SCAN_STYLE_FLATBED)
    log.debug(scan_style)

    if scan_style == SCAN_STYLE_SCROLLFED:
        fit_to_page = pml.COPIER_FIT_TO_PAGE_DISABLED

    log.debug("num_copies = %d" % num_copies)
    log.debug("contrast= %d" % contrast)
    log.debug("reduction = %d" % reduction)
    log.debug("quality = %d" % quality)
    log.debug("fit_to_page = %d" % fit_to_page)
    log.debug("max_reduction = %d" % max_reduction)
    log.debug("max_enlargement = %d" % max_enlargement)
    log.debug("scan_style = %d" % scan_style)

    update_queue = Queue.Queue()
    event_queue = Queue.Queue()

    dev.copy(num_copies, contrast, reduction,
             quality, fit_to_page, scan_style,
             update_queue, event_queue)

    try:
        cont = True
        while cont:
            while update_queue.qsize():
                try:
                    status = update_queue.get(0)
                except Queue.Empty:
                    break

                if status == copier.STATUS_IDLE:
                    log.debug("Idle")
                    continue

                elif status in (copier.STATUS_SETTING_UP, copier.STATUS_WARMING_UP):
                    log.info("Warming up...")
                    continue

                elif status == copier.STATUS_ACTIVE:
                    log.info("Copying...")
                    continue

                elif status in (copier.STATUS_ERROR, copier.STATUS_DONE):

                    if status == copier.STATUS_ERROR:
                        log.error("Copier error!")
                        service.sendEvent(hpssd_sock, EVENT_COPY_JOB_FAIL, device_uri=device_uri)
                        cont = False
                        break

                    elif status == copier.STATUS_DONE:
                        cont = False
                        break

            time.sleep(2)

    except KeyboardInterrupt:
        event_queue.put(copier.COPY_CANCELED)
        service.sendEvent(hpssd_sock, EVENT_COPY_JOB_CANCELED, device_uri=device_uri)            
        log.error("Cancelling...")

    dev.close()

    dev.waitForCopyThread()
    service.sendEvent(hpssd_sock, EVENT_END_COPY_JOB, device_uri=device_uri)
    hpssd_sock.close()
    log.info("Done.")

sys.exit(0)

