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

#Std Lib
import socket
import time
import os.path

# Local
from g import *
from codes import *
import msg


def startup(startup_if_not_running=True):
    log.debug("Startup: Trying to connect to hpssd on %s:%d" % (prop.hpssd_host, prop.hpssd_port))
    hpssd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        hpssd_sock.connect((prop.hpssd_host, prop.hpssd_port))
    except socket.error:
        if startup_if_not_running:
            log.debug("Cannot connect to hpssd. Launching...")
            os.system("python " + os.path.join(prop.home_dir, "hpssd.py"))
            time.sleep(0.5)
            time_left = 10
            start_time = time.time()
            
            while time_left:
                try:
                    hpssd_sock.connect((prop.hpssd_host, prop.hpssd_port))
                except socket.error:
                    time.sleep(0.5)
                    time_left -= (time.time() - start_time)
                else:
                    break
            else:
                log.error("Unable to connect to HPLIP I/O (hpssd).")
                raise Error(ERROR_UNABLE_TO_CONTACT_SERVICE)
        else:
            log.debug("Cannot connect to hpssd.")
            raise Error(ERROR_UNABLE_TO_CONTACT_SERVICE)
    
    log.debug("Connected to hpssd on %s:%d" % (prop.hpssd_host, prop.hpssd_port))
    return hpssd_sock
    

def registerGUI(sock, username, host, port, pid, typ):
    msg.sendEvent(sock,
                  "RegisterGUIEvent",
                  None,
                  { 'username' : username,
                    'hostname' : host,
                    'port' : port,
                    'pid' : pid,
                    'type' : typ }
                  )


def unregisterGUI(sock, username, pid, typ):
    msg.sendEvent(sock,
                   "UnRegisterGUIEvent",
                   None,
                   {
                       'username' : username,
                       'pid' : pid,
                       'type' : typ,
                   }
                  )



def testEmail(sock, username): 
    fields = {}
    result_code = ERROR_SUCCESS
    try:
        fields, data, result_code = \
            msg.xmitMessage(sock,
                            "TestEmail",
                            None,
                            {'username': username,})
    except Error, e:
        result_code = e.opt
        utils.log_exception()

    return result_code


def sendEvent(sock, event, typ='event', jobid=0, 
              username=prop.username, device_uri='', 
              other_fields={}, data=None):

    fields = {'job-id'        : jobid,
              'event-type'    : typ,
              'event-code'    : event,
              'username'      : username,
              'device-uri'    : device_uri,
              'retry-timeout' : 0,}

    if other_fields:
        fields.update(other_fields)

    msg.sendEvent(sock, 'Event', data, fields)


def setAlertsEx(sock):
    email_to_addresses = user_cfg.alerts.email_to_addresses
    email_from_address = user_cfg.alerts.email_from_address
    email_alerts = user_cfg.alerts.email_alerts

    setAlerts(sock, email_alerts, email_from_address, email_to_addresses)


def setAlerts(sock, email_alerts, email_from_address, email_to_addresses): 
    fields, data, result_code = \
        msg.xmitMessage(sock,
                        "SetAlerts",
                        None,
                        {
                            'username'      : prop.username,
                            'email-alerts'  : email_alerts,
                            'email-from-address' : email_from_address,
                            'email-to-addresses' : email_to_addresses,
                        })

