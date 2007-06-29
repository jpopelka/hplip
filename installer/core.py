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

# Std Lib
import sys, os, os.path, getopt, re, socket, gzip, time

# Local
from base.g import *
from base.codes import *
from base import utils, msg, service
from distros import *
import dcheck


# components
# 'name': ('description', [<option list>])
components = {
    'hplip': ("HP Linux Imaging and Printing System", ['base', 'network', 'gui', 'fax', 'scan', 'parallel', 'docs']),
    'hpijs': ("HP IJS Printer Driver", ['hpijs', 'hpijs-cups'])
}

selected_component = 'hplip'

# options
# name: (<required>, "<display_name>", [<dependency list>]), ...
options = { 
    'base':     (True,  'Required HPLIP base components', []), # HPLIP
    'network' : (False, 'Network/JetDirect I/O', []),
    'gui' :     (False, 'Graphical User Interfaces (GUIs)', []),
    'fax' :     (False, 'PC Send Fax', []),
    'scan':     (False, 'Scanning', []),
    'parallel': (False, 'Parallel I/O (LPT)', []),
    'docs':     (False, 'HPLIP documentation (HTML)', []),

    # hpijs only
    'hpijs':       (True,  'Required HPIJS base components', []),
    'hpijs-cups' : (False, 'CUPS support for HPIJS', []),
}

# holds whether the user has selected (turned on each option)
# initial values are defaults (for GUI only)
selected_options = {
    'base':        True,
    'network':     True,
    'gui':         True,
    'fax':         True,
    'scan':        True,
    'parallel':    False,
    'docs':        True,

    # hpijs only
    'hpijs':       True,
    'hpijs-cups' : True,
}

# dependencies
# 'name': (<required for option>, [<option list>], <display_name>, <check_func>), ...
# Note: any change to the list of dependencies must be reflected in base/distros.py
dependencies = {
    'libjpeg':          (True,  ['base', 'hpijs'], "libjpeg - JPEG library", dcheck.check_libjpeg),
    'libtool':          (True,  ['base'], "libtool - Library building support services", dcheck.check_libtool),
    'cups' :            (True,  ['base', 'hpijs-cups'], 'cups - Common Unix Printing System', dcheck.check_cups), 
    'cups-devel':       (True,  ['base'], 'cups-devel- Common Unix Printing System development files', dcheck.check_cups_devel),
    'gcc' :             (True,  ['base', 'hpijs'], 'gcc - GNU Project C and C++ Compiler', dcheck.check_gcc),
    'make' :            (True,  ['base', 'hpijs'], "make - GNU make utility to maintain groups of programs", dcheck.check_make),
    'python-devel' :    (True,  ['base'], "python-devel - Python development files", dcheck.check_python_devel),
    'libpthread' :      (True,  ['base'], "libpthread - POSIX threads library", dcheck.check_libpthread),
    'python2x':         (True,  ['base'], "Python 2.2 or greater - Python programming language", dcheck.check_python2x),
    'gs':               (True,  ['base', 'hpijs'], "GhostScript - PostScript and PDF language interpreter and previewer", dcheck.check_gs),
    'libusb':           (True,  ['base'], "libusb - USB library", dcheck.check_libusb),
    
    'sane':             (True,  ['scan'], "SANE - Scanning library", dcheck.check_sane),
    'sane-devel' :      (True,  ['scan'], "SANE - Scanning library development files", dcheck.check_sane_devel),
    'xsane':            (False, ['scan'], "xsane - Graphical scanner frontend for SANE", dcheck.check_xsane),
    'scanimage':        (False, ['scan'], "scanimage - Shell scanning program", dcheck.check_scanimage),
    'pil':              (False, ['scan'], "PIL - Python Imaging Library (required for commandline scanning with hp-scan)", dcheck.check_pil), 

    'reportlab':        (False, ['fax'], "Reportlab - PDF library for Python", dcheck.check_reportlab), 
    'python23':         (True,  ['fax'], "Python 2.3 or greater - Required for fax functionality", dcheck.check_python23),

    'ppdev':            (True,  ['parallel'], "ppdev - Parallel port support kernel module.", dcheck.check_ppdev),

    'pyqt':             (True,  ['gui'], "PyQt - Qt interface for Python", dcheck.check_pyqt),

    'libnetsnmp-devel': (True,  ['network'], "libnetsnmp-devel - SNMP networking library development files", dcheck.check_libnetsnmp),
    'libcrypto':        (True,  ['network'], "libcrypto - OpenSSL cryptographic library", dcheck.check_libcrypto),

}


def check_pkg_mgr(): # modified from EasyUbuntu
    """
    Check if any pkg mgr processes are running
    """
    log.debug("Searching for '%s' in 'ps' output..." % package_mgrs)

    p = os.popen("ps -U root -o comm") # TODO: Doesn't work on Mac OS X
    pslist = p.readlines()
    p.close()

    for process in pslist:
        for p in package_mgrs:
            if p in process:
                return p
    return ''

def getHPLIPVersion():
    version_description, version_public, version_internal = '', '', ''
    ac_init_pat = re.compile(r"""AC_INIT\(\[(.*?)\], *\[(.*?)\], *\[(.*?)\], *\[(.*?)\] *\)""", re.IGNORECASE)
    
    try:
        config_in = file('./configure.in', 'r')
    except IOError:
        version_description, version_public, version_internal = \
            '', sys_cfg.configure['internal-tag'], sys_cfg.hplip.version
    else:
        for c in config_in:
            if c.startswith("AC_INIT"):
                match_obj = ac_init_pat.search(c)
                version_description = match_obj.group(1)
                version_public = match_obj.group(2)
                version_internal = match_obj.group(3)
                name = match_obj.group(4)
                break
        
        config_in.close()
        
        if name != 'hplip':
            log.error("Invalid archive!")
    
    return version_description, version_public, version_internal

    
def configure(enable_ppds=True, hpijs_build=False, ppd_dir=None):
    configure_cmd = './configure'

    if selected_options['network']:
        configure_cmd += ' --enable-network-build'
    else:
        configure_cmd += ' --disable-network-build'

    if selected_options['parallel']:
        configure_cmd += ' --enable-pp-build'
    else:
        configure_cmd += ' --disable-pp-build'

    if selected_options['fax']:
        configure_cmd += ' --enable-fax-build'
    else:
        configure_cmd += ' --disable-fax-build'

    if selected_options['gui']:
        configure_cmd += ' --enable-gui-build'
    else:
        configure_cmd += ' --disable-gui-build'

    if selected_options['scan']:
        configure_cmd += ' --enable-scan-build'
    else:
        configure_cmd += ' --disable-scan-build'

    if selected_options['docs']:
        configure_cmd += ' --enable-doc-build'
    else:
        configure_cmd += ' --disable-doc-build'
        
    if enable_ppds:
        configure_cmd += ' --enable-foomatic-ppd-install --disable-foomatic-xml-install'
    else:
        configure_cmd += ' --disable-foomatic-ppd-install --enable-foomatic-xml-install'
    
    if hpijs_build:
        configure_cmd += ' --enable-hpijs-only-build'
    else:
        configure_cmd += ' --disable-hpijs-only-build'
    
    if bitness == 64:
        configure_cmd += ' --libdir=/usr/lib64'
        
    configure_cmd += ' --prefix=%s' % install_location
    
    if cups11:
        configure_cmd += ' --enable-cups11-build'
        
    if ppd_dir is not None:
        configure_cmd += ' --with-hpppddir=%s' % ppd_dir
    
    return configure_cmd


def restart_cups():
    if os.path.exists('/etc/init.d/cups'):
        return su_sudo() % '/etc/init.d/cups restart'

    elif os.path.exists('/etc/init.d/cupsys'):
        return su_sudo() % '/etc/init.d/cupsys restart'

    else:
        return su_sudo() % 'killall -HUP cupsd'

def stop_hplip():
    return su_sudo() % "/etc/init.d/hplip stop"

def su_sudo():
    if os.geteuid() == 0:
        return '%s'
    else:
        try:
            cmd = distros[distro_name]['su_sudo']
        except KeyError:
            cmd = 'su'

        if cmd == 'su':
            return 'su -c "%s"'
        else:
            return 'sudo %s'

def build_cmds(enable_ppds=True, hpijs_build=False, cups11=False, ppd_dir=None):
    return [configure(enable_ppds, hpijs_build, ppd_dir), 
            'make clean', 
            'make', 
            su_sudo() % 'make install']

version_description, version_public, version_internal = '', '', ''
hpijs_version_description, hpijs_version = '', ''
bitness = 32
endian = utils.LITTLE_ENDIAN
distro, distro_name, distro_version = 0, '', '0.0'
distro_version_supported = False
install_location = '/usr'
hpoj_present = False
hplip_present = False
have_dependencies = {}
cups11 = False

def ppd_install_flag(): # True=install PPDs, False=install XML
    if cups11:
        return True
    else:
        return get_distro_ver_data('ppd_install', 'ppd') == 'ppd'
                
def get_distro_ver_data(key, default=None):
    try:
        return distros[distro_name]['versions'][distro_version].get(key, None) or distros[distro_name].get(key, None) or default
    except KeyError:
        return default
    
    return value
    
def get_distro_data(key, default=None):
    try:
        return distros[distro_name].get(key, None) or default
    except KeyError:
        return default
        
def get_ver_data(key, default=None):
    try:
        return distros[distro_name]['versions'][distro_version].get(key, None) or default
    except KeyError:
        return default
    
    return value

def distro_known():
    return distro != distros.DISTRO_UNKNOWN and distro_version != '0.0'
    
def distro_supported():
    return distro != DISTRO_UNKNOWN and distro_version != '0.0' and get_ver_data('supported', False)


def init(callback=None):
    if callback is not None:
        callback("Initializing...\n")

    global version_description, version_public, version_internal
    global bitness, endian
    global distro, distro_name, distro_version
    global distro_version_supported
    global install_location
    global hpoj_present, hplip_present
    global have_dependencies
    global cups11

    version_description, version_public, version_internal = getHPLIPVersion()
    log.debug("HPLIP Description=%s Public version=%s Internal version = %s"  % 
        (version_description, version_public, version_internal))

    for opt in options:
        update_spinner()
        for d in dependencies:
            if opt in dependencies[d][1]:
                options[opt][2].append(d)

    cleanup_spinner()

    # have_dependencies
    # is each dependency satisfied?
    # start with each one 'No'
    for d in dependencies:
        have_dependencies[d] = False

    dcheck.update_ld_output()

    if callback is not None:
        callback("Checking dependencies...\n")

    for d in dependencies:
        log.debug("***")

        update_spinner()

        log.debug("Checking for dependency '%s'...\n" % d)

        if callback is not None:
            callback("Checking for dependency '%s'...\n" % d)

        have_dependencies[d] = dependencies[d][3]()
        log.debug("have %s = %d" % (d, have_dependencies[d]))

    cleanup_spinner()

    log.debug("******")
    for d in dependencies:
        log.debug("have %s = %d" % (d, have_dependencies[d]))

        if callback is not None:
            callback("Dependency '%s' = %d.\n" % (d, have_dependencies[d]))

    log.debug("******")

    log.debug("Running package manager: %s" % check_pkg_mgr())

    bitness = utils.getBitness()
    log.debug("Bitness = %d" % bitness)

    endian = utils.getEndian()
    log.debug("Endian = %d" % endian)

    if callback is not None:
        callback("Checking distribution...\n")

    distro, distro_version = getDistro()
    distro_name = distros_index[distro]

    try:
        distro_version_supported = distros[distro_name]['versions'][distro_version]['supported']
    except KeyError:
        distro_version_supported = False

    log.debug("Distro = %s Distro Name = %s Display Name= %s Version = %s Supported = %s" % 
        (distro, distro_name, distros[distro_name]['display_name'], distro_version, distro_version_supported))

    if callback is not None:
        callback("Checking for HPOJ and HPLIP...\n")

    hpoj_present = dcheck.check_hpoj()
    log.debug("HPOJ = %s" % hpoj_present)

    hplip_present = dcheck.check_hplip()
    log.debug("HPLIP (prev install) = %s" % hplip_present)
    
    status, output = utils.run('cups-config --version', log_output=False)
    output = output.strip()
    log.debug("CUPS version = %s" % output)
    
    cups11 = output.startswith('1.1')
    log.debug("Is CUPS 1.1.x? %s" % cups11)

    # Record the installation time/date and version.
    # Also has the effect of making the .hplip.conf file user r/w
    # on the 1st run so that running hp-setup as root doesn't lock
    # the user out of owning the file
    user_cfg.installation.date_time = time.strftime("%x %H:%M:%S", time.localtime())
    user_cfg.installation.version = version_public
    
    
    
