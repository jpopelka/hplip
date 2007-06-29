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
import sys, cStringIO, select, socket

# Local
from g import *
from codes import *

#valid_encodings = ('', 'none', 'base64')
#valid_char_encodings = ('', 'utf-8', 'latin-1')


def buildResultMessage(msg_type, payload=None, result_code=ERROR_SUCCESS, other_fields={}):
    other_fields.update({'result-code' : result_code})
    return buildMessage(msg_type, payload, other_fields)

def buildMessage(msg_type, payload=None, other_fields={}):

    if msg_type is None or not msg_type:
        raise Error(ERROR_INVALID_MSG_TYPE)

    msg = cStringIO.StringIO()
    msg.write("msg=%s\n" % msg_type.lower())

    if other_fields:
        for k in other_fields:
            msg.write('%s=%s\n' % (k, str(other_fields[k])))

    if payload is not None:
        #msg.write("encoding=none\n")
        msg.write("length=%d\n" % len(str(payload)))
        msg.write("data:\n%s" % str(payload))

    return msg.getvalue()


def parseMessage(message):
    fields, data_found, data, remaining_msg = {}, False, '', ''
    msg_key_found, second_msg_key = False, False

    try:
        msg = cStringIO.StringIO(message)
    except TypeError:
        raise Error(ERROR_INVALID_MSG_TYPE)

    while True:
        pos = msg.tell()
        line = msg.readline().strip()

        if line == "":
            break

        if line.startswith('data:'):
            data = msg.read(fields['length']) or ''
            data_found = True
            continue

        if line.startswith('#'):
            continue

        try:
            key, value = line.split('=', 1)
            key = key.strip().lower()
        except ValueError:
            raise Error(ERROR_INVALID_MSG_TYPE)

        if key == 'msg':
            if msg_key_found:
                # already found, another message...
                second_msg_key = True
                break
            else:
                msg_key_found = True

        # If it looks like a number, convert it, otherwise leave it alone
        try:
            fields[key] = int(value)
        except ValueError:
            fields[key] = value

    if second_msg_key:
        msg.seek(pos)
        remaining_msg = msg.read() or ''

    return fields, data, remaining_msg


def sendEvent(sock, msg_type, payload=None, other_fields={}, 
              timeout=prop.read_timeout):

    m = buildMessage(msg_type, payload, other_fields)

    log.debug("Sending data on channel (%d)" % sock.fileno())
    log.debug(repr(m))

    r, w, e = select.select([], [sock], [], timeout)

    if w == []:
        raise Error(ERROR_INTERNAL)

    try:
        sock.send(m)
    except socket.error:
        log.exception()
        raise Error(ERROR_INTERNAL)


def xmitMessage(sock, msg_type, payload=None,
                 other_fields={},
                 timeout=prop.read_timeout):

    fields, data, result_code = {}, '', ERROR_INTERNAL

    msg_type = msg_type.lower().strip()
    m = buildMessage(msg_type, payload, other_fields)

    log.debug("(xmit) Sending data on channel (%d)" % sock.fileno())
    log.debug(repr(m))

    r, w, e = select.select([], [sock], [], timeout)

    if w == []:
        raise Error(ERROR_INTERNAL)

    try:
        sock.send(m)
    except socket.error:
        log.exception()
        raise Error(ERROR_INTERNAL)

    read_tries = 0
    read_flag = True

    while read_flag:
        remaining = ''
        read_tries += 1

        if read_tries > 3:
            break

        r, w, e = select.select([sock], [], [], timeout)

        if r == []:
            raise Error(ERROR_INTERNAL)

        m = sock.recv(prop.max_message_read)

        if m == '':
            continue

        log.debug("(xmit) Reading data on channel (%d)" % sock.fileno())

        while True:
            log.debug(repr(m))
            fields, data, remaining = parseMessage(m)

            try:
                result_code = fields['result-code']
            except KeyError:
                result_code = ERROR_INTERNAL
            else:
                del fields['result-code']

            try:
                result_msg_type = fields['msg'].lower().strip()
            except KeyError:
                result_msg_type = ''
            else:
                del fields['msg']

            # Found the msg we were looking for or error
            if result_msg_type == ''.join([msg_type, 'result']) or \
                result_msg_type == 'messageerror': 
                read_flag = False # exit read loop
                break
            else:
                log.debug("Ignored out of sequence message")

            if remaining: # more messages to look at in this read
                log.debug("Remaining message")
                m = remaining # parse remainder
            else:
                # keep reading until we find the result msg...
                break


    return fields, data, result_code




def recvMessage(sock, timeout=prop.read_timeout):
    fields, data, result_code = {}, '', ERROR_INTERNAL

    read_tries = 0
    read_flag = True

    while read_flag:
        remaining = ''
        read_tries += 1

        if read_tries > 3:
            break

        r, w, e = select.select([sock], [], [], timeout)

        if r == []:
            #raise Error(ERROR_INTERNAL)
            continue

        m = sock.recv(prop.max_message_read)

        if m == '':
            continue

        log.debug("(xmit) Reading data on channel (%d)" % sock.fileno())

        while True:
            log.debug(repr(m))
            fields, data, remaining = parseMessage(m)

            try:
                result_code = fields['result-code']
            except KeyError:
                result_code = ERROR_INTERNAL
            else:
                del fields['result-code']

            try:
                result_msg_type = fields['msg'].lower().strip()
            except KeyError:
                result_msg_type = ''
            else:
                del fields['msg']

            # Found the msg we were looking for or error
            #if result_msg_type == ''.join([msg_type, 'result']) or \
            if result_msg_type == 'messageerror': 
                read_flag = False # exit read loop
                break
            #else:
            #    log.debug("Ignored out of sequence message")

            if remaining: # more messages to look at in this read
                log.debug("Remaining message")
                m = remaining # parse remainder
            else:
                # keep reading until we find the result msg...
                break    

    return fields, data, result_code

