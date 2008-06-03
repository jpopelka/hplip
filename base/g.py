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
# NOTE: This module is safe for 'from g import *'
#

# Std Lib
import sys
import os
import os.path
import ConfigParser
import locale
import pwd
import stat

# Local
from codes import *
import logger

# System wide logger
log = logger.Logger('', logger.Logger.LOG_LEVEL_INFO, logger.Logger.LOG_TO_CONSOLE)
log.set_level('info')

MINIMUM_PYQT_MAJOR_VER = 3
MINIMUM_PYQT_MINOR_VER = 14
MINIMUM_QT_MAJOR_VER = 3
MINIMUM_QT_MINOR_VER = 0

def to_bool(s, default=False):
    if isinstance(s, str) and s:
        if s[0].lower() in ['1', 't', 'y']:
            return True
        elif s[0].lower() in ['0', 'f', 'n']:
            return False
    elif isinstance(s, bool):
        return s

    return default

# System wide properties
class Properties(dict):

    def __getattr__(self, attr):
        if attr in self.keys():
            return self.__getitem__(attr)
        else:
            return ""

    def __setattr__(self, attr, val):
        self.__setitem__(attr, val)

prop = Properties()


# User config file
class ConfigSection(dict):
    def __init__(self, section_name, config_obj, filename, *args, **kwargs):
        dict.__setattr__(self, "section_name", section_name)
        dict.__setattr__(self, "config_obj", config_obj)
        dict.__setattr__(self, "filename", filename)
        dict.__init__(self, *args, **kwargs)

    def __getattr__(self, attr):
        if attr in self.keys():
            return self.__getitem__(attr)
        else:
            return ""

    def __setattr__(self, option, val):
        self.__setitem__(option, val)
        if not self.config_obj.has_section(self.section_name):
            self.config_obj.add_section(self.section_name)

        self.config_obj.set(self.section_name, option, val)
        
        try:
            f = file(self.filename, 'w')
            self.config_obj.write(f)
            f.close()
        except IOError:
            pass


class Config(dict):
    def __init__(self, filename, error_if_not_found=False, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        dict.__setattr__(self, "config_obj", ConfigParser.ConfigParser())
        dict.__setattr__(self, "filename", filename)

        log.debug("Reading config file %s" % filename)

        try:
            f = file(filename, 'r')
            self.config_obj.readfp(f)
            f.close()
        except ConfigParser.Error:
            log.error("There is an error in the config file: %s" % filename)
            sys.exit(1)
        except IOError:
            pass

        for s in self.config_obj.sections():
            opts = []
            for o in self.config_obj.options(s):
                opts.append((o, self.config_obj.get(s, o)))

            self.__setitem__(s, ConfigSection(s, self.config_obj, filename, opts))

    def __getattr__(self, sect):
        if sect not in self.keys():
            self.__setitem__(sect, ConfigSection(sect, self.config_obj, self.filename))

        return self.__getitem__(sect)

    def __setattr__(self, sect, val):
        self.__setitem__(sect, val)

# Config file: directories and ports
prop.sys_config_file = '/etc/hp/hplip.conf'
prop.user_dir = os.path.expanduser('~/.hplip')

os.umask(0037)
try:
    if not os.path.exists(prop.user_dir):
        os.makedirs(prop.user_dir)
except OSError:
    pass # This is sometimes OK, if running hpfax: for example
    
prop.user_config_file = os.path.join(prop.user_dir, 'hplip.conf')

if not os.path.exists(prop.user_config_file):
    try:
        file(prop.user_config_file, 'w').close()
        s = os.stat(os.path.dirname(prop.user_config_file))
        os.chown(prop.user_config_file, s[stat.ST_UID], s[stat.ST_GID])
    except IOError:
        pass
    
sys_cfg = Config(prop.sys_config_file, True)
user_cfg = Config(prop.user_config_file)


# Language settings
try:
    prop.locale, prop.encoding = locale.getdefaultlocale()
except ValueError:
    prop.locale = 'en_US'
    prop.encoding = 'UTF8'
    
prop.version = sys_cfg.hplip.version or 'x.x.x'
prop.home_dir = sys_cfg.dirs.home or os.path.realpath(os.path.normpath(os.getcwd()))
prop.username = pwd.getpwuid(os.getuid())[0]
pdb = pwd.getpwnam(prop.username)
prop.userhome = pdb[5]

prop.data_dir = os.path.join(prop.home_dir, 'data')
prop.image_dir = os.path.join(prop.home_dir, 'data', 'images')
prop.xml_dir = os.path.join(prop.home_dir, 'data', 'xml')
prop.models_dir = os.path.join(prop.home_dir, 'data', 'models')
prop.localization_dir = os.path.join(prop.home_dir, 'data', 'localization')

prop.max_message_len = 8192
prop.max_message_read = 65536
prop.read_timeout = 90

prop.ppd_search_path = '/usr/share;/usr/local/share;/usr/lib;/usr/local/lib;/usr/libexec;/opt;/usr/lib64'
prop.ppd_search_pattern = 'HP-*.ppd.*'
prop.ppd_download_url = 'http://www.linuxprinting.org/ppd-o-matic.cgi'
prop.ppd_file_suffix = '-hpijs.ppd'

# Build and install configurations
prop.gui_build = to_bool(sys_cfg.configure.get('gui-build', '0'))
prop.net_build = to_bool(sys_cfg.configure.get('network-build', '0'))
prop.par_build = to_bool(sys_cfg.configure.get('pp-build', '0'))
prop.usb_build = True 
prop.scan_build = to_bool(sys_cfg.configure.get('scanner-build', '0'))
prop.fax_build = to_bool(sys_cfg.configure.get('fax-build', '0'))
prop.doc_build = to_bool(sys_cfg.configure.get('doc-build', '0'))
prop.foomatic_xml_install = to_bool(sys_cfg.configure.get('foomatic-xml-install', '0'))
prop.foomatic_ppd_install = to_bool(sys_cfg.configure.get('foomatic-ppd-install', '0'))

# Spinner, ala Gentoo Portage
spinner = "\|/-\|/-"
spinpos = 0

def update_spinner():
    global spinner, spinpos
    if not log.is_debug() and sys.stdout.isatty():
        sys.stdout.write("\b" + spinner[spinpos])
        spinpos=(spinpos + 1) % 8
        sys.stdout.flush()

def cleanup_spinner():
    if not log.is_debug() and sys.stdout.isatty():
        sys.stdout.write("\b \b")
        sys.stdout.flush()


# Internal/messaging errors

ERROR_STRINGS = {
                ERROR_SUCCESS : 'No error',
                ERROR_UNKNOWN_ERROR : 'Unknown error',
                ERROR_DEVICE_NOT_FOUND : 'Device not found',
                ERROR_INVALID_DEVICE_ID : 'Unknown/invalid device-id field',
                ERROR_INVALID_DEVICE_URI : 'Unknown/invalid device-uri field',
                #ERROR_INVALID_MSG_TYPE : 'Unknown message type',
                #ERROR_INVALID_DATA_ENCODING : 'Unknown data encoding',
                #ERROR_INVALID_CHAR_ENCODING : 'Unknown character encoding',
                ERROR_DATA_LENGTH_EXCEEDS_MAX : 'Data length exceeds maximum',
                #ERROR_DATA_LENGTH_MISMATCH : "Data length doesn't match length field",
                #ERROR_DATA_DIGEST_MISMATCH : "Digest of data doesn't match digest field",
                #ERROR_INVALID_JOB_ID : 'Invalid job-id',
                ERROR_DEVICE_IO_ERROR : 'Device I/O error',
                #ERROR_STRING_QUERY_FAILED : 'String/error query failed',
                #ERROR_QUERY_FAILED : 'Query failed',
                #ERROR_GUI_NOT_AVAILABLE : 'hpguid not running',
                #ERROR_NO_CUPS_DEVICES_FOUND : 'No CUPS devices found (deprecated)',
                ERROR_NO_PROBED_DEVICES_FOUND : 'No probed devices found',
                #ERROR_INVALID_BUS_TYPE : 'Invalid bus type',
                #ERROR_BUS_TYPE_CANNOT_BE_PROBED : 'Bus cannot be probed',
                ERROR_DEVICE_BUSY : 'Device busy',
                #ERROR_NO_DATA_AVAILABLE : 'No data avaiable',
                #ERROR_INVALID_DEVICEID : 'Invalid/missing DeviceID',
                #ERROR_INVALID_CUPS_VERSION : 'Invlaid CUPS version',
                #ERROR_CUPS_NOT_RUNNING : 'CUPS not running',
                ERROR_DEVICE_STATUS_NOT_AVAILABLE : 'DeviceStatus not available',
                #ERROR_DATA_IN_SHORT_READ: 'ChannelDataIn short read',
                ERROR_INVALID_SERVICE_NAME : 'Invalid service name',
                #ERROR_INVALID_USER_ERROR_CODE : 'Invalid user level error code',
                ERROR_ERROR_INVALID_CHANNEL_ID : 'Invalid channel-id (service name)',
                ERROR_CHANNEL_BUSY : 'Channel busy',
                #ERROR_CHANNEL_CLOSE_FAILED : 'ChannelClose failed. Channel not open',
                #ERROR_UNSUPPORTED_BUS_TYPE : 'Unsupported bus type',
                ERROR_DEVICE_DOES_NOT_SUPPORT_OPERATION : 'Device does not support operation',
                #ERROR_DEVICE_NOT_OPEN : 'Device not open',
                #ERROR_UNABLE_TO_CONTACT_SERVICE : 'Unable to contact service',
                #ERROR_UNABLE_TO_BIND_SOCKET : 'Unable to bind to socket',
                ERROR_DEVICEOPEN_FAILED : 'Device open failed',
                ERROR_INVALID_DEVNODE : 'Invalid device node',
                #ERROR_TEST_EMAIL_FAILED : "Email test failed",
                ERROR_INVALID_HOSTNAME : "Invalid hostname ip address",
                ERROR_INVALID_PORT_NUMBER : "Invalid JetDirect port number",
                #ERROR_INTERFACE_BUSY : "Interface busy",
                ERROR_NO_CUPS_QUEUE_FOUND_FOR_DEVICE : "No CUPS queue found for device.",
                #ERROR_UNSUPPORTED_MODEL : "Unsupported printer model.",
                #ERROR_INVALID_GUI_NAME: "Invalid GUI",
                ERROR_DATFILE_ERROR: "DAT file error",
                ERROR_INVALID_TIMEOUT: "Invalid timeout",
                ERROR_IO_TIMEOUT: "I/O timeout",
                ERROR_FAX_INCOMPATIBLE_OPTIONS: "Incompatible fax options",
                ERROR_FAX_INVALID_FAX_FILE: "Invalid fax file",
                #ERROR_FAX_MUST_RUN_SENDFAX_FIRST: "Run sendfax first",
                #ERROR_FAX_PROCESSING: "Fax processing",
                #ERROR_FAX_READY: "Fax ready",
                ERROR_FAX_FILE_NOT_FOUND: "Fax file not found",
                ERROR_INTERNAL : 'Unknown internal error',
               }
               

class Error(Exception):
    def __init__(self, opt=ERROR_INTERNAL):
        self.opt = opt
        self.msg = ERROR_STRINGS.get(opt, ERROR_STRINGS[ERROR_INTERNAL])
        log.debug("Exception: %d (%s)" % (opt, self.msg))
        Exception.__init__(self, self.msg, opt)


# Make sure True and False are avail. in pre-2.2 versions
try:
    True
except NameError:
    True = (1==1)
    False = not True

# as new translations are completed, add them here
supported_locales =  { 'en_US': ('us', 'en', 'en_us', 'american', 'america', 'usa', 'english'),
                       'zh_CN': ('zh', 'cn', 'zh_cn' , 'china', 'chinese', 'prc'),
                       'de_DE': ('de', 'de_de', 'german', 'deutsche'),
                       'fr_FR': ('fr', 'fr_fr', 'france', 'french', 'français'),
                       'it_IT': ('it', 'it_it', 'italy', 'italian', 'italiano'),
                       'ru_RU': ('ru', 'ru_ru', 'russian'),
                       'pt_BR': ('pt', 'br', 'pt_br', 'brazil', 'brazilian', 'portuguese', 'brasil', 'portuguesa'),
                       'es_MX': ('es', 'mx', 'es_mx', 'mexico', 'spain', 'spanish', 'espanol', 'español'),
                     }
                     
                     
