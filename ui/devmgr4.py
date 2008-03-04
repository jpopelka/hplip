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
# Authors: Don Welch, Pete Parks
#

from __future__ import generators

# Std Lib
import sys, time, os, gzip

# Local
from base.g import *
from base import device, utils, service
from prnt import cups
from base.codes import *

# Qt
from qt import *

# Main form
from devmgr4_base import DevMgr4_base

# Scrollviews
from scrollview import ScrollView
from scrollfunc import ScrollFunctionsView
from scrollstatus import ScrollStatusView
from scrollprintsettings import ScrollPrintSettingsView
from scrollprintcontrol import ScrollPrintJobView
from scrolltool import ScrollToolView, ScrollDeviceInfoView, ScrollTestpageView, ScrollPrinterInfoView
from scrollsupplies import ScrollSuppliesView
from scrollprint import ScrollPrintView

if prop.fax_build:
    from scrollfax import ScrollFaxView
    
from scrollunload import ScrollUnloadView
from scrollcopy import ScrollCopyView

# Misc forms
from nodevicesform import NoDevicesForm
from settingsdialog import SettingsDialog
from aboutdlg import AboutDlg

# all in seconds
MIN_AUTO_REFRESH_RATE = 5
MAX_AUTO_REFRESH_RATE = 60
DEF_AUTO_REFRESH_RATE = 30


class IconViewItem(QIconViewItem):
    def __init__(self, parent, text, pixmap, device_uri, is_avail=True):
        QIconViewItem.__init__(self, parent, text, pixmap)
        self.device_uri = device_uri
        self.is_avail = is_avail


class PasswordDialog(QDialog):
    def __init__(self,prompt, parent = None,name = None,modal = 0,fl = 0):
        QDialog.__init__(self,parent,name,modal,fl)

        if not name:
            self.setName("PasswordDialog")

        passwordDlg_baseLayout = QGridLayout(self,1,1,11,6,"passwordDlg_baseLayout")

        self.passwordLineEdit = QLineEdit(self,"passwordLineEdit")
        self.passwordLineEdit.setEchoMode(QLineEdit.Password)

        passwordDlg_baseLayout.addMultiCellWidget(self.passwordLineEdit,1,1,0,1)

        self.promptTextLabel = QLabel(self,"promptTextLabel")

        passwordDlg_baseLayout.addMultiCellWidget(self.promptTextLabel,0,0,0,1)
        spacer1 = QSpacerItem(20,61,QSizePolicy.Minimum,QSizePolicy.Expanding)
        passwordDlg_baseLayout.addItem(spacer1,2,0)
        spacer2 = QSpacerItem(321,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        passwordDlg_baseLayout.addItem(spacer2,3,0)

        self.okPushButton = QPushButton(self,"okPushButton")

        passwordDlg_baseLayout.addWidget(self.okPushButton,3,1)

        self.languageChange()

        self.resize(QSize(420,163).expandedTo(self.minimumSizeHint()))
        self.clearWState(Qt.WState_Polished)

        self.connect(self.okPushButton,SIGNAL("clicked()"),self.accept)
        self.connect(self.passwordLineEdit,SIGNAL("returnPressed()"),self.accept)
        self.promptTextLabel.setText(prompt)

    def getPassword(self):
        return unicode(self.passwordLineEdit.text())

    def languageChange(self):
        self.setCaption(self.__tr("HP Device Manager - Enter Password"))
        self.okPushButton.setText(self.__tr("OK"))

    def __tr(self,s,c = None):
        return qApp.translate("PasswordDialog",s,c)


def PasswordUI(prompt):
    QApplication.restoreOverrideCursor()

    dlg = PasswordDialog(prompt, None)

    if dlg.exec_loop() == QDialog.Accepted:
        return dlg.getPassword()

    QApplication.setOverrideCursor(QApplication.waitCursor)
    return ""


class DevMgr4(DevMgr4_base):
    def __init__(self, hpssd_sock, 
                 cleanup=None, toolbox_version='0.0',
                 parent=None, name=None, fl = 0):

        DevMgr4_base.__init__(self, parent, name, fl)

        icon = QPixmap(os.path.join(prop.image_dir, 'HPmenu.png'))
        self.setIcon(icon)

        log.debug("Initializing toolbox UI...")
        log.debug("HPLIP Version: %s" % sys_cfg.hplip.version)

        self.cleanup = cleanup
        self.hpssd_sock = hpssd_sock
        self.toolbox_version = toolbox_version
        self.cur_device_uri = user_cfg.last_used.device_uri # Device URI
        self.devices = {}    # { Device_URI : device.Device(), ... }
        self.device_vars = {}
        self.num_devices = 0
        self.cur_device = None
        self.rescanning = False

        self.user_settings = utils.UserSettings()

        if not self.user_settings.auto_refresh:
            self.autoRefresh.toggle()

        self.InitDeviceList()

        self.InitFunctionsTab()
        self.InitStatusTab()
        self.InitMaintTab()
        self.InitSuppliesTab()
        self.InitPrintSettingsTab()
        self.InitPrintJobsTab()

        self.TabIndex = { self.FunctionsTab: self.FuncList,
                          self.StatusTab: self.StatusList,
                          self.MaintTab: self.ToolList,
                          self.SuppliesTab: self.SuppliesList,
                          self.PrintSettingsTab: self.PrintSettingsList,
                          self.PrintJobsTab: self.PrintJobsList,
                          self.MaintTab: self.ToolList
                        }

        self.funcs_page = 'funcs'
        self.maint_page = 'tools'

        cups.setPasswordCallback(PasswordUI)
        
        #if not prop.doc_build:
        #    self.helpContentsAction.setEnabled(False)
            
        self.allow_auto_refresh = True

        QTimer.singleShot(0, self.InitialUpdate)


    def InitialUpdate(self):
        self.RescanDevices(init=True)

        self.refresh_timer = QTimer(self, "RefreshTimer")
        self.connect(self.refresh_timer, SIGNAL('timeout()'), self.TimedRefresh)

        if MIN_AUTO_REFRESH_RATE <= self.user_settings.auto_refresh_rate <= MAX_AUTO_REFRESH_RATE:
            self.refresh_timer.start(self.user_settings.auto_refresh_rate * 1000)

    def InitDeviceList(self):
        self.DeviceList.setAutoArrange(False)
        # Resize the splitter so that the device list starts as a single column
        self.splitter2.setSizes([120, 700]) 


    def InitFunctionsTab(self):
        self.FuncList = ScrollFunctionsView(self.FunctionsTab, self, "FuncView")

        self.FuncTabLayout = QGridLayout(self.FunctionsTab,1,1,11,6,"FuncTabLayout")
        self.FuncTabLayout.addWidget(self.FuncList,0,0)

    def SwitchFunctionsTab(self, page='funcs'):
        self.FuncTabLayout.remove(self.FuncList)
        self.FuncList.hide()
        self.deviceRemoveAction.setEnabled(False)
        self.deviceInstallAction.setEnabled(False)        

        if page  == 'funcs':
            self.allow_auto_refresh = True
            self.Tabs.changeTab(self.FunctionsTab,self.__tr("Functions"))
            self.FuncList = ScrollFunctionsView(self.FunctionsTab, self, "FuncView")
            self.deviceRemoveAction.setEnabled(True)
            self.deviceInstallAction.setEnabled(True)        

        elif page == 'print':
            self.allow_auto_refresh = False
            self.Tabs.changeTab(self.FunctionsTab,self.__tr("Functions > Print"))
            self.FuncList = ScrollPrintView(True, self.FunctionsTab, self, "PrintView")

        elif page == 'scan':
             self.allow_auto_refresh = False
             pass

        elif page == 'copy':
            self.allow_auto_refresh = False
            self.Tabs.changeTab(self.FunctionsTab,self.__tr("Functions > Make Copies"))
            self.FuncList = ScrollCopyView(self.hpssd_sock, True, parent=self.FunctionsTab, form=self, name="CopyView")

        elif page == 'fax':
            self.allow_auto_refresh = False
            self.Tabs.changeTab(self.FunctionsTab, self.__tr("Functions > Fax"))
            self.FuncList = ScrollFaxView(self.hpssd_sock, True, self.FunctionsTab, self, "FaxView")

        elif page == 'pcard':
            self.allow_auto_refresh = False
            self.Tabs.changeTab(self.FunctionsTab, self.__tr("Functions > Unload Photo Card"))
            self.FuncList = ScrollUnloadView(True, self.FunctionsTab, self, "UnloadView")

        self.funcs_page = page
        self.FuncTabLayout.addWidget(self.FuncList, 0, 0)
        self.FuncList.show()
        self.TabIndex[self.FunctionsTab] = self.FuncList
        self.FuncList.onDeviceChange(self.cur_device)


    def InitStatusTab(self):
        StatusTabLayout = QGridLayout(self.StatusTab,1,1,11,6,"StatusTabLayout")

        self.Panel_2 = QLabel(self.StatusTab,"Panel_2")
        self.Panel_2.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed,0,0,self.Panel_2.sizePolicy().hasHeightForWidth()))
        self.Panel_2.setMinimumSize(QSize(254,40))
        self.Panel_2.setMaximumSize(QSize(254,40))
        self.Panel_2.setScaledContents(1)

        StatusTabLayout.addWidget(self.Panel_2,0,1)
        spacer21 = QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        StatusTabLayout.addItem(spacer21,0,2)
        spacer22 = QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        StatusTabLayout.addItem(spacer22,0,0)

        self.StatusList = ScrollStatusView(self.StatusTab, "statuslist")
        StatusTabLayout.addMultiCellWidget(self.StatusList,1,1,0,2)

        self.warning_pix_small = QPixmap(os.path.join(prop.image_dir, "warning_small.png"))
        self.error_pix_small = QPixmap(os.path.join(prop.image_dir, "error_small.png"))
        self.ok_pix_small = QPixmap(os.path.join(prop.image_dir, "ok_small.png"))
        self.lowink_pix_small = QPixmap(os.path.join(prop.image_dir, 'inkdrop_small.png'))
        self.lowtoner_pix_small = QPixmap(os.path.join(prop.image_dir, 'toner_small.png'))
        self.busy_pix_small = QPixmap(os.path.join(prop.image_dir, 'busy_small.png'))
        self.lowpaper_pix_small = QPixmap(os.path.join(prop.image_dir, 'paper_small.png'))

        # pixmaps: (inkjet, laserjet)
        self.SMALL_ICONS = { ERROR_STATE_CLEAR : (None, None),
                              ERROR_STATE_BUSY : (self.busy_pix_small, self.busy_pix_small),
                              ERROR_STATE_ERROR : (self.error_pix_small, self.error_pix_small),
                              ERROR_STATE_LOW_SUPPLIES : (self.lowink_pix_small, self.lowtoner_pix_small),
                              ERROR_STATE_OK : (self.ok_pix_small, self.ok_pix_small),
                              ERROR_STATE_WARNING : (self.warning_pix_small, self.warning_pix_small),
                              ERROR_STATE_LOW_PAPER: (self.lowpaper_pix_small, self.lowpaper_pix_small),
                              ERROR_STATE_PRINTING : (self.busy_pix_small, self.busy_pix_small),   
                              ERROR_STATE_SCANNING : (self.busy_pix_small, self.busy_pix_small),
                              ERROR_STATE_PHOTOCARD : (self.busy_pix_small, self.busy_pix_small),
                              ERROR_STATE_FAXING : (self.busy_pix_small, self.busy_pix_small),
                              ERROR_STATE_COPYING : (self.busy_pix_small, self.busy_pix_small),
                            }

        self.blank_lcd = os.path.join(prop.image_dir, "panel_lcd.xpm")
        self.Panel_2.setPixmap(QPixmap(self.blank_lcd))

    def InitMaintTab(self): # Add Scrolling Maintenance (Tools)
        self.ToolList = ScrollToolView(True, self.MaintTab, self, "ToolView")
        self.MaintTabLayout = QGridLayout(self.MaintTab,1,1,11,6,"MaintTabLayout")
        self.MaintTabLayout.addWidget(self.ToolList,0,0)

    def SwitchMaintTab(self, page='tools'):
        self.MaintTabLayout.remove(self.ToolList)
        self.ToolList.hide()
        self.deviceRemoveAction.setEnabled(False)
        self.deviceInstallAction.setEnabled(False)        

        if page  == 'tools':
            self.allow_auto_refresh = True
            self.Tabs.changeTab(self.MaintTab,self.__tr("Tools"))
            self.ToolList = ScrollToolView(True, self.MaintTab, self, "ToolView")
            self.deviceRemoveAction.setEnabled(True)
            self.deviceInstallAction.setEnabled(True)        

        elif page == 'device_info':
            self.allow_auto_refresh = False
            self.Tabs.changeTab(self.MaintTab,self.__tr("Tools > Device Information"))
            self.ToolList = ScrollDeviceInfoView(True, self.MaintTab, self, "DeviceInfoView")

        elif page == 'printer_info':
            self.allow_auto_refresh = False
            self.Tabs.changeTab(self.MaintTab,self.__tr("Tools > Printer Information"))
            self.ToolList = ScrollPrinterInfoView(True, self.MaintTab, self, "PrinterInfoView")

        elif page == 'testpage':
            self.allow_auto_refresh = False
            self.Tabs.changeTab(self.MaintTab,self.__tr("Tools > Print Test Page"))

            self.ToolList = ScrollTestpageView(True, self.MaintTab, self, "ScrollTestpageView")

        self.maint_page = page
        self.MaintTabLayout.addWidget(self.ToolList, 0, 0)
        self.ToolList.show()
        self.TabIndex[self.MaintTab] = self.ToolList
        self.ToolList.onDeviceChange(self.cur_device)


    def InitSuppliesTab(self): # Add Scrolling Supplies 
        self.SuppliesList = ScrollSuppliesView(self.SuppliesTab, "SuppliesView")
        SuppliesTabLayout = QGridLayout(self.SuppliesTab,1,1,11,6,"SuppliesTabLayout")
        self.SuppliesList.setHScrollBarMode(QScrollView.AlwaysOff)
        SuppliesTabLayout.addWidget(self.SuppliesList,0,0)    

    def InitPrintSettingsTab(self): # Add Scrolling Print Settings
        PrintJobsTabLayout = QGridLayout(self.PrintSettingsTab,1,1,11,6,"PrintJobsTabLayout")

        self.PrintSettingsList = ScrollPrintSettingsView(self.PrintSettingsTab, "PrintSettingsView")
        PrintJobsTabLayout.addMultiCellWidget(self.PrintSettingsList,1,1,0,5)

        self.PrintSettingsPrinterCombo = QComboBox(0,self.PrintSettingsTab,"comboBox5")
        self.PrintSettingsPrinterCombo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed,0,0,
            self.PrintSettingsPrinterCombo.sizePolicy().hasHeightForWidth()))

        PrintJobsTabLayout.addMultiCellWidget(self.PrintSettingsPrinterCombo,0,0,2,3)

        textLabel12 = QLabel(self.PrintSettingsTab,"textLabel12")
        PrintJobsTabLayout.addWidget(textLabel12,0,1)

        textLabel12.setText(self.__tr("Printer Name:"))

        spacer34 = QSpacerItem(20,20,QSizePolicy.Preferred,QSizePolicy.Minimum)
        PrintJobsTabLayout.addMultiCell(spacer34,0,0,4,5)

        spacer35 = QSpacerItem(20,20,QSizePolicy.Preferred,QSizePolicy.Minimum)
        PrintJobsTabLayout.addItem(spacer35,0,0)

        self.connect(self.PrintSettingsPrinterCombo, SIGNAL("activated(const QString&)"), self.SettingsPrinterCombo_activated)

    def InitPrintJobsTab(self):
        # Add Scrolling Print Jobs
        PrintJobsTabLayout = QGridLayout(self.PrintJobsTab,1,1,11,6,"PrintJobsTabLayout")

        self.PrintJobsList = ScrollPrintJobView(self.PrintJobsTab, "PrintJobsView")
        PrintJobsTabLayout.addMultiCellWidget(self.PrintJobsList,1,1,0,5)

        self.PrintJobPrinterCombo = QComboBox(0,self.PrintJobsTab,"comboBox5")
        self.PrintJobPrinterCombo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed,0,0,
            self.PrintJobPrinterCombo.sizePolicy().hasHeightForWidth()))

        PrintJobsTabLayout.addMultiCellWidget(self.PrintJobPrinterCombo,0,0,2,3)

        textLabel12 = QLabel(self.PrintJobsTab,"textLabel12")
        PrintJobsTabLayout.addWidget(textLabel12,0,1)

        textLabel12.setText(self.__tr("Printer Name:"))

        spacer34 = QSpacerItem(171,20,QSizePolicy.Preferred,QSizePolicy.Minimum)
        PrintJobsTabLayout.addMultiCell(spacer34,0,0,4,5)

        spacer35 = QSpacerItem(71,20,QSizePolicy.Preferred,QSizePolicy.Minimum)
        PrintJobsTabLayout.addItem(spacer35,0,0)

        self.connect(self.PrintJobPrinterCombo, SIGNAL("activated(const QString&)"), self.JobsPrinterCombo_activated)

    def TimedRefresh(self):
        if self.user_settings.auto_refresh and self.allow_auto_refresh:
            log.debug("Refresh timer...")
            self.CleanupChildren()

            if self.user_settings.auto_refresh_type == 0:
                self.UpdateDevice()
            else:
                self.RescanDevices()

    def autoRefresh_toggled(self,a0):
        self.user_settings.auto_refresh = bool(a0)
        #self.user_settings.save()

    def closeEvent(self, event):
        self.Cleanup()
        event.accept()

    def RescanDevices(self, init=False):
        if not self.rescanning:
            self.deviceRefreshAll.setEnabled(False)
            self.DeviceListRefresh()
            self.deviceRefreshAll.setEnabled(True)

            if not init:
                self.UpdateDevice()

    def ActivateDevice(self, device_uri):
        log.debug(log.bold("Activate: %s %s %s" % ("*"*20, device_uri, "*"*20)))
        d = self.DeviceList.firstItem()
        found = False

        while d is not None:

            if d.device_uri == device_uri:
                found = True
                self.DeviceList.setSelected(d, True)
                break

            d = d.nextItem()

        return found


    def Cleanup(self):
        self.CleanupChildren()
        if self.cleanup is not None:
            self.cleanup()


    def CleanupChildren(self):
        log.debug("Cleaning up child processes.")
        try:
            os.waitpid(-1, os.WNOHANG)
        except OSError:
            pass


    def DeviceList_currentChanged(self, a0):
        if not self.rescanning:
            try:
                self.cur_device_uri = self.DeviceList.currentItem().device_uri
                self.cur_device = self.devices[self.cur_device_uri]
                user_cfg.last_used.device_uri = self.cur_device_uri
            except AttributeError:
                pass

            self.UpdateDevice()


    def DeviceList_rightButtonClicked(self, item, pos):
        popup = QPopupMenu(self)

        if item is not None:
            if self.cur_device.error_state != ERROR_STATE_ERROR:
                if self.user_settings.cmd_print_int:
                    popup.insertItem(self.__tr("Print >>"), self.PrintButton_clicked)
                else:
                    popup.insertItem(self.__tr("Print..."), self.PrintButton_clicked)

                if self.cur_device.scan_type:
                    if self.user_settings.cmd_scan_int:
                        popup.insertItem(self.__tr("Scan >>"), self.ScanButton_clicked)
                    else:
                        popup.insertItem(self.__tr("Scan..."), self.ScanButton_clicked)

                if self.cur_device.pcard_type:
                    if self.user_settings.cmd_pcard_int:
                        popup.insertItem(self.__tr("Access Photo Cards >>"), self.PCardButton_clicked)
                    else:
                        popup.insertItem(self.__tr("Access Photo Cards..."), self.PCardButton_clicked)

                if self.cur_device.fax_type:
                    if self.user_settings.cmd_fax_int:
                        popup.insertItem(self.__tr("Send Fax >>"), self.SendFaxButton_clicked)
                    else:
                        popup.insertItem(self.__tr("Send Fax..."), self.SendFaxButton_clicked)

                if self.cur_device.copy_type:
                    if self.user_settings.cmd_copy_int:
                        popup.insertItem(self.__tr("Make Copies >>"), self.MakeCopiesButton_clicked)
                    else:
                        popup.insertItem(self.__tr("Make Copies..."), self.MakeCopiesButton_clicked)

                popup.insertSeparator()

            if self.cur_device.device_settings_ui is not None:
                popup.insertItem(self.__tr("Device Settings..."), self.deviceSettingsButton_clicked)

            popup.insertItem(self.__tr("Refresh Device"), self.UpdateDevice)

        popup.insertItem(self.__tr("Refresh All"), self.deviceRefreshAll_activated)

        popup.popup(pos)


    def UpdateDevice(self, check_state=True):
        if self.cur_device is not None:
            log.debug(log.bold("Update: %s %s %s" % ("*"*20, self.cur_device_uri, "*"*20)))
            self.setCaption(self.__tr("HP Device Manager - %1").arg(self.cur_device.model_ui))

            self.updatePrinterList()
            
            if not self.rescanning:
                self.statusBar().message(QString("%1 (%2)").arg(self.cur_device_uri).arg(', '.join(self.cur_device.cups_printers)))

            if self.cur_device.supported and check_state and not self.rescanning:
                QApplication.setOverrideCursor(QApplication.waitCursor)

                try:
                    try:
                        self.cur_device.open()
                    except Error, e:
                        log.warn(e.msg)

                    if self.cur_device.device_state == DEVICE_STATE_NOT_FOUND:
                        self.cur_device.error_state = ERROR_STATE_ERROR
                    else:
                        try:
                            self.cur_device.queryDevice(quick=False, no_fwd=False, 
                                reread_cups_printers=False)

                        except Error, e:
                            log.error("Query device error (%s)." % e.msg)
                            self.cur_device.error_state = ERROR_STATE_ERROR

                finally:
                    self.cur_device.close()
                    QApplication.restoreOverrideCursor()

                log.debug("Device state = %d" % self.cur_device.device_state)
                log.debug("Status code = %d" % self.cur_device.status_code)
                log.debug("Error state = %d" % self.cur_device.error_state)

                icon = self.CreatePixmap()
                self.DeviceList.currentItem().setPixmap(icon)

            self.cur_device.hist = []

            if not self.rescanning: 
                self.UpdateHistory()
                
                if self.allow_auto_refresh:
                    self.Tabs_deviceChanged(self.Tabs.currentPage())
                
                self.UpdatePrinterCombos()
                self.UpdatePanel()
                self.setupDevice.setEnabled(self.cur_device.device_settings_ui is not None)

    def updatePrinterList(self):
        if self.cur_device is not None and \
            self.cur_device.supported:

            printers = cups.getPrinters()
            self.cur_device.cups_printers = []
            cur_device_uri_tail = self.cur_device_uri.split(':')[1]

            for p in printers:
                try:
                    p_tail = p.device_uri.split(':')[1]
                except IndexError:
                    continue

                if p_tail == cur_device_uri_tail:
                    self.cur_device.cups_printers.append(p.name)
    
    def UpdatePrinterCombos(self):
        self.PrintSettingsPrinterCombo.clear()
        self.PrintJobPrinterCombo.clear()

        if self.cur_device is not None and \
            self.cur_device.supported:

            for c in self.cur_device.cups_printers:
                #print repr(c), type(c)
                #print c.encode('latin1')
                self.PrintSettingsPrinterCombo.insertItem(c.decode("utf-8"))
                self.PrintJobPrinterCombo.insertItem(c.decode("utf-8"))

            self.current_printer = unicode(self.PrintSettingsPrinterCombo.currentText())

    def SettingsPrinterCombo_activated(self, s):
        #self.current_printer = str(s)
        self.current_printer = unicode(s)
        self.PrintJobPrinterCombo.setCurrentText(self.current_printer.encode("latin1"))
        return self.PrinterCombo_activated(self.current_printer)

    def JobsPrinterCombo_activated(self, s):
        #self.current_printer = str(s)
        self.current_printer = unicode(s)
        self.PrintSettingsPrinterCombo.setCurrentText(self.current_printer.encode("latin1"))
        return self.PrinterCombo_activated(self.current_printer)

    def PrinterCombo_activated(self, printer):
        self.PrintJobsList.onPrinterChange(printer)
        self.PrintSettingsList.onPrinterChange(printer)
        self.FuncList.onPrinterChange(printer)

    def Tabs_currentChanged(self, tab):
        """ Called when the active tab changes. """
        log.debug("Tabs_currentChanged()")
        try:
            self.TabIndex[tab].onUpdate(self.cur_device)
        except AttributeError:
            pass

    def Tabs_deviceChanged(self, tab):
        """ Called when the device changes. """
        log.debug("Tabs_deviceChanged()")

        if tab is self.FunctionsTab and self.funcs_page != 'funcs':
            self.SwitchFunctionsTab('funcs')

        elif tab is self.MaintTab and self.maint_page != 'tools':
            self.SwitchMaintTab('tools')

        else:
            try:
                self.TabIndex[tab].onDeviceChange(self.cur_device)
            except AttributeError:
                self.TabIndex[tab]()
                
    
    def DeviceList_onItem(self, a0):
        pass

    def CreatePixmap(self, dev=None):
        if dev is None:
            dev = self.cur_device

        try:
            pix = QPixmap(os.path.join(prop.image_dir, dev.icon))
        except AttributeError:
            pix = QPixmap(os.path.join(prop.image_dir, 'default_printer.png'))

        error_state = dev.error_state
        icon = QPixmap(pix.width(), pix.height())
        p = QPainter(icon)
        p.eraseRect(0, 0, icon.width(), icon.height())
        p.drawPixmap(0, 0, pix)

        try:
            tech_type = dev.tech_type
        except AttributeError:
            tech_type = TECH_TYPE_NONE

        if error_state != ERROR_STATE_CLEAR:
            if tech_type in (TECH_TYPE_COLOR_INK, TECH_TYPE_MONO_INK):
                status_icon = self.SMALL_ICONS[error_state][0] # ink
            else:
                status_icon = self.SMALL_ICONS[error_state][1] # laser

            if status_icon is not None:
                p.drawPixmap(0, 0, status_icon)

        p.end()

        return icon


    def DeviceListRefresh(self):
        log.debug("Rescanning device list...")

        if not self.rescanning:
            self.setCaption(self.__tr("Refreshing Device List - HP Device Manager"))
            self.statusBar().message(self.__tr("Refreshing device list..."))

            self.rescanning = True
            total_changes = 0
            total_steps = 0

            self.cups_devices = device.getSupportedCUPSDevices()

            QApplication.setOverrideCursor(QApplication.waitCursor)

            # TODO: Use Set() when 2.3+ is ubiquitous

            for d in self.cups_devices: # adds
                if d not in self.devices:
                    total_steps += 1
                    total_changes += 1

            updates = []
            for d in self.devices: # removes
                if d not in self.cups_devices:
                    total_steps += 1
                    total_changes += 1
                else:
                    # Don't update current device as it will be updated at end
                    if self.cur_device is not None and self.cur_device_uri != d:
                        updates.append(d) # updates
                        total_steps += 1

            log.debug("total changes = %d" % total_changes)

            step_num = 0
            pb = None

            if total_steps:
                pb = QProgressBar(self.statusBar(), 'ProgressBar')
                pb.setTotalSteps(total_changes + total_steps)
                self.statusBar().addWidget(pb)
                pb.show()

            if total_changes:
                # Item addition (device added to CUPS)
                for d in self.cups_devices: 
                    if d not in self.devices:
                        qApp.processEvents()
                        log.debug("adding: %s" % d)

                        pb.setProgress(step_num)
                        step_num += 1
                        qApp.processEvents()

                        log.debug(log.bold("Refresh: %s %s %s" % \
                            ("*"*20, d, "*"*20)))

                        try:
                            dev = device.Device(d, hpssd_sock=self.hpssd_sock,
                                                callback=self.callback)
                        except Error:
                            log.error("Unexpected error in Device class.")
                            log.exception()
                            return

                        try:
                            try:
                                dev.open()
                            except Error, e:
                                log.warn(e.msg)

                            if dev.device_state == DEVICE_STATE_NOT_FOUND:
                                dev.error_state = ERROR_STATE_ERROR
                            else:
                                dev.queryDevice(quick=True) #, no_fwd=True)

                        finally:
                            dev.close()

                        self.CheckForDeviceSettingsUI(dev)

                        icon = self.CreatePixmap(dev)

                        IconViewItem(self.DeviceList, dev.model_ui,
                                     icon, d)

                        self.devices[d] = dev

                # Item removal (device removed from CUPS)
                for d in self.devices.keys():
                    if d not in self.cups_devices:
                        qApp.processEvents()
                        item = self.DeviceList.firstItem()
                        log.debug("removing: %s" % d)

                        pb.setProgress(step_num)
                        step_num += 1
                        qApp.processEvents()

                        while item is not None:
                            if item.device_uri == d:
                                self.DeviceList.takeItem(item)
                                del self.devices[d]
                                break

                            item = item.nextItem()

            # Item updates
            for d in updates:
                log.debug("updating: %s" % d)
                qApp.processEvents()
                dev = self.devices[d]

                pb.setProgress(step_num)
                step_num += 1
                qApp.processEvents()

                prev_error_state = dev.error_state

                try:
                    try:
                        dev.open()
                    except Error, e:
                        log.warn(e.msg)

                    if dev.device_state == DEVICE_STATE_NOT_FOUND:
                        dev.error_state = ERROR_STATE_ERROR
                    else:
                        dev.queryDevice(quick=True) #, no_fwd=True)

                finally:
                    dev.close()

                if dev.error_state != prev_error_state:
                    item = self.DeviceList.firstItem()

                    while item is not None:
                        if item.device_uri == d:
                            item.setPixmap(self.CreatePixmap(dev))
                            break

                        item = item.nextItem()

            if pb is not None:
                pb.hide()
                self.statusBar().removeWidget(pb)
                pb = None

            if not len(self.cups_devices):
                QApplication.restoreOverrideCursor()
                self.cur_device = None
                self.deviceRescanAction.setEnabled(False)
                self.deviceRemoveAction.setEnabled(False)
                self.rescanning = False
                self.statusBar().message(self.__tr("Press F6 to refresh."))
                self.UpdatePrinterCombos()
                self.UpdatePanel()
                #self.Tabs_deviceChanged(self.Tabs.currentPage())
                self.TabIndex[self.Tabs.currentPage()].onDeviceChange(None)
                #self.onDeviceChange()
                dlg = NoDevicesForm(self, "", True)
                dlg.show()
                return

            # Select current item
            self.rescanning = False

            if self.cur_device_uri:
                item = self.DeviceList.firstItem()

                while item is not None:
                    qApp.processEvents()
                    if item.device_uri == self.cur_device_uri:
                        self.DeviceList.setCurrentItem(item)
                        self.DeviceList.setSelected(item, True)
                        break

                    item = item.nextItem()

                else:
                    self.cur_device = None
                    self.cur_device_uri = ''

            if not self.cur_device_uri:
                self.cur_device_uri = self.DeviceList.firstItem().device_uri
                self.cur_device = self.devices[self.cur_device_uri]
                self.DeviceList.setCurrentItem(self.DeviceList.firstItem())

            user_cfg.last_used.device_uri = self.cur_device_uri

            self.DeviceList.adjustItems()
            self.DeviceList.updateGeometry()
            self.deviceRescanAction.setEnabled(True)
            self.deviceRemoveAction.setEnabled(True)

            QApplication.restoreOverrideCursor()


    def callback(self):
        pass

    def CheckForDeviceSettingsUI(self, dev):
        dev.device_settings_ui = None
        name = '.'.join(['plugins', dev.model])
        log.debug("Attempting to load plugin: %s" % name)
        try:
            mod = __import__(name, globals(), locals(), [])
        except ImportError:
            log.debug("No plugin found.")
            return
        else:
            components = name.split('.')
            for c in components[1:]:
                mod = getattr(mod, c)
            log.debug("Loaded: %s" % repr(mod))
            dev.device_settings_ui = mod.settingsUI

    def UpdateHistory(self):
        try:
            self.cur_device.queryHistory()
        except Error:
            log.error("History query failed.")
            self.cur_device.last_event = None
            self.cur_device.error_state = ERROR_STATE_ERROR
            self.cur_device.status_code = STATUS_UNKNOWN
        else:
            try:
                self.cur_device.last_event = self.cur_device.hist[-1]
            except IndexError:
                self.cur_device.last_event = None
                self.cur_device.error_state = ERROR_STATE_ERROR
                self.cur_device.status_code = STATUS_UNKNOWN


    def UpdatePanel(self):
        if self.cur_device is not None and \
            self.cur_device.supported:

            dq = self.cur_device.dq

            if dq.get('panel', 0) == 1:
                line1 = dq.get('panel-line1', '')
                line2 = dq.get('panel-line2', '')
            else:
                try:
                    line1 = self.cur_device.hist[0][12]
                except IndexError:
                    line1 = ''

                line2 = ''

            pm = QPixmap(self.blank_lcd)

            p = QPainter()
            p.begin(pm)
            p.setPen(QColor(0, 0, 0))
            p.setFont(self.font())

            x, y_line1, y_line2 = 10, 17, 33

            # TODO: Scroll long lines
            p.drawText(x, y_line1, line1)
            p.drawText(x, y_line2, line2)
            p.end()

            self.Panel_2.setPixmap(pm)

        else:
            self.Panel_2.setPixmap(QPixmap(self.blank_lcd))


    def settingsConfigure_activated(self, tab_to_show=0):
        dlg = SettingsDialog(self.hpssd_sock, self)
        dlg.TabWidget.setCurrentPage(tab_to_show)

        if dlg.exec_loop() == QDialog.Accepted:
            old_auto_refresh = self.user_settings.auto_refresh_rate
            self.user_settings.load()

            if self.user_settings.auto_refresh and old_auto_refresh != self.user_settings.auto_refresh_rate:
                self.refresh_timer.changeInterval(self.user_settings.auto_refresh_rate * 1000)

            if old_auto_refresh != self.user_settings.auto_refresh:
                self.autoRefresh.toggle()

            self.SetAlerts()


    def SetAlerts(self):
        service.setAlerts(self.hpssd_sock,
                          self.user_settings.email_alerts,
                          self.user_settings.email_to_addresses,
                          self.user_settings.email_from_address)

    def deviceRescanAction_activated(self):
        self.deviceRescanAction.setEnabled(False)
        self.UpdateDevice()
        self.deviceRescanAction.setEnabled(True)

    def deviceRefreshAll_activated(self):
        self.RescanDevices()

    def DeviceList_clicked(self,a0):
        pass

    def PrintButton_clicked(self):
        if self.user_settings.cmd_print_int:
            self.Tabs.setCurrentPage(0)
            self.SwitchFunctionsTab("print")
        else:
            self.RunCommand(self.user_settings.cmd_print)

    def ScanButton_clicked(self):
        if self.user_settings.cmd_scan_int:
            self.Tabs.setCurrentPage(0)
            self.SwitchFunctionsTab("scan")
        else:
            self.RunCommand(self.user_settings.cmd_scan)

    def PCardButton_clicked(self):
        if self.cur_device.pcard_type == PCARD_TYPE_MLC:
            if self.user_settings.cmd_pcard_int:
                self.Tabs.setCurrentPage(0)
                self.SwitchFunctionsTab("pcard")
            else:
                self.RunCommand(self.user_settings.cmd_pcard)

        elif self.cur_device.pcard_type == PCARD_TYPE_USB_MASS_STORAGE:
            self.FailureUI(self.__tr("<p><b>Photocards on your printer are only available by mounting them as drives using USB mass storage.</b><p>Please refer to your distribution's documentation for setup and usage instructions."))

    def SendFaxButton_clicked(self):
        if self.user_settings.cmd_fax_int:
            self.Tabs.setCurrentPage(0)
            self.SwitchFunctionsTab("fax")
        else:
            self.RunCommand(self.user_settings.cmd_fax)

    def MakeCopiesButton_clicked(self):
        if self.user_settings.cmd_copy_int:
            self.Tabs.setCurrentPage(0)
            self.SwitchFunctionsTab("copy")
        else:
            self.RunCommand(self.user_settings.cmd_copy)

    def ConfigureFeaturesButton_clicked(self):
        self.settingsConfigure_activated(2)

    def RunCommand(self, cmd, macro_char='%'):
        QApplication.setOverrideCursor(QApplication.waitCursor)

        try:
            if len(cmd) == 0:
                self.FailureUI(self.__tr("<p><b>Unable to run command. No command specified.</b><p>Use <pre>Configure...</pre> to specify a command to run."))
                log.error("No command specified. Use settings to configure commands.")
            else:
                log.debug("Run: %s %s (%s) %s" % ("*"*20, cmd, self.cur_device_uri, "*"*20))
                log.debug(cmd)
                
                try:
                    cmd = ''.join([self.cur_device.device_vars.get(x, x) \
                                     for x in cmd.split(macro_char)])
                except AttributeError:
                    pass
                    
                log.debug(cmd)

                path = cmd.split()[0]
                args = cmd.split()

                log.debug(path)
                log.debug(args)

                self.CleanupChildren()
                os.spawnvp(os.P_NOWAIT, path, args)

        finally:
            QApplication.restoreOverrideCursor()

    def helpAbout(self):
        dlg = AboutDlg(self)
        dlg.VersionText.setText(prop.version)
        dlg.ToolboxVersionText.setText(self.toolbox_version)
        dlg.exec_loop()

    def deviceSettingsButton_clicked(self):
        try:
            self.cur_device.open()
            self.cur_device.device_settings_ui(self.cur_device, self)
        finally:
            self.cur_device.close()

    def setupDevice_activated(self):
        try:
            self.cur_device.open()
            self.cur_device.device_settings_ui(self.cur_device, self)
        finally:
            self.cur_device.close()

        #self.cur_device.device_settings_ui(self.cur_device, self)

    def helpContents(self):
        f = "http://hplip.sf.net"
        
        if prop.doc_build:
            g = os.path.join(sys_cfg.dirs.doc, 'index.html')
            if os.path.exists(g):
                f = "file://%s" % g
            
        log.debug(f)
        utils.openURL(f)

    def deviceInstallAction_activated(self):
        su_sudo = None

        if utils.which('kdesu'):
            su_sudo = 'kdesu -- %s'

        elif utils.which('gksu'):
            su_sudo = 'gksu "%s"'

        if su_sudo is None:
            QMessageBox.critical(self,
                                self.caption(),
                                self.__tr("<b>Unable to find an appropriate su/sudo utility to run hp-setup.</b>"),
                                QMessageBox.Ok,
                                QMessageBox.NoButton,
                                QMessageBox.NoButton)

        else:
            if utils.which('hp-setup'):
                cmd = su_sudo % 'hp-setup -u'
            else:
                cmd = su_sudo % 'python ./setup.py -u'

            log.debug(cmd)
            utils.run(cmd, log_output=True, password_func=None, timeout=1)
            self.RescanDevices()        


    def deviceRemoveAction_activated(self):
        if self.cur_device is not None:
            x = QMessageBox.critical(self,
                                     self.caption(),
                                     self.__tr("<b>Annoying Confirmation: Are you sure you want to remove this device?</b>"),
                                      QMessageBox.Yes,
                                      QMessageBox.No | QMessageBox.Default,
                                      QMessageBox.NoButton)
            if x == QMessageBox.Yes:
                QApplication.setOverrideCursor(QApplication.waitCursor)
                print_uri = self.cur_device.device_uri
                fax_uri = print_uri.replace('hp:', 'hpfax:')

                log.debug(print_uri)
                log.debug(fax_uri)

                self.cups_devices = device.getSupportedCUPSDevices(['hp', 'hpfax'])

                for d in self.cups_devices:
                    if d in (print_uri, fax_uri):
                        for p in self.cups_devices[d]:
                            log.debug("Removing %s" % p)
                            cups.delPrinter(p)

                self.cur_device = None
                self.cur_device_uri = ''
                user_cfg.last_used.device_uri = ''

                QApplication.restoreOverrideCursor()

                self.RescanDevices()


    def FailureUI(self, error_text):
        log.error(unicode(error_text).replace("<b>", "").replace("</b>", "").replace("<p>", " "))
        QMessageBox.critical(self,
                             self.caption(),
                             error_text,
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)

    def WarningUI(self, msg):
        QMessageBox.warning(self,
                             self.caption(),
                             msg,
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)

    def __tr(self,s,c = None):
        return qApp.translate("DevMgr4",s,c)
