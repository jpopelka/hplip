# -*- coding: utf-8 -*-
#   Id: asyncore.py,v 2.51 2000/09/07 22:29:26 rushing Exp
# Modified for hplips 2003/06/20
#   Author: Sam Rushing <rushing@nightmare.com>
# ======================================================================
# Copyright 1996 by Sam Rushing
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
# Modified by: Don Welch
#




"""
Basic infrastructure for asynchronous socket service clients and servers.

There are only two ways to have a program on a single processor do "more
than one thing at a time".  Multi-threaded programming is the simplest and
most popular way to do it, but there is another very different technique,
that lets you have nearly all the advantages of multi-threading, without
actually using multiple threads. it's really only practical if your program
is largely I/O bound. If your program is CPU bound, then pre-emptive
scheduled threads are probably what you really need. Network servers are
rarely CPU-bound, however.

If your operating system supports the select() system call in its I/O
library (and nearly all do), then you can use it to juggle multiple
communication channels at once; doing other work while your I/O is taking
place in the "background."  Although this strategy can seem strange and
complex, especially at first, it is in many ways easier to understand and
control than multi-threaded programming. The module documented here solves
many of the difficult problems for you, making the task of building
sophisticated high-performance network servers and clients a snap.

NOTICE: This copy of asyncore has been modified from the Python Std Lib version.

"""


import select
import socket
import sys
import time
import os
from qt import *
from g import *


from errno import EALREADY, EINPROGRESS, EWOULDBLOCK, ECONNRESET, \
     ENOTCONN, ESHUTDOWN, EINTR, EISCONN, EAGAIN


class ExitNow(Exception):
    pass


channels = {}    

class dispatcher(QObject):
    connected = False
    accepting = False
    closing = False
    addr = None

    def __init__ (self, sock=None):
        self.sock_write_notifier = None
        self.sock_read_notifier = None

        if sock:
            self.set_socket(sock) 
            self.socket.setblocking(0)
            self.connected = True
            try:
                self.addr = sock.getpeername()
            except socket.error:
                # The addr isn't crucial
                pass
        else:
            self.socket = None


    def add_channel(self): 
        global channels
        channels[self._fileno] = self

        self.sock_read_notifier = QSocketNotifier(self._fileno, QSocketNotifier.Read) 
        QObject.connect(self.sock_read_notifier, SIGNAL("activated(int)"), self.handle_read_event)

        self.sock_read_notifier.setEnabled(True)

        self.sock_write_notifier = QSocketNotifier(self._fileno, QSocketNotifier.Write) 
        QObject.connect(self.sock_write_notifier, SIGNAL("activated(int)"), self.handle_write_event)

        self.sock_write_notifier.setEnabled(False)

    def del_channel(self): 
        QObject.disconnect(self.sock_read_notifier, SIGNAL("activated(int)"), self.handle_read_event)
        QObject.disconnect(self.sock_write_notifier, SIGNAL("activated(int)"), self.handle_write_event)

        self.sock_write_notifier.setEnabled(False)
        self.sock_read_notifier.setEnabled(False)

        global channels
        try:
            del channels[self._fileno]
        except KeyError:
            pass 

        self._fileno = 0


    def create_socket(self, family, type):
        self.family_and_type = family, type
        self.socket = socket.socket (family, type)
        self.socket.setblocking(0)
        self._fileno = self.socket.fileno()
        self.add_channel()

    def set_socket(self, sock): 
        self.socket = sock
        self._fileno = sock.fileno()
        self.add_channel()

    def set_reuse_addr(self):
        # try to re-use a server port if possible
        try:
            self.socket.setsockopt (
                socket.SOL_SOCKET, socket.SO_REUSEADDR,
                self.socket.getsockopt (socket.SOL_SOCKET,
                                        socket.SO_REUSEADDR) | 1
                )
        except socket.error:
            pass


    # ==================================================
    # socket object methods.
    # ==================================================

    def listen (self, num):
        self.accepting = True
        return self.socket.listen(num)

    def bind(self, addr):
        self.addr = addr
        return self.socket.bind(addr)

    def connect(self, address):
        self.connected = False
        err = self.socket.connect_ex(address)

        if err in (EINPROGRESS, EALREADY, EWOULDBLOCK):
            r, w, e = select.select([], [self.socket.fileno()], [], 5.0)
            err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)

        if err in (0, EISCONN):
            self.addr = address
            self.connected = True
            self.handle_connect()
        else:
            raise socket.error, err

    def accept (self):
        try:
            conn, addr = self.socket.accept()
            return conn, addr
        except socket.error, why:
            if why[0] == EWOULDBLOCK:
                pass
            else:
                raise socket.error, why

    def send (self, data):
        try:
            result = self.socket.send(data)
        except socket.error, why:
            if why[0] == EWOULDBLOCK:
                return 0
            elif why[0] == EAGAIN:
                self.sock_write_notifier.setEnabled(True)
                return 0
            else:
                raise socket.error, why
        else: # write succeeded
            self.sock_write_notifier.setEnabled(False)
            return result

    def recv(self, buffer_size):
        try:
            data = self.socket.recv (buffer_size)
            if not data:
                # a closed connection is indicated by signaling
                # a read condition, and having recv() return 0.
                self.handle_close()
                return ''
            else:
                return data
        except socket.error, why:
            # winsock sometimes throws ENOTCONN
            if why[0] in [ECONNRESET, ENOTCONN, ESHUTDOWN]:
                self.handle_close()
                return ''
            else:
                raise socket.error, why

    def close (self):
        self.del_channel()
        self.connected = False
        self.socket.close()

    # cheap inheritance, used to pass all other attribute
    # references to the underlying socket object.
    def __getattr__ (self, attr):
        return getattr (self.socket, attr)

    def handle_read_event(self):
        if self.accepting:
            # for an accepting socket, getting a read implies
            # that we are connected
            if not self.connected:
                self.connected = True
            self.handle_accept()
        elif not self.connected:
            self.handle_connect()
            self.connected = True
            self.handle_read()
        else:
            self.handle_read()

    def handle_write_event(self):
        # getting a write implies that we are connected
        if not self.connected:
            self.handle_connect()
            self.connected = True
        self.handle_write()

    def handle_expt_event(self):
        self.handle_expt()

    def handle_error(self):
        self.handle_close()

    def handle_expt(self):
        raise Error

    def handle_read(self):
        raise Error

    def handle_write(self):
        raise Error

    def handle_connect(self):
        pass

    def handle_accept(self):
        raise Error

    def handle_close(self):
        self.close()



def close_all(): 
    global channels
    for x in channels.values():
        x.channels.close()
    channels.clear()

