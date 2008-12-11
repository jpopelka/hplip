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
import socket
import operator

# Local
from base.g import *
from base import device, utils,  models
from prnt import cups
from base.codes import *
from ui_utils import *

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Ui
from setupdialog_base import Ui_Dialog

# Fax
try:
    from fax import fax
    fax_import_ok = True
except ImportError:
    # This can fail on Python < 2.3 due to the datetime module
    fax_import_ok = False
    log.warning("Fax setup disabled - Python 2.3+ required.")


PAGE_DISCOVERY = 0
PAGE_DEVICES = 1
PAGE_ADD_PRINTER = 2
PAGE_MAX = 2

BUTTON_NEXT = 0
BUTTON_FINISH = 1
BUTTON_ADD_PRINTER = 2

ADVANCED_SHOW = 0
ADVANCED_HIDE = 1

DEVICE_DESC_ALL = 0
DEVICE_DESC_SINGLE_FUNC = 1
DEVICE_DESC_MULTI_FUNC = 2



class DeviceTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, device_uri):
        QTableWidgetItem.__init__(self, text, QTableWidgetItem.UserType)
        self.device_uri = device_uri



class SetupDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, param, jd_port, username):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.param = param
        self.jd_port = jd_port
        self.username = username
        self.device_uri = None

        self.initUi()

        if self.skip_discovery:
            QTimer.singleShot(0, self.showDevicesPage)
        else:
            QTimer.singleShot(0, self.showDiscoveryPage)

    #
    # INIT
    #

    def initUi(self):
        self.setWindowIcon(QIcon(load_pixmap('prog', '48x48')))

        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.BackButton, SIGNAL("clicked()"), self.BackButton_clicked)
        self.connect(self.NextButton, SIGNAL("clicked()"), self.NextButton_clicked)
        self.connect(self.ManualGroupBox,  SIGNAL("clicked(bool)"),  self.ManualGroupBox_clicked)

        self.initDiscoveryPage()
        self.initDevicesPage()
        self.initAddPrinterPage()

    #
    #  DISCOVERY PAGE
    #

    def initDiscoveryPage(self):
        self.UsbRadioButton.setChecked(True)
        self.setUsbRadioButton(True)
        self.ManualGroupBox.setChecked(False)

        self.advanced = False
        self.manual = False
        self.skip_discovery = False
        self.NetworkRadioButton.setEnabled(prop.net_build)
        self.ParallelRadioButton.setEnabled(prop.par_build)
        self.devices = {}
        self.bus = 'usb'
        self.timeout = 5
        self.ttl = 4
        self.search = ''
        self.print_test_page = False
        self.device_desc = DEVICE_DESC_ALL

        if self.param:
            log.info("Searching for device...")
            self.manual = True
            self.advanced = True
            self.ManualParamLineEdit.setText(self.param)
            self.JetDirectSpinBox.setValue(self.jd_port)
            self.ManualGroupBox.setChecked(True)
            self.DiscoveryOptionsGroupBox.setEnabled(False)

            if self.manualDiscovery():
                self.skip_discovery = True
            else:
                FailureUI(self, self.__tr("<b>Device not found.</b> <p>Please make sure your printer is properly connected and powered-on."))

                match = device.usb_pat.match(self.param)
                if match is not None:
                    self.UsbRadioButton.setChecked(True)
                    self.setUsbRadioButton(True)

                else:
                    match = device.dev_pat.match(self.param)
                    if match is not None and prop.par_build:
                        self.ParallelRadioButton.setChecked(True)
                        self.setParallelRadioButton(True)

                    else:
                        match = device.ip_pat.match(self.param)
                        if match is not None and prop.net_build:
                            self.NetworkRadioButton.setChecked(True)
                            self.setNetworkRadioButton(True)

                        else:
                            FailureUI(self, self.__tr("<b>Invalid manual discovery parameter.</b>"))

        # If no network or parallel, usb is only option, skip initial page...
        elif not prop.par_build and not prop.net_build:
            self.skip_discovery = True
            self.bus = 'usb'
            self.UsbRadioButton.setChecked(True)
            self.setUsbRadioButton(True)

        self.DeviceTypeComboBox.addItem("All devices/printers", QVariant(DEVICE_DESC_ALL))
        self.DeviceTypeComboBox.addItem("Single function printers only", QVariant(DEVICE_DESC_SINGLE_FUNC))
        self.DeviceTypeComboBox.addItem("All-in-one/MFP devices only", QVariant(DEVICE_DESC_MULTI_FUNC))

        self.connect(self.AdvancedButton, SIGNAL("clicked()"), self.AdvancedButton_clicked)
        self.connect(self.UsbRadioButton, SIGNAL("toggled(bool)"), self.UsbRadioButton_toggled)
        self.connect(self.NetworkRadioButton, SIGNAL("toggled(bool)"), self.NetworkRadioButton_toggled)
        self.connect(self.ParallelRadioButton, SIGNAL("toggled(bool)"), self.ParallelRadioButton_toggled)
        self.connect(self.NetworkTTLSpinBox,  SIGNAL("valueChanged(int)"), self.NetworkTTLSpinBox_valueChanged)
        self.connect(self.NetworkTimeoutSpinBox,  SIGNAL("valueChanged(int)"),
                     self.NetworkTimeoutSpinBox_valueChanged)
        self.connect(self.ManualGroupBox,  SIGNAL("toggled(bool)"),  self.ManualGroupBox_toggled)

        self.showAdvanced()


    def ManualGroupBox_toggled(self, checked):
        self.DiscoveryOptionsGroupBox.setEnabled(not checked)


    def manualDiscovery(self):
        ret = False
        # Validate param...
        device_uri, sane_uri, fax_uri = device.makeURI(self.param, self.jd_port)

        if device_uri:
            back_end, is_hp, bus, model, serial, dev_file, host, port = \
                device.parseDeviceURI(device_uri)

            name = ''
            if bus == 'net':
                try:
                    name = socket.gethostbyaddr(host)[0]
                except socket.herror:
                    pass

            self.devices = {device_uri : (model, model, name)}

            if bus == 'usb':
                self.UsbRadioButton.setChecked(True)
                self.setUsbRadioButton(True)

            elif bus == 'net' and prop.net_build:
                self.NetworkRadioButton.setChecked(True)
                self.setNetworkRadioButton(True)

            elif bus == 'par' and prop.par_build:
                self.ParallelRadioButton.setChecked(True)
                self.setParallelRadioButton(True)

            ret = True

        return ret


    def ManualGroupBox_clicked(self, checked):
        self.manual = checked
        network = self.NetworkRadioButton.isChecked()
        self.setJetDirect(network)


    def showDiscoveryPage(self):
        self.BackButton.setEnabled(False)
        self.NextButton.setEnabled(True)
        self.setNextButton(BUTTON_NEXT)
        self.displayPage(PAGE_DISCOVERY)


    def AdvancedButton_clicked(self):
        self.advanced = not self.advanced
        self.showAdvanced()


    def showAdvanced(self):
        if self.advanced:
            self.AdvancedStackedWidget.setCurrentIndex(ADVANCED_SHOW)
            self.AdvancedButton.setText(self.__tr("Hide Advanced Options"))
            self.AdvancedButton.setIcon(QIcon(load_pixmap("minus", "16x16")))
        else:
            self.AdvancedStackedWidget.setCurrentIndex(ADVANCED_HIDE)
            self.AdvancedButton.setText(self.__tr("Show Advanced Options"))
            self.AdvancedButton.setIcon(QIcon(load_pixmap("plus", "16x16")))


    def setJetDirect(self, enabled):
        self.JetDirectLabel.setEnabled(enabled and self.manual)
        self.JetDirectSpinBox.setEnabled(enabled and self.manual)


    def setNetworkOptions(self,  enabled):
        self.NetworkTimeoutLabel.setEnabled(enabled)
        self.NetworkTimeoutSpinBox.setEnabled(enabled)
        self.NetworkTTLLabel.setEnabled(enabled)
        self.NetworkTTLSpinBox.setEnabled(enabled)


    def setNetworkDiscovery(self, enabled):
        self.NetworkDiscoveryMethodLabel.setEnabled(enabled and self.manual)
        self.NetworkDiscoveryMethodComboBox.setEnabled(enabled and self.manual)


    def UsbRadioButton_toggled(self, radio_enabled):
        self.setUsbRadioButton(radio_enabled)


    def setUsbRadioButton(self, checked):
        self.setNetworkDiscovery(not checked)
        self.setJetDirect(not checked)
        self.setNetworkOptions(not checked)

        if checked:
            self.ManualParamLabel.setText(self.__tr("USB bus ID:device ID (bbb:ddd):"))
            self.bus = 'usb'
            # TODO: Set bbb:ddd validator


    def NetworkRadioButton_toggled(self, radio_enabled):
        self.setNetworkRadioButton(radio_enabled)


    def setNetworkRadioButton(self, checked):
        self.setNetworkDiscovery(checked)
        self.setJetDirect(checked)
        self.setNetworkOptions(checked)

        if checked:
            self.ManualParamLabel.setText(self.__tr("IP Address or network name:"))
            self.bus = 'net'
            # TODO: Reset validator


    def ParallelRadioButton_toggled(self, radio_enabled):
        self.setParallelRadioButton(radio_enabled)


    def setParallelRadioButton(self, checked):
        self.setNetworkDiscovery(not checked)
        self.setJetDirect(not checked)
        self.setNetworkOptions(not checked)

        if checked:
            self.ManualParamLabel.setText(self.__tr("Device node (/dev/...):"))
            self.bus = 'par'
            # TODO: Set /dev/... validator


    def NetworkTTLSpinBox_valueChanged(self, ttl):
        self.ttl = ttl


    def NetworkTimeoutSpinBox_valueChanged(self, timeout):
        self.timeout = timeout

    #
    # DEVICES PAGE
    #

    def initDevicesPage(self):
        self.connect(self.RefreshButton,  SIGNAL("clicked()"),  self.RefreshButton_clicked)
        #filename =  "/home/dwelch/svn/trunk/src/data/images/other/hp-tux-printer.png"
        #self.DevicesTableWidget.setStyleSheet('background-image: url("%s"); background-attachment: fixed;' % filename)

    def showDevicesPage(self):
        self.BackButton.setEnabled(True)
        self.setNextButton(BUTTON_NEXT)

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            if not self.devices:
                if self.manual and self.param: # manual, but not passed-in on command line
                    self.manualDiscovery()

                else: # probe
                    if self.bus == 'net':
                        log.info("Searching... (bus=%s, timeout=%d, ttl=%d, search=%s desc=%d)" %
                                 (self.bus,  self.timeout, self.ttl, self.search or "(None)",
                                  self.device_desc))
                    else:
                        log.info("Searching... (bus=%s, search=%s desc=%d)" %
                                 (self.bus,  self.search or "(None)", self.device_desc))

                    if self.device_desc == DEVICE_DESC_SINGLE_FUNC:
                        filter_dict = {'scan-type' : (operator.le, SCAN_TYPE_NONE)}

                    elif self.device_desc == DEVICE_DESC_MULTI_FUNC:
                        filter_dict = {'scan-type': (operator.gt, SCAN_TYPE_NONE)}

                    else: # DEVICE_DESC_ALL
                        filter_dict = {}

                    self.devices = device.probeDevices([self.bus], self.timeout, self.ttl,
                                                       filter_dict, self.search)
        finally:
            QApplication.restoreOverrideCursor()

        #print self.devices
        self.clearDevicesTable()

        if self.devices:
            self.NextButton.setEnabled(True)
            self.DevicesFoundIcon.setPixmap(load_pixmap('info', '16x16'))

            if len(self.devices) == 1:
                self.DevicesFoundLabel.setText(self.__tr("<b>1 device found.</b> Click <i>Next</i> to continue."))
            else:
                self.DevicesFoundLabel.setText(self.__tr("<b>%1 devices found.</b> Select the device to install and click <i>Next</i> to continue.").arg(len(self.devices)))

            self.loadDevicesTable()

        else:
            self.NextButton.setEnabled(False)
            self.DevicesFoundIcon.setPixmap(load_pixmap('error', '16x16'))
            log.error("No devices found on bus: %s" % self.bus)
            self.DevicesFoundLabel.setText(self.__tr("<b>No devices found.</b><br>Click <i>Back</i> to change discovery options, or <i>Refresh</i> to search again."))

        self.displayPage(PAGE_DEVICES)


    def loadDevicesTable(self):
        self.DevicesTableWidget.setRowCount(len(self.devices))

        if self.bus == 'net':
            headers = [self.__tr('Model'), self.__tr('IP Address'), self.__tr('Host Name'), self.__tr('Device URI')]
            device_uri_col = 3
        else:
            headers = [self.__tr('Model'), self.__tr('Device URI')]
            device_uri_col = 1

        self.DevicesTableWidget.setColumnCount(len(headers))
        self.DevicesTableWidget.setHorizontalHeaderLabels(headers)
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled

        for row, d in enumerate(self.devices):
            back_end, is_hp, bus, model, serial, dev_file, host, port = device.parseDeviceURI(d)
            model_ui = models.normalizeModelUIName(model)

            i = DeviceTableWidgetItem(QString(model_ui), d)
            i.setFlags(flags)
            self.DevicesTableWidget.setItem(row, 0, i)

            i = QTableWidgetItem(QString(d))
            i.setFlags(flags)
            self.DevicesTableWidget.setItem(row, device_uri_col, i)

            if self.bus == 'net':
                i = QTableWidgetItem(QString(host))
                i.setFlags(flags)
                self.DevicesTableWidget.setItem(row, 1, i)

                i = QTableWidgetItem(QString(self.devices[d][2]))
                i.setFlags(flags)
                self.DevicesTableWidget.setItem(row, 2, i)

        self.DevicesTableWidget.resizeColumnsToContents()
        self.DevicesTableWidget.selectRow(0)


    def clearDevicesTable(self):
        self.DevicesTableWidget.clear()
        self.DevicesTableWidget.setRowCount(0)
        self.DevicesTableWidget.setColumnCount(0)


    def RefreshButton_clicked(self):
        self.clearDevicesTable()
        self.devices = []
        QTimer.singleShot(0, self.showDevicesPage)

    #
    # ADD PRINTER PAGE
    #

    def initAddPrinterPage(self):
        self.mq = {}

        self.connect(self.PrinterNameLineEdit, SIGNAL("textEdited(const QString &)"),
                     self.PrinterNameLineEdit_textEdited)

        self.connect(self.FaxNameLineEdit, SIGNAL("textEdited(const QString &)"),
                     self.FaxNameLineEdit_textEdited)

        self.PrinterNameLineEdit.setValidator(PrinterNameValidator(self.PrinterNameLineEdit))
        self.FaxNameLineEdit.setValidator(PrinterNameValidator(self.FaxNameLineEdit))
        self.FaxNumberLineEdit.setValidator(PhoneNumValidator(self.FaxNumberLineEdit))

        self.OtherPPDButton.setIcon(QIcon(load_pixmap('folder_open', '16x16')))
        self.connect(self.OtherPPDButton, SIGNAL("clicked(bool)"), self.OtherPPDButton_clicked)

        self.OtherPPDButton.setToolTip(self.__tr("Browse for an alternative PPD file for this printer."))

        self.printer_fax_names_same = False
        self.printer_name = ''
        self.fax_name = ''
        self.fax_setup_ok = True
        self.fax_setup = False


    def showAddPrinterPage(self):
        self.setNextButton(BUTTON_ADD_PRINTER)
        if not self.printer_name:
            self.setDefaultPrinterName()

        self.findPrinterPPD()

        if fax_import_ok and prop.fax_build and \
            self.mq.get('fax-type', FAX_TYPE_NONE) not in (FAX_TYPE_NONE, FAX_TYPE_NOT_SUPPORTED):

            self.fax_setup = True
            self.SetupFaxGroupBox.setChecked(True)
            self.SetupFaxGroupBox.setEnabled(True)

            if not self.fax_name:
                self.setDefaultFaxName()

            self.findFaxPPD()

            self.readwriteFaxInformation()

        else:
            self.SetupFaxGroupBox.setChecked(False)
            self.SetupFaxGroupBox.setEnabled(False)
            self.fax_name = ''
            self.fax_name_ok = True
            self.fax_setup = False
            self.fax_setup_ok = True

        self.updatePPD()
        self.setAddPrinterButton()
        self.displayPage(PAGE_ADD_PRINTER)


    def updatePPD(self):
        if self.print_ppd is None:
            log.error("No appropriate print PPD file found for model %s" % self.model)
            self.PPDFileLineEdit.setText(self.__tr('(Not found. Click browse button to select a PPD file.)'))
            self.PrinterDescriptionLineEdit.setText(QString(""))

        else:
            self.PPDFileLineEdit.setText(self.print_ppd[0])
            self.PrinterDescriptionLineEdit.setText(self.print_ppd[1])


    def OtherPPDButton_clicked(self, b):
        ppd_file = unicode(QFileDialog.getOpenFileName(self, self.__tr("Select PPD File"),
                                                       sys_cfg.dirs.ppd,
                                                       self.__tr("PPD Files (*.ppd *.ppd.gz);;All Files (*)")))

        if ppd_file and os.path.exists(ppd_file):
            self.print_ppd = (ppd_file, cups.getPPDDescription(ppd_file))
            self.updatePPD()


    def findPrinterPPD(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            log.debug("Searching for print PPD for model %s" % self.model)
            self.ppds = cups.getSystemPPDs()
            model = self.model.replace('hp_', '').replace('hp-', '')
            found_ppds = {}

            for p in self.ppds:
                if model in p:
                    print "Found print PPD: %s (%s)" % (p, self.ppds[p])
                    found_ppds[p] = self.ppds[p]

            if len(found_ppds) == 0:
                self.print_ppd = None

            elif len(found_ppds) == 1:
                self.print_ppd = found_ppds.items()[0] # (filename, description)

            elif len(found_ppds) > 1:
                ppd = cups.getPPDFile(self.model, found_ppds)
                self.print_ppd = ppd.items()[0]

        finally:
            QApplication.restoreOverrideCursor()


    def findFaxPPD(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            log.debug("Searching for fax PPD for model %s" % self.model)

            if self.mq.get('fax-type', FAX_TYPE_NONE) == FAX_TYPE_SOAP:
                fax_ppd_name = "HP-Fax2-hplip" # Fixed width (2528 pixels) and 300dpi rendering
                nick = "HP Fax 2"
            else:
                fax_ppd_name = "HP-Fax-hplip" # Standard
                nick = "HP Fax"

            ppds = []

            for f in utils.walkFiles(sys_cfg.dirs.ppd, pattern="HP-Fax*.ppd*", abs_paths=True):
                ppds.append(f)

            for f in ppds:
                if f.find(fax_ppd_name) >= 0 and cups.getPPDDescription(f) == nick:
                    self.fax_ppd = f
                    self.fax_setup_ok = True
                    print "Found fax PPD:", f
                    break
            else:
                self.fax_ppd = None
                self.fax_setup_ok = False

        finally:
            QApplication.restoreOverrideCursor()



    def setDefaultPrinterName(self):
        self.installed_print_devices = device.getSupportedCUPSDevices(['hp'])
        log.debug(self.installed_print_devices)

        self.installed_queues = [p.name for p in cups.getPrinters()]

        back_end, is_hp, bus, model, serial, dev_file, host, port = device.parseDeviceURI(self.device_uri)
        default_model = utils.xstrip(model.replace('series', '').replace('Series', ''), '_')

        printer_name = default_model

        # Check for duplicate names
        if self.device_uri in self.installed_print_devices and \
            printer_name in self.installed_print_devices[self.device_uri]:
                i = 2
                while True:
                    t = printer_name + "_%d" % i
                    if t not in self.installed_print_devices[self.device_uri]:
                        printer_name += "_%d" % i
                        break
                    i += 1

        self.printer_name_ok = True
        self.PrinterNameLineEdit.setText(printer_name)
        log.debug(printer_name)
        self.printer_name = printer_name


    def setDefaultFaxName(self):
        self.installed_fax_devices = device.getSupportedCUPSDevices(['hpfax'])
        log.debug(self.installed_fax_devices)

        self.fax_uri = self.device_uri.replace('hp:', 'hpfax:')

        back_end, is_hp, bus, model, serial, dev_file, host, port = device.parseDeviceURI(self.fax_uri)
        default_model = utils.xstrip(model.replace('series', '').replace('Series', ''), '_')

        fax_name = default_model + "_fax"

        # Check for duplicate names
        if self.fax_uri in self.installed_fax_devices and \
            fax_name in self.installed_fax_devices[self.fax_uri]:
                i = 2
                while True:
                    t = fax_name + "_%d" % i
                    if t not in self.installed_fax_devices[self.fax_uri]:
                        fax_name += "_%d" % i
                        break
                    i += 1

        self.fax_name_ok = True
        self.FaxNameLineEdit.setText(fax_name)
        self.fax_name = fax_name


    def PrinterNameLineEdit_textEdited(self, t):
        self.printer_name = unicode(t)
        self.printer_name_ok = True

        if not self.printer_name:
            self.PrinterNameLineEdit.setToolTip(self.__tr('You must enter a name for the printer.'))
            self.printer_name_ok = False

        elif self.fax_name == self.printer_name:
            s = self.__tr('The printer name and fax name must be different. Please choose different names.')
            self.PrinterNameLineEdit.setToolTip(s)
            self.FaxNameLineEdit.setToolTip(s)
            self.fax_name_ok = False
            self.printer_name_ok = False
            self.printer_fax_names_same = True

        elif self.printer_name in self.installed_queues:
            self.PrinterNameLineEdit.setToolTip(self.__tr('A printer already exists with this name. Please choose a different name.'))
            self.printer_name_ok = False

        elif self.printer_fax_names_same:
            if self.fax_name != self.printer_name:
                self.printer_fax_names_same = False
                self.printer_name_ok = True

                self.FaxNameLineEdit.emit(SIGNAL("textChanged(const QString &)"),
                            (self.FaxNameLineEdit.text(),))

        self.setIndicators()
        self.setAddPrinterButton()


    def FaxNameLineEdit_textEdited(self, t):
        self.fax_name = unicode(t)
        self.fax_name_ok = True

        if not self.fax_name:
            self.FaxNameLineEdit.setToolTip(self.__tr('You must enter a fax name.'))
            self.fax_name_ok = False

        elif self.fax_name == self.printer_name:
            s = self.__tr('The printer name and fax name must be different. Please choose different names.')
            self.PrinterNameLineEdit.setToolTip(s)
            self.FaxNameLineEdit.setToolTip(s)
            self.printer_name_ok = False
            self.fax_name_ok = False
            self.printer_fax_names_same = True

        elif self.fax_name in self.installed_queues:
            self.FaxNameLineEdit.setToolTip(self.__tr('A fax already exists with this name. Please choose a different name.'))
            self.fax_name_ok = False

        elif self.printer_fax_names_same:
            if self.fax_name != self.printer_name:
                self.printer_fax_names_same = False
                self.fax_name_ok = True

                self.PrinterNameLineEdit.emit(SIGNAL("textChanged(const QString&)"),
                            (self.PrinterNameLineEdit.text(),))

        self.setIndicators()
        self.setAddPrinterButton()


    def setIndicators(self):
        if self.printer_name_ok:
            self.PrinterNameLineEdit.setToolTip(QString(""))
            self.PrinterNameLineEdit.setStyleSheet("")
        else:
            self.PrinterNameLineEdit.setStyleSheet("background-color: yellow")

        if self.fax_name_ok:
            self.FaxNameLineEdit.setToolTip(QString(""))
            self.PrinterNameLineEdit.setStyleSheet("")
        else:
            self.PrinterNameLineEdit.setStyleSheet("background-color: yellow")


    def setAddPrinterButton(self):
        self.NextButton.setEnabled(self.printer_name_ok and self.fax_name_ok and
                                   self.print_ppd is not None and self.fax_setup_ok)


    #
    # ADD PRINTER
    #

    def addPrinter(self):
        self.setupPrinter()

        if self.fax_setup:
            self.setupFax()
            self.readwriteFaxInformation(False)

        if self.print_test_page:
            self.printTestPage()

        self.close()



    #
    # SETUP PRINTER/FAX
    #

    def setupPrinter(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            if not os.path.exists(self.print_ppd[0]): # assume foomatic: or some such
                status, status_str = cups.addPrinter(self.printer_name.encode('utf8'), self.device_uri,
                    self.print_location, '', self.print_ppd[0], self.print_desc)
            else:
                status, status_str = cups.addPrinter(self.printer_name.encode('utf8'), self.device_uri,
                    self.print_location, self.print_ppd[0], '', self.print_desc)

            log.debug("addPrinter() returned (%d, %s)" % (status, status_str))
            self.installed_print_devices = device.getSupportedCUPSDevices(['hp'])

            log.debug(self.installed_print_devices)

            if self.device_uri not in self.installed_print_devices or \
                self.printer_name not in self.installed_print_devices[self.device_uri]:

                QApplication.restoreOverrideCursor()
                FailureUI(self, self.__tr("<b>Printer queue setup failed.</b><p>Please restart CUPS and try again."))
            else:
                # TODO:
                #service.sendEvent(self.hpssd_sock, EVENT_CUPS_QUEUES_CHANGED, device_uri=self.device_uri)
                pass

        finally:
            QApplication.restoreOverrideCursor()


    def setupFax(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            if not os.path.exists(self.fax_ppd):
                status, status_str = cups.addPrinter(self.fax_name.encode('utf8'),
                    self.fax_uri, self.fax_location, '', self.fax_ppd,  self.fax_desc)
            else:
                status, status_str = cups.addPrinter(self.fax_name.encode('utf8'),
                    self.fax_uri, self.fax_location, self.fax_ppd, '', self.fax_desc)

            log.debug("addPrinter() returned (%d, %s)" % (status, status_str))
            self.installed_fax_devices = device.getSupportedCUPSDevices(['hpfax'])

            log.debug(self.installed_fax_devices)

            if self.fax_uri not in self.installed_fax_devices or \
                self.fax_name not in self.installed_fax_devices[self.fax_uri]:

                QApplication.restoreOverrideCursor()
                FailureUI(self, self.__tr("<b>Fax queue setup failed.</b><p>Please restart CUPS and try again."))
            else:
                pass
                # TODO:
                #service.sendEvent(self.hpssd_sock, EVENT_CUPS_QUEUES_CHANGED, device_uri=self.fax_uri)

        finally:
            QApplication.restoreOverrideCursor()


    def readwriteFaxInformation(self, read=True):
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

            d = fax.getFaxDevice(self.fax_uri, disable_dbus=True)

            while True:
                try:
                    d.open()
                except Error:
                    error_text = self.__tr("Unable to communicate with the device. Please check the device and try again.")
                    log.error(unicode(error_text))
                    if QMessageBox.critical(self,
                                           self.caption(),
                                           error_text,
                                           QMessageBox.Retry | QMessageBox.Default,
                                           QMessageBox.Cancel | QMessageBox.Escape,
                                           QMessageBox.NoButton) == QMessageBox.Cancel:
                        break

                else:
                    try:
                        tries = 0
                        ok = True

                        while True:
                            tries += 1

                            try:
                                if read:
                                    self.fax_number = unicode(d.getPhoneNum())
                                    self.fax_name_company = unicode(d.getStationName())
                                else:
                                    d.setStationName(self.fax_name_company)
                                    d.setPhoneNum(self.fax_number)

                            except Error:
                                error_text = self.__tr("<b>Device I/O Error</b><p>Could not communicate with device. Device may be busy.")
                                log.error(unicode(error_text))

                                if QMessageBox.critical(self,
                                                       self.caption(),
                                                       error_text,
                                                       QMessageBox.Retry | QMessageBox.Default,
                                                       QMessageBox.Cancel | QMessageBox.Escape,
                                                       QMessageBox.NoButton) == QMessageBox.Cancel:
                                    break


                                time.sleep(5)
                                ok = False

                                if tries > 12:
                                    break

                            else:
                                ok = True
                                break

                    finally:
                        d.close()

                    if ok and read:
                        self.FaxNumberLineEdit.setText(self.fax_number)
                        self.NameCompanyLineEdit.setText(self.fax_name_company)

                    break

        finally:
            QApplication.restoreOverrideCursor()


    def printTestPage(self):
        try:
            d = device.Device(self.device_uri)
        except Error, e:
            self.FailureUI(self.__tr("<b>Device error:</b><p>%s (%s)." % (e.msg, e.opt)))

        else:
            try:
                d.open()
            except Error:
                self.FailureUI(self.__tr("<b>Unable to print to printer.</b><p>Please check device and try again."))
            else:
                if d.isIdleAndNoError():
                    d.close()

                    try:
                        d.printTestPage(self.printer_name)
                    except Error, e:
                        if e.opt == ERROR_NO_CUPS_QUEUE_FOUND_FOR_DEVICE:
                            self.FailureUI(self.__tr("<b>No CUPS queue found for device.</b><p>Please install the printer in CUPS and try again."))
                        else:
                            self.FailureUI(self.__tr("<b>Printer Error</b><p>An error occured: %s (code=%d)." % (e.msg, e.opt)))
                else:
                    self.FailureUI(self.__tr("<b>Printer Error.</b><p>Printer is busy, offline, or in an error state. Please check the device and try again."))
                    d.close()

    #
    # Misc
    #

    def NextButton_clicked(self):
        p = self.StackedWidget.currentIndex()
        if p == PAGE_DISCOVERY:
            self.manual = self.ManualGroupBox.isChecked()
            self.param = unicode(self.ManualParamLineEdit.text())
            self.jd_port = self.JetDirectSpinBox.value()
            self.search = unicode(self.SearchLineEdit.text())
            self.device_desc = int(self.DeviceTypeComboBox.itemData(self.DeviceTypeComboBox.currentIndex()).toInt()[0])
            self.showDevicesPage()

        elif p == PAGE_DEVICES:
            row = self.DevicesTableWidget.currentRow()
            self.device_uri = self.DevicesTableWidget.item(row, 0).device_uri
            self.mq = device.queryModelByURI(self.device_uri)
            back_end, is_hp, bus, model, serial, dev_file, host, port = device.parseDeviceURI(self.device_uri)
            self.model = models.normalizeModelName(model).lower()
            self.showAddPrinterPage()

        elif p == PAGE_ADD_PRINTER:
            self.print_test_page = self.SendTestPageCheckBox.isChecked()
            self.print_desc = unicode(self.PrinterDescriptionLineEdit.text()).encode('utf8')
            self.print_location = unicode(self.PrinterLocationLineEdit.text()).encode('utf8')
            self.fax_setup = self.SetupFaxGroupBox.isChecked()
            self.fax_desc = unicode(self.FaxDescriptionLineEdit.text()).encode('utf8')
            self.fax_location = unicode(self.FaxLocationLineEdit.text()).encode('utf8')
            self.fax_name_company = unicode(self.NameCompanyLineEdit.text()).encode('utf8')
            self.fax_number = unicode(self.FaxNumberLineEdit.text()).encode('utf8')
            self.addPrinter()

        else:
            log.error("Invalid page!") # shouldn't happen!


    def BackButton_clicked(self):
        p = self.StackedWidget.currentIndex()
        if p == PAGE_DEVICES:
            self.devices = {}
            self.showDiscoveryPage()

        elif p == PAGE_ADD_PRINTER:
            self.showDevicesPage()

        else:
            log.error("Invalid page!") # shouldn't happen!


    def CancelButton_clicked(self):
        self.close()


    def displayPage(self, page):
        self.updateStepText(page)
        self.StackedWidget.setCurrentIndex(page)


    def setNextButton(self, typ=BUTTON_FINISH):
        if typ == BUTTON_ADD_PRINTER:
            self.NextButton.setText(self.__tr("Add Printer"))
        elif typ == BUTTON_NEXT:
            self.NextButton.setText(self.__tr("Next >"))
        elif typ == BUTTON_FINISH:
            self.NextButton.setText(self.__tr("Finish"))


    def updateStepText(self, p):
        self.StepText.setText(self.__tr("Step %1 of %2").arg(p+1).arg(PAGE_MAX+1))


    def __tr(self,s,c = None):
        return qApp.translate("SetupDialog",s,c)


