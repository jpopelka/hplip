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
import os.path

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
from infodialog_base import Ui_Dialog
from deviceuricombobox import DEVICEURICOMBOBOX_TYPE_PRINTER_AND_FAX


class InfoDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, device_uri):
        QDialog.__init__(self, parent)
        self.device_uri = device_uri
        #self.tabs = []
        self.setupUi(self)
        self.initUi()

        QTimer.singleShot(0, self.updateUi)


    def initUi(self):
        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.DeviceComboBox, SIGNAL("DeviceUriComboBox_noDevices"), self.DeviceUriComboBox_noDevices)
        self.connect(self.DeviceComboBox, SIGNAL("DeviceUriComboBox_currentChanged"), self.DeviceUriComboBox_currentChanged)

        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('prog', '48x48')))

        if self.device_uri:
            self.DeviceComboBox.setInitialDevice(self.device_uri)

        self.DeviceComboBox.setType(DEVICEURICOMBOBOX_TYPE_PRINTER_AND_FAX)

        self.headers = [self.__tr("Key"), self.__tr("Value")]


    def updateUi(self):
        self.DeviceComboBox.updateUi()
        #self.updateInfoTable()


    def updateInfoTable(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.DynamicTableWidget.clear()
        self.DynamicTableWidget.setRowCount(0)
        self.DynamicTableWidget.setColumnCount(0)
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled

        while self.TabWidget.count() > 2:
            self.TabWidget.removeTab(2)   


        self.DynamicTableWidget.clear()
        self.DynamicTableWidget.setRowCount(0)
        self.DynamicTableWidget.setColumnCount(len(self.headers))
        self.DynamicTableWidget.setHorizontalHeaderLabels(self.headers)

        try:
            d = device.Device(self.device_uri, None)
        except Error:
            QApplication.restoreOverrideCursor()
            FailureUI(self, self.__tr("<b>Unable to open device %1.</b>").arg(self.device_uri))
            #self.close()
            return

        self.StaticTableWidget.clear()

        self.StaticTableWidget.setColumnCount(len(self.headers))
        self.StaticTableWidget.setHorizontalHeaderLabels(self.headers)

        mq_keys = d.mq.keys()
        mq_keys.sort()

        self.StaticTableWidget.setRowCount(len(mq_keys))

        for row, key in enumerate(mq_keys):            
            i = QTableWidgetItem(QString(key))
            i.setFlags(flags)
            self.StaticTableWidget.setItem(row, 0, i)  

            i = QTableWidgetItem(QString(str(d.mq[key])))
            i.setFlags(flags)
            self.StaticTableWidget.setItem(row, 1, i)  

        self.StaticTableWidget.resizeColumnToContents(0)
        self.StaticTableWidget.resizeColumnToContents(1)

        try:
            try:
                d.open()
                d.queryDevice()
            except Error, e:
                QApplication.restoreOverrideCursor()
                FailureUI(self, self.__tr("<b>Unable to open device %1.</b>").arg(self.device_uri))
                #self.close()
                return

            dq_keys = d.dq.keys()
            dq_keys.sort()

            self.DynamicTableWidget.setRowCount(len(dq_keys))

            for row, key in enumerate(dq_keys):
                i = QTableWidgetItem(QString(key))
                i.setFlags(flags)
                self.DynamicTableWidget.setItem(row, 0, i)  

                i = QTableWidgetItem(QString(str(d.dq[key])))
                i.setFlags(flags)
                self.DynamicTableWidget.setItem(row, 1, i)  


            self.DynamicTableWidget.resizeColumnToContents(0)
            self.DynamicTableWidget.resizeColumnToContents(1)

        finally:
            d.close()

        #self.StaticTableWidget.setColumnWidth(1, self.StaticTableWidget.width() - self.StaticTableWidget.columnWidth(0))

        printers = cups.getPrinters()

        for p in printers:
            if p.device_uri == self.device_uri:
                Tab = QWidget()
                Tab.setObjectName(QString(p.name))

                GridLayout = QGridLayout(Tab)
                GridLayout.setObjectName(QString("GridLayout-%s" % p.name))

                Table = QTableWidget(Tab)
                Table.setAlternatingRowColors(True)
                Table.setSelectionMode(QAbstractItemView.SingleSelection)
                Table.setSelectionBehavior(QAbstractItemView.SelectRows)
                Table.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
                Table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
                Table.setGridStyle(Qt.DotLine)
                Table.setObjectName(QString("Table-%s" % p.name))
                GridLayout.addWidget(Table, 0, 0, 1, 1)
                self.TabWidget.addTab(Tab, QString(p.name))    

                Table.setColumnCount(len(self.headers))
                Table.setHorizontalHeaderLabels(self.headers)

                cups.resetOptions()
                cups.openPPD(p.name)
                current_options = dict(cups.getOptions())

                #current_options['cups_error_log_level'] = cups.getErrorLogLevel()

                try:
                    f = file(os.path.expanduser('~/.cups/lpoptions'))
                except IOError, e:
                    log.error(str(e))
                    current_options['lpoptions_file_data'] = QString("(%1)").arg(str(e))
                else:
                    text = f.read()
                    for d in text.splitlines():
                        if p.name in d:
                            current_options['lpoptions_file_data'] = d
                            break
                    else:
                        current_options['lpoptions_file_data'] = self.__tr("(no data)")

                keys = current_options.keys()
                keys.sort()

                Table.setRowCount(len(keys))

                for row, key in enumerate(keys):            
                    i = QTableWidgetItem(QString(key))
                    i.setFlags(flags)
                    Table.setItem(row, 0, i)  

                    if key == 'printer-state':
                        state = int(current_options[key])
                        if state == cups.IPP_PRINTER_STATE_IDLE:
                            i = QTableWidgetItem(self.__tr("idle (%1)").arg(state))
                        elif state == cups.IPP_PRINTER_STATE_PROCESSING:
                            i = QTableWidgetItem(self.__tr("busy/printing (%1)").arg(state))
                        elif state == cups.IPP_PRINTER_STATE_STOPPED:
                            i = QTableWidgetItem(self.__tr("stopped (%1)").arg(state))
                        else:
                            i = QTableWidgetItem(QString(str(state)))
                    else:
                        i = QTableWidgetItem(QString(str(current_options[key])))

                    i.setFlags(flags)
                    Table.setItem(row, 1, i)  

                Table.resizeColumnToContents(0)
                Table.resizeColumnToContents(1)

        cups.closePPD()
        self.TabWidget.setCurrentIndex(0)
        QApplication.restoreOverrideCursor()


    def DeviceUriComboBox_currentChanged(self, device_uri):
        self.device_uri = device_uri
        self.updateInfoTable()


    def DeviceUriComboBox_noDevices(self):
        FailureUI(self, self.__tr("<b>No devices found.</b>"))
        self.close()


    def CancelButton_clicked(self):
        self.close()

    #
    # Misc
    # 

    def __tr(self,s,c = None):
        return qApp.translate("InfoDialog",s,c)


