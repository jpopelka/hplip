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

__version__ = '4.0'
__title__ = 'Print Utility'
__doc__ = "A simple front end to 'lp'. Provides a print UI from the Device Manager if kprinter, gtklp, or xpp are not installed."

# Std Lib
import sys
import os
import getopt

# Local
from base.g import *
from base import utils, device, tui
from prnt import cups

log.set_module('hp-print')

app = None
printdlg = None

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-print [PRINTER|DEVICE-URI] [OPTIONS] [FILE LIST]", "", "summary", True),
         utils.USAGE_ARGS,
         utils.USAGE_DEVICE,
         ("To specify a CUPS printer:", "-P<printer>, -p<printer> or --printer=<printer>", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         ("[FILELIST]", "", "heading", False),
         ("Optional list of files:", """Space delimited list of files to print. Files can also be selected for print by adding them to the file list in the UI.""", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1, utils.USAGE_STD_NOTES2, 
         ]


def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-print', __version__)
    sys.exit(0)


try:
    opts, args = getopt.getopt(sys.argv[1:], 'P:p:d:hl:gq:',
                               ['printer=', 'device=', 'help', 
                                'help-rest', 'help-man', 'logging=', 
                                'lang=', 'help-desc'])
except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

printer_name = None
device_uri = None
log_level = logger.DEFAULT_LOG_LEVEL
loc = None
bus = ['cups']

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

    elif o in ('-p', '-P', '--printer'):
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

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-q', '--lang'):
        if a.strip() == '?':
            tui.show_languages()
            sys.exit(0)

        loc = utils.validate_language(a.lower())



# Security: Do *not* create files that other users can muck around with
os.umask (0037)

utils.log_title(__title__, __version__)

if os.getuid() == 0:
    log.warn("hp-print should not be run as root.")

if not utils.canEnterGUIMode():
    log.error("hp-print requires GUI support. Exiting.")
    sys.exit(1)


from qt import *
from ui.printerform import PrinterForm


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


printdlg = PrinterForm(bus, device_uri, printer_name, args)
printdlg.show()
app.setMainWidget(printdlg)

try:
    log.debug("Starting GUI loop...")
    app.exec_loop()
except KeyboardInterrupt:
    pass
#except:
#    log.exception()

#sock.close()
sys.exit(0)


