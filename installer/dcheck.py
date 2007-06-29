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

import os, os.path, re, sys

from base.g import *
from base import utils

ver_pat = re.compile("""(\d+.\d+)""", re.IGNORECASE)

ld_output = ''
ps_output = ''
mod_output = ''

# 
# Generic fucntions
#

def update_ld_output():
    # For library checks
    global ld_output
    status, ld_output = utils.run('%s -p' % os.path.join(utils.which('ldconfig'), 'ldconfig'), log_output=False)

    if status != 0:
        log.debug("ldconfig failed.")

def check_tool(cmd, min_ver=0.0):
    log.debug("Checking: %s (min ver=%f)" % (cmd, min_ver))
    status, output = utils.run(cmd)

    if status != 0:
        log.debug("Not found!")
        return False
    else:
        if min_ver:
            try:
                line = output.splitlines()[0]
            except IndexError:
                line = ''
            log.debug(line)
            match_obj = ver_pat.search(line)
            try:
                ver = match_obj.group(1)
            except AttributeError:
                ver = ''

            try:
                v_f = float(ver)
            except ValueError:
                return False
            else:
                log.debug("Ver=%f Min ver=%f" % (v_f, min_ver))

                if v_f < min_ver:
                    log.debug("Found, but newer version required.")

                return v_f >= min_ver
        else:
            log.debug("Found.")
            return True


def check_lib(lib, min_ver=0):
    log.debug("Checking for library '%s'..." % lib)

    if ld_output.find(lib) >= 0:
        log.debug("Found.")

        #if min_ver:
        #    pass
        #else:
        return True
    else:
        log.debug("Not found.")
        return False

def check_file(f, dir="/usr/include"):
    log.debug("Searching for file '%s' under '%s'..." % (f, dir))
    for w in utils.walkFiles(dir, recurse=True, abs_paths=True, return_folders=False, pattern=f):
        log.debug("File found at '%s'" % w)
        return True

    log.debug("File not found.")
    return False

def check_lsb():
    return check_file("install_initd", '/usr/lib/lsb') or \
           check_file('install_initd', '/usr/sbin') or \
           check_file('install_initd', '/usr/bin')

def locate_files(f, dir):
    log.debug("Searching for file(s) '%s' under '%s'..." % (f, dir))
    found = []
    for w in utils.walkFiles(dir, recurse=True, abs_paths=True, return_folders=False, pattern=f):
        log.debug(w)
        found.append(w)

    if found:
        log.debug("Found files: %s" % found)
    else:
        log.debug("No files not found.")

    return found

def check_file_contains(f, s):
    log.debug("Checking file '%s' for contents '%s'..." % (f, s))
    try:
        if os.path.exists(f):
            for a in file(f, 'r'):
                update_spinner()

                if s in a:
                    log.debug("'%s' found in file '%s'." % (s.replace('\n', ''), f))
                    return True

        log.debug("Contents not found.")
        return False

    finally:
        cleanup_spinner()

def check_ps(process_list):
    global ps_output
    
    log.debug("Searching any process(es) '%s' in 'ps' output..." % process_list)
    
    if not ps_output:
        status, ps_output = utils.run('ps -e -a -o pid,cmd', log_output=False)

    try:
        for a in ps_output.splitlines():
            update_spinner()

            for p in process_list:
                if p in a:
                    log.debug("'%s' found." % a.replace('\n', ''))
                    return True

        log.debug("Process not found.")
        return False

    finally:
        cleanup_spinner()
        
def get_ps_pid(process):
    global ps_output
    
    log.debug("Searching for the PID for process '%s' in 'ps' output..." % process)
    
    if not ps_output:
        status, ps_output = utils.run('ps -e -a -o pid,cmd', log_output=False)
    
    try:
        for a in ps_output.splitlines():
            update_spinner()
            try:
                pid, command = a.strip().split(' ', 1)
            except ValueError:
                continue
            
            if process in command:
                try:
                    pid = int(pid)
                except ValueError:
                    continue
                    
                log.debug("'%s' found (pid=%d)." % (command, pid))
                return pid

        log.debug("Process not found.")
        return 0

    finally:
        cleanup_spinner()        
        
        
def check_lsmod(module):
    global mod_output
    
    if not mod_output:
        lsmod = utils.which('lsmod')
        status, mod_output = utils.run(os.path.join(lsmod, 'lsmod'), log_output=False)
        
    return mod_output.find(module) >= 0

#
# Specific functions    
#

def check_python2x():
    py_ver = sys.version_info
    py_major_ver, py_minor_ver = py_ver[:2]
    log.debug("Python ver=%d.%d" % (py_major_ver, py_minor_ver))
    return py_major_ver >= 2

def check_gcc():
    return check_tool('gcc --version', 0) and check_tool('g++ --version', 0)

def check_make():
    return check_tool('make --version', 3.0)

def check_libusb():
    if not check_lib('libusb'):
        return False

    for f in locate_files('usb.h', '/usr/include'):
        if check_file_contains(f, 'usb_init(void)'):
            return True

    return False

def check_libjpeg():
    return check_lib("libjpeg") and check_file("jpeglib.h")

def check_libcrypto():
    return check_lib("libcrypto") and check_file("crypto.h")

def check_libpthread():
    return check_lib("libpthread") and check_file("pthread.h")

def check_libnetsnmp():
    return check_lib("libnetsnmp") and check_file("net-snmp-config.h")

def check_reportlab():
    try:
        log.debug("Trying to import 'reportlab'...")
        import reportlab
        log.debug("Success.")
        return True
    except ImportError:
        log.debug("Failed.")
        return False

def check_python23():
    py_ver = sys.version_info
    py_major_ver, py_minor_ver = py_ver[:2]
    log.debug("Python ver=%d.%d" % (py_major_ver, py_minor_ver))
    return py_major_ver >= 2 and py_minor_ver >= 3

def check_sane():
    return check_lib('libsane')
    
def check_sane_devel():
    return check_file("sane.h")

def check_xsane():
    if os.getenv('DISPLAY'):
        return check_tool('xsane --version', 0.9) # will fail if X not running...
    else:
        return bool(utils.which("xsane")) # ...so just see if it installed somewhere

def check_scanimage():
    return check_tool('scanimage --version', 1.0)

def check_ppdev():
    return check_lsmod('ppdev')

def check_gs():
    return check_tool('gs -v', 7.05)

def check_pyqt():
    try:
        import qt
        pyqtVersion = None
        try:
            pyqtVersion = qt.PYQT_VERSION_STR
            log.debug("PYQT_VERSION_STR = %s" % pyqtVersion)
        except:
            try:
                pyqtVersion = qt.PYQT_VERSION
                log.debug("PYQT_VERSION = %s" % pyqtVersion)
            except:
                pass

        if pyqtVersion is not None:
            while pyqtVersion.count('.') < 2:
                pyqtVersion += '.0'

            (maj_ver, min_ver, pat_ver) = pyqtVersion.split('.')

            if pyqtVersion.find('snapshot') >= 0:
                log.debug("A non-stable snapshot version of PyQt is installed.")
                pass
            else:    
                try:
                    maj_ver = int(maj_ver)
                    min_ver = int(min_ver)
                    pat_ver = int(pat_ver)
                except ValueError:
                    maj_ver, min_ver, pat_ver = 0, 0, 0
                else:
                    log.debug("Version %d.%d.%d installed." % (maj_ver, min_ver, pat_ver))

                if maj_ver < MINIMUM_PYQT_MAJOR_VER or \
                    (maj_ver == MINIMUM_PYQT_MAJOR_VER and min_ver < MINIMUM_PYQT_MINOR_VER):
                    log.debug("HPLIP may not function properly with the version of PyQt that is installed (%d.%d.%d)." % (maj_ver, min_ver, pat_ver))
                    log.debug("Incorrect version of PyQt installed. Ver. %d.%d or greater required." % (MINIMUM_PYQT_MAJOR_VER, MINIMUM_PYQT_MINOR_VER))
                    return True
                else:
                    return True

    except ImportError:
         return False

def check_python_devel():
    return check_file('Python.h')

def check_cups_devel():
    return check_file('cups.h') and bool(utils.which('lpr'))

def check_cups():
    status, output = utils.run('lpstat -r')

    if status > 0:
        log.debug("CUPS is not running.")
        return False
    else:
        log.debug("CUPS is running.")
        return True

def check_hpoj():
    log.debug("Checking for 'HPOJ'...")
    return check_ps(['ptal-mlcd', 'ptal-printd', 'ptal-photod']) or \
        bool(utils.which("ptal-init"))

def check_hplip():
    log.debug("Checking for HPLIP...")
    return check_ps(['hpiod', 'hpssd']) and locate_files('hplip.conf', '/etc/hp')
    
def check_hpssd():
    log.debug("Checking for hpssd...")
    return check_ps(['hpssd'])

def check_libtool():
    log.debug("Checking for libtool...")
    return check_tool('libtool --version')

def check_pil():
    log.debug("Checking for PIL...")
    try:
        import Image
        return True
    except ImportError:
        return False
        
        
