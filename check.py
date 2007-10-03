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

__version__ = '12.0'
__title__ = 'Dependency/Version Check Utility'
__doc__ = "Check the existence and versions of HPLIP dependencies."

# Std Lib
import sys
import os
import getopt
import commands
import re

# Local
from base.g import *
from base import utils, tui, models #, device
from installer import dcheck
from installer.core_install import *

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-check/check.py [OPTIONS]", "", "summary", True),
         utils.USAGE_OPTIONS,
         ("Pre-install check:", "-p or --pre", "option", False),
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_LOGGING_PLAIN,
         utils.USAGE_HELP,
         utils.USAGE_NOTES,
         ("1. For posting to the mailing list, use the -t parameter and then copy/paste the onscreen output or use the generated hp-check.log file.", "", "note", False),
         ("2. Use with the '-p' switch prior to installation to check for dependencies and system requirements (skips some checks).", "", "note", False),
         ("3. Run without the '-p' switch after installation to check for proper install (runs all checks). ", "", "note", False),
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-check', __version__)
    sys.exit(0)        

build_str = "HPLIP will not build, install, and/or function properly without this dependency."

pat_deviceuri = re.compile(r"""(.*):/(.*?)/(\S*?)\?(?:serial=(\S*)|device=(\S*)|ip=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[^&]*))(?:&port=(\d))?""", re.IGNORECASE)

def parseDeviceURI(device_uri):
    m = pat_deviceuri.match(device_uri)

    if m is None:
        raise Error(ERROR_INVALID_DEVICE_URI)

    back_end = m.group(1).lower() or ''
    is_hp = (back_end in ('hp', 'hpfax', 'hpaio'))
    bus = m.group(2).lower() or ''

    if bus not in ('usb', 'net', 'bt', 'fw', 'par'):
        raise Error(ERROR_INVALID_DEVICE_URI)

    model = m.group(3) or ''
    serial = m.group(4) or ''
    dev_file = m.group(5) or ''
    host = m.group(6) or ''
    port = m.group(7) or 1

    if bus == 'net':
        try:
            port = int(port)
        except (ValueError, TypeError):
            port = 1

        if port == 0:
            port = 1

    return back_end, is_hp, bus, model, serial, dev_file, host, port

num_errors = 0
fmt = True
pre = False
overall_commands_to_run = []

try:
    log.set_module("hp-check")

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hl:gtp', 
            ['help', 'help-rest', 'help-man', 'help-desc', 'logging=', 'pre']) 

    except getopt.GetoptError, e:
        log.error(e.msg)
        usage()
        sys.exit(1)

    if os.getenv("HPLIP_DEBUG"):
        log.set_level('debug')

    log_level = 'info'

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

        elif o in ('-l', '--logging'):
            log_level = a.lower().strip()

        elif o == '-g':
            log_level = 'debug'

        elif o == '-t':
            fmt = False

        elif o in ('-p', '--pre'):
            pre = True


    if not log.set_level(log_level):
        usage()
        
    if not fmt:
        log.no_formatting()

    utils.log_title(__title__, __version__)

    log_file = os.path.normpath('./hp-check.log')
    print "Saving output in log file: %s" % log_file
    log.debug("Log file=%s" % log_file)
    if os.path.exists(log_file):
        os.remove(log_file)

    log.set_logfile(log_file)
    log.set_where(log.LOG_TO_CONSOLE_AND_FILE)

    log.info("\nInitializing. Please wait...")
    core =  CoreInstall(MODE_CHECK)
    core.init()

    tui.header("SYSTEM INFO")

    log.info(log.bold("Basic system information:"))
    log.info(core.sys_uname_info)

    log.info("")
    log.info(log.bold("Distribution:"))
    log.info("%s %s" % (core.distro_name, core.distro_version))

    log.info(log.bold("\nHPOJ running?"))

    if core.hpoj_present:
        log.error("Yes, HPOJ is running. HPLIP is not compatible with HPOJ. To run HPLIP, please remove HPOJ.")
        num_errors += 1
    else:
        log.info("No, HPOJ is not running (OK).")


    log.info("")
    log.info(log.bold("Checking Python version..."))
    ver = sys.version_info
    log.debug("sys.version_info = %s" % repr(ver))
    ver_maj = ver[0]
    ver_min = ver[1]
    ver_pat = ver[2]

    if ver_maj == 2:
        if ver_min >= 1:
            log.info("OK, version %d.%d.%d installed" % ver[:3])
        else:
            log.error("Version %d.%d.%d installed. Please update to Python >= 2.1" % ver[:3])
            sys.exit(1)


    log.info("")
    log.info(log.bold("Checking PyQt version..."))

    # PyQt
    try:
        import qt
    except ImportError:
        num_errors += 1
        log.error("NOT FOUND OR FAILED TO LOAD!")
    else:
        # check version of Qt
        qtMajor = int(qt.qVersion().split('.')[0])

        if qtMajor < MINIMUM_QT_MAJOR_VER:
            log.error("Incorrect version of Qt installed. Ver. 3.0.0 or greater required.")
        else:
            #check version of PyQt
            try:
                pyqtVersion = qt.PYQT_VERSION_STR
            except:
                pyqtVersion = qt.PYQT_VERSION

            while pyqtVersion.count('.') < 2:
                pyqtVersion += '.0'

            (maj_ver, min_ver, pat_ver) = pyqtVersion.split('.')

            if pyqtVersion.find('snapshot') >= 0:
                log.error("A non-stable snapshot version of PyQt is installed (%s)." % pyqtVersion)
                num_errors += 1
            else:
                try:
                    maj_ver = int(maj_ver)
                    min_ver = int(min_ver)
                    pat_ver = int(pat_ver)
                except ValueError:
                    maj_ver, min_ver, pat_ver = 0, 0, 0

                if maj_ver < MINIMUM_PYQT_MAJOR_VER or \
                    (maj_ver == MINIMUM_PYQT_MAJOR_VER and min_ver < MINIMUM_PYQT_MINOR_VER):
                    num_errors += 1
                    log.error("HPLIP may not function properly with the version of PyQt that is installed (%d.%d.%d)." % (maj_ver, min_ver, pat_ver))
                    log.error("Ver. %d.%d or greater required." % (MINIMUM_PYQT_MAJOR_VER, MINIMUM_PYQT_MINOR_VER))
                else:
                    log.info("OK, version %d.%d installed." % (maj_ver, min_ver))


    log.info("")
    log.info(log.bold("Checking SIP version..."))

    sip_ver = None
    try:
        import pyqtconfig
    except ImportError:
        pass
    else:
        sip_ver = pyqtconfig.Configuration().sip_version_str 

    if sip_ver is not None:
        log.info("OK, Version %s installed" % sip_ver)
    else:
        num_errors += 1
        log.error("SIP not installed or version not found.")

    log.info("")
    log.info(log.bold("Checking for CUPS..."))

    status, output = utils.run('lpstat -r')
    if status == 0:
        log.info("Status: %s" % output.strip())
    else:
        log.error("Status: (Not available. CUPS may not be installed or not running.)")
        num_errors += 1

    status, output = utils.run('cups-config --version')
    if status == 0:
        log.info("Version: %s" % output.strip())
    else:
        log.error("Version: (Not available. CUPS may not be installed or not running.)")
        num_errors += 1

    tui.header("DEPENDENCIES")

    log.info("")

    dd = core.dependencies.keys()
    dd.sort()
    for d in dd:
        log.debug("***")
        
        log.info(log.bold("Checking for dependency: %s..." % core.dependencies[d][2]))

        if core.have_dependencies[d]:
            log.info("OK, found.")
        else:
            num_errors += 1

            if core.dependencies[d][0]:
                log.error("NOT FOUND! This is a REQUIRED dependency. Please make sure that this dependency is installed before installing or running HPLIP.")
            else:
                log.warn("NOT FOUND! This is an OPTIONAL dependency. Some HPLIP functionality may not function properly.")

            if core.distro_supported():
                packages_to_install, commands = core.get_dependency_data(d)
                
                commands_to_run = []

                if packages_to_install:
                    package_mgr_cmd = core.get_distro_data('package_mgr_cmd')

                    if package_mgr_cmd:
                        packages_to_install = ' '.join(packages_to_install)
                        commands_to_run.append(utils.cat(package_mgr_cmd))

                if commands:
                    commands_to_run.extend(commands)

                overall_commands_to_run.extend(commands_to_run)
                
                if len(commands_to_run) == 1:
                    log.info("To install this dependency, execute this command:")
                    log.info(commands_to_run[0])

                elif len(commands_to_run) > 1:
                    log.info("To install this dependency, execute these commands:")
                    for c in commands_to_run:
                        log.info(c)


        log.info("")

    if not pre:
        tui.header("HPLIP INSTALLATION")

        scanning_enabled = utils.to_bool(sys_cfg.configure.get("scanner-build", False))

        log.info("")
        log.info(log.bold("Currently installed HPLIP version..."))
        v = sys_cfg.hplip.version
        home = sys_cfg.dirs.home

        if v:
            log.info("HPLIP %s currently installed in '%s'." % (v, home))

            log.info("")
            log.info(log.bold("Current contents of '/etc/hp/hplip.conf' file:"))
            output = file('/etc/hp/hplip.conf', 'r').read()
            log.info(output)

        else:
            log.info("Not found.")  

        tui.header("INSTALLED PRINTERS")
        
        lpstat_pat = re.compile(r"""^device for (.*): (.*)""", re.IGNORECASE)

        status, output = utils.run('lpstat -v')
        log.info("")

        cups_printers = []
        for p in output.splitlines():
            try:
                match = lpstat_pat.search(p)
                printer_name = match.group(1)
                device_uri = match.group(2)
                cups_printers.append((printer_name, device_uri))
            except AttributeError:
                pass

        if cups_printers:
            non_hp = False
            for p in cups_printers:
                printer_name, device_uri = p
                try:
                    back_end, is_hp, bus, model, serial, dev_file, host, port = \
                        parseDeviceURI(device_uri)
                except Error:
                    back_end, is_hp, bus, model, serial, dev_file, host, port = \
                        '', False, '', '', '', '', '', 1

                log.info(log.bold(printer_name))
                log.info(log.bold('-'*len(printer_name)))

                x = "Unknown"
                if back_end == 'hpfax':
                    x = "Fax"
                elif back_end == 'hp':
                    x = "Printer"

                log.info("Type: %s" % x)

                if is_hp:
                    x = 'Yes, using the %s: CUPS backend.' % back_end
                else:
                    x = 'No, not using the hp: or hpfax: CUPS backend.'
                    non_hp = True

                log.info("Installed in HPLIP?: %s" % x)
                log.info("Device URI: %s" % device_uri)

                ppd = os.path.join('/etc/cups/ppd', printer_name + '.ppd')

                if os.path.exists(ppd):
                    log.info("PPD: %s" % ppd)
                    nickname_pat = re.compile(r'''\*NickName:\s*\"(.*)"''', re.MULTILINE)

                    f = file(ppd, 'r').read(4096)

                    try:
                        desc = nickname_pat.search(f).group(1)
                    except AttributeError:
                        desc = ''

                    log.info("PPD Description: %s" % desc)

                    status, output = utils.run('lpstat -p%s' % printer_name)
                    log.info("Printer status: %s" % output.replace("\n", ""))

                    if back_end == 'hpfax' and desc != 'HP Fax':
                        num_errors += 1
                        log.error("Incorrect PPD file for fax queue '%s'. Fax queues must use 'HP-Fax-hplip.ppd'." % printer_name)

                    elif back_end == 'hp' and desc == 'HP Fax':
                        num_errors += 1
                        log.error("Incorrect PPD file for a print queue '%s'. Print queues must not use 'HP-Fax-hplip.ppd'." % printer_name)

                    elif back_end not in ('hp', 'hpfax'):
                        log.warn("Printer is not HPLIP installed. Printers must use the hp: or hpfax: CUPS backend to function in HPLIP.")
                        num_errors += 1
                        
##                if is_hp:
##                    try:
##                        d = device.Device(device_uri)
##                    except Error:
##                        log.debug("Device() init failed.")
##                        continue
##                        
##                    if d.mq.get('plugin', 0):
##                        home = sys_cfg.dirs.home
##                        if not home:
##                            home = os.path.realpath(os.path.normpath(os.getcwd()))
##                        
##                        model = model.lower()
##                        if os.path.exists(os.path.join(home, "data", "plugins", "%s.plugin" % model)):
##                            log.info("Plug-in Required: OK, plug-in is installed.")
##                        else:
##                            log.info("A plug-in is required for this model:")
##                            log.error("Plug-in not installed.")
##                            num_errors += 1
##                            
##                log.info("")

        else:
            log.warn("No queues found.")

        if scanning_enabled:
            tui.header("SANE CONFIGURATION")
            log.info(log.bold("'hpaio' in '/etc/sane.d/dll.conf'..."))
            try:
                f = file('/etc/sane.d/dll.conf', 'r')
            except IOError:
                log.error("'/etc/sane.d/dll.conf' not found. Is SANE installed?")
                num_errors += 1
            else:
                found = False
                for line in f:
                    if 'hpaio' in line:
                        found = True

                if found:
                    log.info("OK, found. SANE backend 'hpaio' is properly set up.")
                else:
                    num_errors += 1
                    log.error("Not found. SANE backend 'hpaio' NOT properly setup (needs to be added to /etc/sane.d/dll.conf).")

                log.info("")
                log.info(log.bold("Checking output of 'scanimage -L'..."))
                if utils.which('scanimage'):
                    status, output = utils.run("scanimage -L")
                    log.info(output)
                else:
                    log.error("scanimage not found.")

        tui.header("PYTHON EXTENSIONS")

        log.info(log.bold("Checking 'cupsext' CUPS extension..."))
        try:
            import cupsext
        except ImportError:
            num_errors += 1
            log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of cupsext.")
        else:
            log.info("OK, found.")

        log.info("")
        log.info(log.bold("Checking 'pcardext' Photocard extension..."))
        try:
            import pcardext
        except ImportError:
            num_errors += 1
            log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of pcardext.")
        else:
            log.info("OK, found.")

        log.info("")
        log.info(log.bold("Checking 'hpmudext' I/O extension..."))
        try:
            import hpmudext
            hpmudext_avail = True
        except ImportError:
            hpmudext_avail = False
            num_errors += 1
            log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of hpmudext.")
        else:
            log.info("OK, found.")        

        if scanning_enabled:
            log.info("")
            log.info(log.bold("Checking 'scanext' SANE scanning extension..."))
            try:
                import scanext
            except ImportError:
                num_errors += 1
                log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of scanext.")
            else:
                log.info("OK, found.")        

                log.info("")

        tui.header("USB I/O SETUP")
        
        if hpmudext_avail:
            lsusb = utils.which('lsusb')
            if lsusb:
                log.info("")
                log.info(log.bold("Checking for permissions of USB attached printers..."))
                lsusb = os.path.join(lsusb, 'lsusb')
                status, output = utils.run("%s -d03f0:" % lsusb)

                lsusb_pat = re.compile("""^Bus\s([0-9a-fA-F]{3,3})\sDevice\s([0-9a-fA-F]{3,3}):\sID\s([0-9a-fA-F]{4,4}):([0-9a-fA-F]{4,4})(.*)""", re.IGNORECASE)
                log.debug(output)

                for o in output.splitlines():
                    ok = True
                    match = lsusb_pat.search(o)

                    if match is not None:
                        bus, device, vid, pid, mfg = match.groups()
                        log.info("HP Device 0x%x at %s:%s: " % (int(pid, 16), bus, device))
                        result_code, deviceuri = hpmudext.make_usb_uri(bus, device)

                        if result_code == hpmudext.HPMUD_R_OK:
                            log.info("    Device URI: %s" %  deviceuri)
                        else:
                            log.warn("    Device URI: (Makeuri FAILED)")

                        devnode = os.path.join("/", "dev", "bus", "usb", bus, device)

                        if not os.path.exists(devnode):
                            devnode = os.path.join("/", "proc", "bus", "usb", bus, device)
                        
                        if os.path.exists(devnode):
                            log.info("    Device node: %s" % devnode)

                            st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, \
                                st_size, st_atime, st_mtime, st_ctime = \
                                os.stat(devnode)

                            log.info("    Mode: 0%o" % (st_mode & 0777))
                            
                            getfacl = utils.which('getfacl')
                            if getfacl:
                                getfacl = os.path.join(getfacl, "getfacl")
                                
                                status, output = utils.run("%s %s" % (getfacl, devnode))
                                
                                log.info(output)
                                

    tui.header("SUMMARY")

    if num_errors:
        if num_errors == 1:
            log.error("1 error or warning.")
        else:
            log.error("%d errors and/or warnings." % num_errors)
            
        if overall_commands_to_run:
            log.info("")
            log.info(log.bold("Summary of needed commands to run to satisfy missing dependencies:"))
            for c in overall_commands_to_run:
                log.info(c)

        log.info("")
        log.info("Please refer to the installation instructions at:")
        log.info("http://hplip.sourceforge.net/install/index.html\n")

    else:
        log.info(log.green("No errors or warnings."))

except KeyboardInterrupt:
    log.warn("Aborted")
