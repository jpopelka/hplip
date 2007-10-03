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
import sys, os, os.path, re, time
import cStringIO, grp, pwd
import urllib, sha, tarfile

# Local
from base.g import *
from base.codes import *
from base import utils, pexpect
from dcheck import *

DISTRO_UNKNOWN = 0
DISTRO_VER_UNKNOWN = '0.0'

MODE_INSTALLER = 0 # hplip-install
MODE_CHECK = 1 # hp-check
MODE_CREATE_DOCS = 2 # create_docs

TYPE_STRING=1
TYPE_LIST=2
TYPE_BOOL=3
TYPE_INT = 4

PING_TARGET = "www.google.com"
HTTP_GET_TARGET = "http://www.google.com"

try:
    from functools import update_wrapper
except ImportError: # using Python version < 2.5
    def trace(f):
        def newf(*args, **kw):
           print "TRACE: func=%s(), args=%s, kwargs=%s" % (f.__name__, args, kw)
           return f(*args, **kw)
        newf.__name__ = f.__name__
        newf.__dict__.update(f.__dict__)
        newf.__doc__ = f.__doc__
        newf.__module__ = f.__module__
        return newf
else: # using Python 2.5+
    def trace(f):
        def newf(*args, **kw):
            log.debug("TRACE: func=%s(), args=%s, kwargs=%s" % (f.__name__, args, kw))
            return f(*args, **kw)
        return update_wrapper(newf, f)


class CoreInstall(object):
    def __init__(self, mode=MODE_INSTALLER, ui_mode=INTERACTIVE_MODE):
        os.umask(0022)
        self.mode = mode
        self.ui_mode = ui_mode
        self.password = ''
        self.version_description, self.version_public, self.version_internal = '', '', ''
        self.bitness = 32
        self.endian = utils.LITTLE_ENDIAN
        self.distro, self.distro_name, self.distro_version = DISTRO_UNKNOWN, '', DISTRO_VER_UNKNOWN
        self.distro_version_supported = False
        self.install_location = '/usr'
        self.hpoj_present = False
        self.hplip_present = False
        self.have_dependencies = {}
        self.cups11 = False
        self.hpijs_build = False
        self.ppd_dir = None
        self.distros = {}
        self.plugin_path = os.path.join(prop.home_dir, "data", "plugins")
        self.logoff_required = False
        self.restart_required = False

        self.FIELD_TYPES = {
            'distros' : TYPE_LIST,
            'index' : TYPE_INT,
            'versions' : TYPE_LIST,
            'display_name' : TYPE_STRING,
            'alt_names': TYPE_LIST,
            'display': TYPE_BOOL,
            'notes': TYPE_STRING,
            'package_mgrs': TYPE_LIST,
            'package_mgr_cmd':TYPE_STRING,
            'pre_install_cmd': TYPE_LIST,
            'pre_depend_cmd': TYPE_LIST,
            'post_depend_cmd': TYPE_LIST,
            'hpoj_remove_cmd': TYPE_STRING,
            'hplip_remove_cmd': TYPE_STRING,
            'su_sudo': TYPE_STRING,
            'ppd_install': TYPE_STRING,
            'udev_mode_fix': TYPE_BOOL,
            'ppd_dir': TYPE_STRING,
            'fix_ppd_symlink': TYPE_BOOL,
            'code_name': TYPE_STRING,
            'supported': TYPE_BOOL,
            'release_date': TYPE_STRING,
            'packages': TYPE_LIST,
            'commands': TYPE_LIST,
        }

        # components
        # 'name': ('description', [<option list>])
        self.components = {
            'hplip': ("HP Linux Imaging and Printing System", ['base', 'network', 'gui', 'fax', 'scan', 'parallel', 'docs']),
            'hpijs': ("HP IJS Printer Driver", ['hpijs', 'hpijs-cups'])
        }

        self.selected_component = 'hplip'

        # options
        # name: (<required>, "<display_name>", [<dependency list>]), ...
        self.options = { 
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
        self.selected_options = {
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
        self.dependencies = {
            'libjpeg':          (True,  ['base', 'hpijs'], "libjpeg - JPEG library", self.check_libjpeg),
            'libtool':          (True,  ['base'], "libtool - Library building support services", self.check_libtool),
            'cups' :            (True,  ['base', 'hpijs-cups'], 'cups - Common Unix Printing System', self.check_cups), 
            'cups-devel':       (True,  ['base'], 'cups-devel- Common Unix Printing System development files', self.check_cups_devel),
            'gcc' :             (True,  ['base', 'hpijs'], 'gcc - GNU Project C and C++ Compiler', self.check_gcc),
            'make' :            (True,  ['base', 'hpijs'], "make - GNU make utility to maintain groups of programs", self.check_make),
            'python-devel' :    (True,  ['base'], "python-devel - Python development files", self.check_python_devel),
            'libpthread' :      (True,  ['base'], "libpthread - POSIX threads library", self.check_libpthread),
            'python2x':         (True,  ['base'], "Python 2.2 or greater - Python programming language", self.check_python2x),
            'gs':               (True,  ['base', 'hpijs'], "GhostScript - PostScript and PDF language interpreter and previewer", self.check_gs),
            'libusb':           (True,  ['base'], "libusb - USB library", self.check_libusb),

            'sane':             (True,  ['scan'], "SANE - Scanning library", self.check_sane),
            'sane-devel' :      (True,  ['scan'], "SANE - Scanning library development files", self.check_sane_devel),
            'xsane':            (False, ['scan'], "xsane - Graphical scanner frontend for SANE", self.check_xsane),
            'scanimage':        (False, ['scan'], "scanimage - Shell scanning program", self.check_scanimage),
            'pil':              (False, ['scan'], "PIL - Python Imaging Library (required for commandline scanning with hp-scan)", self.check_pil), 

            'reportlab':        (False, ['fax'], "Reportlab - PDF library for Python", self.check_reportlab), 
            'python23':         (True,  ['fax'], "Python 2.3 or greater - Required for fax functionality", self.check_python23),

            'ppdev':            (True,  ['parallel'], "ppdev - Parallel port support kernel module.", self.check_ppdev),

            'pyqt':             (True,  ['gui'], "PyQt - Qt interface for Python", self.check_pyqt),

            'libnetsnmp-devel': (True,  ['network'], "libnetsnmp-devel - SNMP networking library development files", self.check_libnetsnmp),
            'libcrypto':        (True,  ['network'], "libcrypto - OpenSSL cryptographic library", self.check_libcrypto),
        }

        for opt in self.options:
            update_spinner()
            for d in self.dependencies:
                if opt in self.dependencies[d][1]:
                    self.options[opt][2].append(d)

        self.load_distros()

        self.distros_index = {}
        for d in self.distros:
            self.distros_index[self.distros[d]['index']] = d        


    def init(self, callback=None):
        if callback is not None:
            callback("Init...\n")

        update_spinner()

        # Package manager names
        self.package_mgrs = []
        for d in self.distros:
            update_spinner()

            for a in self.distros[d].get('package_mgrs', []):
                if a and a not in self.package_mgrs:
                    self.package_mgrs.append(a)

        self.version_description, self.version_public, self.version_internal = self.get_hplip_version()
        log.debug("HPLIP Description=%s Public version=%s Internal version = %s"  % 
            (self.version_description, self.version_public, self.version_internal))

        # have_dependencies
        # is each dependency satisfied?
        # start with each one 'No'
        for d in self.dependencies:
            update_spinner()
            self.have_dependencies[d] = False

        self.get_distro()

        if callback is not None:
            callback("Distro: %s\n" % self.distro)

        self.check_dependencies(callback)

        log.debug("******")
        for d in self.dependencies:
            update_spinner()

            log.debug("have %s = %d" % (d, self.have_dependencies[d]))

            if callback is not None:
                callback("Result: %s = %d\n" % (d, self.have_dependencies[d]))

        log.debug("******")

        log.debug("Running package manager: %s" % self.check_pkg_mgr())

        self.bitness = utils.getBitness()
        log.debug("Bitness = %d" % self.bitness)

        update_spinner()

        self.endian = utils.getEndian()
        log.debug("Endian = %d" % self.endian)

        update_spinner()
        
        self.distro_name = self.distros_index[self.distro]
        self.distro_version_supported = self.get_distro_ver_data('supported', False)

        log.debug("Distro = %s Distro Name = %s Display Name= %s Version = %s Supported = %s" % 
            (self.distro, self.distro_name, self.distros[self.distro_name]['display_name'], 
             self.distro_version, self.distro_version_supported))

        self.hpoj_present = self.check_hpoj()
        log.debug("HPOJ = %s" % self.hpoj_present)

        update_spinner()

        self.hplip_present = self.check_hplip()
        log.debug("HPLIP (prev install) = %s" % self.hplip_present)

        status, output = self.run('cups-config --version')
        self.cups_ver = output.strip()
        log.debug("CUPS version = %s" % self.cups_ver)

        self.cups11 = output.startswith('1.1')
        log.debug("Is CUPS 1.1.x? %s" % self.cups11)

        status, self.sys_uname_info = self.run('uname -a')
        self.sys_uname_info = self.sys_uname_info.replace('\n', '')
        log.debug(self.sys_uname_info)

        self.ppd_install_flag()
        self.ppd_dir = self.get_distro_ver_data('ppd_dir')

        # Record the installation time/date and version.
        # Also has the effect of making the .hplip.conf file user r/w
        # on the 1st run so that running hp-setup as root doesn't lock
        # the user out of owning the file
        user_cfg.installation.date_time = time.strftime("%x %H:%M:%S", time.localtime())
        user_cfg.installation.version = self.version_public

        if callback is not None:
            callback("Done")


    def check_dependencies(self, callback=None):
        update_ld_output()

        for d in self.dependencies:
            log.debug("***")

            update_spinner()

            log.debug("Checking for dependency '%s'...\n" % d)

            if callback is not None:
                callback("Checking: %s\n" % d)

            self.have_dependencies[d] = self.dependencies[d][3]()
            log.debug("have %s = %d" % (d, self.have_dependencies[d]))

        cleanup_spinner()


    def password_func(self):
        if self.password:
            return self.password
        elif self.ui_mode == INTERACTIVE_MODE:
            import getpass
            return getpass.getpass("Enter password: ")
        else:
            return ''

    def run(self, cmd, callback=None):
        output = cStringIO.StringIO()
        
        try:
            child = pexpect.spawn(cmd, timeout=1)
        except pexpect.ExceptionPexpect:
            return 1, ''
        
        try:
            while True:
                update_spinner()
                i = child.expect(["[pP]assword:|password for", pexpect.EOF, pexpect.TIMEOUT])
                cb = child.before
                if cb:
                    log.log_to_file(cb)
                    output.write(cb)

                    if callback is not None:
                        if callback(cb): # cancel
                            break
                
                if i == 0: # Password:
                    child.sendline(self.password)

                elif i == 1: # EOF
                    break

                elif i == 2: # TIMEOUT
                    continue
                
        except Exception:
            log.exception()
            cleanup_spinner()
            return 1, ''

        cleanup_spinner()

        try: 
            child.close()
        except OSError:
            pass
        return child.exitstatus, output.getvalue()


    def get_distro(self):
        log.debug("Determining distro...")
        self.distro, self.distro_version = DISTRO_UNKNOWN, '0.0'

        found = False

        lsb_release = utils.which("lsb_release")

        if lsb_release:
            log.debug("Using 'lsb_release -i/-r'")
            cmd = os.path.join(lsb_release, "lsb_release")

            status, name = self.run(cmd + ' -i')

            if name and ':' in name:
                name = name.split(':')[1].strip().lower()
                status, ver = self.run(cmd + ' -r')

                if ver and ':' in ver:
                    self.distro_version = ver.split(':')[1].strip()

                    log.debug("LSB: %s %s" % (name, self.distro_version))

                    for d in self.distros:
                        if name.find(d) > -1:
                            self.distro = self.distros[d]['index']
                            found = True
                            break

        if not found:
            try:
                name = file('/etc/issue', 'r').read().lower().strip()
            except IOError:
                # Some O/Ss don't have /etc/issue (Mac)
                self.distro, self.distro_version = DISTRO_UNKNOWN, '0.0'
            else:
                for d in self.distros:
                    if name.find(d) > -1:
                        self.distro = self.distros[d]['index']
                        found = True
                    else:
                        for x in self.distros[d].get('alt_names', ''):
                            if x and name.find(x) > -1:
                                self.distro = self.distros[d]['index']
                                found = True
                                break
    
                    if found:
                        break
    
                if found:
                    for n in name.split(): 
                        if '.' in n:
                            m = '.'.join(n.split('.')[:2])
                        else:
                            m = n
    
                        try:
                            self.distro_version = str(float(m))
                        except ValueError:
                            try:
                                self.distro_version = str(int(m))
                            except ValueError:
                                self.distro_version = '0.0'
                            else:
                                break
                        else:
                            break
    
                    log.debug("/etc/issue: %s %s" % (name, self.distro_version))

        log.debug("distro=%d, distro_version=%s" % (self.distro, self.distro_version))


    def distro_changed(self):
        self.ppd_install_flag()
        self.ppd_dir = self.get_distro_ver_data('ppd_dir')
        self.distro_version_supported = self.get_distro_ver_data('supported', False)

    def __fixup_data(self, key, data):
        field_type = self.FIELD_TYPES.get(key, TYPE_STRING)
        if field_type == TYPE_BOOL:
            return utils.to_bool(data)

        elif field_type == TYPE_STRING:
            return data.strip()

        elif field_type == TYPE_INT:
            try:
                return int(data)
            except ValueError:
                return 0

        elif field_type == TYPE_LIST:
            return [x for x in data.split(',') if x]

    def load_distros(self):
        if self.mode  == MODE_INSTALLER:
            distros_dat_file = os.path.join('installer', 'distros.dat')

        elif self.mode == MODE_CREATE_DOCS:
            distros_dat_file = os.path.join('..', '..', 'installer', 'distros.dat')

        else: # MODE_CHECK
            distros_dat_file = os.path.join(prop.home_dir, 'installer', 'distros.dat')

            if not os.path.exists(distros_dat_file):
                log.debug("DAT file not found at %s. Using local relative path..." % distros_dat_file)
                distros_dat_file = os.path.join('installer', 'distros.dat')

        distros_dat = Config(distros_dat_file, True)

        distros_list = distros_dat.distros.distros.split(',')
        log.debug(distros_list)

        for distro in distros_list:
            update_spinner()
            try:
                distro_section = distros_dat[distro]
            except KeyError:
                continue

            for key in distro_section:
                distro_section[key] = self.__fixup_data(key, distro_section[key])

            self.distros[distro] = distro_section

            if type(self.distros[distro]['versions']) == type(''):
                self.distros[distro]['versions'] = [self.distros[distro]['versions']]

            temp_versions = self.distros[distro]['versions']
            self.distros[distro]['versions'] = {}

            for ver in temp_versions:
                try:
                    ver_section = distros_dat["%s:%s" % (distro, ver)]
                except KeyError:
                    continue

                for key in ver_section:
                    ver_section[key] = self.__fixup_data(key, ver_section[key])

                self.distros[distro]['versions'][ver] = ver_section
                self.distros[distro]['versions'][ver]['dependency_cmds'] = {}

                for dep in self.dependencies:
                    try:
                        dep_section = distros_dat["%s:%s:%s" % (distro, ver, dep)]
                    except KeyError:
                        continue

                    for key in dep_section:
                        dep_section[key] = self.__fixup_data(key, dep_section[key])
                        self.distros[distro]['versions'][ver]['dependency_cmds'][dep] = dep_section


    def pre_install(self):
        pass

    def pre_depend(self):
        pass

    def check_python2x(self):
        py_ver = sys.version_info
        py_major_ver, py_minor_ver = py_ver[:2]
        log.debug("Python ver=%d.%d" % (py_major_ver, py_minor_ver))
        return py_major_ver >= 2

    def check_gcc(self):
        return check_tool('gcc --version', 0) and check_tool('g++ --version', 0)

    def check_make(self):
        return check_tool('make --version', 3.0)

    def check_libusb(self):
        if not check_lib('libusb'):
            return False

        return len(locate_file_contains("usb.h", '/usr/include', 'usb_init(void)')) > 0
        

    def check_libjpeg(self):
        return check_lib("libjpeg") and check_file("jpeglib.h")

    def check_libcrypto(self):
        return check_lib("libcrypto") and check_file("crypto.h")

    def check_libpthread(self):
        return check_lib("libpthread") and check_file("pthread.h")

    def check_libnetsnmp(self):
        return check_lib("libnetsnmp") and check_file("net-snmp-config.h")

    def check_reportlab(self):
        try:
            log.debug("Trying to import 'reportlab'...")
            import reportlab
            log.debug("Success.")
            return True
        except ImportError:
            log.debug("Failed.")
            return False

    def check_python23(self):
        py_ver = sys.version_info
        py_major_ver, py_minor_ver = py_ver[:2]
        log.debug("Python ver=%d.%d" % (py_major_ver, py_minor_ver))
        return py_major_ver >= 2 and py_minor_ver >= 3

    def check_sane(self):
        return check_lib('libsane')

    def check_sane_devel(self):
        return len(locate_file_contains("sane.h", '/usr/include', 'extern SANE_Status sane_init')) > 0

    def check_xsane(self):
        if os.getenv('DISPLAY'):
            return check_tool('xsane --version', 0.9) # will fail if X not running...
        else:
            return bool(utils.which("xsane")) # ...so just see if it installed somewhere

    def check_scanimage(self):
        return check_tool('scanimage --version', 1.0)

    def check_ppdev(self):
        return check_lsmod('ppdev')

    def check_gs(self):
        return check_tool('gs -v', 7.05)

    def check_pyqt(self):
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

    def check_python_devel(self):
        return check_file('Python.h')

    def check_cups_devel(self):
        return check_file('cups.h') and bool(utils.which('lpr'))

    def check_cups(self):
        status, output = self.run('lpstat -r')

        if status > 0:
            log.debug("CUPS is not running.")
            return False
        else:
            log.debug("CUPS is running.")
            return True

    def check_hpoj(self):
        log.debug("Checking for 'HPOJ'...")
        return check_ps(['ptal-mlcd', 'ptal-printd', 'ptal-photod']) or \
            bool(utils.which("ptal-init"))

    def check_hplip(self):
        log.debug("Checking for HPLIP...")
        return check_ps(['hpiod', 'hpssd']) and locate_files('hplip.conf', '/etc/hp')

    def check_hpssd(self):
        log.debug("Checking for hpssd...")
        return check_ps(['hpssd'])

    def check_libtool(self):
        log.debug("Checking for libtool...")
        return check_tool('libtool --version')

    def check_pil(self):
        log.debug("Checking for PIL...")
        try:
            import Image
            return True
        except ImportError:
            return False

    def check_pkg_mgr(self): # modified from EasyUbuntu
        """
            Check if any pkg mgr processes are running
        """
        log.debug("Searching for '%s' in 'ps' output..." % self.package_mgrs)

        p = os.popen("ps -U root -o comm") # TODO: Doesn't work on Mac OS X
        pslist = p.readlines()
        p.close()

        for process in pslist:
            for p in self.package_mgrs:
                if p in process:
                    return p
        return ''

    def get_hplip_version(self):
        self.version_description, self.version_public, self.version_internal = '', '', ''

        if self.mode == MODE_INSTALLER:
            ac_init_pat = re.compile(r"""AC_INIT\(\[(.*?)\], *\[(.*?)\], *\[(.*?)\], *\[(.*?)\] *\)""", re.IGNORECASE)

            try:
                config_in = open('./configure.in', 'r')
            except IOError:
                self.version_description, self.version_public, self.version_internal = \
                    '', sys_cfg.configure['internal-tag'], sys_cfg.hplip.version
            else:
                for c in config_in:
                    if c.startswith("AC_INIT"):
                        match_obj = ac_init_pat.search(c)
                        self.version_description = match_obj.group(1)
                        self.version_public = match_obj.group(2)
                        self.version_internal = match_obj.group(3)
                        name = match_obj.group(4)
                        break

                config_in.close()

                if name != 'hplip':
                    log.error("Invalid archive!")


        else: # MODE_CHECK
            try:
                self.version_description, self.version_public, self.version_internal = \
                    '', sys_cfg.configure['internal-tag'], sys_cfg.hplip.version
            except KeyError:
                self.version_description, self.version_public, self.version_internal = '', '', ''
                
        return self.version_description, self.version_public, self.version_internal            

    def configure(self): 
        configure_cmd = './configure'

        if self.selected_options['network']:
            configure_cmd += ' --enable-network-build'
        else:
            configure_cmd += ' --disable-network-build'

        if self.selected_options['parallel']:
            configure_cmd += ' --enable-pp-build'
        else:
            configure_cmd += ' --disable-pp-build'

        if self.selected_options['fax']:
            configure_cmd += ' --enable-fax-build'
        else:
            configure_cmd += ' --disable-fax-build'

        if self.selected_options['gui']:
            configure_cmd += ' --enable-gui-build'
        else:
            configure_cmd += ' --disable-gui-build'

        if self.selected_options['scan']:
            configure_cmd += ' --enable-scan-build'
        else:
            configure_cmd += ' --disable-scan-build'

        if self.selected_options['docs']:
            configure_cmd += ' --enable-doc-build'
        else:
            configure_cmd += ' --disable-doc-build'

        if self.enable_ppds:
            configure_cmd += ' --enable-foomatic-ppd-install --disable-foomatic-xml-install'

            if self.ppd_dir is not None:
                configure_cmd += ' --with-hpppddir=%s' % self.ppd_dir
        else:
            configure_cmd += ' --disable-foomatic-ppd-install --enable-foomatic-xml-install'

        if self.hpijs_build:
            configure_cmd += ' --enable-hpijs-only-build'
        else:
            configure_cmd += ' --disable-hpijs-only-build'

        if self.bitness == 64:
            configure_cmd += ' --libdir=/usr/lib64'

        configure_cmd += ' --prefix=%s' % self.install_location

        if self.cups11:
            configure_cmd += ' --enable-cups11-build'

        return configure_cmd


    def restart_cups(self):
        if os.path.exists('/etc/init.d/cups'):
            cmd = self.su_sudo() % '/etc/init.d/cups restart'

        elif os.path.exists('/etc/init.d/cupsys'):
            cmd = self.su_sudo() % '/etc/init.d/cupsys restart'

        else:
            cmd = self.su_sudo() % 'killall -HUP cupsd'

        self.run(cmd)

    def stop_hplip(self):
        return self.su_sudo() % "/etc/init.d/hplip stop"

    def su_sudo(self):
        if os.geteuid() == 0:
            return '%s'
        else:
            try:
                cmd = self.distros[self.distro_name]['su_sudo']
            except KeyError:
                cmd = 'su'

            if cmd == 'su':
                return 'su -c "%s"'
            else:
                return 'sudo %s'

    def su_sudo_str(self):
        return self.get_distro_data('su_sudo', 'su')


    def build_cmds(self): 
        return [self.configure(), 
                'make clean', 
                'make', 
                self.su_sudo() % 'make install']

    def ppd_install_flag(self): 
        if self.cups11:
            self.enable_ppds = True
        else:
            self.enable_ppds = (self.get_distro_ver_data('ppd_install', 'ppd') == 'ppd')

        log.debug("Enable PPD install: %s" % self.enable_ppds)

    def get_distro_ver_data(self, key, default=None):
        try:
            return self.distros[self.distro_name]['versions'][self.distro_version].get(key, None) or \
                self.distros[self.distro_name].get(key, None) or default
        except KeyError:
            return default

        return value

    def get_distro_data(self, key, default=None):
        try:
            return self.distros[self.distro_name].get(key, None) or default
        except KeyError:
            return default

    def get_ver_data(self, key, default=None):
        try:
            return self.distros[self.distro_name]['versions'][self.distro_version].get(key, None) or default
        except KeyError:
            return default

        return value

    def get_dependency_data(self, dependency):
        dependency_cmds = self.get_ver_data("dependency_cmds", {})
        dependency_data = dependency_cmds.get(dependency, {})
        packages = dependency_data.get('packages', [])
        commands = dependency_data.get('commands', [])
        return packages, commands


    def distro_known(self):
        return self.distro != DISTRO_UNKNOWN and self.distro_version != DISTRO_VER_UNKNOWN

    def distro_supported(self):
        return self.distro != DISTRO_UNKNOWN and self.distro_version != DISTRO_VER_UNKNOWN and self.get_ver_data('supported', False)

    def sort_vers(self, x, y):
        try:
            return cmp(float(x), float(y))
        except ValueError:
            return cmp(x, y)

    def running_as_root(self):
        return os.geteuid() == 0

    def show_release_notes_in_browser(self):
        url = "file://%s" % os.path.join(os.getcwd(), 'doc', 'release_notes.html')
        log.debug(url)
        status, output = self.run("xhost +")
        utils.openURL(url)

    def count_num_required_missing_dependencies(self):
        num_req_missing = 0
        for d, desc, opt in self.missing_required_dependencies():
            num_req_missing += 1
        return num_req_missing

    def count_num_optional_missing_dependencies(self):
        num_opt_missing = 0
        for d, desc, req, opt in self.missing_optional_dependencies():
            num_opt_missing += 1
        return num_opt_missing

    def missing_required_dependencies(self):
        for opt in self.components[self.selected_component][1]:
            if self.options[opt][0]: # required options
                for d in self.options[opt][2]: # dependencies for option
                    if not self.have_dependencies[d]: # missing
                        log.debug("Missing required dependency: %s" % d)
                        yield d, self.dependencies[d][2], opt
                        # depend, desc, option

    def missing_optional_dependencies(self):
        for opt in self.components[self.selected_component][1]:
            if not self.options[opt][0]: # not required
                if self.selected_options[opt]: # only for options that are ON
                    for d in self.options[opt][2]: # dependencies
                        if not self.have_dependencies[d]: # missing dependency
                            log.debug("Missing optional dependency: %s" % d)
                            yield d, self.dependencies[d][2], self.dependencies[d][0], opt
                            # depend, desc, required_for_opt, opt


    def select_options(self, answer_callback):
        num_opt_missing = 0
        # not-required options
        for opt in self.components[self.selected_component][1]:
            if not self.options[opt][0]: # not required
                self.selected_options[opt] = answer_callback(opt, self.options[opt][1])

                if self.selected_options[opt]: # only for options that are ON
                    for d in self.options[opt][2]: # dependencies
                        if not self.have_dependencies[d]: # missing dependency
                            log.debug("Missing optional dependency: %s" % d)
                            num_opt_missing += 1

        return num_opt_missing

    
    def check_network_connection(self):
        ok = False

        wget = utils.which("wget")
        if wget:
            wget = os.path.join(wget, "wget")
            cmd = "%s --timeout=5 %s" % (wget, HTTP_GET_TARGET)
            log.debug(cmd)
            status, output = self.run(cmd)
            log.debug("wget returned: %d" % status)
            ok = (status == 0)
                
        else:
            curl = utils.which("curl")
            if curl:
                curl = os.path.join(curl, "curl")
                cmd = "%s --connect-timeout 3 --max-time 5 %s" % (curl, HTTP_GET_TARGET)
                log.debug(cmd)
                status, output = self.run(cmd)
                log.debug("curl returned: %d" % status)
                ok = (status == 0)
                
            else:
                ping = utils.which("ping")
        
                if ping:
                    ping = os.path.join(ping, "ping")
                    cmd = "%s -c1 -W1 -w5 %s" % (ping, PING_TARGET)
                    log.debug(cmd)
                    status, output = self.run(cmd)
                    log.debug("ping returned: %d" % status)
                    ok = (status == 0)
            
        return ok
        

    def run_pre_install(self, callback=None):
        pre_cmd = self.get_distro_ver_data('pre_install_cmd')
        log.debug(pre_cmd)
        if pre_cmd:
            x = 1
            for cmd in pre_cmd:
                status, output = self.run(cmd)

                if status != 0:
                    log.warn("An error occurred running '%s'" % cmd)

                if callback is not None:
                    callback(cmd, "Pre-install step %d" % x)

                x += 1

            return True

        else:
            return False

    def run_pre_depend(self, callback=None):
        pre_cmd = self.get_distro_ver_data('pre_depend_cmd')
        log.debug(pre_cmd)
        if pre_cmd:
            x = 1
            for cmd in pre_cmd:
                status, output = self.run(cmd)

                if status != 0:
                    log.warn("An error occurred running '%s'" % cmd)

                if callback is not None:
                    callback(cmd, "Pre-depend step %d" % x)

                x += 1

    def run_post_depend(self, callback=None):
        post_cmd = self.get_distro_ver_data('post_depend_cmd')
        log.debug(post_cmd)
        if post_cmd:
            x = 1
            for cmd in post_cmd:
                status, output = self.run(cmd)

                if status != 0:
                    log.warn("An error occurred running '%s'" % cmd)

                if callback is not None:
                    callback(cmd, "Post-depend step %d" % x)

                x += 1


    def pre_build(self):
        cmds = []
        if self.get_distro_ver_data('fix_ppd_symlink', False):
            cmds.append(self.su_sudo() % 'python ./installer/fix_symlink.py')
            
        return cmds
    
    def run_pre_build(self, callback=None):
        x = 1
        for cmd in self.pre_build():
            status, output = self.run(cmd)
            if callback is not None:
                callback(cmd, "Pre-build step %d"  % x)
            
            x += 1
             
            
        # Remove the link /usr/share/foomatic/db/source/PPD if the symlink is corrupt (Dapper only?)
##        if self.get_distro_ver_data('fix_ppd_symlink', False):
##            cmd = self.su_sudo() % 'python ./installer/fix_symlink.py'
##            status, output = self.run(cmd)
##            if callback is not None:
##                callback(cmd, "Fix PPD symlink")
##        else:
##            if callback is not None:
##                callback()


        
    
    def run_post_build(self, callback=None):
        x = 1
        for cmd in self.post_build():
            status, output = self.run(cmd)
            if callback is not None:
                callback(cmd, "Post-build step %d"  % x)
            
            x += 1

    
    def post_build(self):
        cmds = []
        self.logoff_required = False
        self.restart_required = True
        trigger_required = True

##        # Trigger USB devices so that the new .rules will take effect 
##        if trigger_required:
##            #self.logoff_required = True # Temp hack...
##            self.restart_required = True
##            # TODO: Fix trigger utility!
##            cmd = self.su_sudo() % 'python ./installer/trigger.py'
##            log.debug("Running USB trigger utility: %s" % cmd)
##            status, output = self.run(cmd)
##            if callback is not None:
##                callback(cmd, "USB triggering utility")


        # Restart CUPS if necessary
        if self.cups11: # or mdk_usb_fix:
            cmds.append(self.restart_cups())

        # Kill any running hpssd.py instance from a previous install
        if self.check_hpssd():
            pid = get_ps_pid('hpssd')
            if pid:
                kill = os.path.join(utils.which("kill"), "kill") + " %d" % pid
                
                cmds.append(self.su_sudo() % kill)
            
##            try:
##                os.kill(pid, 9)
##                status = 0
##            except OSError:
##                status = 1
##
##            if callback is not None:
##                callback("", "Stopping hpssd")

        return cmds

    def logoff(self):
        ok = False
        pkill = utils.which('pkill')
        if pkill:
            cmd = "%s -KILL -u %s" % (os.path.join(pkill, "pkill"), prop.username)
            cmd = self.su_sudo() % cmd
            status, output = self.run(cmd)

            ok = (status == 0)

        return ok

    def restart(self):
        ok = False
        shutdown = utils.which('shutdown')
        if shutdown:
            cmd = "%s -r now" % (os.path.join(shutdown, "shutdown"))
            cmd = self.su_sudo() % cmd
            status, output = self.run(cmd)

            ok = (status == 0)

        return ok

    def check_for_gui_support(self):
        return os.getenv('DISPLAY') and self.selected_options['gui'] and utils.checkPyQtImport()

    def run_hp_setup(self):
        if self.selected_options['gui'] and self.check_for_gui_support():
            su_sudo = self.su_sudo()

            if utils.which('hp-setup'):
                c = 'hp-setup -u --username=%s' % prop.username
                cmd = su_sudo % c
            else:
                c = 'python ./setup.py -u --username=%s' % prop.username
                cmd = su_sudo % c

            log.debug(cmd)
            status, output = self.run(cmd)

        else:
            hpsetup = utils.which("hp-setup")

            if hpsetup:
                cmd = "hp-setup -i"
            else:
                cmd = "python ./setup.py -i"

            cmd = self.su_sudo() % cmd
            status, output = self.run(cmd)


    def remove_hplip(self, callback=None):
        failed = True
        self.stop_pre_2x_hplip(callback)

        hplip_remove_cmd = self.get_distro_data('hplip_remove_cmd')
        if hplip_remove_cmd:
            if callback is not None:
                callback(hplip_remove_cmd, "Removing old HPLIP version")

                status, output = self.run(hplip_remove_cmd)

            if status == 0:
                self.hplip_present = self.check_hplip()

                if not self.hplip_present:
                    failed = False

        return failed


    def stop_pre_2x_hplip(self, callback=None):
        hplip_init_script = '/etc/init.d/hplip stop'
        if os.path.exists(hplip_init_script):
            cmd = self.su_sudo() % hplip_init_script

            if callback is not None:
                callback(cmd, "Stopping old HPLIP version.")

            status, output = self.run(cmd)


    def remove_hpoj(self, callback=None):
        # TODO: Must stop PTAL?
        hpoj_remove_cmd = self.get_distro_data('hpoj_remove_cmd')
        if hpoj_remove_cmd:
            if callback is not None:
                callback(hpoj_remove_cmd, "Removing HPOJ")

                status, output = self.run(hpoj_remove_cmd)

            if status == 0:
                self.hpoj_present = check_hpoj()

                if not self.hpoj_present:
                    failed = False

        return failed

    def check_password(self, password_entry_callback, callback=None):
        self.clear_su_sudo_password()
        x = 1
        while True:
            self.password = password_entry_callback()
            cmd = self.su_sudo() % "true"

            log.debug(cmd)

            status, output = self.run(cmd)

            log.debug(status)
            log.debug(output)

            if status == 0:
                if callback is not None:
                    callback("", "Password accepted")
                return True

            if callback is not None:
                callback("", "Password incorrect. %d attempt(s) left." % (3-x))

            x += 1

            if x > 3:
                return False

    def clear_su_sudo_password(self):
        if self.su_sudo_str() == 'sudo':
            log.debug("Clearing password...")
            self.run("sudo -K")

    # PLUGIN SUPPORT
    
    def get_plugin_info(self, model):
        ok, url, size, checksum, timestamp = False, '', 0, 0, 0.0
        
        if self.check_network_connection():
            filename, headers = urllib.urlretrieve("http://hplip.sf.net/plugins.conf")
            
            g, conf = utils.make_temp_file()
            
            f = file(filename, 'r')
            t = f.read()
            log.debug_block("plugins.conf", t)
            os.write(g, t)
            f.close()
            
            plugin_cfg = Config(conf, True)
            
            try:
                url = plugin_cfg[model]['url']
                size = int(plugin_cfg[model]['size'])
                checksum = plugin_cfg[model]['checksum']
                timestamp = float(plugin_cfg[model]['timestamp'])
                ok = True
            except KeyError:
                pass
        else:
            log.error("No network connection detected. Cannot download required plugin.")
        
        return url, size, checksum, timestamp, ok
        
    def download_plugin(self, model, url, size, checksum, timestamp):
        log.debug("Downloading %s.plugin from %s" % (model, url))
        
        if not os.path.exists(self.plugin_path):
            try:
                log.debug("Creating plugin directory: %s" % self.plugin_path)
                os.makedirs(self.plugin_path)
            except (OSError, IOError), e:
                log.error("Unable to create directory: %s" % e.strerror)
                return False
            
        plugin_file = os.path.join(self.plugin_path, model+".plugin")
        filename, headers = urllib.urlretrieve(url, plugin_file)
        calc_checksum = sha.new(file(plugin_file, 'r').read()).hexdigest()
        log.debug("D/L file checksum=%s" % calc_checksum)
        
        #if calc_checksum == checksum:
        #    log.debug("D/L OK")
        #    return True, plugin_file
        
        #log.error("D/L failed (checksum error).")
        #return False, ''
        return True, plugin_file
        
        
    def copy_plugin(self, model, src):
        plugin_file = os.path.join(self.plugin_path, model+".plugin")
        
        if not os.path.exists(self.plugin_path):
            try:
                log.debug("Creating plugin directory: %s" % self.plugin_path)
                os.makedirs(self.plugin_path)
            except (OSError, IOError), e:
                log.error("Unable to create directory: %s" % e.strerror)
                return False
        
        import shutil
        try:
            log.debug("Copying plugin from %s to %s" % (src, plugin_file))
            shutil.copyfile(src, plugin_file)
        except (OSError, IOError), e:
            log.error("Copy failed: %s" % e.strerror)
            return False
    
        return True
        
    def install_plugin(self, model, plugin_lib):
        log.debug("Installing %s.plugin to %s..." % (model, self.plugin_path))
        ok = False
        plugin_file = os.path.join(self.plugin_path, model+".plugin")
        ppd_path = sys_cfg.dirs.ppd
        rules_path = '/etc/udev/rules.d'
        
        if not os.path.exists(rules_path):
            log.error("Rules path %s does not exist!" % rules_path)
        
        firmware_path = os.path.join(prop.home_dir, "data", "firmware")
        if not os.path.exists(firmware_path):
            try:
                log.debug("Creating plugin directory: %s" % firmware_path)
                os.makedirs(firmware_path)
            except (OSError, IOError), e:
                log.error("Unable to create directory: %s" % e.strerror)
            
        lib_path = os.path.join(prop.home_dir, "prnt", "plugins")
        if not os.path.exists(lib_path):
            try:
                log.debug("Creating plugin directory: %s" % lib_path)
                os.makedirs(lib_path)
            except (OSError, IOError), e:
                log.error("Unable to create directory: %s" % e.strerror)
            
        tar = tarfile.open(plugin_file, "r:gz")
        for tarinfo in tar:
            name = tarinfo.name
            if name.endswith('.fw') or name.endswith('.fw.gz'):
                # firmware file
                log.debug("Extracting fw file %s to %s" % (name, firmware_path))
                tar.extract(tarinfo, firmware_path)
            
            elif name.endswith('.ppd') or name.endswith('.ppd.gz'):
                # PPD file
                log.debug("Extracting ppd file %s to %s" % (name, ppd_path))
                tar.extract(tarinfo, ppd_path,)
                
            elif name.endswith('.so'):
                # Library file(s)
                log.debug("Extracting library file %s to %s" % (name, lib_path))
                tar.extract(tarinfo, lib_path)
                
            elif name.endswith('.rules'):
                # .rules file
                log.debug("Extracting .rules file %s to %s" % (name, rules_path))
                tar.extract(tarinfo, rules_path)
                
            else:
                log.debug("Skipping file: %s" % name)
                
                
        tar.close()
        
        self.bitness = utils.getBitness()
        self.processor = utils.getProcessor()
        
        link_file = os.path.join(lib_path, '%s.so' % plugin_lib)
        
        if self.processor == 'power_macintosh':
            trg_file = os.path.join(lib_path,'%s-ppc.so' % plugin_lib)
        else:
            trg_file = os.path.join(lib_path,"%s-x86_%s.so" % (plugin_lib, self.bitness))
            
        try:
            log.debug("Creating link: %s -> %s" % (link_file, trg_file))
            os.symlink(trg_file, link_file)
        except (OSError, IOError), e:
            log.error("Unable to create symlink: %s" % e.strerror)
        
        return True
        
    def check_for_plugin(self, model): 
        plugin_file = os.path.join(self.plugin_path, model+".plugin")
        # TODO: Check for each file of the plugin is installed?
        return os.path.exists(plugin_file)
        
        
