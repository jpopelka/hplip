#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2011 Hewlett-Packard Development Company, L.P.
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
# Author: Amarnath Chitumalla, Suma Byrappa
#

__version__ = '1.0'
__mod__ = 'hp-diagnose_plugin'
__title__ = 'Plugin Download and Install Utility'
__doc__ = ""

# Std Lib
import sys
import getopt
import time
import os.path
import re
import os

# Local
from base.g import *
from base import utils, module

pm = None



USAGE = [ (__doc__, "", "name", True),
          ("Usage: %s [MODE] [OPTIONS]" % __mod__, "", "summary", True),
          utils.USAGE_MODE,
          ("Installation for required printer mode:", "--required (Qt4 only)", "option", False),
          ("Installation for optional printer mode:", "--optional (Qt4 only)", "option", False),
          #("Installation generic mode:", "--generic (default)", "option", False),
          utils.USAGE_LANGUAGE,
          utils.USAGE_OPTIONS,
          utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
          utils.USAGE_HELP,
          utils.USAGE_SPACE,
          utils.USAGE_SEEALSO,
          ("hp-plugin", "", "seealso", False),
          ("hp-setup", "", "seealso", False),
          ("hp-firmware", "", "seealso", False),
        ]


mod = module.Module(__mod__, __title__, __version__, __doc__, USAGE,
                    (INTERACTIVE_MODE, GUI_MODE),
                    (UI_TOOLKIT_QT3, UI_TOOLKIT_QT4), True)

opts, device_uri, printer_name, mode, ui_toolkit, loc = \
    mod.parseStdOpts( handle_device_printer=False)

plugin_path = None
install_mode = PLUGIN_NONE # reuse plugin types for mode (PLUGIN_NONE = generic)
plugin_reason = PLUGIN_REASON_NONE

for o, a in opts:
    if o == '--required':
        install_mode = PLUGIN_REQUIRED
        if ui_toolkit == 'qt3':
            log.warn("--required switch ignored.")

    elif o == '--optional':
        install_mode = PLUGIN_OPTIONAL
        if ui_toolkit == 'qt3':
            log.warn("--optional switch ignored.")

    elif o == '--reason':
        plugin_reason = int(a)


version = prop.installed_version



if mode == GUI_MODE:
    if ui_toolkit == 'qt3':
        if not utils.canEnterGUIMode():
            log.error("%s requires GUI support (try running with --qt4). Try using interactive (-i) mode." % __mod__)
            sys.exit(1)
    else:
        if not utils.canEnterGUIMode4():
            log.error("%s requires GUI support (try running with --qt3). Try using interactive (-i) mode." % __mod__)
            sys.exit(1)


if mode == GUI_MODE:
    if ui_toolkit == 'qt3':
        log.error("Unable to load Qt3. Please use qt4")

    else: # qt4
        try:
            from PyQt4.QtGui import QApplication, QMessageBox
            from ui4.plugindiagnose import PluginDiagnose
        except ImportError:
            log.error("Unable to load Qt4 support. Is it installed?")
            sys.exit(1)

        app = QApplication(sys.argv)

	dialog = PluginDiagnose(None, install_mode, plugin_reason)
        dialog.show()

        try:
            log.debug("Starting GUI loop...")
            app.exec_()
        except KeyboardInterrupt:
            log.error("User exit")
            sys.exit(0)


log.info("")
log.info("Done.")

