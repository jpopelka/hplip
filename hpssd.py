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

__version__ = '10.1'
__title__ = "Services and Status System Tray dBus Child Process"
__doc__ = "Provides persistent data and event services to HPLIP client applications. Required to be running for PC send fax, optional in all other cases."


# StdLib
import sys
import struct
import os
import time
import getopt
import select
import signal
import tempfile

# Local
from base.g import *
from base.codes import *
from base import utils, device, status, models

# dBus
try:
    from dbus import lowlevel, SystemBus, SessionBus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gobject import MainLoop
    dbus_loaded = True
except ImportError:
    log.error("dbus failed to load (python-dbus ver. 0.80+ required). Exiting...")
    dbus_loaded = False
    sys.exit(1)


# Globals
PIPE_BUF = 4096
dbus_loop = None
system_bus = None
session_bus = None
w = None
devices = {} # { 'device_uri' : DeviceCache, ... }


USAGE = [(__doc__, "", "name", True),
         ("Usage: hpssd.py [OPTIONS]", "", "summary", True),
         utils.USAGE_OPTIONS,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2,
         ("Run in debug mode:", "-g (same as options: -ldebug -x)", "option", False),
         utils.USAGE_HELP,
        ]


def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hpssd.py', __version__)
    sys.exit(0)



class DeviceCache(object):
    def __init__(self, model=''):
        self.history = utils.RingBuffer(prop.history_size) # circular buffer of ServiceEvent
        self.model = models.normalizeModelName(model)
        self.cache = {} # variable name : value
        self.faxes = {} # (username, jobid): FaxEvent



class ServiceEvent(device.Event):
    def __init__(self, device_uri, printer_name, event_code, username, job_id, title):
        device.Event.__init__(self, device_uri, printer_name, event_code, username, job_id, title, time.time())

    def debug(self):
        log.debug("EVENT:")
        device.Event.debug(self)

    def __str__(self):
        return "<ServiceEvent('%s', '%s', %d, '%s', %d, '%s', %f)>" % self.as_tuple()



class FaxEvent(device.Event):
    def __init__(self, temp_file, event):
        device.Event.__init__(self, *event.as_tuple())
        self.temp_file = temp_file

    def debug(self):
        log.debug("FAX:")
        device.Event.debug(self)
        log.debug("    temp_file=%s" % self.temp_file)

    def __str__(self):
        return "<FaxEvent('%s', '%s', %d, '%s', %d, '%s', %f, '%s')>" % self.as_tuple()      

    def as_tuple(self):
        return (self.device_uri, self.printer_name, self.event_code, 
             self.username, self.job_id, self.title, self.timedate,
             self.temp_file)



#  dbus interface on session bus
class StatusService(dbus.service.Object):
    def __init__(self, name, object_path):
        dbus.service.Object.__init__(self, name, object_path)


    @dbus.service.method('com.hplip.StatusService', in_signature='s', out_signature='a(ssisisd)')
    def GetHistory(self, device_uri):
        log.debug("GetHistory('%s')" % device_uri)
        try:
            devices[device_uri]
        except KeyError:
            #log.warn("Unknown device URI: %s" % device_uri)
            return []
        else:
            h = devices[device_uri].history.get()
            log.debug("%d events in history:" % len(h))
            [x.debug() for x in h]
            return [x.as_tuple() for x in h]



    @dbus.service.method('com.hplip.StatusService', in_signature='ssi', out_signature='i')
    def SetCachedIntValue(self, device_uri, key, value):
        log.debug("SetCachedIntValue('%s', '%s', %d)" % (device_uri, key, value))
        if check_device(device_uri) == ERROR_SUCCESS: 
            devices[device_uri].cache[key] = value
            return value

        return -1


    @dbus.service.method('com.hplip.StatusService', in_signature='ss', out_signature='i')
    def GetCachedIntValue(self, device_uri, key):
        try:
            ret = devices[device_uri].cache[key]
        except KeyError:
            ret = -1

        log.debug("GetCachedIntValue('%s', '%s') --> %d" % (device_uri, key, ret))
        return ret


    @dbus.service.method('com.hplip.StatusService', in_signature='sss', out_signature='s')
    def SetCachedStrValue(self, device_uri, key, value):
        log.debug("SetCachedStrValue('%s', '%s', '%s')" % (device_uri, key, value))
        if check_device(device_uri) == ERROR_SUCCESS: 
            devices[device_uri].cache[key] = value
            return value

        return ''


    @dbus.service.method('com.hplip.StatusService', in_signature='ss', out_signature='s')
    def GetCachedStrValue(self, device_uri, key):
        try:
            ret = devices[device_uri].cache[key]
        except KeyError:
            ret = ''

        log.debug("GetCachedStrValue('%s', '%s') --> %s" % (device_uri, key, ret))
        return ret


    # Pass a non-zero job_id to retrieve a specific fax
    # Pass zero for job_id to retrieve any avail. fax
    @dbus.service.method('com.hplip.StatusService', in_signature='ssi', out_signature='ssisisds')
    def CheckForWaitingFax(self, device_uri, username, job_id=0):
        #device_uri = device_uri.replace('hp:', 'hpfax:')
        log.debug("CheckForWaitingFax('%s', '%s', %d)" % (device_uri, username, job_id))
        r = (device_uri, '', 0, username, job_id, '', 0.0, '')
        
        check_device(device_uri)
        #try:
        #    devices[device_uri]
        #except KeyError:
        #    log.warn("Unknown device URI: %s" % device_uri)
        #    return r
        #else:
        if 1:
            show_waiting_faxes(device_uri)

            if job_id: # check for specific job_id
                try:
                    devices[device_uri].faxes[(username, job_id)]
                except KeyError:
                    return r
                else:
                    return self.check_for_waiting_fax_return(device_uri, username, job_id)

            else: # return any matching one from cache. call mult. times to get all.
                for u, j in devices[device_uri].faxes.keys():
                    if u == username:
                        return self.check_for_waiting_fax_return(device_uri, u, j)

                return r


    # if CheckForWaitingFax returns a fax job, that job is removed from the cache
    def check_for_waiting_fax_return(self, d, u, j):
        log.debug("Fax (username=%s, jobid=%d) removed from faxes and returned to caller." % (u, j))
        r = devices[d].faxes[(u, j)].as_tuple()
        del devices[d].faxes[(u, j)]
        show_waiting_faxes(d)
        return r 


    # Alternate way to "send" an event rather than using a signal message
    @dbus.service.method('com.hplip.StatusService', in_signature='ssisis', out_signature='')
    def SendEvent(self, device_uri, printer_name, event_code, username, job_id, title):
        event = ServiceEvent(device_uri, printer_name, event_code, username, job_id, title)
        handle_event(event)



def check_device(device_uri):
    try:
        devices[device_uri]
    except KeyError:
        log.debug("New device: %s" % device_uri)
        try:
            back_end, is_hp, bus, model, serial, dev_file, host, port = \
                device.parseDeviceURI(device_uri)
        except Error:
            log.error("Invalid device URI")
            return ERROR_INVALID_DEVICE_URI

        devices[device_uri] = DeviceCache(model)

    return ERROR_SUCCESS   


def create_history(event):
    history = devices[event.device_uri].history.get()

    if history and history[-1].event_code == event.event_code:
        log.debug("Duplicate event. Replacing previous event.")
        devices[event.device_uri].history.replace(event)
        return True
    else:
        devices[event.device_uri].history.append(event)
        return False


def handle_fax_event(event, pipe_name):
    if event.event_code == EVENT_FAX_RENDER_COMPLETE and \
        event.username == prop.username:

        fax_file_fd, fax_file_name = tempfile.mkstemp(prefix="hpfax-")
        pipe = os.open(pipe_name, os.O_RDONLY) 
        bytes_read = 0
        while True:
            data = os.read(pipe, PIPE_BUF)
            if not data: 
                break

            os.write(fax_file_fd, data)
            bytes_read += len(data)

        log.debug("Saved %d bytes to file %s" % (bytes_read, fax_file_name))

        os.close(pipe)
        os.close(fax_file_fd)

        devices[event.device_uri].faxes[(event.username, event.job_id)] = \
            FaxEvent(fax_file_name, event)

        show_waiting_faxes(event.device_uri)

        try:
            os.waitpid(-1, os.WNOHANG)
        except OSError:
            pass

        # See if hp-sendfax is already running for this queue
        ok, lock_file = utils.lock_app('hp-sendfax-%s' % event.printer_name, True)

        if ok: 
            # able to lock, not running...
            utils.unlock(lock_file)
            
            path = utils.which('hp-sendfax')
            if path:
                path = os.path.join(path, 'hp-sendfax')
            else:
                log.error("Unable to find hp-sendfax on PATH.")
                return

            log.debug(path)
            
            log.debug("Running hp-sendfax: hp-senfax --fax=%s" % event.printer_name)
            
            os.spawnlp(os.P_NOWAIT, path, 'hp-sendfax', 
                '--fax=%s' % event.printer_name)
        
        else: 
            # hp-sendfax running
            # no need to do anything... hp-sendfax is polling
            log.debug("hp-sendfax is running. Waiting for CheckForWaitingFax() call.")

    else:
        log.warn("Not handled!")
        pass


def show_waiting_faxes(d):
    f = devices[d].faxes
    if not len(f):
        log.debug("No faxes waiting for %s" % d)
    else:
        if len(f) == 1:
            log.debug("1 fax waiting for %s:" % d)
        else:
            log.debug("%d faxes waiting for %s:" % (len(f), d))

        [f[x].debug() for x in f]


def handle_event(event, more_args=None):
    log.debug("Handling event...")
    if more_args is None: 
        more_args = []

    event.debug()

    if event.device_uri and check_device(event.device_uri) != ERROR_SUCCESS:
        return
   
    # If event-code > 10001, its a PJL error code, so convert it
    if event.event_code > EVENT_MAX_EVENT:
        event.event_code = status.MapPJLErrorCode(event.event_code)

    # regular user/device status event
    if EVENT_MIN_USER_EVENT <= event.event_code <= EVENT_MAX_USER_EVENT:
        
        if event.device_uri:
            #event.device_uri = event.device_uri.replace('hpfax:', 'hp:')
            dup_event = create_history(event)

        # Send to system tray icon if available
        if not dup_event and event.event_code != STATUS_PRINTER_IDLE:
            if w is not None:
                log.debug("Sending event to system tray icon UI...")
                try:
                    os.write(w, event.pack())
                except OSError:
                    log.debug("Failed.")
                    
        # send EVENT_HISTORY_UPDATE signal to hp-toolbox
        send_toolbox_event(event, EVENT_HISTORY_UPDATE)

        
    # Handle fax signals
    elif EVENT_FAX_MIN <= event.event_code <= EVENT_FAX_MAX and more_args:
        log.debug("Fax event")
        pipe_name = str(more_args[0])
        handle_fax_event(event, pipe_name)


def send_toolbox_event(event, event_code):
    args = [event.device_uri, event.printer_name, event_code, 
            prop.username, event.job_id, event.title, '']
            
    msg = lowlevel.SignalMessage('/', 'com.hplip.Toolbox', 'Event')
    msg.append(signature='ssisiss', *args)

    SessionBus().send_message(msg)


def handle_signal(typ, *args, **kwds):
    if kwds['interface'] == 'com.hplip.Service' and \
        kwds['member'] == 'Event':

        event = ServiceEvent(*args[:6])
        return handle_event(event, args[6:])


def handle_system_signal(*args,**kwds):
    return handle_signal('system', *args, **kwds)


def handle_session_signal(*args, **kwds):
    return handle_signal('session', *args, **kwds)


# Entry point for hp-systray
def run(write_pipe=None, parent_pid=0):
    global dbus_loop
    global system_bus
    global session_bus
    global w

    log.set_module("hp-systray(hpssd)")
    w = write_pipe

    dbus_loop = DBusGMainLoop(set_as_default=True)
    
    try:
        system_bus = SystemBus(mainloop=dbus_loop)
    except dbus.exceptions.DBusException, e:        
        log.error("Unable to connect to dbus system bus. Exiting.")
        sys.exit(1)

    try:
        session_bus = dbus.SessionBus()
    except dbus.exceptions.DBusException, e:
        if os.getuid() != 0:
            log.error("Unable to connect to dbus session bus. Exiting.")
            sys.exit(1)
        else:
            log.error("Unable to connect to dbus session bus (running as root?)")            
            sys.exit(1)    

    # Receive events from the system bus
    system_bus.add_signal_receiver(handle_system_signal, sender_keyword='sender',
        destination_keyword='dest', interface_keyword='interface',
        member_keyword='member', path_keyword='path')

    # Receive events from the session bus
    session_bus.add_signal_receiver(handle_session_signal, sender_keyword='sender',
        destination_keyword='dest', interface_keyword='interface',
        member_keyword='member', path_keyword='path')

    # Export an object on the session bus
    session_name = dbus.service.BusName("com.hplip.StatusService", session_bus)
    status_service = StatusService(session_name, "/com/hplip/StatusService")

    log.debug("Entering main loop...")
    try:
        MainLoop().run()
    except KeyboardInterrupt:
        log.debug("Ctrl-C: Exiting...")



if __name__ == '__main__':
    log.set_module('hpssd')

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'l:hg', 
            ['level=', 'help', 'help-man', 'help-rest', 'help-desc'])

    except getopt.GetoptError, e:
        log.error(e.msg)
        usage()

    if os.getenv("HPLIP_DEBUG"):
        log.set_level('debug')

    for o, a in opts:
        if o in ('-l', '--logging'):
            log_level = a.lower().strip()
            if not log.set_level(log_level):
                usage()

        elif o == '-g':
            log.set_level('debug')

        elif o in ('-h', '--help'):
            usage()

        elif o == '--help-rest':
            usage('rest')

        elif o == '--help-man':
            usage('man')

        elif o == '--help-desc':
            print __doc__,
            sys.exit(0)


    utils.log_title(__title__, __version__)    
    sys.exit(run())
