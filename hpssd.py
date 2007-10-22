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
# Authors: Don Welch, Pete Parks
#
# Thanks to Henrique M. Holschuh <hmh@debian.org> for various security patches
#
# ======================================================================
# Async code is Copyright 1996 by Sam Rushing
#
#                         All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of Sam
# Rushing not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# SAM RUSHING DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN
# NO EVENT SHALL SAM RUSHING BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# ======================================================================
#


__version__ = '9.2'
__title__ = "Services and Status Daemon"
__doc__ = "Provides persistent data and event services to HPLIP client applications."


# Std Lib
import sys, socket, os, os.path, signal, getopt, time, select
import subprocess, threading, tempfile

from errno import EALREADY, EINPROGRESS, EWOULDBLOCK, ECONNRESET, \
     ENOTCONN, ESHUTDOWN, EINTR, EISCONN

# Local
from base.g import *
from base.codes import *
from base.msg import *
from base import utils, device
from base.async import dispatcher, loop

# CUPS support
from prnt import cups

# Per user alert settings
alerts = {}

# Fax
fax_file = {}
fax_file_ready = {}
fax_meta_data = {}

# Active devices - to hold event history
devices = {} # { 'device_uri' : ServerDevice, ... }

socket_map = {}
loopback_trigger = None


class ServerDevice(object):
    def __init__(self, model=''):
        self.history = utils.RingBuffer(prop.history_size)
        self.model = device.normalizeModelName(model)
        self.cache = {}

class hpssd_server(dispatcher):
    def __init__(self, ip, port):
        self.ip = ip
        self.send_events = False
        self.port = port
        
        if port == 0:
            raise Error(ERROR_INVALID_PORT_NUMBER)

        dispatcher.__init__(self)
        self.typ = 'server'
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()

        try:
            self.bind((ip, port))
        except socket.error:
            raise Error(ERROR_UNABLE_TO_BIND_SOCKET)

        prop.hpssd_port = self.port = self.socket.getsockname()[1]
        self.listen(5)


    def writable(self):
        return False

    def readable(self):
        return self.accepting

    def handle_accept(self):
        try:
            conn, addr = self.accept()
            log.debug("Connected to client: %s:%d (%d)" % (addr[0], addr[1], self._fileno))
        except socket.error:
            log.error("Socket error on accept()")
            return
        except TypeError:
            log.error("EWOULDBLOCK exception on accept()")
            return
        handler = hpssd_handler(conn, addr, self)

    def handle_close(self):
        dispatcher.handle_close(self)


class hpssd_handler(dispatcher):
    def __init__(self, conn, addr, server):
        dispatcher.__init__(self, sock=conn)
        self.addr = addr
        self.in_buffer = ''
        self.out_buffer = ''
        self.server = server
        self.fields = {}
        self.payload = ''
        self.signal_exit = False
        self.typ = ''
        self.send_events = False 
        self.username = ''

        # handlers for all the messages we expect to receive
        self.handlers = {
            # Request/Reply Messages
            'setalerts'            : self.handle_setalerts,
            'testemail'            : self.handle_test_email,
            'queryhistory'         : self.handle_queryhistory,
            'setvalue'             : self.handle_setvalue, # device cache
            'getvalue'             : self.handle_getvalue, # device cache

            # Event Messages (no reply message)
            'event'                : self.handle_event,
            'registerguievent'     : self.handle_registerguievent, # register for events
            'unregisterguievent'   : self.handle_unregisterguievent,
            'exit'                 : self.handle_exit,

            # Fax
            # hpfax: -> hpssd
            'hpfaxbegin'           : self.handle_hpfaxbegin,
            'hpfaxdata'            : self.handle_hpfaxdata,
            'hpfaxend'             : self.handle_hpfaxend,
            # hp-sendfax -> hpssd
            'faxgetdata'           : self.handle_faxgetdata,
            'faxcheck'             : self.handle_faxcheck,

            # Misc
            'unknown'              : self.handle_unknown,
        }


    def handle_read(self):
        log.debug("Reading data on channel (%d)" % self._fileno)
        self.in_buffer = self.recv(prop.max_message_read)

        if not self.in_buffer:
            return False

        log.debug(repr(self.in_buffer))
        remaining_msg = self.in_buffer

        while True:
            try:
                self.fields, self.payload, remaining_msg = parseMessage(remaining_msg)
            except Error, e:
                err = e.opt
                log.warn("Message parsing error: %s (%d)" % (e.msg, err))
                self.out_buffer = self.handle_unknown(err)
                log.debug(self.out_buffer)
                return True

            msg_type = self.fields.get('msg', 'unknown').lower()
            log.debug("Handling: %s %s %s" % ("*"*20, msg_type, "*"*20))
            log.debug(repr(self.in_buffer))

            try:
                self.handlers.get(msg_type, self.handle_unknown)()
            except Error:
                log.error("Unhandled exception during processing:")
                log.exception()

            try:
                self.handle_write()
            except socket.error, why:
                log.error("Socket error: %s" % why)

            if not remaining_msg:
                break

        return True

    def handle_unknown(self, err=ERROR_INVALID_MSG_TYPE):
        pass


    def handle_write(self):
        if not self.out_buffer:
            return

        log.debug("Sending data on channel (%d)" % self._fileno)
        log.debug(repr(self.out_buffer))

        while self.out_buffer:
            sent = self.send(self.out_buffer)
            self.out_buffer = self.out_buffer[sent:]

        if self.signal_exit:
            self.handle_close()


    def __checkdevice(self, device_uri):
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

            devices[device_uri] = ServerDevice(model)

        return ERROR_SUCCESS


    def handle_getvalue(self):
        device_uri = self.fields.get('device-uri', '').replace('hpfax:', 'hp:')
        value = ''
        key = self.fields.get('key', '')
        result_code = self.__checkdevice(device_uri)

        if result_code == ERROR_SUCCESS:
            try:
                value = devices[device_uri].cache[key]
            except KeyError:
                value, result_code = '', ERROR_INTERNAL

        self.out_buffer = buildResultMessage('GetValueResult', value, result_code)

    def handle_setvalue(self):
        device_uri = self.fields.get('device-uri', '').replace('hpfax:', 'hp:')
        key = self.fields.get('key', '')
        value = self.fields.get('value', '')
        result_code = self.__checkdevice(device_uri)

        if result_code == ERROR_SUCCESS:    
            devices[device_uri].cache[key] = value

        self.out_buffer = buildResultMessage('SetValueResult', None, ERROR_SUCCESS)

    def handle_queryhistory(self):
        device_uri = self.fields.get('device-uri', '').replace('hpfax:', 'hp:')
        payload = ''
        result_code = self.__checkdevice(device_uri)

        if result_code == ERROR_SUCCESS:    
            for h in devices[device_uri].history.get():
                payload = '\n'.join([payload, ','.join([str(x) for x in h])])

        self.out_buffer = buildResultMessage('QueryHistoryResult', payload, result_code)

    # TODO: Need to load alerts at start-up
    def handle_setalerts(self):
        result_code = ERROR_SUCCESS
        username = self.fields.get('username', '')

        alerts[username] = {'email-alerts'       : utils.to_bool(self.fields.get('email-alerts', '0')),
                            'email-from-address' : self.fields.get('email-from-address', ''),
                            'email-to-addresses' : self.fields.get('email-to-addresses', ''),
                           }

        self.out_buffer = buildResultMessage('SetAlertsResult', None, result_code)


    # EVENT
    def handle_registerguievent(self):
        username = self.fields.get('username', '')
        typ = self.fields.get('type', 'unknown')
        self.typ = typ
        self.username = username
        self.send_events = True
        log.debug("Registering GUI for events: (%s, %s, %d)" % (username, typ, self._fileno))

    # EVENT
    def handle_unregisterguievent(self):
        username = self.fields.get('username', '')
        self.send_events = False


    def handle_test_email(self):
        result_code = ERROR_SUCCESS
        username = self.fields.get('username', prop.username)
        message = device.queryString('email_test_message')
        subject = device.queryString('email_test_subject')
        result_code = self.sendEmail(username, subject, message, True)
        self.out_buffer = buildResultMessage('TestEmailResult', None, result_code)

    def createHistory(self, device_uri, code, jobid=0, username=prop.username):
        result_code = self.__checkdevice(device_uri)

        if result_code == ERROR_SUCCESS:    
            history = devices[device_uri].history.get()
            
            if history and history[-1][11] == code:
                devices[device_uri].history.replace(tuple(time.localtime()) +
                                                (jobid, username, code))
                return True
            else:
                devices[device_uri].history.append(tuple(time.localtime()) +
                                                    (jobid, username, code))
                return False

    # sent by hpfax: to indicate the start of a complete fax rendering job
    def handle_hpfaxbegin(self):
        username = self.fields.get('username', prop.username)
        job_id = self.fields.get('job-id', 0)
        printer_name = self.fields.get('printer', '')
        device_uri = self.fields.get('device-uri', '').replace('hp:', 'hpfax:')
        title = self.fields.get('title', '')

        log.debug("Creating data store for %s:%d" % (username, job_id))
        fax_file[(username, job_id)] = tempfile.NamedTemporaryFile(prefix="hpfax")
        fax_file_ready[(username, job_id)] = False
        fax_meta_data[(username, job_id)] = {'username': username, 'job-id': job_id, 'title': title, 'printer': printer_name, 'device-uri': device_uri, 'size': 0}

        log.debug("Fax job %d for user %s stored in temp file %s." % (job_id, username, fax_file[(username, job_id)].name))
        self.out_buffer = buildResultMessage('HPFaxBeginResult', None, ERROR_SUCCESS)


    # sent by hpfax: to transfer completed fax rendering data
    def handle_hpfaxdata(self):
        username = self.fields.get('username', prop.username)
        job_id = self.fields.get('job-id', 0)

        if self.payload and (username, job_id) in fax_file and \
            not fax_file_ready[(username, job_id)]:

            fax_file[(username, job_id)].write(self.payload)

        self.out_buffer = buildResultMessage('HPFaxDataResult', None, ERROR_SUCCESS)


    # sent by hpfax: to indicate the end of a complete fax rendering job
    def handle_hpfaxend(self):
        username = self.fields.get('username', '')
        job_id = self.fields.get('job-id', 0)
        printer_name = self.fields.get('printer', '')
        device_uri = self.fields.get('device-uri', '').replace('hp:', 'hpfax:')
        title = self.fields.get('title', '')
        job_size = self.fields.get('job-size', 0)

        fax_file[(username, job_id)].seek(0)
        fax_file_ready[(username, job_id)] = True
        fax_meta_data[(username, job_id)]['job-size'] = job_size

        self.out_buffer = buildResultMessage('HPFaxEndResult', None, ERROR_SUCCESS)


    # sent by hp-sendfax to see if any faxes have been printed and need to be picked up
    def handle_faxcheck(self):
        username = self.fields.get('username', '')
        result_code = ERROR_NO_DATA_AVAILABLE
        other_fields = {}

        for f in fax_file:
            user, job_id = f

            if user == username:
                other_fields = fax_meta_data[(username, job_id)]

                if fax_file_ready[f]:
                    result_code = ERROR_FAX_READY
                else:
                    result_code = ERROR_FAX_PROCESSING

                break

        self.out_buffer = buildResultMessage('FaxCheckResult', None, result_code, other_fields)

    # sent by hp-sendfax to retrieve a complete fax rendering job
    # sent in response to the EVENT_FAX_RENDER_COMPLETE event or
    # after being run with --job param, both after a hpfaxend message
    def handle_faxgetdata(self):
        result_code = ERROR_SUCCESS
        username = self.fields.get('username', '')
        job_id = self.fields.get('job-id', 0)

        try:
            fax_file[(username, job_id)]

        except KeyError:
            result_code, data = ERROR_NO_DATA_AVAILABLE, ''

        else:
            if fax_file_ready[(username, job_id)]:
                data = fax_file[(username, job_id)].read(prop.max_message_len)

                if not data:
                    result_code = ERROR_NO_DATA_AVAILABLE
                    log.debug("Deleting data store for %s:%d" % (username, job_id))
                    del fax_file[(username, job_id)]
                    del fax_file_ready[(username, job_id)]
                    del fax_meta_data[(username, job_id)]

            else:
                result_code, data = ERROR_NO_DATA_AVAILABLE, ''

        self.out_buffer = buildResultMessage('FaxGetDataResult', data, result_code)


    # EVENT
    def handle_event(self):
        gui_port, gui_host = None, None
        event_type = self.fields.get('event-type', 'event')
        event_code = self.fields.get('event-code', 0)
        device_uri = self.fields.get('device-uri', '').replace('hpfax:', 'hp:')
        log.debug("Device URI: %s" % device_uri)

        error_string_short = device.queryString(str(event_code), 0)
        error_string_long = device.queryString(str(event_code), 1)

        log.debug("Short/Long: %s/%s" % (error_string_short, error_string_long))

        job_id = self.fields.get('job-id', 0)

        try:
            username = self.fields['username']
        except KeyError:
            if job_id == 0:
                username = prop.username
            else:
                jobs = cups.getAllJobs()
                for j in jobs:
                    if j.id == job_id:
                        username = j.user
                        break
                else:
                    username = prop.username


        no_fwd = utils.to_bool(self.fields.get('no-fwd', '0'))
        log.debug("Username (jobid): %s (%d)" % (username, job_id))
        retry_timeout = self.fields.get('retry-timeout', 0)
        user_alerts = alerts.get(username, {})        

        dup_event = False
        if event_code <= EVENT_MAX_USER_EVENT:
            dup_event = self.createHistory(device_uri, event_code, job_id, username)

        if not no_fwd:
            if event_code <= EVENT_MAX_USER_EVENT and \
                user_alerts.get('email-alerts', False) and \
                event_type == 'error' and \
                not dup_event:

                subject = device.queryString('email_alert_subject') + device_uri

                message = '\n'.join([device_uri, 
                                     time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()),
                                     error_string_short, 
                                     error_string_long,
                                     str(event_code)])

                self.sendEmail(username, subject, message, False)


    def sendEmail(self, username, subject, message, wait):
        msg = cStringIO.StringIO()
        result_code = ERROR_SUCCESS

        user_alerts = alerts.get(username, {}) 
        from_address = user_alerts.get('email-from-address', '')
        to_addresses = user_alerts.get('email-to-addresses', from_address)

        t = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        UUID = file("/proc/sys/kernel/random/uuid").readline().rstrip("\n")

        msg.write("Date: %s\n" % t)
        msg.write("From: <%s>\n" % from_address)
        msg.write("To: %s\n" % to_addresses)
        msg.write("Message-Id: <%s %s>\n" % (UUID, t))
        msg.write('Content-Type: text/plain\n')
        msg.write("Content-Transfer-Encoding: 7bit\n")
        msg.write('Mime-Version: 1.0\n')
        msg.write("Subject: %s\n" % subject)
        msg.write('\n')
        msg.write(message)
        #msg.write('\n')
        email_message = msg.getvalue()
        log.debug(repr(email_message))

        mt = MailThread(email_message, from_address)
        mt.start()

        if wait:
            mt.join() # wait for thread to finish
            result_code = mt.result

        return result_code


    # EVENT
    def handle_exit(self):
        self.signal_exit = True
        sys.exit(0)

    def handle_messageerror(self):
        pass

    def writable(self):
        return not (not self.out_buffer and self.connected)


    def handle_close(self):
        log.debug("Closing channel (%d)" % self._fileno)
        self.connected = False
        self.close()


class MailThread(threading.Thread):
    def __init__(self, message, from_address):
        threading.Thread.__init__(self)
        self.message = message
        self.from_address = from_address
        self.result = ERROR_SUCCESS

    def run(self):
        log.debug("Starting Mail Thread...")
        sendmail = utils.which('sendmail')

        if sendmail:
            sendmail = os.path.join(sendmail, 'sendmail')
            cmd = [sendmail,'-t','-r',self.from_address]

            log.debug(repr(cmd))
            err = None
            try:
                sp = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                std_out, std_err = sp.communicate(self.message)
                log.debug(repr(self.message))
                if std_err != '':
                    err = std_err

            except OSError, e:
                err = str(e)

            if err:
                log.error(repr(err))
                self.result = ERROR_TEST_EMAIL_FAILED

        else:
            log.error("Mail send failed. sendmail not found.")
            self.result = ERROR_TEST_EMAIL_FAILED

        log.debug("Exiting mail thread")

USAGE = [(__doc__, "", "name", True),
         ("Usage: hpssd.py [OPTIONS]", "", "summary", True),
         utils.USAGE_OPTIONS,
         ("Do not daemonize:", "-x", "option", False),
         ("Port to listen on:", "-p<port> or --port=<port> (overrides value in /etc/hp/hplip.conf)", "option", False),
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2,
         ("Run in debug mode:", "-g (same as options: -ldebug -x)", "option", False),
         utils.USAGE_HELP,
        ]


def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hpssd.py', __version__)
    sys.exit(0)

def handleSIGUSR1(num, frame):
    log.debug("Signal USR1 received.")

def handleSIGHUP(signo, frame):
    log.info("SIGHUP")

def main(args):
    log.set_module('hpssd')

    prop.prog = sys.argv[0]
    prop.daemonize = True

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'l:xhp:g', 
            ['level=', 'help', 'help-man', 'help-rest', 'port=', 'help-desc'])

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
            prop.daemonize = False

        elif o in ('-x',):
            prop.daemonize = False

        elif o in ('-h', '--help'):
            usage()

        elif o == '--help-rest':
            usage('rest')

        elif o == '--help-man':
            usage('man')

        elif o == '--help-desc':
            print __doc__,
            sys.exit(0)

        elif o in ('-p', '--port'):
            try:
                prop.hpssd_port = int(a)
            except ValueError:
                log.error('Port must be a numeric value')
                usage()


    utils.log_title(__title__, __version__)

    prop.history_size = 100

    if prop.daemonize:
        utils.daemonize()

    # hpssd server dispatcher object
    try:
        server = hpssd_server(prop.hpssd_host, prop.hpssd_port)
    except Error, e:
        log.error("Server exited with error: %s" % e.msg)
        sys.exit(1)

    os.umask (0077)
    log.debug('host=%s port=%d' % (prop.hpssd_host, prop.hpssd_port))
    log.info("Listening on %s:%d" % (prop.hpssd_host, prop.hpssd_port))

    signal.signal(signal.SIGUSR1, handleSIGUSR1)

    try:
        log.debug("Starting async loop...")
        try:
            loop(timeout=5.0)
        except KeyboardInterrupt:
            log.warn("Ctrl-C hit, exiting...")
        except Exception:
            log.exception()

        log.debug("Cleaning up...")
    finally:
        server.close()
        return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


