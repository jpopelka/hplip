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
# Author: Don Welch
#

# Local
from base.g import *
from base.codes import *
from ui_utils import *

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class SystrayFrame(QFrame):
    def __init__(self, parent):
        QFrame.__init__(self, parent)
#        self.systray_visible = 0
#        self.polling = polling
#        self.polling_interval = polling_interval
#        self.device_list = device_list
        #self.initUi()
        

    def initUi(self, systray_visible, polling, polling_interval, device_list):
        self.systray_visible = systray_visible
        self.polling = polling
        self.polling_interval = polling_interval
        self.device_list = device_list
        
        self.GridLayout = QGridLayout(self)
        self.GridLayout.setObjectName("GridLayout")

        self.GroupBox2 = QGroupBox(self)
        self.GroupBox2.setObjectName("GroupBox2")

        self.GridLayout2 = QGridLayout(self.GroupBox2)
        self.GridLayout2.setObjectName("GridLayout2")

        self.ShowAlwaysRadioButton = QRadioButton(self.GroupBox2)
        self.ShowAlwaysRadioButton.setObjectName("ShowAlwaysRadioButton")
        self.GridLayout2.addWidget(self.ShowAlwaysRadioButton,0,0,1,1)

        self.HideWhenInactiveRadioButton = QRadioButton(self.GroupBox2)
        self.HideWhenInactiveRadioButton.setObjectName("HideWhenInactiveRadioButton")
        self.GridLayout2.addWidget(self.HideWhenInactiveRadioButton,1,0,1,1)

        self.HideAlwaysRadioButton = QRadioButton(self.GroupBox2)
        self.HideAlwaysRadioButton.setObjectName("HideAlwaysRadioButton")
        self.GridLayout2.addWidget(self.HideAlwaysRadioButton,2,0,1,1)
        
        self.GridLayout.addWidget(self.GroupBox2,0,0,1,1)

        self.GroupBox = QGroupBox(self)
        self.GroupBox.setCheckable(True)
        self.GroupBox.setObjectName("GroupBox")

        self.GridLayout3 = QGridLayout(self.GroupBox)
        self.GridLayout3.setObjectName("GridLayout3")

        self.label = QLabel(self.GroupBox)
        self.label.setObjectName("label")
        self.GridLayout3.addWidget(self.label,0,0,1,1)

        self.DevicesListWidget = QListWidget(self.GroupBox)
        self.DevicesListWidget.setObjectName("DevicesListWidget")
        self.GridLayout3.addWidget(self.DevicesListWidget,1,0,1,1)
        
        self.GridLayout.addWidget(self.GroupBox,1,0,1,1)
        
        self.GroupBox2.setTitle(self.__tr("System tray icon visibility"))
        self.ShowAlwaysRadioButton.setText(self.__tr("Always show"))
        self.HideWhenInactiveRadioButton.setText(self.__tr("Hide when inactive"))
        self.HideAlwaysRadioButton.setText(self.__tr("Always hide"))
        self.GroupBox.setTitle(self.__tr("Monitor button presses on devices"))
        self.label.setText(self.__tr("Devices to Monitor:"))
        
        self.connect(self.ShowAlwaysRadioButton, SIGNAL("clicked(bool)"), self.ShowAlwaysRadioButton_clicked)
        self.connect(self.HideWhenInactiveRadioButton, SIGNAL("clicked(bool)"), self.HideWhenInactiveRadioButton_clicked)
        self.connect(self.HideAlwaysRadioButton, SIGNAL("clicked(bool)"), self.HideAlwaysRadioButton_clicked)
        
        self.GroupBox.setEnabled(False) # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


    def updateUi(self):
        self.updateVisibility()
        self.updateDeviceList()
        
        
    def updateVisibility(self):
        if self.systray_visible == SYSTRAY_VISIBLE_SHOW_ALWAYS:
            self.ShowAlwaysRadioButton.setChecked(True)
            
        elif self.systray_visible == SYSTRAY_VISIBLE_HIDE_WHEN_INACTIVE:
            self.HideWhenInactiveRadioButton.setChecked(True)
            
        else: # SYSTRAY_VISIBLE_HIDE_ALWAYS
            self.HideAlwaysRadioButton.setChecked(True)
            
    
    def ShowAlwaysRadioButton_clicked(self, b):
        if b: self.systray_visible = SYSTRAY_VISIBLE_SHOW_ALWAYS
        
        
    def HideWhenInactiveRadioButton_clicked(self, b):
        if b: self.systray_visible = SYSTRAY_VISIBLE_HIDE_WHEN_INACTIVE
        
        
    def HideAlwaysRadioButton_clicked(self, b):
        if b: self.systray_visible = SYSTRAY_VISIBLE_HIDE_ALWAYS
    
    
    def updateDeviceList(self):    
        pass
        
        
#    def saveSettings(self):
##        print self.ShowAlwaysRadioButton.isChecked()
##        print self.HideWhenInactiveRadioButton.isChecked()
##        print self.HideAlwaysRadioButton.isChecked()
#        
#        if self.ShowAlwaysRadioButton.isChecked():
#            print "show always"
#            self.user_settings.systray_visible = SYSTRAY_VISIBLE_SHOW_ALWAYS
#            
#        elif self.HideWhenInactiveRadioButton.isChecked():
#            print "hide when inactive"
#            self.user_settings.systray_visible = SYSTRAY_VISIBLE_HIDE_WHEN_INACTIVE
#            
#        else: # HideAlwaysRadioButton.isChecked()
#            print "hide always"
#            self.user_settings.systray_visible = SYSTRAY_VISIBLE_HIDE_ALWAYS
#            
#        self.systray_visible = self.user_settings.systray_visible
#        self.user_settings.save()
            
            
    def __tr(self, s, c=None):
        #return qApp.translate("SystrayFrame", s, c)
        return QApplication.translate("SystrayFrame", s, c, QApplication.UnicodeUTF8)
        
