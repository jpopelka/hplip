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
from base import device, utils
from prnt import cups
from base.codes import *
from ui_utils import *

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Ui
from faxsetupdialog_base import Ui_Dialog
from deviceuricombobox import DEVICEURICOMBOBOX_TYPE_FAX_ONLY


class FaxSetupDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, device_uri):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.device_uri = device_uri
        self.initUi()

        QTimer.singleShot(0, self.updateUi)


    def initUi(self):
        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        #self.connect(self.ApplyButton, SIGNAL("clicked()"), self.ApplyButton_clicked)
        self.connect(self.FaxComboBox, SIGNAL("DeviceUriComboBox_noDevices"), self.FaxComboBox_noDevices)
        self.connect(self.FaxComboBox, SIGNAL("DeviceUriComboBox_currentChanged"), self.FaxComboBox_currentChanged)
        self.FaxComboBox.setType(DEVICEURICOMBOBOX_TYPE_FAX_ONLY)
        
        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('prog', '48x48')))

        if self.device_uri:
            self.FaxComboBox.setInitialDevice(self.device_uri)

    
    def updateUi(self):
        self.FaxComboBox.updateUi()
        

    def FaxComboBox_currentChanged(self, device_uri):
        self.device_uri = device_uri
        self.updateHeaderTab()
        self.updateCoverpageTab()
    
    
    def FaxComboBox_noDevices(self):
        FailureUI(self, self.__tr("<b>No devices that support fax setup found.</b>"))
        self.close()
    
    
    def CancelButton_clicked(self):
        self.close()
        
        
    def updateHeaderTab(self):
        pass
        
        
    def updateCoverpageTab(self):
        pass

    #
    # Misc
    # 

    def __tr(self,s,c = None):
        return qApp.translate("FaxSetupDialog",s,c)


