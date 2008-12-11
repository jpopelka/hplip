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
from settingsdialog_base import Ui_SettingsDialog_base



class SettingsDialog(QDialog, Ui_SettingsDialog_base):
    def __init__(self, parent=None): 
        QDialog.__init__(self, parent) 
        self.setupUi(self)
        
        self.SetDefaultsButton.setEnabled(False)
        self.connect(self.SetDefaultsButton, SIGNAL("clicked()"),  self.SetDefaultsButton_clicked)
        
        self.user_settings = UserSettings()
        self.user_settings.load()
        
        self.SystemTraySettings.initUi(self.user_settings.systray_visible, 
                                       self.user_settings.polling, 
                                       self.user_settings.polling_interval, 
                                       self.user_settings.device_list)
        
        self.updateControls()


    def updateControls(self):
        self.AutoRefreshCheckBox.setChecked(self.user_settings.auto_refresh)
        self.AutoRefreshRateSpinBox.setValue(self.user_settings.auto_refresh_rate) # min
        #self.refreshTypeButtonGroup.setButton(self.user_settings.auto_refresh_type)
        if self.user_settings.auto_refresh_type == 1:
            self.RefreshCurrentRadioButton.setChecked(True)
        else:   
            RefreshAllRadioButton.setChecked(True)
            
        #self.PrintCommandLineEdit.setText(self.user_settings.cmd_print)
        self.ScanCommandLineEdit.setText(self.user_settings.cmd_scan)
        #self.AccessPCardCommandLineEdit.setText(self.user_settings.cmd_pcard)
        #self.SendFaxCommandLineEdit.setText(self.user_settings.cmd_fax)
        #self.MakeCopiesCommandLineEdit.setText(self.user_settings.cmd_copy)
        self.SystemTraySettings.systray_visible = self.user_settings.systray_visible
        self.SystemTraySettings.updateUi()
        
    
    def updateData(self):
        self.user_settings.systray_visible = self.SystemTraySettings.systray_visible
        #self.user_settings.cmd_print = unicode(self.PrintCommandLineEdit.text())
        self.user_settings.cmd_scan = unicode(self.ScanCommandLineEdit.text())
        #self.user_settings.cmd_pcard = unicode(self.AccessPCardCommandLineEdit.text())
        #self.user_settings.cmd_fax   = unicode(self.SendFaxCommandLineEdit.text())
        #self.user_settings.cmd_copy  = unicode(self.MakeCopiesCommandLineEdit.text())
        self.user_settings.auto_refresh = bool(self.AutoRefreshCheckBox.isChecked())
        #self.user_settings.auto_refresh_type = self.refreshScopeButtonGroup.selectedId()
        
        if self.RefreshCurrentRadioButton.isChecked():
            self.user_settings.auto_refresh_type = 1
        else:
            self.user_settings.auto_refresh_type = 2
            
        self.user_settings.auto_refresh_rate = self.AutoRefreshRateSpinBox.value()


    def SetDefaultsButton_clicked(self):
        self.user_settings.loadDefaults()
        self.updateControls()

#    def TabWidget_currentChanged(self,a0):
#        name = str(a0.name())
#
#        if name == 'FunctionCommands':
#            self.DefaultsButton.setEnabled(True)
#        else:
#            self.DefaultsButton.setEnabled(False)

    #def autoRefreshCheckBox_clicked(self):
    #    pass

    #def refreshTypeButtonGroup_clicked(self,a0):
    #    self.auto_refresh_type = int(a0)

    def accept(self):
        self.updateData()
        #self.SystemTraySettings.saveSettings()
        self.user_settings.save()
        QDialog.accept(self)
        
        # TODO: Need a way to signal hp-systray if systray_visible has changed

    def __tr(self,s,c = None):
        return qApp.translate("SettingsDialog",s,c)


