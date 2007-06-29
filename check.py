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

__version__ = '8.0'
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
from base import utils
from installer import dcheck, core
from installer.distros import *

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-check [OPTIONS]", "", "summary", True),
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

def usage(typ='text', fmt=True):
    if typ == 'text':
        utils.log_title(__title__, __version__, fmt)

    utils.format_text(USAGE, typ, __title__, 'hp-check', __version__)
    sys.exit(0)        

build_str = "HPLIP will not build, install, and/or function properly without this dependency."

dependencies = {
    'libjpeg':          (True, "libjpeg - JPEG library", build_str, dcheck.check_libjpeg),
    'cups' :            (True, "cups - Common Unix Printing System", build_str, dcheck.check_cups), 
    'cups-devel':       (True, 'cups-devel- Common Unix Printing System development files', build_str, dcheck.check_cups_devel),
    'gcc' :             (True, 'gcc - GNU Project C and C++ Compiler', build_str, dcheck.check_gcc),
    'make' :            (True, "make - GNU make utility to maintain groups of programs", build_str, dcheck.check_make),
    'python-devel' :    (True, "python-devel - Python development files", build_str, dcheck.check_python_devel),
    'libpthread' :      (True, "libpthread - POSIX threads library", build_str, dcheck.check_libpthread),
    'python2x':         (True, "Python 2.2 or greater - Python programming language", build_str, dcheck.check_python2x),
    'gs':               (True, "GhostScript - PostScript and PDF language interpreter and previewer", build_str, dcheck.check_gs),
    'libusb':           (True, "libusb - USB library", build_str, dcheck.check_libusb),
    #'lsb':              (True, "LSB - Linux Standard Base support", build_str, dcheck.check_lsb),

    'sane':             (True,  "sane - Scanning library", "HPLIP scanning feature will not function.", dcheck.check_sane),
    'sane-devel':       (True, "sane-devel - Scanning library development files", "HPLIP scanning feature will not function.", dcheck.check_sane_devel),
    'xsane':            (False, "xsane - Graphical scanner frontend for SANE", "This is an optional package.", dcheck.check_xsane),
    'scanimage':        (False, "scanimage - Shell scanning program", "This is an optional package.", dcheck.check_scanimage),

    'reportlab':        (False, "Reportlab - PDF library for Python", "HPLIP faxing will not have the coverpage feature.", dcheck.check_reportlab), 
    'python23':         (True,  "Python 2.3 or greater - Required for fax functionality", "HPLIP faxing feature will not function.", dcheck.check_python23),

    'ppdev':            (False,  "ppdev - Parallel port support kernel module.", "Parallel port (LPT) connected printers will not work with HPLIP", dcheck.check_ppdev),

    'pyqt':             (True,  "PyQt - Qt interface for Python", "HPLIP GUIs will not function.", dcheck.check_pyqt),

    'libnetsnmp-devel': (True,  "libnetsnmp-devel - SNMP networking library development files", "Networked connected printers will not work with HPLIP", dcheck.check_libnetsnmp),
    'libcrypto':        (True,  "libcrypto - OpenSSL cryptographic library", "Networked connected printers will not work with HPLIP", dcheck.check_libcrypto),

}

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

def header(text):
    c = len(text)
    log.info("")
    log.info("-"*(c+4))
    log.info("| "+text+" |")
    log.info("-"*(c+4))
    log.info("")

num_errors = 0
fmt = True
pre = False
overall_commands_to_run = []

try:
    log.set_module("hp-check")

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hl:gtp', 
            ['help', 'help-rest', 'help-man', 'help-desc', 'logging=', 'pre']) 

    except getopt.GetoptError:
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

    utils.log_title(__title__, __version__, fmt)

    log.info("Initializing. Please wait...")
    core.init()

    log_file = os.path.normpath('./hp-check.log')
    print "Saving output in log file: %s" % log_file
    if os.path.exists(log_file):
        os.remove(log_file)

    log.set_logfile(log_file)
    log.set_where(log.LOG_TO_CONSOLE_AND_FILE)

    log.debug("Log file=%s" % log_file)

    header("SYSTEM INFO")

    log.info(utils.bold("Basic system information:", fmt), fmt)
    status, output = utils.run('uname -a')
    log.info("%s" % output.replace('\n', ''))

    log.info("", fmt)
    log.info(utils.bold("Distribution:"), fmt)
    log.info("%s %s" % (core.distro_name, core.distro_version), fmt)

    log.info(utils.bold("\nHPOJ running?", fmt), fmt)
    hpoj_present = dcheck.check_hpoj()

    if hpoj_present:
        log.error("Yes, HPOJ is running. HPLIP is not compatible with HPOJ. To run HPLIP, please remove HPOJ.", fmt)
        num_errors += 1
    else:
        log.info("No, HPOJ is not running (OK).", fmt)


    log.info("", fmt)
    log.info(utils.bold("Checking Python version...", fmt), fmt)
    ver = sys.version_info
    log.debug("sys.version_info = %s" % repr(ver))
    ver_maj = ver[0]
    ver_min = ver[1]
    ver_pat = ver[2]

    if ver_maj == 2:
        if ver_min >= 1:
            log.info("OK, version %d.%d.%d installed" % ver[:3], fmt)
        else:
            log.error("Version %d.%d.%d installed. Please update to Python >= 2.1" % ver[:3], fmt)
            sys.exit(1)


    log.info("", fmt)
    log.info(utils.bold("Checking PyQt version...", fmt), fmt)

    # PyQt
    try:
        import qt
    except ImportError:
        num_errors += 1
        log.error("Not found!", fmt)
    else:
        # check version of Qt
        qtMajor = int(qt.qVersion().split('.')[0])

        if qtMajor < MINIMUM_QT_MAJOR_VER:
            log.error("Incorrect version of Qt installed. Ver. 3.0.0 or greater required.", fmt)
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
                log.error("A non-stable snapshot version of PyQt is installed (%s)." % pyqtVersion, fmt)
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
                    log.error("HPLIP may not function properly with the version of PyQt that is installed (%d.%d.%d)." % (maj_ver, min_ver, pat_ver), fmt)
                    log.error("Ver. %d.%d or greater required." % (MINIMUM_PYQT_MAJOR_VER, MINIMUM_PYQT_MINOR_VER), fmt)
                else:
                    log.info("OK, version %d.%d installed." % (maj_ver, min_ver), fmt)


    log.info("", fmt)
    log.info(utils.bold("Checking SIP version...", fmt), fmt)

    sip_ver = None
    try:
        import pyqtconfig
    except ImportError:
        pass
    else:
        sip_ver = pyqtconfig.Configuration().sip_version_str 

    if sip_ver is not None:
        log.info("OK, Version %s installed" % sip_ver, fmt)
    else:
        num_errors += 1
        log.error("SIP not installed or version not found.", fmt)

    log.info("", fmt)
    log.info(utils.bold("Checking for CUPS...", fmt), fmt)

    status, output = utils.run('lpstat -r')
    if status == 0:
        log.info("Status: %s" % output.strip(), fmt)
    else:
        log.error("Status: (Not available. CUPS may not be installed or not running.)", fmt)
        num_errors += 1

    status, output = utils.run('cups-config --version')
    if status == 0:
        log.info("Version: %s" % output.strip(), fmt)
    else:
        log.error("Version: (Not available. CUPS may not be installed or not running.)", fmt)
        num_errors += 1

    header("DEPENDENCIES")

    dcheck.update_ld_output()
    log.info("")

    dd = dependencies.keys()
    dd.sort()
    for d in dd:
        log.debug("***")

        log.info(utils.bold("Checking for dependency %s..." % dependencies[d][1], fmt), fmt)

        #if 0:
        if dependencies[d][3]():
            log.info("OK, found.", fmt)
        else:
            num_errors += 1

            if dependencies[d][0]:
                log.error("NOT FOUND! This is a REQUIRED dependency. Please make sure that this dependency is installed before installing or running HPLIP.", fmt)
            else:
                log.warn("NOT FOUND! This is an OPTIONAL dependency. Some HPLIP functionality may not function properly.", fmt)

            if core.distro_supported():
                packages_to_install, command = core.get_ver_data('dependency_cmds', {}).get(d, ('', ''))

                commands_to_run = []

                if packages_to_install:
                    package_mgr_cmd = core.get_distro_data('package_mgr_cmd')

                    if package_mgr_cmd:
                        commands_to_run.append(utils.cat(package_mgr_cmd))

                if command:
                    if type(command) == type(''):
                        commands_to_run.append(command)
                    else:
                        commands_to_run.extend(command)

                overall_commands_to_run.extend(commands_to_run)
                
                if len(commands_to_run) == 1:
                    log.info("To install this dependency, execute this command:", fmt)
                    log.info(commands_to_run[0])

                elif len(commands_to_run) > 1:
                    log.info("To install this dependency, execute these commands:", fmt)
                    for c in commands_to_run:
                        log.info(c)


        log.info("", fmt)

    if not pre:
        header("HPLIP INSTALLATION")

        scanning_enabled = utils.to_bool(sys_cfg.configure.get("scanner-build", False))

        log.info("", fmt)
        log.info(utils.bold("Currently installed HPLIP version...", fmt), fmt)
        v = sys_cfg.hplip.version
        home = sys_cfg.dirs.home

        if v:
            log.info("HPLIP %s currently installed in '%s'." % (v, home), fmt)

            log.info("", fmt)
            log.info(utils.bold("Current contents of '/etc/hp/hplip.conf' file:", fmt), fmt)
            output = file('/etc/hp/hplip.conf', 'r').read()
            log.info(output, fmt)

        else:
            log.info("Not found.")  

        header("INSTALLED PRINTERS")

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
                try:
                    back_end, is_hp, bus, model, serial, dev_file, host, port = \
                        parseDeviceURI(p[1])
                except Error:
                    back_end, is_hp, bus, model, serial, dev_file, host, port = \
                        '', False, '', '', '', '', '', 1

                log.info(utils.bold(p[0], fmt), fmt)
                log.info(utils.bold('-'*len(p[0]), fmt), fmt)

                x = "Unknown"
                if back_end == 'hpfax':
                    x = "Fax"
                elif back_end == 'hp':
                    x = "Printer"

                log.info("Type: %s" % x, fmt)

                if is_hp:
                    x = 'Yes, using the %s: CUPS backend.' % back_end
                else:
                    x = 'No, not using the hp: or hpfax: CUPS backend.'
                    non_hp = True

                log.info("Installed in HPLIP?: %s" % x, fmt)
                log.info("Device URI: %s" % p[1], fmt)

                ppd = os.path.join('/etc/cups/ppd', p[0] + '.ppd')

                if os.path.exists(ppd):
                    log.info("PPD: %s" % ppd)
                    nickname_pat = re.compile(r'''\*NickName:\s*\"(.*)"''', re.MULTILINE)

                    f = file(ppd, 'r').read(4096)

                    try:
                        desc = nickname_pat.search(f).group(1)
                    except AttributeError:
                        desc = ''

                    log.info("PPD Description: %s" % desc, fmt)

                    status, output = utils.run('lpstat -p%s' % p[0])
                    log.info("Printer status: %s" % output.replace("\n", ""), fmt)

                    if back_end == 'hpfax' and desc != 'HP Fax':
                        num_errors += 1
                        log.error("Incorrect PPD file for fax queue '%s'. Fax queues must use 'HP-Fax-hplip.ppd'." % p[0], fmt)

                    elif back_end == 'hp' and desc == 'HP Fax':
                        num_errors += 1
                        log.error("Incorrect PPD file for a print queue '%s'. Print queues must not use 'HP-Fax-hplip.ppd'." % p[0], fmt)

                    elif back_end not in ('hp', 'hpfax'):
                        log.error("Printer is not HPLIP installed. Printers must use the hp: or hpfax: CUPS backend to function in HPLIP.", fmt)
                        num_errors += 1

                log.info("")

        else:
            log.warn("No queues found.", fmt)

        if scanning_enabled:
            header("SANE CONFIGURATION")
            log.info(utils.bold("'hpaio' in '/etc/sane.d/dll.conf'...", fmt), fmt)
            try:
                f = file('/etc/sane.d/dll.conf', 'r')
            except IOError:
                log.error("'/etc/sane.d/dll.conf' not found. Is SANE installed?", fmt)
                num_errors += 1
            else:
                found = False
                for line in f:
                    if 'hpaio' in line:
                        found = True

                if found:
                    log.info("OK, found. SANE backend 'hpaio' is properly set up.", fmt)
                else:
                    num_errors += 1
                    log.error("Not found. SANE backend 'hpaio' NOT properly setup (needs to be added to /etc/sane.d/dll.conf).", fmt)

                log.info("", fmt)
                log.info(utils.bold("Checking output of 'scanimage -L'...", fmt), fmt)
                if utils.which('scanimage'):
                    status, output = utils.run("scanimage -L")
                    log.info(output)
                else:
                    log.error("scanimage not found.", fmt)

        header("PYTHON EXTENSIONS")

        log.info(utils.bold("Checking 'cupsext' CUPS extension...", fmt), fmt)
        try:
            import cupsext
        except ImportError:
            num_errors += 1
            log.error("NOT FOUND! Please reinstall HPLIP and check for the proper installation of cupsext.", fmt)
        else:
            log.info("OK, found.", fmt)

        log.info("")
        log.info(utils.bold("Checking 'pcardext' Photocard extension...", fmt), fmt)
        try:
            import pcardext
        except ImportError:
            num_errors += 1
            log.error("NOT FOUND! Please reinstall HPLIP and check for the proper installation of pcardext.", fmt)
        else:
            log.info("OK, found.", fmt)

        log.info("")
        log.info(utils.bold("Checking 'hpmudext' I/O extension...", fmt), fmt)
        try:
            import hpmudext
            hpmudext_avail = True
        except ImportError:
            hpmudext_avail = False
            num_errors += 1
            log.error("NOT FOUND! Please reinstall HPLIP and check for the proper installation of hpmudext.", fmt)
        else:
            log.info("OK, found.", fmt)        

        if scanning_enabled:
            log.info("")
            log.info(utils.bold("Checking 'scanext' SANE scanning extension...", fmt), fmt)
            try:
                import scanext
            except ImportError:
                num_errors += 1
                log.error("NOT FOUND! Please reinstall HPLIP and check for the proper installation of scanext.", fmt)
            else:
                log.info("OK, found.", fmt)        

                log.info("", fmt)

        header("USB I/O SETUP")

        log.info(utils.bold("Checking proper HPLIP I/O setup (USB I/O only)...", fmt), fmt)

        mode_pat = re.compile("""MODE\s*=\s*\"(\d\d\d\d)\"""",  re.IGNORECASE)

        found = False
        for f1 in utils.walkFiles('/etc/udev/rules.d', recurse=True, abs_paths=True, return_folders=False, pattern='*.rules'):
            f3 = file(f1, 'r').readlines()
            for f2 in f3:
                s = mode_pat.search(f2)
                if "usb_device" in f2 and s is not None:
                    log.debug("Found udev usb_device MODE: %s in file %s" % (f2.strip(), os.path.basename(f1)))
                    found = True
                    break

            if found:
                break

        if found:
            mode = int(s.group(1), 8)

            if mode & 0660 == 0660:
                log.info('udev "usb_device" access mode: 0%o (OK)' % mode)
            else:
                log.error('udev "usb_device" access mode is INCORRECT: 0%o (it must be 066x)' % mode)
                num_errors += 1

        import pwd
        import grp

        if hpmudext_avail:
            lsusb = utils.which('lsusb')
            if lsusb:
                log.info("", fmt)
                log.info(utils.bold("Checking for permissions of USB attached printers...", fmt), fmt)
                lsusb = os.path.join(lsusb, 'lsusb')
                status, output = utils.run("%s -d03f0:" % lsusb)

                lsusb_pat = re.compile("""^Bus\s([0-9a-fA-F]{3,3})\sDevice\s([0-9a-fA-F]{3,3}):\sID\s([0-9a-fA-F]{4,4}):([0-9a-fA-F]{4,4})(.*)""", re.IGNORECASE)
                log.debug(output)

                for o in output.splitlines():
                    ok = True
                    match = lsusb_pat.search(o)

                    if match is not None:
                        bus, device, vid, pid, mfg = match.groups()
                        log.info("HP Device 0x%x at %s:%s: " % (int(pid, 16), bus, device), fmt)
                        result_code, deviceuri = hpmudext.make_usb_uri(bus, device)

                        if result_code == hpmudext.HPMUD_R_OK:
                            log.info("    Device URI: %s" %  deviceuri, fmt)
                        else:
                            log.warn("    Device URI: (Makeuri FAILED)", fmt)

                        devnode = os.path.join("/", "dev", "bus", "usb", bus, device)

                        if os.path.exists(devnode):
                            log.info("    Device node: %s" % devnode, fmt)

                            st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, \
                                st_size, st_atime, st_mtime, st_ctime = \
                                os.stat(devnode)

                            log.info("    Mode: 0%o" % (st_mode & 0777), fmt)

                            if st_mode & 0660 != 0660:
                                log.error("INCORRECT mode. Mode must be 066x", fmt)
                                ok = False
                                num_errors += 1

                            user = pwd.getpwuid(st_uid)[0]
                            group = grp.getgrgid(st_gid)[0]
                            log.info("    UID: %d (%s)" % (st_uid, user), fmt)
                            log.info("    GID: %d (%s)" % (st_gid, group), fmt)

                            if group != 'lp':
                                log.error("INCORRECT group. Group must be 'lp'", fmt)
                                ok = False
                                num_errors += 1

                        else:
                            log.warn("    Device node NOT FOUND: %s" % devnode, fmt) 
                            ok = False
                            num_errors += 1

                    if ok:
                        log.info("    Device group and mode appear correct.", fmt)
                    else:
                        log.error("    Device group and mode are NOT properly setup.", fmt)

        all_groups = grp.getgrall()
        for g in all_groups:
            name, pw, gid, members = g
            log.debug("group=%s gid=%d" % (name, gid))

        log.info("", fmt)
        for p in pwd.getpwall():
            user, pw, uid, gid, name, home, ci = p
            log.debug("user=%s uid=%d gid=%d" % (user, uid, gid))
            if 1000 <= uid <= 10000:
                log.info(utils.bold("Is user '%s' a member of the 'lp' group?" % user, fmt), fmt)
                grps = []
                for g in all_groups:
                    grp_name, pw, gid, members = g
                    if user in members:
                        grps.append(grp_name)
                log.debug("Member of groups: %s" % ', '.join(grps), fmt)

                if 'lp' in grps:
                    log.info("Yes (OK)", fmt)
                else:
                    log.warn("NO (HPLIP USB I/O users must be member of 'lp' group)", fmt)
                    log.note("This may not be a problem if this user will not be printing using HPLIP USB I/O.", fmt)
                    num_errors += 1

                log.info("", fmt)

    header("SUMMARY")

    if num_errors:
        if num_errors == 1:
            log.error("1 error or warning.", fmt)
        else:
            log.error("%d errors and/or warnings." % num_errors, fmt)
            
        if overall_commands_to_run:
            log.info("", fmt)
            log.info(utils.bold("Summary of needed commands to run to satisfy missing dependencies:"), fmt)
            for c in overall_commands_to_run:
                log.info(c)

        log.info("", fmt)
        log.info("Please refer to the installation instructions at:", fmt)
        log.info("http://hplip.sourceforge.net/install/index.html\n", fmt)

    else:
        log.info(utils.green("No errors or warnings.", fmt), fmt)

except KeyboardInterrupt:
    log.warn("Aborted", fmt)
