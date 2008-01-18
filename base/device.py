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
import socket
import re
import gzip
import os.path
import time
import urllib
import StringIO
import httplib

# Local
from g import *
from codes import *
from msg import *
import utils, status, pml, service, tui
from prnt import pcl, ldl, cups
import models, mdns, slp
from strings import StringTable

try:
    import hpmudext
except ImportError:
    if not os.getenv("HPLIP_BUILD"):
        log.error("HPMUDEXT could not be loaded. Please check HPLIP installation.")
        sys.exit(1)


DEFAULT_PROBE_BUS = 'usb,par,cups'
VALID_BUSES = ('par', 'net', 'cups', 'usb') #, 'bt', 'fw')
VALID_BUSES_WO_CUPS = ('par', 'net', 'usb')
DEFAULT_FILTER = None
VALID_FILTERS = ('print', 'scan', 'fax', 'pcard', 'copy')

pat_deviceuri = re.compile(r"""(.*):/(.*?)/(\S*?)\?(?:serial=(\S*)|device=(\S*)|ip=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[^&]*))(?:&port=(\d))?""", re.IGNORECASE)
http_pat_url = re.compile(r"""/(.*?)/(\S*?)\?(?:serial=(\S*)|device=(\S*))&loc=(\S*)""", re.IGNORECASE)
direct_pat = re.compile(r'direct (.*?) "(.*?)" "(.*?)" "(.*?)"', re.IGNORECASE)

# Pattern to check for ; at end of CTR fields
# Note: If ; not present, CTR value is invalid
pat_dynamic_ctr = re.compile(r"""CTR:\d*\s.*;""", re.IGNORECASE)

MAX_BUFFER = 8192

# Cache for model data
model_dat = models.ModelData()

ip_pat = re.compile(r"""\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b""", re.IGNORECASE)

dev_pat = re.compile(r"""/dev/.+""", re.IGNORECASE)

usb_pat = re.compile(r"""(\d+):(\d+)""", re.IGNORECASE)
    
    
def makeURI(param, port=1):  
    

    cups_uri, sane_uri, fax_uri = '', '', ''
    found = False

    # see if the param represents a hostname
    try:
        param = socket.gethostbyname(param)
    except socket.gaierror:
        log.debug("Gethostbyname() failed. Trying other patterns...")

    if dev_pat.search(param) is not None: # parallel
        log.debug("Trying parallel with %s" % param)

        result_code, uri = hpmudext.make_par_uri(param)
        
        if result_code == hpmudext.HPMUD_R_OK and uri: 
            log.debug("Found: %s" % uri)
            found = True
            cups_uri = uri
        else:
            log.debug("Not found.")

    elif usb_pat.search(param) is not None: # USB
        match_obj = usb_pat.search(param)
        usb_bus_id = match_obj.group(1)
        usb_dev_id = match_obj.group(2)

        log.debug("Trying USB with bus=%s dev=%s..." % (usb_bus_id, usb_dev_id))
        result_code, uri = hpmudext.make_usb_uri(usb_bus_id, usb_dev_id)

        if result_code == ERROR_SUCCESS and uri:
            log.debug("Found: %s" % uri)
            found = True
            cups_uri = uri
        else:
            log.debug("Not found.")

    elif ip_pat.search(param) is not None: # IPv4 dotted quad
        log.debug("Trying IP address %s" % param)

        result_code, uri = hpmudext.make_net_uri(param, port)

        if result_code == hpmudext.HPMUD_R_OK and uri:
            log.debug("Found: %s" % uri)
            found = True
            cups_uri = uri
        else:
            log.debug("Not found.")

    else: # serial
        log.debug("Trying serial number %s" % param)
        devices = probeDevices(bus="usb,par")

        for d in devices:
            log.debug(d)

            # usb has serial in URI...
            back_end, is_hp, bus, model, serial, dev_file, host, port = \
                parseDeviceURI(d)

            if bus == 'par': # ...parallel does not. Must get Device ID to obtain it...
                mq = queryModelByURI(d)

                result_code, device_id = \
                    hpmudext.device_open(d, mq.get('io-mode', hpmudext.HPMUD_UNI_MODE))

                if result_code == hpmudext.HPMUD_R_OK:
                    result_code, data = hpmudext.get_device_id(device_id)
                    serial = parseDeviceID(data).get('SN', '')
                    hpmudext.close_device(device_id)

            if serial.lower() == param.lower():
                #log.debug("Match")
                log.debug("Found: %s" % d)
                found = True
                cups_uri = d
                break
            else:
                log.debug("Not found.")

    if found:
        try:
            mq = queryModelByURI(cups_uri)
        except Error, e:
            log.error("Error: %s" % e.msg)
            cups_uri, sane_uri, fax_uri = '', '', ''
        else:
            if mq.get('scan-type', 0):
                sane_uri = cups_uri.replace("hp:", "hpaio:")

            if mq.get('fax-type', 0):
                fax_uri = cups_uri.replace("hp:", "hpfax:")

    else:
        scan_uri, fax_uri = '', ''

    if cups_uri:
        user_cfg.last_used.device_uri = cups_uri

    return cups_uri, sane_uri, fax_uri


def queryModelByModel(model):
    model = normalizeModelName(model).lower()
    return model_dat[model]

def queryModelByURI(device_uri):
    try:
        back_end, is_hp, bus, model, \
            serial, dev_file, host, port = \
            parseDeviceURI(device_uri)
    except Error:
        raise Error(ERROR_INVALID_DEVICE_URI)
    else:
        return queryModelByModel(model)

        
def __checkFilter(filter, mq):
    for f, p in filter.items():
        if f is not None:
            op, val = p
            if not op(mq[f], val):
                return False
     
    return True   

def getInteractiveDeviceURI(bus='cups,usb,par', filter=DEFAULT_FILTER, back_end_filter=('hp',)):
    probed_devices = probeDevices(bus.lower(), filter=filter)
    cups_printers = cups.getPrinters()
    log.debug(probed_devices)
    log.debug(cups_printers)
    max_deviceid_size, x, devices = 0, 0, {}

    for d in probed_devices:
        printers = []

        back_end, is_hp, bus, model, serial, dev_file, host, port = \
            parseDeviceURI(d)

        if back_end in back_end_filter:
            for p in cups_printers:
                if p.device_uri == d:
                    printers.append(p.name)

            devices[x] = (d, printers)
            x += 1
            max_deviceid_size = max(len(d), max_deviceid_size)

    if x == 0:
        log.error("No devices found.")
        raise Error(ERROR_NO_PROBED_DEVICES_FOUND)

    elif x == 1:
        log.info(log.bold("Using device: %s" % devices[0][0]))
        user_cfg.last_used.device_uri = devices[0][0]
        return devices[0][0]

    else:
        last_used_device_uri = user_cfg.last_used.device_uri
        last_used_index = None

        rows, cols = utils.ttysize()
        if cols > 100: cols = 100

        log.info(log.bold("\nChoose device from probed devices connected on bus(es): %s:\n" % bus))
        formatter = utils.TextFormatter(
                (
                    {'width': 4},
                    {'width': max_deviceid_size, 'margin': 2},
                    {'width': cols-max_deviceid_size-8, 'margin': 2},
                )
            )
        log.info(formatter.compose(("Num.", "Device-URI", "CUPS printer(s)")))
        log.info(formatter.compose(('-'*4, '-'*(max_deviceid_size), '-'*(cols-max_deviceid_size-10))))

        for y in range(x):
            log.info(formatter.compose((str(y), devices[y][0], ', '.join(devices[y][1]))))

            if last_used_device_uri == devices[y][0]:
                last_used_index = y

        if last_used_index is not None:
            ok, i = tui.enter_range("\nEnter number 0...%d for device (q=quit, enter=last used device: %s) ?" % 
                ((x-1), last_used_device_uri), 0, (x-1), -1)

        else:
            ok, i = tui.enter_range("\nEnter number 0...%d for device (q=quit) ?" % 
                (x-1), 0, (x-1), -1)

        if not ok:
            sys.exit(0) 

        if last_used_index is not None and i == -1:
            i = last_used_index

        user_cfg.last_used.device_uri = devices[i][0]
        return devices[i][0]


def probeDevices(bus='cups,usb,par', timeout=10,
                 ttl=4, filter=DEFAULT_FILTER,  search='', net_search='slp', 
                 back_end_filter=('hp',)):

    num_devices, ret_devices = 0, {}

    if search:
        try:
            search_pat = re.compile(search, re.IGNORECASE)
        except:
            log.error("Invalid search pattern. Search uses standard regular expressions. For more info, see: http://www.amk.ca/python/howto/regex/")
            search = ''

    buses = bus
    for bus in buses.split(','):
        bus = bus.lower().strip()

        if bus not in VALID_BUSES:
            log.error("Invalid bus: %s" % bus)
            continue

        if bus == 'net':
            if net_search == 'slp':
                try:
                    detected_devices = slp.detectNetworkDevices(ttl, timeout)
                except Error, socket.error:
                    log.error("An error occured during network probe.")
                    raise ERROR_INTERNAL
            else:
                try:
                    detected_devices = mdns.detectNetworkDevices(ttl, timeout)
                except Error, socket.error:
                    log.error("An error occured during network probe.")
                    raise ERROR_INTERNAL

            for ip in detected_devices:
                update_spinner()
                hn = detected_devices[ip].get('hn', '?UNKNOWN?')
                num_devices_on_jd = detected_devices[ip].get('num_devices', 0)
                num_ports_on_jd = detected_devices[ip].get('num_ports', 1)

                if num_devices_on_jd > 0:
                    for port in range(num_ports_on_jd):
                        dev = detected_devices[ip].get('device%d' % (port+1), '0')

                        if dev is not None and dev != '0':
                            device_id = parseDeviceID(dev)
                            model = normalizeModelName(device_id.get('MDL', '?UNKNOWN?'))

                            if num_ports_on_jd == 1:
                                device_uri = 'hp:/net/%s?ip=%s' % (model, ip)
                            else:
                                device_uri = 'hp:/net/%s?ip=%s&port=%d' % (model, ip, (port+1))

                            include = True
                            mq = queryModelByModel(model)

                            if not mq:
                                log.debug("Not found.")
                                include = False

                            elif int(mq.get('support-type', SUPPORT_TYPE_NONE)) == SUPPORT_TYPE_NONE:
                                log.debug("Not supported.")
                                include = False
                            
                            elif filter not in (None, 'print', 'print-type'):
                                include = __checkFilter(filter, mq)
                                
                            if include:
                                ret_devices[device_uri] = (model, model, hn)

        elif bus in ('usb', 'par'):
            if bus == 'par':
                b = hpmudext.HPMUD_BUS_PARALLEL
            else:
                b = hpmudext.HPMUD_BUS_USB

            result_code, data = hpmudext.probe_devices(b)

            if result_code == hpmudext.HPMUD_R_OK:
                for x in data.splitlines():
                    m = direct_pat.match(x)

                    uri = m.group(1) or ''
                    mdl = m.group(2) or ''
                    desc = m.group(3) or ''
                    devid = m.group(4) or ''

                    log.debug(uri)

                    try:
                        back_end, is_hp, bus, model, serial, dev_file, host, port = \
                            parseDeviceURI(uri)
                    except Error:
                        continue

                    include = True

                    if mdl and uri and is_hp:
                        mq = queryModelByModel(model)

                        if not mq:
                            log.debug("Not found.")
                            include = False

                        elif int(mq.get('support-type', SUPPORT_TYPE_NONE)) == SUPPORT_TYPE_NONE:
                            log.debug("Not supported.")
                            include = False

                        elif filter not in (None, 'print', 'print-type'):
                            include = __checkFilter(filter, mq)

                        if include:
                            ret_devices[uri] = (mdl, desc, devid) # model w/ _'s, mdl w/o

        elif bus == 'cups':
            cups_printers = cups.getPrinters()
            x = len(cups_printers)

            for p in cups_printers:
                device_uri = p.device_uri
                log.debug("%s: %s" % (device_uri, p.name))

                if device_uri != '':
                    try:
                        back_end, is_hp, bs, model, serial, dev_file, host, port = \
                            parseDeviceURI(device_uri)
                    except Error:
                        log.warning("Inrecognized URI: %s" % device_uri)
                        continue

                    if not is_hp:
                        continue

                    include = True
                    mq = queryModelByModel(model)

                    if not mq:
                        include = False
                        log.debug("Not found.")

                    elif int(mq.get('support-type', SUPPORT_TYPE_NONE)) == SUPPORT_TYPE_NONE:
                        log.debug("Not supported.")
                        include = False

                    elif filter not in (None, 'print', 'print-type'):
                        include = __checkFilter(filter, mq)

                    if include:
                        ret_devices[device_uri] = (model, model, '')

    probed_devices = {}
    for uri in ret_devices:
        num_devices += 1
        mdl, model, devid_or_hn = ret_devices[uri]

        include = True
        if search:
            match_obj = search_pat.search("%s %s %s %s" % (mdl, model, devid_or_hn, uri))

            if match_obj is None:
                log.debug("%s %s %s %s: Does not match search '%s'." % (mdl, model, devid_or_hn, uri, search))
                include = False

        if include:
            probed_devices[uri] = ret_devices[uri]

    cleanup_spinner()
    return probed_devices


def getSupportedCUPSDevices(back_end_filter=['hp']):
    devices = {}
    printers = cups.getPrinters()

    for p in printers:
        try:
            back_end, is_hp, bus, model, serial, dev_file, host, port = \
                parseDeviceURI(p.device_uri)

        except Error:
            continue

        if back_end_filter == '*' or back_end in back_end_filter:
            try:
                devices[p.device_uri]
            except KeyError:
                devices[p.device_uri] = [p.name]
            else:
                devices[p.device_uri].append(p.name)

    return devices # { 'device_uri' : [ CUPS printer list ], ... }


def parseDeviceID(device_id):
    d= {}
    x = [y.strip() for y in device_id.strip().split(';') if y]

    for z in x:
        y = z.split(':')
        try:
            d.setdefault(y[0].strip(), y[1])
        except IndexError:
            d.setdefault(y[0].strip(), None)

    d.setdefault('MDL', '')
    d.setdefault('SN',  '')

    if 'MODEL' in d:
        d['MDL'] = d['MODEL']
        del d['MODEL']

    if 'SERIAL' in d:
        d['SN'] = d['SERIAL']
        del d['SERIAL']

    elif 'SERN' in d:
        d['SN'] = d['SERN']
        del d['SERN']

    if d['SN'].startswith('X'):
        d['SN'] = ''

    return d


def parseDynamicCounter(ctr_field, convert_to_int=True):
    counter, value = ctr_field.split(' ')
    try:
        counter = int(utils.xlstrip(str(counter), '0') or '0')

        if convert_to_int:
            value = int(utils.xlstrip(str(value), '0') or '0')
    except ValueError:
        if convert_to_int:
            counter, value = 0, 0
        else:
            counter, value = 0, ''

    return counter, value


def parseDeviceURI(device_uri):
    #print repr(pat_deviceuri)
    #print repr(device_uri)
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


def validateBusList(bus, allow_cups=True):
    for x in bus.split(','):
        bb = x.lower().strip()
        if allow_cups:
            vb = VALID_BUSES
        else:
            vb = VALID_BUSES_WO_CUPS
        if bb not in vb:
            log.error("Invalid bus name: %s" % bb)
            return False

    return True

def validateFilterList(filter):
    if filter is None:
        return True
        
    for f in filter.split(','):
        if f not in VALID_FILTERS:
            log.error("Invalid term '%s' in filter list" % f)
            return False

    return True


inter_pat = re.compile(r"""%(.*)%""", re.IGNORECASE)
st = StringTable()
strings_init = False

def initStrings():
    global strings_init, st
    strings_init = True
    cycles = 0

    while True:
        found = False

        for s in st.string_table:
            short_string, long_string = st.string_table[s]
            short_replace, long_replace = short_string, long_string

            try:
                short_match = inter_pat.match(short_string).group(1)
            except (AttributeError, TypeError):
                short_match = None

            if short_match is not None:
                found = True

                try:
                    short_replace, dummy = st.string_table[short_match]
                except KeyError:
                    log.error("String interpolation error: %s" % short_match)

            try:
                long_match = inter_pat.match(long_string).group(1)
            except (AttributeError, TypeError):
                long_match = None

            if long_match is not None:
                found = True

                try:
                    dummy, long_replace = st.string_table[long_match]
                except KeyError:
                    log.error("String interpolation error: %s" % long_match)

            if found:
                st.string_table[s] = (short_replace, long_replace)

        if not found:
            break
        else:
            cycles +=1
            if cycles > 1000:
                break


def queryString(string_id, typ=0):
    if not strings_init:
        initStrings()

    log.debug("queryString(%s)" % string_id)
    s = st.string_table.get(str(string_id), ('', ''))[typ]

    if type(s) == type(''):
        return s

    return s()


AGENT_types = { AGENT_TYPE_NONE        : 'invalid',
                AGENT_TYPE_BLACK       : 'black',
                AGENT_TYPE_CMY         : 'cmy',
                AGENT_TYPE_KCM         : 'kcm',
                AGENT_TYPE_CYAN        : 'cyan',
                AGENT_TYPE_MAGENTA     : 'magenta',
                AGENT_TYPE_YELLOW      : 'yellow',
                AGENT_TYPE_CYAN_LOW    : 'photo_cyan',
                AGENT_TYPE_MAGENTA_LOW : 'photo_magenta',
                AGENT_TYPE_YELLOW_LOW  : 'photo_yellow',
                AGENT_TYPE_GGK         : 'photo_gray',
                AGENT_TYPE_BLUE        : 'photo_blue',
                AGENT_TYPE_KCMY_CM     : 'kcmy_cm',
                AGENT_TYPE_LC_LM       : 'photo_cyan_and_photo_magenta',
                #AGENT_TYPE_Y_M         : 'yellow_and_magenta',
                #AGENT_TYPE_C_K         : 'cyan_and_black',
                AGENT_TYPE_LG_PK       : 'light_gray_and_photo_black',
                AGENT_TYPE_LG          : 'light_gray',
                AGENT_TYPE_G           : 'medium_gray',
                AGENT_TYPE_PG          : 'photo_gray',
                AGENT_TYPE_C_M         : 'cyan_and_magenta',
                AGENT_TYPE_K_Y         : 'black_and_yellow',
                AGENT_TYPE_UNSPECIFIED : 'unspecified', # Kind=5,6
            }

AGENT_kinds = {AGENT_KIND_NONE            : 'invalid',
                AGENT_KIND_HEAD            : 'head',
                AGENT_KIND_SUPPLY          : 'supply',
                AGENT_KIND_HEAD_AND_SUPPLY : 'cartridge',
                AGENT_KIND_TONER_CARTRIDGE : 'toner',
                AGENT_KIND_MAINT_KIT       : 'maint_kit', # fuser
                AGENT_KIND_ADF_KIT         : 'adf_kit',
                AGENT_KIND_DRUM_KIT        : 'drum_kit',
                AGENT_KIND_TRANSFER_KIT    : 'transfer_kit',
                AGENT_KIND_INT_BATTERY     : 'battery',
                AGENT_KIND_UNKNOWN         : 'unknown',
              }

AGENT_healths = {AGENT_HEALTH_OK           : 'ok',
                  AGENT_HEALTH_MISINSTALLED : 'misinstalled', # supply/cart
                  #AGENT_HEALTH_FAIR_MODERATE : '',
                  AGENT_HEALTH_INCORRECT    : 'incorrect',
                  AGENT_HEALTH_FAILED       : 'failed',
                  AGENT_HEALTH_OVERTEMP     : 'overtemp', # battery
                  AGENT_HEALTH_CHARGING     : 'charging', # battery
                  AGENT_HEALTH_DISCHARGING  : 'discharging', # battery
                }


AGENT_levels = {AGENT_LEVEL_TRIGGER_MAY_BE_LOW : 'low',
                 AGENT_LEVEL_TRIGGER_PROBABLY_OUT : 'low',
                 AGENT_LEVEL_TRIGGER_ALMOST_DEFINITELY_OUT : 'out',
               }


MODEL_UI_REPLACEMENTS = {'laserjet'   : 'LaserJet',
                          'psc'        : 'PSC',
                          'officejet'  : 'Officejet',
                          'deskjet'    : 'Deskjet',
                          'hp'         : 'HP',
                          'business'   : 'Business',
                          'inkjet'     : 'Inkjet',
                          'photosmart' : 'Photosmart',
                          'color'      : 'Color',
                          'series'     : 'series',
                          'printer'    : 'Printer',
                          'mfp'        : 'MFP',
                          'mopier'     : 'Mopier',
                          'pro'        : 'Pro',
                        }


def normalizeModelUIName(model):
    if not model.lower().startswith('hp'):
        z = 'HP ' + model.replace('_', ' ')
    else:
        z = model.replace('_', ' ')

    y = []
    for x in z.split():
        xx = x.lower()
        y.append(MODEL_UI_REPLACEMENTS.get(xx, xx))

    return ' '.join(y)

def normalizeModelName(model):
    return utils.xstrip(model.replace(' ', '_').replace('__', '_').replace('~','').replace('/', '_'), '_')


def isLocal(bus):
    return bus in ('par', 'usb', 'fw', 'bt')


# **************************************************************************** #

string_cache = {}

class Device(object):
    def __init__(self, device_uri, printer_name=None,
                hpssd_sock=None,
                callback=None):

        log.debug("Device URI: %s" % device_uri)
        log.debug("Printer: %s" % printer_name)

        printers = cups.getPrinters()

        if device_uri is None and printer_name is not None:
            for p in printers:
                if p.name.lower() == printer_name.lower():
                    device_uri = p.device_uri
                    break
            else:
                raise Error(ERROR_DEVICE_NOT_FOUND)


        self.device_uri = device_uri
        self.callback = callback
        self.close_socket = False
        self.query_device_thread = None

        try:
            self.back_end, self.is_hp, self.bus, self.model, \
                self.serial, self.dev_file, self.host, self.port = \
                parseDeviceURI(self.device_uri)
        except Error:
            self.io_state = IO_STATE_NON_HP
            raise Error(ERROR_INVALID_DEVICE_URI)

        log.debug("URI: backend=%s, is_hp=%s, bus=%s, model=%s, serial=%s, dev=%s, host=%s, port=%d" % \
            (self.back_end, self.is_hp, self.bus, self.model, self.serial, self.dev_file, self.host, self.port))

        self.model_ui = normalizeModelUIName(self.model)
        self.model = normalizeModelName(self.model)

        log.debug("Model/UI model: %s/%s" % (self.model, self.model_ui))

        if hpssd_sock is None:
            self.hpssd_sock = service.startup()
        else:
            self.hpssd_sock = hpssd_sock

        log.debug("hpssd socket: %d" % self.hpssd_sock.fileno())

        service.setAlertsEx(self.hpssd_sock)

        self.mq = {} # Model query
        self.dq = {} # Device query
        self.cups_printers = []
        self.channels = {} # { 'SERVICENAME' : channel_id, ... }
        self.device_id = -1
        self.r_values = None # ( r_value, r_value_str, rg, rr )
        self.deviceID = ''
        self.panel_check = True
        self.io_state = IO_STATE_HP_READY
        self.is_local = isLocal(self.bus)

        self.supported = False

        self.queryModel()
        if not self.supported:
            log.error("Unsupported model: %s" % self.model)
            self.sendEvent(STATUS_DEVICE_UNSUPPORTED)
        else:
            self.supported = True


        self.mq.update({'model'    : self.model,
                        'model-ui' : self.model_ui})

        self.error_state = ERROR_STATE_ERROR
        self.device_state = DEVICE_STATE_NOT_FOUND
        self.status_code = EVENT_ERROR_DEVICE_NOT_FOUND

        for p in printers:
            if self.device_uri == p.device_uri:
                self.cups_printers.append(p.name)
                self.state = p.state # ?

                if self.io_state == IO_STATE_NON_HP:
                    self.model = p.makemodel.split(',')[0]

        try:
            self.first_cups_printer = self.cups_printers[0]
        except IndexError:
            self.first_cups_printer = ''

        if self.mq.get('fax-type', FAX_TYPE_NONE) != FAX_TYPE_NONE:
            self.dq.update({ 'fax-uri' : self.device_uri.replace('hp:/', 'hpfax:/').replace('hpaio:/', 'hpfax:/')})

        if self.mq.get('scan-type', SCAN_TYPE_NONE) != SCAN_TYPE_NONE:
            self.dq.update({ 'scan-uri' : self.device_uri.replace('hp:/', 'hpaio:/').replace('hpfax:/', 'hpaio:/')})

        self.dq.update({
            'back-end'         : self.back_end,
            'is-hp'            : self.is_hp,
            'serial'           : self.serial,
            'dev-file'         : self.dev_file,
            'host'             : self.host,
            'port'             : self.port,
            'cups-printer'     : ','.join(self.cups_printers),
            'status-code'      : self.status_code,
            'status-desc'      : '',
            'deviceid'         : '',
            'panel'            : 0,
            'panel-line1'      : '',
            'panel-line2'      : '',
            'device-state'     : self.device_state,
            'error-state'      : self.error_state,
            'device-uri'       : self.device_uri,
            'cups-uri'         : self.device_uri.replace('hpfax:/', 'hp:/').replace('hpaio:/', 'hp:/'),
            })

        self.device_vars = {
            'URI'        : self.device_uri,
            'DEVICE_URI' : self.device_uri,
            'SCAN_URI'   : self.device_uri.replace('hp:', 'hpaio:'),
            'SANE_URI'   : self.device_uri.replace('hp:', 'hpaio:'),
            'FAX_URI'    : self.device_uri.replace('hp:', 'hpfax:'),
            'PRINTER'    : self.first_cups_printer,
            'HOME'       : prop.home_dir,
                           }            

    def xmitHpssdMessage(self, msg_type, other_fields={},
                         payload=None, timeout=prop.read_timeout):

        return xmitMessage(self.hpssd_sock, msg_type,
                                payload, other_fields, timeout)

    def quit(self):
        if self.close_hpssd_socket:
            self.hpssd_sock.close()                

    def queryModel(self):
        if not self.mq:
            self.mq = queryModelByURI(self.device_uri)

        self.supported = bool(self.mq)

        if self.supported:
            for m in self.mq:
                self.__dict__[m.replace('-','_')] = self.mq[m]

    def queryString(self, string_id):
        return queryString(string_id)

    def open(self, open_for_printing=False):
        if self.supported and self.io_state in (IO_STATE_HP_READY, IO_STATE_HP_NOT_AVAIL):
            prev_device_state = self.device_state
            self.io_state = IO_STATE_HP_NOT_AVAIL
            self.device_state = DEVICE_STATE_NOT_FOUND
            self.error_state = ERROR_STATE_ERROR
            self.status_code = EVENT_ERROR_DEVICE_NOT_FOUND
            self.device_id = -1
            self.open_for_printing = open_for_printing

            if open_for_printing:
                log.debug("Opening device: %s (for printing)" % self.device_uri)
                self.io_mode = self.mq.get('io-mode', hpmudext.HPMUD_UNI_MODE)
            else:
                log.debug("Opening device: %s (not for printing)" % self.device_uri)
                self.io_mode = self.mq.get('io-mfp-mode', hpmudext.HPMUD_UNI_MODE)

            log.debug("I/O mode=%d" % self.io_mode)
            result_code, self.device_id = \
                hpmudext.open_device(self.device_uri, self.io_mode)

            if result_code != hpmudext.HPMUD_R_OK:
                self.sendEvent(result_code + ERROR_CODE_BASE, typ='error')

                if result_code == hpmudext.HPMUD_R_DEVICE_BUSY:
                    log.error("Device busy: %s" % self.device_uri)
                else:
                    log.error("Unable to communicate with device (code=%d): %s" % (result_code, self.device_uri))

                raise Error(ERROR_DEVICE_NOT_FOUND)

            else:
                log.debug("device-id=%d" % self.device_id)
                self.io_state = IO_STATE_HP_OPEN
                self.error_state = ERROR_STATE_CLEAR
                log.debug("Opened device: %s (backend=%s, is_hp=%s, bus=%s, model=%s, dev=%s, serial=%s, host=%s, port=%d)" %
                    (self.back_end, self.device_uri, self.is_hp, self.bus, self.model, 
                     self.dev_file, self.serial, self.host, self.port))

                if prev_device_state == DEVICE_STATE_NOT_FOUND:
                    self.device_state = DEVICE_STATE_JUST_FOUND
                else:
                    self.device_state = DEVICE_STATE_FOUND

                self.getDeviceID()
                self.getSerialNumber()
                return self.device_id



    def close(self):
        if self.io_state == IO_STATE_HP_OPEN:
            log.debug("Closing device...")

            if len(self.channels) > 0:

                for c in self.channels.keys():
                    self.__closeChannel(c)

            result_code = hpmudext.close_device(self.device_id)
            log.debug("Result-code = %d" % result_code)

            self.channels.clear()
            self.io_state = IO_STATE_HP_READY


    def __openChannel(self, service_name):
        if self.io_state == IO_STATE_HP_OPEN:
            if service_name == hpmudext.HPMUD_S_PRINT_CHANNEL and not self.open_for_printing:
                self.close()
                self.open(True)
            elif service_name != hpmudext.HPMUD_S_PRINT_CHANNEL and self.open_for_printing:
                self.close()
                self.open(False)
        else:    
            self.open(service_name == hpmudext.HPMUD_S_PRINT_CHANNEL)

        #if not self.mq['io-mode'] == IO_MODE_UNI:
        if 1:
            service_name = service_name.upper()

            if service_name not in self.channels:
                log.debug("Opening %s channel..." % service_name)

                result_code, channel_id = hpmudext.open_channel(self.device_id, service_name)

                self.channels[service_name] = channel_id
                log.debug("channel-id=%d" % channel_id)
                return channel_id
            else:
                return self.channels[service_name]
        else:
            return -1


    def openChannel(self, service_name):
        return self.__openChannel(service_name)

    def openPrint(self):
        return self.__openChannel(hpmudext.HPMUD_S_PRINT_CHANNEL)

    def openFax(self):
        return self.__openChannel(hpmudext.HPMUD_S_FAX_SEND_CHANNEL)

    def openPCard(self):
        return self.__openChannel(hpmudext.HPMUD_S_MEMORY_CARD_CHANNEL)

    def openEWS(self):
        return self.__openChannel(hpmudext.HPMUD_S_EWS_CHANNEL)

    def closePrint(self):
        return self.__closeChannel(hpmudext.HPMUD_S_PRINT_CHANNEL)

    def closePCard(self):
        return self.__closeChannel(hpmudext.HPMUD_S_MEMORY_CARD_CHANNEL)

    def closeFax(self):
        return self.__closeChannel(hpmudext.HPMUD_S_FAX_SEND_CHANNEL)

    def openPML(self):
        return self.__openChannel(hpmudext.HPMUD_S_PML_CHANNEL)

    def closePML(self):
        return self.__closeChannel(hpmudext.HPMUD_S_PML_CHANNEL)

    def closeEWS(self):
        return self.__closeChannel(hpmudext.HPMUD_S_EWS_CHANNEL)

    def openCfgUpload(self):
        return self.__openChannel(hpmudext.HPMUD_S_CONFIG_UPLOAD_CHANNEL)

    def closeCfgUpload(self):
        return self.__closeChannel(hpmudext.HPMUD_S_CONFIG_UPLOAD_CHANNEL)

    def openCfgDownload(self):
        return self.__openChannel(hpmudext.HPMUD_S_CONFIG_DOWNLOAD_CHANNEL)

    def closeCfgDownload(self):
        return self.__closeChannel(hpmudext.HPMUD_S_CONFIG_DOWNLOAD_CHANNEL)

    def openSoapFax(self):
        return self.__openChannel(hpmudext.HPMUD_S_SOAP_FAX)
        
    def closeSoapFax(self):
        return self.__closeChannel(hpmudext.HPMUD_S_SOAP_FAX)
        
    def __closeChannel(self, service_name):
        #if not self.mq['io-mode'] == IO_MODE_UNI and \
        if self.io_state == IO_STATE_HP_OPEN:

            service_name = service_name.upper()

            if service_name in self.channels:
                log.debug("Closing %s channel..." % service_name)

                result_code = hpmudext.close_channel(self.device_id, 
                    self.channels[service_name])

                del self.channels[service_name]


    def closeChannel(self, service_name):
        return self.__closeChannel(service_name)


    def getDeviceID(self):
        needs_close = False
        if self.io_state != IO_STATE_HP_OPEN:
           self.open()
           needs_close = True

        result_code, data = hpmudext.get_device_id(self.device_id) 

        if result_code != hpmudext.HPMUD_R_OK:
            self.raw_deviceID = ''
            self.deviceID = {}
        else:
            self.raw_deviceID = data
            self.deviceID = parseDeviceID(data)
        
        if needs_close:
            self.close()

        return self.deviceID


    def getSerialNumber(self):
        if self.serial:
            return

        try:
            self.serial = self.deviceID['SN']
        except KeyError:
            pass
        else:
            if self.serial:
                return

        if self.mq.get('status-type', STATUS_TYPE_NONE) != STATUS_TYPE_NONE: # and \
            #not self.mq.get('io-mode', IO_MODE_UNI) == IO_MODE_UNI:

            try:
                try:
                    error_code, self.serial = self.getPML(pml.OID_SERIAL_NUMBER)
                except Error:
                    self.serial = ''
            finally:
                self.closePML()

        if self.serial is None:
            self.serial = ''


    def getThreeBitStatus(self):
        pass


    def getStatusFromDeviceID(self):
        self.getDeviceID()
        return status.parseStatus(parseDeviceID(self.raw_deviceID))


    def __parseRValues(self, r_value):
        r_value_str = str(r_value)
        r_value_str = ''.join(['0'*(9 - len(r_value_str)), r_value_str])
        rg, rr = r_value_str[:3], r_value_str[3:]
        r_value = int(rr)
        self.r_values = r_value, r_value_str, rg, rr
        return r_value, r_value_str, rg, rr


    def getRValues(self, r_type, status_type, dynamic_counters):
        r_value, r_value_str, rg, rr = 0, '000000000', '000', '000000'

        if r_type > 0 and \
            dynamic_counters != STATUS_DYNAMIC_COUNTERS_NONE:

            if self.r_values is None:
                fields, data, result_code = \
                    self.xmitHpssdMessage('GetValue', {'device-uri': self.device_uri, 'key': 'r_value'})

                if result_code == ERROR_SUCCESS and data:
                    try:
                        r_value = int(data.strip())
                    except:
                        pass
                    else:
                        log.debug("r_value=%d" % r_value)
                        r_value, r_value_str, rg, rr = self.__parseRValues(r_value)

                        return r_value, r_value_str, rg, rr

            if self.r_values is None:   

                if status_type ==  STATUS_TYPE_S and \
                    self.is_local and \
                    dynamic_counters != STATUS_DYNAMIC_COUNTERS_PML_SNMP:

                    try:    
                        try:
                            r_value = self.getDynamicCounter(140)

                            if r_value is not None:
                                log.debug("r_value=%d" % r_value)
                                r_value, r_value_str, rg, rr = self.__parseRValues(r_value)

                                fields, data, result_code = \
                                    self.xmitHpssdMessage('SetValue', {'device-uri': self.device_uri, 'key': 'r_value', 'value': r_value})

                            else:
                                log.error("Error attempting to read r-value (2).")
                                r_value = 0
                        except Error:
                            log.error("Error attempting to read r-value (1).")
                            r_value = 0
                    finally:
                        self.closePrint()


                elif (status_type ==  STATUS_TYPE_S and 
                      dynamic_counters == STATUS_DYNAMIC_COUNTERS_PCL and 
                      not self.is_local) or \
                      dynamic_counters == STATUS_DYNAMIC_COUNTERS_PML_SNMP:

                    try:
                        result_code, r_value = self.getPML(pml.OID_R_SETTING)

                        if r_value is not None:
                            log.debug("r_value=%d" % r_value)
                            r_value, r_value_str, rg, rr = self.__parseRValues(r_value)

                            fields, data, result_code = \
                                self.xmitHpssdMessage('SetValue', {'device-uri': self.device_uri, 'key': 'r_value', 'value': r_value})
                        else:
                            r_value = 0

                    finally:
                        self.closePML()

            else:
                r_value, r_value_str, rg, rr = self.r_values

        return r_value, r_value_str, rg, rr


    def queryDevice(self, quick=False, no_fwd=False, reread_cups_printers=False):
        if not self.supported:
            self.dq = {}
            return

        r_type = self.mq.get('r-type', 0)
        tech_type = self.mq.get('tech-type', TECH_TYPE_NONE)
        status_type = self.mq.get('status-type', STATUS_TYPE_NONE)
        battery_check = self.mq.get('status-battery-check', STATUS_BATTERY_CHECK_NONE)
        dynamic_counters = self.mq.get('status-dynamic-counters', STATUS_DYNAMIC_COUNTERS_NONE)
        #io_mode = self.mq.get('io-mode', IO_MODE_UNI)
        #io_mfp_mode = self.mq.get('io-mfp-mode', IO_MODE_UNI)

        # Turn off status if local connection and bi-di not avail.
        #if io_mode  == IO_MODE_UNI and self.back_end != 'net':
        #    status_type = STATUS_TYPE_NONE

        agents = []

        if self.device_state != DEVICE_STATE_NOT_FOUND:
            if self.tech_type in (TECH_TYPE_MONO_INK, TECH_TYPE_COLOR_INK):
                try:
                    self.getDeviceID()
                except Error, e:
                    log.error("Error getting device ID.")
                    raise Error(ERROR_DEVICE_IO_ERROR)

            status_desc = self.queryString(self.status_code)

            self.dq.update({
                'serial'           : self.serial,
                'cups-printer'     : ','.join(self.cups_printers),
                'status-code'      : self.status_code,
                'status-desc'      : status_desc,
                'deviceid'         : self.raw_deviceID,
                'panel'            : 0,
                'panel-line1'      : '',
                'panel-line2'      : '',
                'device-state'     : self.device_state,
                'error-state'      : self.error_state,
                })

            status_block = {}

            if status_type == STATUS_TYPE_NONE:
                log.warn("No status available for device.")
                status_block = {'status-code' : STATUS_UNKNOWN}

            elif status_type in (STATUS_TYPE_VSTATUS, STATUS_TYPE_S):
                log.debug("Type 1/2 (S: or VSTATUS:) status")
                status_block = status.parseStatus(self.deviceID)

            elif status_type in (STATUS_TYPE_LJ, STATUS_TYPE_PML_AND_PJL):
                log.debug("Type 3/9 LaserJet PML(+PJL) status")
                status_block = status.StatusType3(self, self.deviceID)

            elif status_type == STATUS_TYPE_LJ_XML:
                log.debug("Type 6: LJ XML")
                status_block = status.StatusType6(self)
                
            elif status_type == STATUS_TYPE_PJL:
                log.debug("Type 8: LJ PJL")
                status_block = status.StatusType8(self)

            else:
                log.error("Unimplemented status type: %d" % status_type)

            if battery_check:
                log.debug("Battery check...")
                status.BatteryCheck(self, status_block)

            if status_block:
                log.debug(status_block)
                self.dq.update(status_block)
                try:
                    status_block['agents']
                except KeyError:
                    pass
                else:
                    agents = status_block['agents']
                    del self.dq['agents']


            status_code = self.dq.get('status-code', STATUS_UNKNOWN)

            if not quick and \
                self.mq.get('fax-type', FAX_TYPE_NONE) and \
                status_code == STATUS_PRINTER_IDLE:

                log.debug("Fax activity check...")

                tx_active, rx_active = status.getFaxStatus(self)

                if tx_active:
                    status_code = STATUS_FAX_TX_ACTIVE
                elif rx_active:
                    status_code = STATUS_FAX_RX_ACTIVE


            typ = 'event'
            self.error_state = STATUS_TO_ERROR_STATE_MAP.get(status_code, ERROR_STATE_CLEAR)

            if self.error_state == ERROR_STATE_ERROR:
                typ = 'error'

            self.sendEvent(status_code, typ=typ, no_fwd=no_fwd)

            try:
                self.dq.update({'status-desc' : self.queryString(status_code),
                                'error-state' : self.error_state,
                                })

            except (KeyError, Error):
                self.dq.update({'status-desc' : '',
                                'error-state' : ERROR_STATE_CLEAR,
                                })

            r_value = 0

            if not quick and status_type != STATUS_TYPE_NONE:
                if self.panel_check:
                    self.panel_check = bool(self.mq.get('panel-check-type', 0))

                if self.panel_check and status_type in (STATUS_TYPE_LJ, STATUS_TYPE_S, STATUS_TYPE_VSTATUS):
                    log.debug("Panel check...")
                    try:
                        self.panel_check, line1, line2 = status.PanelCheck(self)
                    finally:
                        self.closePML()

                    self.dq.update({'panel': int(self.panel_check),
                                      'panel-line1': line1,
                                      'panel-line2': line2,})


                if dynamic_counters != STATUS_DYNAMIC_COUNTERS_NONE:
                    r_value, r_value_str, rg, rr = self.getRValues(r_type, status_type, dynamic_counters)
                else:
                    r_value, r_value_str, rg, rr = 0, '000000000', '000', '000000'

                self.dq.update({'r'  : r_value,
                                'rs' : r_value_str,
                                'rg' : rg,
                                'rr' : rr,
                              })

            if not quick and reread_cups_printers:
                self.cups_printers = []
                log.debug("Re-reading CUPS printer queue information.")
                printers = cups.getPrinters()
                for p in printers:
                    if self.device_uri == p.device_uri:
                        self.cups_printers.append(p.name)
                        self.state = p.state # ?

                        if self.io_state == IO_STATE_NON_HP:
                            self.model = p.makemodel.split(',')[0]

                self.dq.update({'cups-printer' : ','.join(self.cups_printers)})

                try:
                    self.first_cups_printer = self.cups_printers[0]
                except IndexError:
                    self.first_cups_printer = ''

            if not quick:
                # Make sure there is some valid agent data for this r_value
                # If not, fall back to r_value == 0
                if r_value > 0 and self.mq.get('r%d-agent1-kind' % r_value, 0) == 0:
                    r_value = 0
                    self.dq.update({'r'  : r_value,
                                    'rs' : r_value_str,
                                    'rg' : rg,
                                    'rr' : rr,
                                  })

                a = 1
                while True:
                    mq_agent_kind = self.mq.get('r%d-agent%d-kind' % (r_value, a), -1)

                    if mq_agent_kind == -1:
                        break

                    mq_agent_type = self.mq.get('r%d-agent%d-type' % (r_value, a), 0)
                    mq_agent_sku = self.mq.get('r%d-agent%d-sku' % (r_value, a), '')

                    found = False

                    for agent in agents:
                        agent_kind = agent['kind']
                        agent_type = agent['type']

                        if agent_kind == mq_agent_kind and \
                           agent_type == mq_agent_type:
                           found = True
                           break

                    if found:
                        log.debug("found: r%d-kind%d-type%d" % (r_value, agent_kind, agent_type))

                        agent_health = agent.get('health', AGENT_HEALTH_OK)
                        agent_level = agent.get('level', 100)
                        agent_level_trigger = agent.get('level-trigger',
                            AGENT_LEVEL_TRIGGER_SUFFICIENT_0)

                        log.debug("health=%d, level=%d, level_trigger=%d, status_code=%d" % 
                            (agent_health, agent_level, agent_level_trigger, status_code))
                        
                        query = 'agent_%s_%s' % (AGENT_types.get(agent_type, 'unknown'), 
                                                 AGENT_kinds.get(agent_kind, 'unknown'))

                        agent_desc = self.queryString(query)
                        query = 'agent_health_ok'

                        # If printer is not in an error state, and
                        # if agent health is OK, check for low supplies. If low, use
                        # the agent level trigger description for the agent description.
                        # Otherwise, report the agent health.
                        if (status_code == STATUS_PRINTER_IDLE or status_code == STATUS_PRINTER_OUT_OF_INK) and \
                            (agent_health == AGENT_HEALTH_OK or 
                             (agent_health == AGENT_HEALTH_FAIR_MODERATE and agent_kind == AGENT_KIND_HEAD)) and \
                            agent_level_trigger >= AGENT_LEVEL_TRIGGER_MAY_BE_LOW:

                            query = 'agent_level_%s' % AGENT_levels.get(agent_level_trigger, 'unknown')

                            if tech_type in (TECH_TYPE_MONO_INK, TECH_TYPE_COLOR_INK):
                                code = agent_type + STATUS_PRINTER_LOW_INK_BASE
                            else:
                                code = agent_type + STATUS_PRINTER_LOW_TONER_BASE

                            self.dq['status-code'] = code
                            self.dq['status-desc'] = self.queryString(code)

                            self.dq['error-state'] = STATUS_TO_ERROR_STATE_MAP.get(code, ERROR_STATE_LOW_SUPPLIES)
                            self.sendEvent(code)

                            if agent_level_trigger in \
                                (AGENT_LEVEL_TRIGGER_PROBABLY_OUT, AGENT_LEVEL_TRIGGER_ALMOST_DEFINITELY_OUT):
                                
                                query = 'agent_level_out'
                            else:
                                query = 'agent_level_low'

                            agent_health_desc = self.queryString(query)
    
                            self.dq.update(
                            {
                                'agent%d-kind' % a :          agent_kind,
                                'agent%d-type' % a :          agent_type,
                                'agent%d-known' % a :         agent.get('known', False),
                                'agent%d-sku' % a :           mq_agent_sku,
                                'agent%d-level' % a :         agent_level,
                                'agent%d-level-trigger' % a : agent_level_trigger,
                                'agent%d-ack' % a :           agent.get('ack', False),
                                'agent%d-hp-ink' % a :        agent.get('hp-ink', False),
                                'agent%d-health' % a :        agent_health,
                                'agent%d-dvc' % a :           agent.get('dvc', 0),
                                'agent%d-virgin' % a :        agent.get('virgin', False),
                                'agent%d-desc' % a :          agent_desc,
                                'agent%d-id' % a :            agent.get('id', 0),
                                'agent%d-health-desc' % a :   agent_health_desc,
                            })

                        else:
                            query = 'agent_health_%s' % AGENT_healths.get(agent_health, AGENT_HEALTH_OK)
                            agent_health_desc = self.queryString(query)
    
                            self.dq.update(
                            {
                                'agent%d-kind' % a :          agent_kind,
                                'agent%d-type' % a :          agent_type,
                                'agent%d-known' % a :         False,
                                'agent%d-sku' % a :           mq_agent_sku,
                                'agent%d-level' % a :         agent_level,
                                'agent%d-level-trigger' % a : agent_level_trigger,
                                'agent%d-ack' % a :           False,
                                'agent%d-hp-ink' % a :        False,
                                'agent%d-health' % a :        agent_health,
                                'agent%d-dvc' % a :           0,
                                'agent%d-virgin' % a :        False,
                                'agent%d-desc' % a :          agent_desc,
                                'agent%d-id' % a :            0,
                                'agent%d-health-desc' % a :   agent_health_desc,
                            })
    
                    a += 1

        else: # Create agent keys for not-found devices

            r_value = 0
            if r_type > 0 and self.r_values is not None:
                r_value = self.r_values[0]

            # Make sure there is some valid agent data for this r_value
            # If not, fall back to r_value == 0
            if r_value > 0 and self.mq.get('r%d-agent1-kind', 0) == 0:
                r_value = 0

            a = 1
            while True:
                mq_agent_kind = self.mq.get('r%d-agent%d-kind' % (r_value, a), 0)

                if mq_agent_kind == 0:
                    break

                mq_agent_type = self.mq.get('r%d-agent%d-type' % (r_value, a), 0)
                mq_agent_sku = self.mq.get('r%d-agent%d-sku' % (r_value, a), '')
                query = 'agent_%s_%s' % (AGENT_types.get(mq_agent_type, 'unknown'),
                                         AGENT_kinds.get(mq_agent_kind, 'unknown'))

                agent_desc = self.queryString(query)

                self.dq.update(
                {
                    'agent%d-kind' % a :          mq_agent_kind,
                    'agent%d-type' % a :          mq_agent_type,
                    'agent%d-known' % a :         False,
                    'agent%d-sku' % a :           mq_agent_sku,
                    'agent%d-level' % a :         0,
                    'agent%d-level-trigger' % a : AGENT_LEVEL_TRIGGER_ALMOST_DEFINITELY_OUT,
                    'agent%d-ack' % a :           False,
                    'agent%d-hp-ink' % a :        False,
                    'agent%d-health' % a :        AGENT_HEALTH_MISINSTALLED,
                    'agent%d-dvc' % a :           0,
                    'agent%d-virgin' % a :        False,
                    'agent%d-health-desc' % a :   self.queryString('agent_health_unknown'),
                    'agent%d-desc' % a :          agent_desc,
                    'agent%d-id' % a :            0,
                })

                a += 1

        for d in self.dq:
            self.__dict__[d.replace('-','_')] = self.dq[d]

        log.debug(self.dq)


    def isBusyOrInErrorState(self):
        self.queryDevice(quick=True)
        return self.error_state > ERROR_STATE_MAX_OK

    def isIdleAndNoError(self):
        self.queryDevice(quick=True)
        #print self.error_state
        return self.error_state <= ERROR_STATE_MAX_OK

    def getPML(self, oid, desired_int_size=pml.INT_SIZE_INT): # oid => ( 'dotted oid value', pml type )
        channel_id = self.openPML()

        result_code, data, typ, pml_result_code = \
            hpmudext.get_pml(self.device_id, channel_id, pml.PMLToSNMP(oid[0]), oid[1])

        if pml_result_code > pml.ERROR_MAX_OK:
            log.debug("PML/SNMP GET %s failed (result code = 0x%x)" % (oid[0], pml_result_code))
            return pml_result_code, None

        converted_data = pml.ConvertFromPMLDataFormat(data, oid[1], desired_int_size)
        
        if log.is_debug():
            if oid[1] in (pml.TYPE_STRING, pml.TYPE_BINARY):
                
                log.debug("PML/SNMP GET %s (result code = 0x%x) returned:" % 
                    (oid[0], pml_result_code))
                log.log_data(data)
            else:
                log.debug("PML/SNMP GET %s (result code = 0x%x) returned: %s" % 
                    (oid[0], pml_result_code, repr(converted_data)))
        
        return pml_result_code, converted_data


    def setPML(self, oid, value): # oid => ( 'dotted oid value', pml type )
        channel_id = self.openPML()

        value = pml.ConvertToPMLDataFormat(value, oid[1])
        
        result_code, pml_result_code = \
            hpmudext.set_pml(self.device_id, channel_id, pml.PMLToSNMP(oid[0]), oid[1], value)
            
        if log.is_debug():
            if oid[1] in (pml.TYPE_STRING, pml.TYPE_BINARY): 
                
                log.debug("PML/SNMP SET %s (result code = 0x%x) to:" % 
                    (oid[0], pml_result_code))
                log.log_data(value)
            else:
                log.debug("PML/SNMP SET %s (result code = 0x%x) to: %s" % 
                    (oid[0], pml_result_code, repr(value)))
        
        return pml_result_code


    def getDynamicCounter(self, counter, convert_to_int=True):
        dynamic_counters = self.mq.get('status-dynamic-counters', STATUS_DYNAMIC_COUNTERS_NONE)
        if dynamic_counters != STATUS_DYNAMIC_COUNTERS_NONE:

            if dynamic_counters == STATUS_DYNAMIC_COUNTERS_LIDIL_0_5_4:
                self.printData(ldl.buildResetPacket(), direct=True) 
                self.printData(ldl.buildDynamicCountersPacket(counter), direct=True)
            else:
                self.printData(pcl.buildDynamicCounter(counter), direct=True)

            value, tries, times_seen, sleepy_time, max_tries = 0, 0, 0, 0.1, 5
            time.sleep(0.1)

            while True:

                if self.callback:
                    self.callback()

                sleepy_time += 0.1
                tries += 1

                time.sleep(sleepy_time)

                self.getDeviceID()

                if 'CTR' in self.deviceID and \
                    pat_dynamic_ctr.search(self.raw_deviceID) is not None:
                    dev_counter, value = parseDynamicCounter(self.deviceID['CTR'], convert_to_int)

                    if counter == dev_counter:
                        self.printData(pcl.buildDynamicCounter(0), direct=True)
                        # protect the value as a string during msg handling
                        if not convert_to_int:
                            value = '#' + value
                        return value

                if tries > max_tries:
                    if dynamic_counters == STATUS_DYNAMIC_COUNTERS_LIDIL_0_5_4:
                        self.printData(ldl.buildResetPacket())
                        self.printData(ldl.buildDynamicCountersPacket(counter), direct=True)
                    else:
                        self.printData(pcl.buildDynamicCounter(0), direct=True)

                    return None

                if dynamic_counters == STATUS_DYNAMIC_COUNTERS_LIDIL_0_5_4:
                    self.printData(ldl.buildResetPacket())
                    self.printData(ldl.buildDynamicCountersPacket(counter), direct=True)
                else:
                    self.printData(pcl.buildDynamicCounter(counter), direct=True)

        else:
            raise Error(ERROR_DEVICE_DOES_NOT_SUPPORT_OPERATION)


    def readPrint(self, bytes_to_read, stream=None, timeout=prop.read_timeout, allow_short_read=False):
        return self.__readChannel(self.openPrint, bytes_to_read, stream, timeout, allow_short_read)

    def readPCard(self, bytes_to_read, stream=None, timeout=prop.read_timeout, allow_short_read=False):
        return self.__readChannel(self.openPCard, bytes_to_read, stream, timeout, allow_short_read)

    def readFax(self, bytes_to_read, stream=None, timeout=prop.read_timeout, allow_short_read=False):
        return self.__readChannel(self.openFax, bytes_to_read, stream, timeout, allow_short_read)

    def readCfgUpload(self, bytes_to_read, stream=None, timeout=prop.read_timeout, allow_short_read=False):
        return self.__readChannel(self.openCfgUpload, bytes_to_read, stream, timeout, allow_short_read)

    def readEWS(self, bytes_to_read, stream=None, timeout=prop.read_timeout, allow_short_read=True):
        return self.__readChannel(self.openEWS, bytes_to_read, stream, timeout, allow_short_read)

    def readSoapFax(self, bytes_to_read, stream=None, timeout=prop.read_timeout, allow_short_read=True):
        return self.__readChannel(self.openSoapFax, bytes_to_read, stream, timeout, allow_short_read)

    def __readChannel(self, opener, bytes_to_read, stream=None, 
                      timeout=prop.read_timeout, allow_short_read=False):

        channel_id = opener()

        log.debug("Reading channel %d..." % channel_id)

        num_bytes = 0

        if stream is None:
            buffer = ''

        while True:
            #print self.device_id, channel_id, bytes_to_read, timeout
            result_code, data = \
                hpmudext.read_channel(self.device_id, channel_id, bytes_to_read, timeout)

            #result_code, data = read_channel(dd, cd, bytes_to_read, [timeout])

            l = len(data)
            #log.log_data(data)
            
            if result_code == hpmudext.HPMUD_R_IO_TIMEOUT:
                log.warn("I/O timeout")
                break

            if result_code != hpmudext.HPMUD_R_OK: 
                log.error("Channel read error")
                raise Error(ERROR_DEVICE_IO_ERROR)

            if not l:
                log.debug("End of data")
                break

            if stream is None:
                buffer = ''.join([buffer, data])
            else:
                stream.write(data)

            num_bytes += l

            if self.callback is not None:
                self.callback()

            if num_bytes == bytes_to_read or allow_short_read:
                log.debug("Read complete")
                break

        if stream is None:
            log.debug("Returned %d total bytes in buffer." % num_bytes)
            return buffer
        else:
            log.debug("Wrote %d total bytes to stream." % num_bytes)
            return num_bytes


    def writePrint(self, data):
        return self.__writeChannel(self.openPrint, data)

    def writePCard(self, data):
        return self.__writeChannel(self.openPCard, data)

    def writeFax(self, data):
        return self.__writeChannel(self.openFax, data)

    def writeEWS(self, data):
        return self.__writeChannel(self.openEWS, data)

    def writeCfgDownload(self, data):
        return self.__writeChannel(self.openCfgDownload, data)
        
    def writeSoapFax(self, data):
        return self.__writeChannel(self.openSoapFax, data)
    

    def __writeChannel(self, opener, data):
        channel_id = opener()

        log.debug("Writing channel %d..." % channel_id)
        buffer, bytes_out, total_bytes_to_write = data, 0, len(data)

        while len(buffer) > 0:
            result_code, bytes_written = \
                hpmudext.write_channel(self.device_id, channel_id, 
                    buffer[:prop.max_message_len])

            if result_code != hpmudext.HPMUD_R_OK:
                log.error("Channel write error")
                raise Error(ERROR_DEVICE_IO_ERROR)

            buffer = buffer[prop.max_message_len:]
            bytes_out += bytes_written 

            if self.callback is not None:
                self.callback()

        if total_bytes_to_write != bytes_out:
            raise Error(ERROR_DEVICE_IO_ERROR)

        return bytes_out


    def writeEmbeddedPML(self, oid, value, style=1, direct=True):
        if style == 1:
            func = pcl.buildEmbeddedPML2
        else:
            func = pcl.buildEmbeddedPML

        data = func(pcl.buildPCLCmd('&', 'b', 'W',
                     pml.buildEmbeddedPMLSetPacket(oid[0],
                                                    value,
                                                    oid[1])))

        log.log_data(data)
        
        self.printData(data, direct=direct, raw=True)


    def printGzipFile(self, file_name, printer_name=None, direct=False, raw=True, remove=False):
        return self.printFile(file_name, printer_name, direct, raw, remove)

    def printParsedGzipPostscript(self, print_file, printer_name=None):
        # always: direct=False, raw=False, remove=True
        try:
            os.stat(print_file)
        except OSError:
            log.error("File not found: %s" % print_file)
            return

        temp_file_fd, temp_file_name = utils.make_temp_file()
        f = gzip.open(print_file, 'r')

        x = f.readline()
        while not x.startswith('%PY_BEGIN'):
            os.write(temp_file_fd, x)
            x = f.readline()

        sub_lines = []
        x = f.readline()
        while not x.startswith('%PY_END'):
            sub_lines.append(x)
            x = f.readline()

        SUBS = {'VERSION' : prop.version,
                 'MODEL'   : self.model_ui,
                 'URI'     : self.device_uri,
                 'BUS'     : self.bus,
                 'SERIAL'  : self.serial,
                 'IP'      : self.host,
                 'PORT'    : self.port,
                 'DEVNODE' : self.dev_file,
                 }

        if self.bus == 'net':
            SUBS['DEVNODE'] = 'n/a'
        else:
            SUBS['IP'] = 'n/a'
            SUBS['PORT'] = 'n/a'

        for s in sub_lines:
            os.write(temp_file_fd, s % SUBS)

        os.write(temp_file_fd, f.read())
        f.close()
        os.close(temp_file_fd)

        self.printFile(temp_file_name, printer_name, direct=False, raw=False, remove=True)

    def printFile(self, file_name, printer_name=None, direct=False, raw=True, remove=False):
        is_gzip = os.path.splitext(file_name)[-1].lower() == '.gz'

        if printer_name is None:
            try:
                printer_name = self.cups_printers[0]
            except IndexError:
                raise Error(ERROR_NO_CUPS_QUEUE_FOUND_FOR_DEVICE)

        log.debug("Printing file '%s' to queue '%s' (gzip=%s, direct=%s, raw=%s, remove=%s)" %
                   (file_name, printer_name, is_gzip, direct, raw, remove))

        if direct: # implies raw==True
            if is_gzip:
                self.writePrint(gzip.open(file_name, 'r').read())
            else:
                self.writePrint(file(file_name, 'r').read())

        else:
            if not utils.which('lpr'):
                lp_opt = ''

                if raw:
                    lp_opt = '-oraw'

                if is_gzip:
                    c = 'gunzip -c %s | lp -c -d%s %s' % (file_name, printer_name, lp_opt)
                else:
                    c = 'lp -c -d%s %s %s' % (printer_name, lp_opt, file_name)

                log.debug(c)
                exit_code = os.system(c)

                if exit_code != 0:
                    log.error("Print command failed with exit code %d!" % exit_code)

                if remove:
                    os.remove(file_name)

            else:
                raw_str, rem_str = '', ''
                if raw: raw_str = '-o raw'
                if remove: rem_str = '-r'

                if is_gzip:
                    c = 'gunzip -c %s | lpr %s %s -P%s' % (file_name, raw_str, rem_str, printer_name)
                else:
                    c = 'lpr -P%s %s %s %s' % (printer_name, raw_str, rem_str, file_name)

                log.debug(c)
                exit_code = os.system(c)

                if exit_code != 0:
                    log.error("Print command failed with exit code %d!" % exit_code)


    def printTestPage(self, printer_name=None):
        return self.printParsedGzipPostscript(os.path.join( prop.home_dir, 'data',
                                              'ps', 'testpage.ps.gz' ), printer_name)


    def printData(self, data, printer_name=None, direct=True, raw=True):
        #log.log_data(data)
        #log.debug("printData(direct=%s, raw=%s)" % (direct, raw))
        if direct:
            self.writePrint(data)
        else:
            temp_file_fd, temp_file_name = utils.make_temp_file()
            os.write(temp_file_fd, data)
            os.close(temp_file_fd)

            self.printFile(temp_file_name, printer_name, False, raw, remove=True)


    def cancelJob(self, jobid):
        cups.cancelJob(jobid)
        self.sendEvent(STATUS_PRINTER_CANCELING, jobid)

    def sendEvent(self, event, jobid=0, typ='event', no_fwd=False): 
        sendEvent(self.hpssd_sock, 'Event', None,
                      {
                          'job-id'        : jobid,
                          'event-type'    : typ,
                          'event-code'    : event,
                          'username'      : prop.username,
                          'device-uri'    : self.device_uri,
                          'retry-timeout' : 0,
                          'no-fwd'        : no_fwd,
                      }
                     )



    def queryHistory(self):
        fields, data, result_code = \
            self.xmitHpssdMessage("QueryHistory", {'device-uri' : self.device_uri,})

        result = []
        lines = data.strip().splitlines()
        lines.reverse()

        for x in lines:
            yr, mt, dy, hr, mi, sec, wd, yd, dst, job, user, ec = x.strip().split(',', 13)
            ec = int(ec)
            ess = queryString(ec, 0)
            esl = queryString(ec, 1)
            result.append((int(yr), int(mt), int(dy), int(hr), int(mi), int(sec), int(wd),
                             int(yd), int(dst), int(job), user, ec, ess, esl))

        self.hist = result
        return result


    def getEWSUrl(self, url, stream):
        try:
            if self.is_local:
                url2 = "%s&loc=%s" % (self.device_uri, url)
                data = self
            else:
                url2 = "http://%s%s" % (self.host, url)
                data = None

            log.debug("Opening: %s" % url2)
            opener = LocalOpener({})
            try:
                f = opener.open(url2, data)
            except Error:
                log.error("Status read failed: %s" % url2)
                stream.seek(0)
                stream.truncate()
            else:
                try:
                    stream.write(f.read())
                finally:
                    f.close()

        finally:
            self.closeEWS()


    def downloadFirmware(self, usb_bus_id=None, usb_device_id=None):
        ok = False
        filename = os.path.join(prop.data_dir, "firmware", self.model.lower() + '.fw.gz')
        log.debug(filename)

        if os.path.exists(filename):
            log.debug("Downloading firmware file '%s'..." % filename)
            
            # Write to port directly (no MUD) so that HAL can enumerate the printer
            if 0: # this currently doesn't work because usblp is loaded...
            #if usb_bus_id is not None and usb_device_id is not None:
                try:
                    p = "/dev/bus/usb/%s/%s" % (usb_bus_id, usb_device_id)
                    log.debug("Writing to %s..." % p)
                    #f = file(p, 'w')
                    f = os.open(p, os.O_RDWR)
                    x = gzip.open(filename).read()
                    os.write(f, x)
                    #f.close()
                    os.close(f)
                    ok = True
                    log.debug("OK")
                except (OSError, IOError), e:
                    log.error("An error occured: %s" % e)
            else:
                try:
                    self.openPrint()
                    bytes_written = self.writePrint(gzip.open(filename).read())
                    log.debug("%s bytes downloaded." % utils.commafy(bytes_written))
                    self.closePrint()
                    ok = True
                    log.debug("OK")
                except Error, e:
                    log.error("An error occured: %s" % e.msg)
        else:
            log.error("Firmware file '%s' not found." % filename)

        return ok


# ********************************** Support classes/functions


class xStringIO(StringIO.StringIO):
    def makefile(self, x, y):
        return self

# URLs: hp:/usb/HP_LaserJet_3050?serial=00XXXXXXXXXX&loc=/hp/device/info_device_status.xml
class LocalOpener(urllib.URLopener):
    def open_hp(self, url, dev):
        log.debug("open_hp(%s)" % url)

        match_obj = http_pat_url.search(url)
        bus = match_obj.group(1) or ''
        model = match_obj.group(2) or ''
        serial = match_obj.group(3) or ''
        device = match_obj.group(4) or ''
        loc = match_obj.group(5) or ''

        dev.openEWS()
        dev.writeEWS("""GET %s HTTP/1.0\nContent-Length:0\nHost:localhost\nUser-Agent:hplip\n\n""" % loc)

        reply = xStringIO()
        dev.readEWS(MAX_BUFFER, reply)

        reply.seek(0)

        response = httplib.HTTPResponse(reply)
        response.begin()

        if response.status != httplib.OK:
            raise Error(ERROR_DEVICE_STATUS_NOT_AVAILABLE)
        else:
            return response.fp

