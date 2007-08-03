# -*- coding: utf-8 -*-
#
# (c) Copyright 2001-2007 Hewlett-Packard Development Company, L.P.
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

# Local
from base.g import *
from base import utils

# Qt
from qt import *
from scrollview import ScrollView

# Std Lib
import os.path, os

class ScrollFunctionsView(ScrollView):
    def __init__(self, parent = None,form=None, name = None,fl = 0):

        ScrollView.__init__(self,parent,name,fl)

        self.user_settings = utils.UserSettings()
        self.form = form

        self.ScanPixmap = QPixmap(os.path.join(prop.image_dir, "scan_icon.png"))
        self.PrintPixmap = QPixmap(os.path.join(prop.image_dir, "print_icon.png"))
        self.SendFaxPixmap =QPixmap(os.path.join(prop.image_dir, "fax_icon.png"))
        self.PhotoCardPixmap = QPixmap(os.path.join(prop.image_dir, "pcard_icon.png"))
        self.MakeCopiesPixmap = QPixmap(os.path.join(prop.image_dir, "makecopies_icon.png"))

    def fillControls(self):
        ScrollView.fillControls(self)

        if self.cur_device is not None and \
            self.cur_device.supported and \
            self.cur_device.device_state != DEVICE_STATE_NOT_FOUND:

            if self.user_settings.cmd_print_int:
                s = self.__tr("Print >>")
            else:
                s = self.__tr("Print...")

            self.addItem(self.__tr("<b>Print</b>"), self.__tr("Print documents or files."), 
                s, self.PrintPixmap, self.PrintButton_clicked)

            if self.cur_device.scan_type and prop.scan_build:
                if self.user_settings.cmd_scan_int:
                    s = self.__tr("Scan >>")
                else:
                    s = self.__tr("Scan...")

                self.addItem(self.__tr("<b>Scan</b>"), self.__tr("Scan a document, image, or photograph."),
                    s, self.ScanPixmap, self.ScanButton_clicked)

            if self.cur_device.fax_type and prop.fax_build:
                if self.user_settings.cmd_fax_int:
                    s = self.__tr("Send PC Fax >>")
                else:
                    s = self.__tr("Send PC Fax...")

                self.addItem(self.__tr("<b>Send PC Fax</b>"), self.__tr("Send a fax from the PC."),
                    s, self.SendFaxPixmap, self.SendFaxButton_clicked)

            if self.cur_device.copy_type:
                if self.user_settings.cmd_copy_int:
                    s = self.__tr("Make Copies >>")
                else:
                    s = self.__tr("Make Copies...")

                self.addItem(self.__tr("<b>Make Copies</b>"), self.__tr("Make copies on the device controlled by the PC."),
                    s, self.MakeCopiesPixmap, self.MakeCopiesButton_clicked)

            if self.cur_device.pcard_type:
                if self.user_settings.cmd_pcard_int:
                    s = self.__tr("Unload Photo Card >>")
                else:
                    s = self.__tr("Unload Photo Card...")

                self.addItem(self.__tr("<b>Unload Photo Card</b>"), self.__tr("Copy images from the device's photo card to the PC."),
                    s, self.PhotoCardPixmap, self.PCardButton_clicked)

        else:
            if not self.cur_device.supported:
                self.addGroupHeading("not_supported", self.__tr("ERROR: Device not supported."))
            else:
                self.addGroupHeading("not_found", self.__tr("ERROR: Device not found. Please check connection and power-on device."))

    def PrintButton_clicked(self):
        if self.user_settings.cmd_print_int:
            self.form.SwitchFunctionsTab("print")
        else:
            self.RunCommand(self.user_settings.cmd_print)

    def ScanButton_clicked(self):
        if self.user_settings.cmd_scan_int:
            self.form.SwitchFunctionsTab("scan")
        else:
            self.RunCommand(self.user_settings.cmd_scan)

    def PCardButton_clicked(self):
        if self.cur_device.pcard_type == PCARD_TYPE_MLC:
            if self.user_settings.cmd_pcard_int:
                self.form.SwitchFunctionsTab("pcard")
            else:
                self.RunCommand(self.user_settings.cmd_pcard)

        elif self.cur_device.pcard_type == PCARD_TYPE_USB_MASS_STORAGE:
            self.form.FailureUI(self.__tr("<p><b>Photocards on your printer are only available by mounting them as drives using USB mass storage.</b><p>Please refer to your distribution's documentation for setup and usage instructions."))

    def SendFaxButton_clicked(self):
        if self.user_settings.cmd_fax_int:
            self.form.SwitchFunctionsTab("fax")
        else:
            self.RunCommand(self.user_settings.cmd_fax)

    def MakeCopiesButton_clicked(self):
        if self.user_settings.cmd_copy_int:
            self.form.SwitchFunctionsTab("copy")
        else:
            self.RunCommand(self.user_settings.cmd_copy)

    def RunCommand(self, cmd, macro_char='%'):
        QApplication.setOverrideCursor(QApplication.waitCursor)

        try:
            if len(cmd) == 0:
                self.form.FailureUI(self.__tr("<p><b>Unable to run command. No command specified.</b><p>Use <pre>Configure...</pre> to specify a command to run."))
                log.error("No command specified. Use settings to configure commands.")
            else:
                log.debug("Run: %s %s (%s) %s" % ("*"*20, cmd, self.cur_device.device_uri, "*"*20))
                log.debug(cmd)
                cmd = ''.join([self.cur_device.device_vars.get(x, x) \
                                 for x in cmd.split(macro_char)])
                log.debug(cmd)

                path = cmd.split()[0]
                args = cmd.split()

                log.debug(path)
                log.debug(args)

                self.CleanupChildren()
                os.spawnvp(os.P_NOWAIT, path, args)

        finally:
            QApplication.restoreOverrideCursor()

    def CleanupChildren(self):
        log.debug("Cleaning up child processes.")
        try:
            os.waitpid(-1, os.WNOHANG)
        except OSError:
            pass

    def addItem(self, title, text, button_text, pixmap, button_func):
        widget = self.getWidget()

        self.addGroupHeading(title, title)

        layout1 = QGridLayout(widget, 1, 3, 5, 10,"layout1")

        layout1.setColStretch(0, 1)
        layout1.setColStretch(1, 10)
        layout1.setColStretch(2, 2)

        pushButton = QPushButton(widget, "pushButton")
        pushButton.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed, 0, 0,
            pushButton.sizePolicy().hasHeightForWidth()))

        layout1.addWidget(pushButton, 0, 3)

        icon = QLabel(widget, "icon")
        icon.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed, 0, 0,
            icon.sizePolicy().hasHeightForWidth()))

        icon.setMinimumSize(QSize(32, 32))
        icon.setMaximumSize(QSize(32, 32))
        icon.setScaledContents(1)
        layout1.addWidget(icon, 0, 0)

        textLabel = QLabel(widget, "textLabel")
        textLabel.setAlignment(QLabel.WordBreak)
        textLabel.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred, 0, 0,
            textLabel.sizePolicy().hasHeightForWidth()))        
        textLabel.setFrameShape(self.frame_shape)
        layout1.addWidget(textLabel, 0, 1)

        spacer1 = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout1.addItem(spacer1, 0, 2)

        textLabel.setText(text)
        pushButton.setText(button_text)
        icon.setPixmap(pixmap)

        self.connect(pushButton, SIGNAL("clicked()"), button_func)

        self.addWidget(widget, unicode(title))


    def __tr(self,s,c = None):
        return qApp.translate("ScrollFunctionsView",s,c)
