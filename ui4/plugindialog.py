# -*- coding: utf-8 -*-
#
# (c) Copyright 2001-2008 Hewlett-Packard Development Company, L.P.
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
# Authors: Don Welch
#


# Local
from base.g import *
from base import device, utils
from prnt import cups
from base.codes import *
from ui_utils import *
from installer.core_install import CoreInstall

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Ui
from plugindialog_base import Ui_Dialog


PAGE_SOURCE = 0
# PAGE_LICENSE = 1 # part of plug-in itself, this is a placeholder
PAGE_MAX = 1



class PluginDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, install_mode=PLUGIN_NONE):
        QDialog.__init__(self, parent)
        self.install_mode = install_mode
        self.core = CoreInstall()
        self.core.set_plugin_version()
        self.setupUi(self)
        self.initUi()

        QTimer.singleShot(0, self.showSourcePage)


    def initUi(self):
        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.NextButton, SIGNAL("clicked()"), self.NextButton_clicked)

        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('prog', '48x48')))


    #
    # SOURCE PAGE
    #
    def showSourcePage(self):
        if self.install_mode == PLUGIN_REQUIRED:
            self.TitleLabel.setText(self.__tr("An additional driver plug-in is required to operate this printer. You may download the plug-in directly from an HP authorized server (recommended), or, if you already have a copy of the file, you can specify a path to the file (advanced)."))
            self.SkipRadioButton.setEnabled(False)

        elif self.install_mode == PLUGIN_OPTIONAL:
            self.TitleLabel.setText(self.__tr("An optional driver plug-in is available to enhance the operation of this printer. You may download the plug-in directly from an HP authorized server (recommended), skip this installation (not recommended), or, if you already have a copy of the file, you can specify a path to the file (advanced)."))

        self.connect(self.DownloadRadioButton, SIGNAL("toggled(bool)"), self.DownloadRadioButton_toggled)
        self.connect(self.CopyRadioButton, SIGNAL("toggled(bool)"), self.CopyRadioButton_toggled)
        self.connect(self.SkipRadioButton, SIGNAL("toggled(bool)"), self.SkipRadioButton_toggled)
        self.connect(self.PathLineEdit, SIGNAL("textChanged(const QString &)"), self.PathLineEdit_textChanged)
        self.connect(self.BrowseToolButton, SIGNAL("clicked()"), self.BrowseToolButton_clicked)

        self.BrowseToolButton.setIcon(QIcon(load_pixmap('folder_open', '16x16')))

        self.displayPage(PAGE_SOURCE)


    def DownloadRadioButton_toggled(self, b):
        if b:
            self.PathLineEdit.setEnabled(False)
            self.BrowseToolButton.setEnabled(False)
            self.NextButton.setEnabled(True)
            self.PathLineEdit.setStyleSheet("")


    def CopyRadioButton_toggled(self, b):
        if b:
            self.PathLineEdit.setEnabled(True)
            self.BrowseToolButton.setEnabled(True)
            self.plugin_path = unicode(self.PathLineEdit.text())
            self.setPathIndicators()


    def SkipRadioButton_toggled(self, b):
        if b:
            self.PathLineEdit.setEnabled(False)
            self.BrowseToolButton.setEnabled(False)
            self.NextButton.setEnabled(True)
            self.PathLineEdit.setStyleSheet("")


    def PathLineEdit_textChanged(self, t):
        self.plugin_path = unicode(t)
        self.setPathIndicators()


    def setPathIndicators(self):
        ok = True
        if not self.plugin_path or (self.plugin_path and os.path.isdir(self.plugin_path)):
            self.PathLineEdit.setToolTip(self.__tr("You must specify a path to the '%1' file.").arg(self.core.plugin_name))
            ok = False
        elif os.path.basename(self.plugin_path) != self.core.plugin_name:
            self.PathLineEdit.setToolTip(self.__tr("The plugin filename must be '%1'.").arg(self.core.plugin_name))
            ok = False

        if not ok:
            self.PathLineEdit.setStyleSheet("background-color: yellow; ")
            self.NextButton.setEnabled(False)
        else:
            self.PathLineEdit.setStyleSheet("")
            self.NextButton.setEnabled(True)
            self.PathLineEdit.setToolTip(QString(""))


    def BrowseToolButton_clicked(self):
        t = unicode(self.PathLineEdit.text())
        if not os.path.exists(t):
            t = os.path.expanduser('~')

        x = unicode(QFileDialog.getOpenFileName(self, self.__tr("Select Plug-in File"),
                                               t,
                                               self.__tr("Plugin Files (*.run)")))

        if x:
            self.plugin_path = x
            self.PathLineEdit.setText(self.plugin_path)

        self.setPathIndicators()

    #
    # Misc
    #

    def displayPage(self, page):
        self.updateStepText(page)
        self.StackedWidget.setCurrentIndex(page)


    def CancelButton_clicked(self):
        self.close()


    def NextButton_clicked(self):
#        p = self.StackedWidget.currentIndex()
        pass


    def updateStepText(self, p):
        self.StepText.setText(self.__tr("Step %1 of %2").arg(p+1).arg(PAGE_MAX+1))


    def __tr(self,s,c = None):
        return qApp.translate("PluginDialog",s,c)


