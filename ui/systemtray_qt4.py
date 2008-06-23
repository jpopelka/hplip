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

# Std Lib
import sys
import struct
import select
import os
import signal
import os.path

# Local
from base.g import *
from base import device, utils
from base.codes import *

# PyQt
try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except ImportError:
    log.error("Python bindings for Qt4 not found. Try using --qt3. Exiting!")
    sys.exit(1)

# dbus
try:
    import dbus
    from dbus import SessionBus, lowlevel
except ImportError:
    log.error("Python bindings for dbus not found. Exiting!")
    sys.exit(1)


ERROR_STATE_TO_ICON = {
    ERROR_STATE_CLEAR: QSystemTrayIcon.Information, 
    ERROR_STATE_OK: QSystemTrayIcon.Information,
    ERROR_STATE_WARNING: QSystemTrayIcon.Warning,
    ERROR_STATE_ERROR: QSystemTrayIcon.Critical,
    ERROR_STATE_LOW_SUPPLIES: QSystemTrayIcon.Warning,
    ERROR_STATE_BUSY: QSystemTrayIcon.Warning,
    ERROR_STATE_LOW_PAPER: QSystemTrayIcon.Warning,
    ERROR_STATE_PRINTING: QSystemTrayIcon.Information,
    ERROR_STATE_SCANNING: QSystemTrayIcon.Information,
    ERROR_STATE_PHOTOCARD: QSystemTrayIcon.Information,
    ERROR_STATE_FAXING: QSystemTrayIcon.Information,
    ERROR_STATE_COPYING: QSystemTrayIcon.Information,
}


def load_pixmap(name, subdir=None, resize_to=None):
    name = ''.join([os.path.splitext(name)[0], '.png'])

    if subdir is None:
        dir = prop.image_dir
    else:
        dir = os.path.join(prop.image_dir, subdir)

    log.debug("Loading pixmap '%s' from %s" % (name, dir))

    f = os.path.join(dir, name)
    if os.path.exists(f):
        if resize_to is not None:
            img = QImage(f)
            x, y = resize_to
            return QPixmap.fromImage(img.scaled(x, y, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        else:
            return QPixmap(f)

    for w in utils.walkFiles(dir, recurse=True, abs_paths=True, return_folders=False, pattern=name):
        if resize_to is not None:
            img = QImage(w)
            x, y = resize_to
            return QPixmap.fromImage(img.scaled(x, y, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        else:
            return QPixmap(w)

    log.error("Pixmap '%s' not found!" % name)
    return None


class SystemTrayApp(QApplication):
    def __init__(self, args, read_pipe, child_pid):
        QApplication.__init__(self, args)

        self.child_pid = child_pid
        self.read_pipe = read_pipe
        self.fmt = "64s64sI32sI64sf"
        self.fmt_size = struct.calcsize(self.fmt)

        self.tray_icon = QSystemTrayIcon()
        icon = QIcon(load_pixmap("prog", "48x48", (22, 22)))
        self.tray_icon.setIcon(icon)

        self.menu = QMenu()

        title = QWidgetAction(self.menu)
        title.setDisabled(True)


        hbox = QFrame(self.menu)
        layout = QHBoxLayout(hbox)
        layout.setMargin(3)
        layout.setSpacing(5)
        pix_label = QLabel(hbox)

        layout.insertWidget(-1, pix_label, 0)

        icon_size = self.menu.style().pixelMetric(QStyle.PM_SmallIconSize)
        pix_label.setPixmap(icon.pixmap(icon_size))

        label = QLabel(hbox)
        layout.insertWidget(-1, label, 20)
        title.setDefaultWidget(hbox)

        label.setText(self.tr("HPLIP Status Service"))

        f = label.font()
        f.setBold(True)
        label.setFont(f)
        self.menu.insertAction(None, title)

        self.menu.addSeparator()

        self.menu.addAction(self.tr("HP Device Manager..."), self.toolbox_triggered)

        # TODO:
        #icon2 = QIcon(os.path.join(prop.image_dir, '16x16', 'settings.png'))
        #self.menu.addAction(icon2, self.tr("Options..."), self.preferences_triggered)

        icon3 = QIcon(os.path.join(prop.image_dir, '16x16', 'quit.png'))

        self.menu.addSeparator()
        self.menu.addAction(icon3, "Quit", self.quit_triggered)
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip("HPLIP Status Service")

        QObject.connect(self.tray_icon, SIGNAL("messageClicked()"), self.message_clicked)

        self.tray_icon.show()

        notifier = QSocketNotifier(self.read_pipe, QSocketNotifier.Read)
        QObject.connect(notifier, SIGNAL("activated(int)"), self.notifier_activated)

        QObject.connect(self.tray_icon, SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.tray_activated)


    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Context:
            #print "context menu"
            pass

        elif reason == QSystemTrayIcon.DoubleClick:
            #print "double click"
            self.toolbox_triggered()
            pass

        elif reason == QSystemTrayIcon.Trigger:
            #print "single click"
            pass

        elif reason == QSystemTrayIcon.MiddleClick:
            #print "middle click"
            pass



    def message_clicked(self):
        #print "\nPARENT: message clicked"
        pass

    def quit_triggered(self):
        self.quit()

    def toolbox_triggered(self):
        try:
            os.waitpid(-1, os.WNOHANG)
        except OSError:
            pass

        # See if it is already running...
        ok, lock_file = utils.lock_app('hp-toolbox', True)

        if ok: # able to lock, not running...
            utils.unlock(lock_file)

            path = utils.which('hp-toolbox')
            if path:
                path = os.path.join(path, 'hp-toolbox')
            else:
                self.tray_icon.showMessage(self.trUtf8("HPLIP Status Service"), 
                                self.trUtf8("Unable to locate hp-toolbox on system PATH."),
                                QSystemTrayIcon.Critical, 5000)

                log.error("Unable to find hp-toolbox on PATH.")
                return

            log.debug(path)
            os.spawnlp(os.P_NOWAIT, path, 'hp-toolbox')

        else: # ...already running, raise it
            args = ['', '', EVENT_RAISE_DEVICE_MANAGER, prop.username, 0, '', '']
            msg = lowlevel.SignalMessage('/', 'com.hplip.Toolbox', 'Event')
            msg.append(signature='ssisiss', *args)

            SessionBus().send_message(msg)


    def preferences_triggered(self):
        #print "\nPARENT: prefs!"
        pass

    def notifier_activated(self, s):
        m = ''
        while True:
            ready = select.select([self.read_pipe], [], [], 1.0)

            if ready[0]:
                m = ''.join([m, os.read(self.read_pipe, self.fmt_size)])
                if len(m) == self.fmt_size:
                    event = device.Event(*struct.unpack(self.fmt, m))
                    desc = device.queryString(event.event_code)

                    error_state = STATUS_TO_ERROR_STATE_MAP.get(event.event_code, ERROR_STATE_CLEAR)
                    icon = ERROR_STATE_TO_ICON.get(error_state, QSystemTrayIcon.Information)

                    if self.tray_icon.supportsMessages():
                        if event.job_id and event.title:
                            self.tray_icon.showMessage(self.trUtf8("HPLIP Device Status"), 
                                QString("%1\n%2\n%3\n(%4/%5/%6)").\
                                arg(event.device_uri).arg(event.event_code).\
                                arg(desc).arg(event.username).arg(event.job_id).arg(event.title),
                                icon, 5000)
                        else:
                            self.tray_icon.showMessage(self.trUtf8("HPLIP Device Status"), 
                                QString("%1\n%2\n%3").arg(event.device_uri).\
                                arg(event.event_code).arg(desc),
                                icon, 5000)

            else:
                break



def run(read_pipe, child_pid):
    log.set_module("hp-systray(qt4)")
    log.debug("Child PID=%d" % child_pid)

    app = SystemTrayApp(sys.argv, read_pipe, child_pid)

    notifier = QSocketNotifier(read_pipe, QSocketNotifier.Read)
    QObject.connect(notifier, SIGNAL("activated(int)"), app.notifier_activated)

    try:
        app.exec_()
    except KeyboardInterrupt:
        log.debug("Ctrl-C: Exiting...")


