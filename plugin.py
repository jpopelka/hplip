#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2008 Hewlett-Packard Development Company, L.P.
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
__title__ = 'Plugin Download and Install Utility'
__doc__ = ""

# Std Lib
import sys
import getopt
import time
import os.path
import re
import os
import gzip


# Local
from base.g import *
from base import device, utils, tui
from prnt import cups

pm = None


def plugin_download_callback(c, s, t):
    pm.update(int(100*c*s/t), 
             utils.format_bytes(c*s))

             
def plugin_install_callback(s):
    print s
    
    

USAGE = [ (__doc__, "", "name", True),
          ("Usage: hp-plugin [OPTIONS]", "", "summary", True),
          ("Enter graphical UI mode:", "-u or --gui (Default)", "option", False),
          ("Run in interactive mode:", "-i or --interactive", "option", False),
          utils.USAGE_LANGUAGE,
          utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
          utils.USAGE_HELP,
          utils.USAGE_SPACE,
          utils.USAGE_SEEALSO,
          ("hp-setup", "", "seealso", False),
        ]


def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-plugin', __version__)
    sys.exit(0)




log.set_module('hp-plugin')

try:
    opts, args = getopt.getopt(sys.argv[1:], 'hl:guiq:p:',
        ['help', 'help-rest', 'help-man',
         'logging=', 'gui', 'interactive',
         'help-desc', 'lang=', 'plugin=', 'path='])
         
except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

log_level = logger.DEFAULT_LOG_LEVEL
mode = GUI_MODE
mode_specified = False
loc = None
plugin_path = None

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    if o in ('-h', '--help'):
        usage('text')

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-u', '--gui'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-i or -u).")
            sys.exit(1)

        mode = GUI_MODE
        mode_specified = True

    elif o in ('-i', '--interactive'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-i or -u).")
            sys.exit(1)

        mode = INTERACTIVE_MODE
        mode_specified = True

    elif o in ('-q', '--lang'):
        if a.strip() == '?':
            tui.show_languages()
            sys.exit(0)

        loc = utils.validate_language(a.lower())
        
    elif o in ('-p', '--path', '--plugin'):
        plugin_path = os.path.normpath(os.path.abspath(os.path.expanduser(a)))


utils.log_title(__title__, __version__)

#version = sys_cfg.hplip.version
version = '.'.join(sys_cfg.hplip.version.split('.')[:3])

if plugin_path is not None:
    if not os.path.exists(plugin_path):
        log.error("Plug-in path '%s' not found." % plugin_path)
        sys.exit(1)
        
    if os.path.isdir(plugin_path):
        plugin_path = os.path.join(plugin_path, 'hplip-%s-plugin.run' % version)
        
        if not os.path.exists(plugin_path):
            log.error("Plug-in path '%s' not found." % plugin_path)
            sys.exit(1)

        
if mode == GUI_MODE:
    if not prop.gui_build:
        log.warn("GUI mode disabled in build. Reverting to interactive mode.")
        mode = INTERACTIVE_MODE

    elif not os.getenv('DISPLAY'):
        log.warn("No display found. Reverting to interactive mode.")
        mode = INTERACTIVE_MODE

    elif not utils.checkPyQtImport():
        log.warn("PyQt init failed. Reverting to interactive mode.")
        mode = INTERACTIVE_MODE

        
if mode == GUI_MODE:
    from qt import *
    from ui import pluginform2

    app = QApplication(sys.argv)
    QObject.connect(app, SIGNAL("lastWindowClosed()"), app, SLOT("quit()"))

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

    if not os.geteuid() == 0:
        log.error("You must be root to run this utility.")

        QMessageBox.critical(None, 
                             "HP Device Manager - Plug-in Installer",
                             "You must be root to run hp-plugin.",
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)

        sys.exit(1)

    #try:
    w = pluginform2.PluginForm2()
    #except Error:
    #    log.error("Unable to connect to HPLIP I/O. Please (re)start HPLIP and try again.")
    #    sys.exit(1)

    app.setMainWidget(w)
    w.show()

    app.exec_loop()

    
    
else: # INTERACTIVE_MODE
    try:
        if not os.geteuid() == 0:
            log.error("You must be root to run this utility.")
            sys.exit(1)

        log.info("(Note: Defaults for each question are maked with a '*'. Press <enter> to accept the default.)")
        log.info("")

        from installer import core_install
        core = core_install.CoreInstall()
        
        core.set_plugin_version() #version)
        
        plugin_filename = 'hplip-%s-plugin.run' % version
        
        tui.header("PLUG-IN INSTALLATION FOR HPLIP %s" % version)
        
        if core.check_for_plugin():
            log.info("The driver plugin for HPLIP %s appears to already be installed.")
            
            cont, ans = tui.enter_yes_no("Do you wish to download and re-install the plug-in?")
            
            if not cont or not ans:
                sys.exit(0)
                
        
        if plugin_path is None:
            table = tui.Formatter(header=('Option', 'Description'), min_widths=(10, 50))
            table.add(('d', 'Download plug-in from HP (recomended)'))
            table.add(('p', 'Specify a path to the plug-in (advanced)'))
            table.add(('q', 'Quit hp-plugin (skip installation)'))
            
            table.output()
            
            cont, ans = tui.enter_choice("\nEnter option (d=download*, p=specify path, q=quit) ? ", 
                ['d', 'p'], 'd')
            
            if not cont: # q
                sys.exit(0)
                
                        
            if ans == 'd': # d - download
                # read plugin.conf (local or on sf.net) to get plugin_path (http://)
                plugin_conf_url = core.get_plugin_conf_url()
                
                if plugin_conf_url.startswith('file://'):
                    tui.header("COPY CONFIGURATION")
                else:
                    tui.header("DOWNLOAD CONFIGURATION")
                    
                    log.info("Checking for network connection...")
                    ok = core.check_network_connection()
                    
                    if not ok:
                        log.error("Network connection not detected.")
                        sys.exit(1)
                    
                
                log.info("Downloading configuration file from: %s" % plugin_conf_url)
                pm = tui.ProgressMeter("Downloading configuration:")
                
                plugin_path, size, checksum, timestamp, ok = core.get_plugin_info(plugin_conf_url, 
                    plugin_download_callback)
                
                print
                
                if not plugin_path.startswith('http://') and not plugin_path.startswith('file://'):
                    plugin_path = 'file://' + plugin_path
            
            else: # p - specify plugin path
            
                while True:
                    plugin_path = raw_input(log.bold("Enter the path to the 'hplip-%s-plugin.run' file (q=quit) : " %
                        version)).strip()
                        
                    if plugin_path.strip().lower() == 'q':
                        sys.exit(1)
                        
                    if not plugin_path.startswith('http://'):
                        plugin_path = os.path.normpath(os.path.abspath(os.path.expanduser(plugin_path)))
                        
                        if not os.path.exists(plugin_path):
                            log.error("Plug-in path '%s' not found." % plugin_path)
                            continue
                            
                        if os.path.isdir(plugin_path):
                            plugin_path = os.path.join(plugin_path, plugin_filename)
                            
                            if not os.path.exists(plugin_path):
                                log.error("Plug-in path '%s' not found." % plugin_path)
                                continue

                        if os.path.basename(plugin_path) != plugin_filename:
                            log.error("Plug-in filename must be '%s'." % plugin_filename)
                            continue
                        
                        plugin_path = 'file://' + plugin_path
                    
                    size, checksum, timestamp = 0, '', 0.0
                    
                    break
        
        
        if plugin_path.startswith('file://'):
            tui.header("COPY PLUGIN")
        else:
            tui.header("DOWNLOAD PLUGIN")
            
            log.info("Checking for network connection...")
            ok = core.check_network_connection()
            
            if not ok:
                log.error("Network connection not detected.")
                sys.exit(1)
    
        log.info("Downloading plug-in from: %s" % plugin_path)
        pm = tui.ProgressMeter("Downloading plug-in:")
        
        ok, local_plugin = core.download_plugin(plugin_path, size, checksum, timestamp, plugin_download_callback)
        print
        
        if not ok:
            log.error("Plug-in download failed: %s" % local_plugin)
            sys.exit(1)
        
        tui.header("INSTALLING PLUG-IN")
        
        core.run_plugin(mode, plugin_install_callback)

        cups_devices = device.getSupportedCUPSDevices(['hp']) #, 'hpfax'])
        #print cups_devices
        
        title = False
        
        for dev in cups_devices:
            mq = device.queryModelByURI(dev)
            
            if mq.get('fw-download', 0):
                
                if not title:
                    tui.header("DOWNLOADING FIRMWARE")
                    title = True
                
                # Download firmware if needed
                log.info(log.bold("\nDownloading firmware to device %s..." % dev))
                try:
                    d = device.Device(dev)
                except Error:
                    log.error("Error opening device. Exiting.")
                    sys.exit(1)

                if d.downloadFirmware():
                    log.info("Firmware download successful.\n")

                d.close()


    except KeyboardInterrupt:
        log.error("User exit")

log.info("")
log.info("Done.")

