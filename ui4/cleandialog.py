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

# StdLib
import operator

# Local
from base.g import *
from base import device, utils, maint
from prnt import cups
from base.codes import *
from ui_utils import *

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Ui
from cleandialog_base import Ui_Dialog


d = None


class CleanDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, device_uri):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.device_uri = device_uri
        self.initUi()
        QTimer.singleShot(0, self.updateUi)
        self.level = 1


    def initUi(self):
        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.CleanButton, SIGNAL("clicked()"), self.CleanButton_clicked)
        self.connect(self.DeviceComboBox, SIGNAL("DeviceUriComboBox_noDevices"), self.DeviceUriComboBox_noDevices)
        self.connect(self.DeviceComboBox, SIGNAL("DeviceUriComboBox_currentChanged"), self.DeviceUriComboBox_currentChanged)
        self.DeviceComboBox.setFilter({'clean-type': (operator.gt, 0)})
        
        if self.device_uri:
            self.DeviceComboBox.setInitialDevice(self.device_uri)

        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('prog', '48x48')))
    
    
    def updateUi(self):
        self.DeviceComboBox.updateUi()
        self.LoadPaper.setButtonName(self.__tr("Clean"))
        self.LoadPaper.updateUi()
        
        if self.level == 1:
            self.Prompt.setText(self.__tr("""Click <i>Clean</i> to begin the level 1 cleaning process.</p>"""))
        elif self.level == 2:
            self.Prompt.setText(self.__tr("""<b>Cleaning level 1 is done after the page being printed is complete.</b> If the printed output from level 1 cleaning is acceptable, then click <i>Cancel</i> to exit. Otherwise, click <i>Clean</i> again to begin the level 2 cleaning process.</p>"""))
        else: # 3
            self.Prompt.setText(self.__tr("""<b>Cleaning level 2 is done after the page being printed is complete.</b> If the printed output from level 2 cleaning is acceptable, then click <i>Cancel</i> to exit. Otherwise, click <i>Clean</i> again to begin the level 3 cleaning process. <b>When the level 3 cleaning process is complete, this utility will automatically exit.<b></p>"""))


    def DeviceUriComboBox_currentChanged(self, device_uri):
        self.device_uri = device_uri
    
    
    def DeviceUriComboBox_noDevices(self):
        FailureUI(self, self.__tr("<b>No devices that support print cartridge cleaning found.</b><p>Click <i>OK</i> to exit.</p>"))
        self.close()


    def CancelButton_clicked(self):
        self.close()
        
        
    def CleanButton_clicked(self):
        global d
        
        self.DeviceComboBox.setEnabled(False)
        
        try:    
            if d is None:
                try:
                    d = device.Device(self.device_uri)
                except Error:
                    CheckDeviceUI(self)
                    return

            clean_type = d.clean_type

            try:
                d.open()
            except Error:
                CheckDeviceUI(self)
            else:
                if d.isIdleAndNoError():
                    if clean_type in (CLEAN_TYPE_PCL, # 1
                                      CLEAN_TYPE_PCL_WITH_PRINTOUT): # 3
                        
                        if self.level == 1:
                            maint.cleanType1(d)
                        
                        elif self.level == 2:
                            maint.primeType1(d)
                        
                        else: # 3
                            maint.wipeAndSpitType1(d)


                    elif clean_type == CLEAN_TYPE_LIDIL: # 2
                        if self.level == 1:
                            maint.cleanType2(d)
                        
                        elif self.level == 2:
                            maint.primeType2(d)
                        
                        else: # 3
                            maint.wipeAndSpitType2(d)

                else:
                    CheckDeviceUI(self)

        finally:
            if d is not None:
                d.close()
            
        # TODO: Add call to maint.print_clean_test_page() (CLEAN_TYPE_PCL_WITH_PRINTOUT)
            
        self.level += 1
        
        if self.level > 3:
            self.close()
            return
        
        self.updateUi()

    #
    # Misc
    # 

    def __tr(self,s,c = None):
        return qApp.translate("CleanDialog",s,c)


