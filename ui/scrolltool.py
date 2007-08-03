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
from base import utils, pml, maint
from prnt import cups
from base.codes import *

# Qt
from qt import *
from scrollview import ScrollView, PixmapLabelButton

# Std Lib
import sys, os.path, os

# Alignment and ColorCal forms
from alignform import AlignForm
from aligntype6form1 import AlignType6Form1
from aligntype6form2 import AlignType6Form2
from paperedgealignform import PaperEdgeAlignForm
from colorcalform import ColorCalForm # Type 1 color cal
from coloradjform import ColorAdjForm  # Type 5 and 6 color adj
from colorcalform2 import ColorCalForm2 # Type 2 color cal
from colorcal4form import ColorCal4Form # Type 4 color cal
from align10form import Align10Form # Type 10 and 11 alignment

# Misc forms
from loadpaperform import LoadPaperForm
from settingsdialog import SettingsDialog
from aboutdlg import AboutDlg
from cleaningform import CleaningForm
from cleaningform2 import CleaningForm2
from waitform import WaitForm
from faxsettingsform import FaxSettingsForm


class ScrollToolView(ScrollView):
    def __init__(self, toolbox_hosted=True, parent = None,form=None, name = None,fl = 0):
        ScrollView.__init__(self,parent,name,fl)

        self.form = form
        self.toolbox_hosted = toolbox_hosted

        user_settings = utils.UserSettings()
        self.cmd_fab = user_settings.cmd_fab
        log.debug("FAB command: %s" % self.cmd_fab)

    def fillControls(self):
        ScrollView.fillControls(self)

        if self.cur_device is not None and \
            self.cur_device.supported and \
            self.cur_device.device_state != DEVICE_STATE_NOT_FOUND:

            if self.cur_device.device_settings_ui is not None:
                self.addItem( "device_settings", self.__tr("<b>Device Settings</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_settings.png')), 
                    self.__tr("Your device has special device settings. You may alter these settings here."), 
                    self.__tr("Device Settings..."), 
                    self.deviceSettingsButton_clicked)

            if self.cur_device.fax_type and prop.fax_build:
                self.addItem( "fax_settings", self.__tr("<b>Fax Setup</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_fax.png')), 
                    self.__tr("Fax support must be setup before you can send faxes."), 
                    self.__tr("Setup Fax..."), 
                    self.faxSettingsButton_clicked)

                self.addItem( "fax_address_book", self.__tr("<b>Fax Address Book</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_fax.png')), 
                    self.__tr("Setup fax phone numbers to use when sending faxes from the PC."), 
                    self.__tr("Fax Address Book..."), 
                    self.faxAddressBookButton_clicked)

            self.addItem( "testpage", self.__tr("<b>Print Test Page</b>"), 
                QPixmap(os.path.join(prop.image_dir, 'icon_testpage.png')), 
                self.__tr("Print a test page to test the setup of your printer."), 
                self.__tr("Print Test Page >>"), 
                self.PrintTestPageButton_clicked)

            self.addItem( "printer_info", self.__tr("<b>View Printer (Queue) Information</b>"), 
                QPixmap(os.path.join(prop.image_dir, 'icon_cups.png')), 
                self.__tr("View the printers (queues) installed in CUPS."), 
                self.__tr("View Printer Information >>"), 
                self.viewPrinterInformation) 

            self.addItem( "device_info", self.__tr("<b>View Device Information</b>"), 
                QPixmap(os.path.join(prop.image_dir, 'icon_info.png')), 
                self.__tr("This information is primarily useful for debugging and troubleshooting (advanced)."), 
                self.__tr("View Device Information >>"), 
                self.viewInformation) 

            if self.cur_device.pq_diag_type:
                self.addItem( "pqdiag", self.__tr("<b>Print Quality Diagnostics</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_pq_diag.png')),
                    self.__tr("Your printer can print a test page to help diagnose print quality problems."), 
                    self.__tr("Print Diagnostic Page..."), 
                    self.pqDiag)

            if self.cur_device.fw_download:
                self.addItem( "fwdownload", self.__tr("<b>Download Firmware</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'download.png')),
                    self.__tr("Download firmware to your printer (required on some devices after each power-up)."), 
                    self.__tr("Download Firmware..."), 
                    self.downloadFirmware)

            if self.cur_device.clean_type:
                self.addItem( "clean", self.__tr("<b>Clean Cartridges</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_clean.png')), 
                    self.__tr("You only need to perform this action if you are having problems with poor printout quality due to clogged ink nozzles."), 
                    self.__tr("Clean Cartridges..."), 
                    self.CleanPensButton_clicked)

            if self.cur_device.align_type:
                self.addItem( "align", self.__tr("<b>Align Cartridges</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_align.png')), 
                    self.__tr("This will improve the quality of output when a new cartridge is installed."), 
                    self.__tr("Align Cartridges..."), 
                    self.AlignPensButton_clicked)

            if self.cur_device.color_cal_type:
                self.addItem( "colorcal", self.__tr("<b>Perform Color Calibration</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_colorcal.png')), 
                    self.__tr("Use this procedure to optimimize your printer's color output."), 
                    self.__tr("Color Calibration..."), 
                    self.ColorCalibrationButton_clicked)

            if self.cur_device.linefeed_cal_type:
                self.addItem( "linefeed", self.__tr("<b>Perform Line Feed Calibration</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_linefeed_cal.png')),
                    self.__tr("Use line feed calibration to optimize print quality (to remove gaps in the printed output)."), 
                    self.__tr("Line Feed Calibration..."), 
                    self.linefeedCalibration) 

            if self.cur_device.embedded_server_type and self.cur_device.bus == 'net' and prop.net_build:
                self.addItem( "ews", self.__tr("<b>Access Embedded Web Page</b>"), 
                    QPixmap(os.path.join(prop.image_dir, 'icon_ews.png')), 
                    self.__tr("You can use your printer's embedded web server to configure, maintain, and monitor the device from a web browser."),
                    self.__tr("Open in Browser..."), 
                    self.OpenEmbeddedBrowserButton_clicked)

        self.addItem("support",  self.__tr("<b>View Documentation</b>"), 
            QPixmap(os.path.join(prop.image_dir, 'icon_support2.png')), 
            self.__tr("View documentation installed on your system."), 
            self.__tr("View Documentation..."), 
            self.viewSupport) 


    def addItem(self, name, title, pix, text, button_text, button_func):
        self.addGroupHeading(title, title)

        widget = self.getWidget()

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
        icon.setPixmap(pix)

        self.connect(pushButton, SIGNAL("clicked()"), button_func)

        self.addWidget(widget, unicode(title))

    def viewInformation(self):
        self.form.SwitchMaintTab("device_info")

    def viewPrinterInformation(self):
        self.form.SwitchMaintTab("printer_info")

    def viewSupport(self):
        f = "http://hplip.sf.net"
        
        if prop.doc_build:
            g = os.path.join(sys_cfg.dirs.doc, 'index.html')
            if os.path.exists(g):
                f = "file://%s" % g
            
        log.debug(f)
        utils.openURL(f)

    def pqDiag(self):
        d = self.cur_device
        pq_diag = d.pq_diag_type

        try:
            QApplication.setOverrideCursor(QApplication.waitCursor)

            try:
                d.open()
            except Error:
                self.CheckDeviceUI()
            else:
                if d.isIdleAndNoError():
                    QApplication.restoreOverrideCursor()

                    if pq_diag == 1:
                        maint.printQualityDiagType1(d, self.LoadPaperUI)

                    elif pq_diag == 2:
                        maint.printQualityDiagType2(d, self.LoadPaperUI)

                else:
                    self.CheckDeviceUI()

        finally:
            d.close()
            QApplication.restoreOverrideCursor()


    def linefeedCalibration(self):
        d = self.cur_device
        linefeed_type = d.linefeed_cal_type

        try:    
            QApplication.setOverrideCursor(QApplication.waitCursor)

            try:
                d.open()
            except Error:
                self.CheckDeviceUI()
            else:
                if d.isIdleAndNoError():
                    QApplication.restoreOverrideCursor()

                    if linefeed_type == 1:
                        maint.linefeedCalType1(d, self.LoadPaperUI)

                    elif linefeed_type == 2:
                        maint.linefeedCalType2(d, self.LoadPaperUI)

                else:
                    self.CheckDeviceUI()

        finally:
            d.close()
            QApplication.restoreOverrideCursor()

    def downloadFirmware(self):
        d = self.cur_device

        try:
            QApplication.setOverrideCursor(QApplication.waitCursor)
            d.open()

            if d.isIdleAndNoError():
                d.downloadFirmware()
            else:
                self.form.FailureUI(self.__tr("<b>An error occured downloading firmware file.</b><p>Please check your printer and try again."))

        finally:
            d.close()
            QApplication.restoreOverrideCursor()


    def CheckDeviceUI(self):
        self.form.FailureUI(self.__tr("<b>Device is busy or in an error state.</b><p>Please check device and try again."))

    def LoadPaperUI(self):
        if LoadPaperForm(self).exec_loop() == QDialog.Accepted:
            return True
        return False

    def AlignmentNumberUI(self, letter, hortvert, colors, line_count, choice_count):
        dlg = AlignForm(self, letter, hortvert, colors, line_count, choice_count)
        if dlg.exec_loop() == QDialog.Accepted:
            return True, dlg.value
        else:
            return False, 0

    def PaperEdgeUI(self, maximum):
        dlg = PaperEdgeAlignForm(self)
        if dlg.exec_loop() == QDialog.Accepted:
            return True, dlg.value
        else:
            return False, 0

    def BothPensRequiredUI(self):
        self.form.WarningUI(self.__tr("<p><b>Both cartridges are required for alignment.</b><p>Please install both cartridges and try again."))

    def InvalidPenUI(self):
        self.form.WarningUI(self.__tr("<p><b>One or more cartiridges are missing from the printer.</b><p>Please install cartridge(s) and try again."))

    def PhotoPenRequiredUI(self):
        self.form.WarningUI(self.__tr("<p><b>Both the photo and color cartridges must be inserted into the printer to perform color calibration.</b><p>If you are planning on printing with the photo cartridge, please insert it and try again."))

    def PhotoPenRequiredUI2(self):
        self.form.WarningUI(self.__tr("<p><b>Both the photo (regular photo or photo blue) and color cartridges must be inserted into the printer to perform color calibration.</b><p>If you are planning on printing with the photo or photo blue cartridge, please insert it and try again."))

    def NotPhotoOnlyRequired(self): # Type 11
        self.form.WarningUI(self.__tr("<p><b>Cannot align with only the photo cartridge installed.</b><p>Please install other cartridges and try again."))

    def AioUI1(self):
        dlg = AlignType6Form1(self)
        return dlg.exec_loop() == QDialog.Accepted


    def AioUI2(self):
        AlignType6Form2(self).exec_loop()

    def Align10and11UI(self, pattern, align_type):
        dlg = Align10Form(pattern, align_type, self)
        dlg.exec_loop()
        return dlg.getValues()

    def AlignPensButton_clicked(self):
        d = self.cur_device
        align_type = d.align_type

        log.debug("Align: %s %s (type=%d) %s" % ("*"*20, self.cur_device.device_uri, align_type, "*"*20))

        try:
            QApplication.setOverrideCursor(QApplication.waitCursor)

            try:
                d.open()
            except Error:
                self.CheckDeviceUI()
            else:
                if d.isIdleAndNoError():
                    QApplication.restoreOverrideCursor()

                    if align_type == ALIGN_TYPE_AUTO:
                        maint.AlignType1(d, self.LoadPaperUI)

                    elif align_type == ALIGN_TYPE_8XX:
                        maint.AlignType2(d, self.LoadPaperUI, self.AlignmentNumberUI,
                                         self.BothPensRequiredUI)

                    elif align_type in (ALIGN_TYPE_9XX,ALIGN_TYPE_9XX_NO_EDGE_ALIGN):
                         maint.AlignType3(d, self.LoadPaperUI, self.AlignmentNumberUI,
                                          self.PaperEdgeUI, align_type)

                    elif align_type in (ALIGN_TYPE_LIDIL_0_3_8, ALIGN_TYPE_LIDIL_0_4_3, ALIGN_TYPE_LIDIL_VIP):
                        maint.AlignxBow(d, align_type, self.LoadPaperUI, self.AlignmentNumberUI,
                                        self.PaperEdgeUI, self.InvalidPenUI, self.ColorAdjUI)

                    elif align_type == ALIGN_TYPE_LIDIL_AIO:
                        maint.AlignType6(d, self.AioUI1, self.AioUI2, self.LoadPaperUI)

                    elif align_type == ALIGN_TYPE_DESKJET_450:
                        maint.AlignType8(d, self.LoadPaperUI, self.AlignmentNumberUI)

                    elif align_type == ALIGN_TYPE_LBOW:
                        maint.AlignType10(d, self.LoadPaperUI, self.Align10and11UI) 

                    elif align_type == ALIGN_TYPE_LIDIL_0_5_4:
                        maint.AlignType11(d, self.LoadPaperUI, self.Align10and11UI, self.NotPhotoOnlyRequired) 

                    elif align_type == ALIGN_TYPE_OJ_PRO:
                        maint.AlignType12(d, self.LoadPaperUI)

                else:
                    self.CheckDeviceUI()

        finally:
            d.close()
            QApplication.restoreOverrideCursor()

    def ColorAdjUI(self, line, maximum=0):
        dlg = ColorAdjForm(self, line)
        if dlg.exec_loop() == QDialog.Accepted:
            return True, dlg.value
        else:
            return False, 0

    def ColorCalUI(self):
        dlg = ColorCalForm(self)
        if dlg.exec_loop() == QDialog.Accepted:
            return True, dlg.value
        else:
            return False, 0

    def ColorCalUI2(self):
        dlg = ColorCalForm2(self)
        if dlg.exec_loop() == QDialog.Accepted:
            return True, dlg.value
        else:
            return False, 0

    def ColorCalUI4(self):
        dlg = ColorCal4Form(self)
        if dlg.exec_loop() == QDialog.Accepted:
            return True, dlg.values
        else:
            return False, None

    def ColorCalibrationButton_clicked(self):
        d = self.cur_device
        color_cal_type = d.color_cal_type
        log.debug("Color-cal: %s %s (type=%d) %s" % ("*"*20, self.cur_device.device_uri, color_cal_type, "*"*20))

        try:
            QApplication.setOverrideCursor(QApplication.waitCursor)

            try:
                d.open()
            except Error:
                self.CheckDeviceUI()
            else:
                if d.isIdleAndNoError():
                    QApplication.restoreOverrideCursor()

                    if color_cal_type == COLOR_CAL_TYPE_DESKJET_450:
                         maint.colorCalType1(d, self.LoadPaperUI, self.ColorCalUI,
                                             self.PhotoPenRequiredUI)

                    elif color_cal_type == COLOR_CAL_TYPE_MALIBU_CRICK:
                        maint.colorCalType2(d, self.LoadPaperUI, self.ColorCalUI2,
                                            self.InvalidPenUI)

                    elif color_cal_type == COLOR_CAL_TYPE_STRINGRAY_LONGBOW_TORNADO:
                        maint.colorCalType3(d, self.LoadPaperUI, self.ColorAdjUI,
                                            self.PhotoPenRequiredUI2)

                    elif color_cal_type == COLOR_CAL_TYPE_CONNERY:
                        maint.colorCalType4(d, self.LoadPaperUI, self.ColorCalUI4,
                                            self.WaitUI)

                    elif color_cal_type == COLOR_CAL_TYPE_COUSTEAU:
                        maint.colorCalType5(d, self.LoadPaperUI)

                    elif color_cal_type == COLOR_CAL_TYPE_CARRIER:
                        maint.colorCalType6(d, self.LoadPaperUI)

                else:
                    self.CheckDeviceUI()

        finally:
            d.close()
            QApplication.restoreOverrideCursor()


    def PrintTestPageButton_clicked(self):
        self.form.SwitchMaintTab("testpage")


    def CleanUI1(self):
        return CleaningForm(self, self.cur_device, 1).exec_loop() == QDialog.Accepted


    def CleanUI2(self):
        return CleaningForm(self, self.cur_device, 2).exec_loop() == QDialog.Accepted


    def CleanUI3(self):
        CleaningForm2(self).exec_loop()
        return True


    def WaitUI(self, seconds):
        WaitForm(seconds, None, self).exec_loop()


    def CleanPensButton_clicked(self):
        d = self.cur_device
        clean_type = d.clean_type
        log.debug("Clean: %s %s (type=%d) %s" % ("*"*20, self.cur_device.device_uri, clean_type, "*"*20))

        try:
            QApplication.setOverrideCursor(QApplication.waitCursor)

            try:
                d.open()
            except Error:
                self.CheckDeviceUI()
            else:
                if d.isIdleAndNoError():
                    QApplication.restoreOverrideCursor()

                    if clean_type == CLEAN_TYPE_PCL:
                        maint.cleaning(d, clean_type, maint.cleanType1, maint.primeType1,
                                        maint.wipeAndSpitType1, self.LoadPaperUI,
                                        self.CleanUI1, self.CleanUI2, self.CleanUI3,
                                        self.WaitUI)

                    elif clean_type == CLEAN_TYPE_LIDIL:
                        maint.cleaning(d, clean_type, maint.cleanType2, maint.primeType2,
                                        maint.wipeAndSpitType2, self.LoadPaperUI,
                                        self.CleanUI1, self.CleanUI2, self.CleanUI3,
                                        self.WaitUI)

                    elif clean_type == CLEAN_TYPE_PCL_WITH_PRINTOUT:
                        maint.cleaning(d, clean_type, maint.cleanType1, maint.primeType1,
                                        maint.wipeAndSpitType1, self.LoadPaperUI,
                                        self.CleanUI1, self.CleanUI2, self.CleanUI3,
                                        self.WaitUI)
                else:
                    self.CheckDeviceUI()

        finally:
            d.close()
            QApplication.restoreOverrideCursor()

    def OpenEmbeddedBrowserButton_clicked(self):
        utils.openURL("http://%s" % self.cur_device.host)

    def faxAddressBookButton_clicked(self):
        self.RunCommand(self.cmd_fab)

    def faxSettingsButton_clicked(self):
        try:
            try:
                self.cur_device.open()
            except Error:
                self.CheckDeviceUI()
            else:
                try:
                    result_code, fax_num = self.cur_device.getPML(pml.OID_FAX_LOCAL_PHONE_NUM)
                except Error:
                    log.error("PML failure.")
                    self.form.FailureUI(self.__tr("<p><b>Operation failed. Device busy.</b>"))
                    return

                fax_num = str(fax_num)

                try:
                    result_code, name = self.cur_device.getPML(pml.OID_FAX_STATION_NAME)
                except Error:
                    log.error("PML failure.")
                    self.form.FailureUI(self.__tr("<p><b>Operation failed. Device busy.</b>"))
                    return

                name = str(name)

                dlg = FaxSettingsForm(self.cur_device, fax_num, name, self)
                dlg.exec_loop()

        finally:
            self.cur_device.close()


    def addressBookButton_clicked(self):
        self.RunCommand(self.cmd_fab)

    def deviceSettingsButton_clicked(self):
        try:
            self.cur_device.open()
            self.cur_device.device_settings_ui(self.cur_device, self)
        finally:
            self.cur_device.close()


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


    def FailureUI(self, error_text):
        QMessageBox.critical(self,
                             self.caption(),
                             error_text,
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)

    def __tr(self,s,c = None):
        return qApp.translate("ScrollToolView",s,c)


#
#
# ScrollDeviceInfoView (View Device Information)
#
#

class ScrollDeviceInfoView(ScrollView):
    def __init__(self, toolbox_hosted=True, parent = None, form=None, name = None,fl = 0):
        ScrollView.__init__(self,parent,name,fl)

        self.form = form
        self.toolbox_hosted = toolbox_hosted

    def fillControls(self):
        ScrollView.fillControls(self)

        self.addDeviceInfo()

        # addActionButton(self, name, action_text, action_func, action_pixmap=None, disabled_action_pixmap=None,
        #                 nav_text ='', nav_func=None):

        if self.toolbox_hosted:
            self.navButton = self.addActionButton("bottom_nav", "", 
                                    None, None, None, self.__tr("<< Tools"), self.navButton_clicked)
        else:
            self.navButton = self.addActionButton("bottom_nav", self.__tr("Close"), 
                                    self.navButton_clicked, None, None, "", None)

        self.maximizeControl()

    def addDeviceInfo(self):
        self.addGroupHeading("info_title", self.__tr("Device Information"))

        widget = self.getWidget()

        layout37 = QGridLayout(widget,1,1,5,10,"layout37")

        self.infoListView = QListView(widget,"fileListView")
        self.infoListView.addColumn(self.__tr("Static/Dynamic"))
        self.infoListView.addColumn(self.__tr("Key"))
        self.infoListView.addColumn(self.__tr("Value"))
        self.infoListView.setAllColumnsShowFocus(1)
        self.infoListView.setShowSortIndicator(1)
        self.infoListView.setColumnWidth(0, 50)
        self.infoListView.setColumnWidth(1, 150)
        self.infoListView.setColumnWidth(2, 300)
        self.infoListView.setItemMargin(2)
        self.infoListView.setSorting(-1)

        layout37.addMultiCellWidget(self.infoListView,1,1,0,3)

        mq_keys = self.cur_device.mq.keys()
        mq_keys.sort()
        mq_keys.reverse()
        for key,i in zip(mq_keys, range(len(mq_keys))):
            QListViewItem(self.infoListView, self.__tr("Static"), key, str(self.cur_device.mq[key]))

        dq_keys = self.cur_device.dq.keys()
        dq_keys.sort()
        dq_keys.reverse()
        for key,i in zip(dq_keys, range(len(dq_keys))):
            QListViewItem(self.infoListView, self.__tr("Dynamic"), key, str(self.cur_device.dq[key]))

        self.addWidget(widget, "file_list", maximize=True)

    def navButton_clicked(self):
        if self.toolbox_hosted:
            self.form.SwitchMaintTab("tools")
        else:
            self.form.close()

    def __tr(self,s,c = None):
        return qApp.translate("ScrollDeviceInfoView",s,c)



#
#
# ScrollTestpageView (Print Test Page)
#
#

class ScrollTestpageView(ScrollView):
    def __init__(self, toolbox_hosted=True, parent = None, form=None, name = None,fl = 0):
        ScrollView.__init__(self,parent,name,fl)

        self.form = form
        self.toolbox_hosted = toolbox_hosted

    def fillControls(self):
        ScrollView.fillControls(self)

        self.addPrinterFaxList()

        self.addTestpageType()

        self.addLoadPaper()

        if self.toolbox_hosted:
            s = self.__tr("<< Tools")
        else:
            s = self.__tr("Close")

        self.printButton = self.addActionButton("bottom_nav", self.__tr("Print Test Page"), 
                                self.printButton_clicked, 'print.png', None, s, self.navButton_clicked)


    def addTestpageType(self):
        self.addGroupHeading("testpage_type", self.__tr("Test Page Type"))
        widget = self.getWidget()

        Form4Layout = QGridLayout(widget,1,1,5,10,"Form4Layout")

        self.buttonGroup3 = QButtonGroup(widget,"buttonGroup3")
        self.buttonGroup3.setLineWidth(0)
        self.buttonGroup3.setColumnLayout(0,Qt.Vertical)
        self.buttonGroup3.layout().setSpacing(5)
        self.buttonGroup3.layout().setMargin(10)

        buttonGroup3Layout = QGridLayout(self.buttonGroup3.layout())
        buttonGroup3Layout.setAlignment(Qt.AlignTop)

        self.radioButton6 = QRadioButton(self.buttonGroup3,"radioButton6")
        self.radioButton6.setEnabled(False)
        buttonGroup3Layout.addWidget(self.radioButton6,1,0)

        self.radioButton5 = QRadioButton(self.buttonGroup3,"radioButton5")
        self.radioButton5.setChecked(1)
        buttonGroup3Layout.addWidget(self.radioButton5,0,0)

        Form4Layout.addWidget(self.buttonGroup3,0,0)

        self.radioButton6.setText(self.__tr("Printer diagnostic page (does not test print driver)"))
        self.radioButton5.setText(self.__tr("HPLIP test page (tests print driver)"))


        self.addWidget(widget, "page_type")


    def navButton_clicked(self):
        if self.toolbox_hosted:
            self.form.SwitchMaintTab("tools")
        else:
            self.form.close()

    def printButton_clicked(self):
        d = self.cur_device
        printer_name = self.cur_printer
        printed = False

        try:
            QApplication.setOverrideCursor(QApplication.waitCursor)

            try:
                d.open()
            except Error:
                self.CheckDeviceUI()
            else:
                if d.isIdleAndNoError():
                    QApplication.restoreOverrideCursor()
                    d.close()

                    d.printTestPage(printer_name)
                    printed = True

                else:
                    d.close()
                    self.CheckDeviceUI()

        finally:
            QApplication.restoreOverrideCursor()

        if printed:
                QMessageBox.information(self,
                                     self.caption(),
                                     self.__tr("<p><b>A test page should be printing on your printer.</b><p>If the page fails to print, please visit http://hplip.sourceforge.net for troubleshooting and support."),
                                      QMessageBox.Ok,
                                      QMessageBox.NoButton,
                                      QMessageBox.NoButton)


        if self.toolbox_hosted:
            self.form.SwitchMaintTab("tools")
        else:
            self.form.close()
            
    def CheckDeviceUI(self):
            self.form.FailureUI(self.__tr("<b>Device is busy or in an error state.</b><p>Please check device and try again."))            


    def __tr(self,s,c = None):
        return qApp.translate("ScrollTestpageView",s,c)







#
#
# ScrollPrinterInfoView (View Device Information)
#
#

class ScrollPrinterInfoView(ScrollView):
    def __init__(self, toolbox_hosted=True, parent = None, form=None, name = None,fl = 0):
        ScrollView.__init__(self,parent,name,fl)

        self.form = form
        self.toolbox_hosted = toolbox_hosted

    def fillControls(self):
        ScrollView.fillControls(self)

        printers = []
        for p in self.printers:
            if p.device_uri == self.cur_device.device_uri or \
                p.device_uri.replace("hpfax:", "hp:") == self.cur_device.device_uri:

                printers.append(p)

        if not printers:
            self.addGroupHeading("error_title", self.__tr("No printers found for this device."))
        else:
            for p in printers:
                self.addPrinterInfo(p)

        if self.toolbox_hosted:
            self.navButton = self.addActionButton("bottom_nav", "", 
                                    None, None, None, self.__tr("<< Tools"), self.navButton_clicked)
        else:
            self.navButton = self.addActionButton("bottom_nav", self.__tr("Close"), 
                                    self.navButton_clicked, None, None, "", None)

        self.maximizeControl()

    def addPrinterInfo(self, p):
        self.addGroupHeading(p.name, p.name)
        widget = self.getWidget()

        layout1 = QVBoxLayout(widget,5,10,"layout1")

        textLabel2 = QLabel(widget,"textLabel2")

        if p.device_uri.startswith("hpfax:"):
            s = self.__tr("Fax")
        else:
            s = self.__tr("Printer")
        textLabel2.setText(self.__tr("Type: %1").arg(s))
        layout1.addWidget(textLabel2)

        textLabel3 = QLabel(widget,"textLabel3")
        textLabel3.setText(self.__tr("Location: %1").arg(p.location))
        layout1.addWidget(textLabel3)

        textLabel4 = QLabel(widget,"textLabel4")
        textLabel4.setText(self.__tr("Description/Info: %1").arg(p.info))
        layout1.addWidget(textLabel4)

        textLabel5 = QLabel(widget,"textLabel5")

        if p.state == cups.IPP_PRINTER_STATE_IDLE:
            s = self.__tr("Idle")
        elif p.state == cups.IPP_PRINTER_STATE_PROCESSING:
            s = self.__tr("Processing")
        elif p.state == cups.IPP_PRINTER_STATE_STOPPED:
            s = self.__tr("Stopped")
        else:
            s = self.__tr("Unknown")

        textLabel5.setText(self.__tr("State: %1").arg(s))
        layout1.addWidget(textLabel5)

        textLabel6 = QLabel(widget,"textLabel6")
        textLabel6.setText(self.__tr("PPD/Driver: %1").arg(p.makemodel))
        layout1.addWidget(textLabel6)

        textLabel7 = QLabel(widget,"textLabel7")
        textLabel7.setText(self.__tr("CUPS/IPP Printer URI: %1").arg(p.printer_uri))
        layout1.addWidget(textLabel7)

        self.addWidget(widget, p.name)

    def navButton_clicked(self):
        if self.toolbox_hosted:
            self.form.SwitchMaintTab("tools")
        else:
            self.form.close()

    def __tr(self,s,c = None):
        return qApp.translate("ScrollPrinterInfoView",s,c)
