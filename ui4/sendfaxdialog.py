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
from sendfaxdialog_base import Ui_Dialog
from filetable import FileTable, FILETABLE_TYPE_FAX
from printernamecombobox import PrinterNameComboBox, PRINTERNAMECOMBOBOX_TYPE_FAX_ONLY
from printsettingsdialog import PrintSettingsDialog
from faxsetupdialog import FaxSetupDialog


PAGE_SELECT_FAX = 0
PAGE_COVERPAGE = 1
PAGE_FILES = 2
PAGE_RECIPIENTS = 3
PAGE_SEND_FAX = 4
PAGE_MAX = 4



class SendFaxDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, device_uri, args=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.device_uri = device_uri
        self.printer_name = None
        self.file_list = []
        
        if args is not None:
            for a in args:
                print a

        self.allowable_mime_types = cups.getAllowableMIMETypes()
        self.allowable_mime_types.append("application/x-python")

        log.debug(self.allowable_mime_types)

        self.MIME_TYPES_DESC = \
        {
            "application/pdf" : (self.__tr("PDF Document"), '.pdf'),
            "application/postscript" : (self.__tr("Postscript Document"), '.ps'),
            "application/vnd.hp-HPGL" : (self.__tr("HP Graphics Language File"), '.hgl, .hpg, .plt, .prn'),
            "application/x-cshell" : (self.__tr("C Shell Script"), '.csh, .sh'),
            "application/x-csource" : (self.__tr("C Source Code"), '.c'),
            "text/cpp": (self.__tr("C++ Source Code"), '.cpp, .cxx'),
            "application/x-perl" : (self.__tr("Perl Script"), '.pl'),
            "application/x-python" : (self.__tr("Python Program"), '.py'),
            "application/x-shell" : (self.__tr("Shell Script"), '.sh'),
            "text/plain" : (self.__tr("Plain Text"), '.txt, .log, etc'),
            "text/html" : (self.__tr("HTML Dcoument"), '.htm, .html'),
            "image/gif" : (self.__tr("GIF Image"), '.gif'),
            "image/png" : (self.__tr("PNG Image"), '.png'),
            "image/jpeg" : (self.__tr("JPEG Image"), '.jpg, .jpeg'),
            "image/tiff" : (self.__tr("TIFF Image"), '.tif, .tiff'),
            "image/x-bitmap" : (self.__tr("Bitmap (BMP) Image"), '.bmp'),
            "image/x-bmp" : (self.__tr("Bitmap (BMP) Image"), '.bmp'),
            "image/x-photocd" : (self.__tr("Photo CD Image"), '.pcd'),
            "image/x-portable-anymap" : (self.__tr("Portable Image (PNM)"), '.pnm'),
            "image/x-portable-bitmap" : (self.__tr("Portable B&W Image (PBM)"), '.pbm'),
            "image/x-portable-graymap" : (self.__tr("Portable Grayscale Image (PGM)"), '.pgm'),
            "image/x-portable-pixmap" : (self.__tr("Portable Color Image (PPM)"), '.ppm'),
            "image/x-sgi-rgb" : (self.__tr("SGI RGB"), '.rgb'),
            "image/x-xbitmap" : (self.__tr("X11 Bitmap (XBM)"), '.xbm'),
            "image/x-xpixmap" : (self.__tr("X11 Pixmap (XPM)"), '.xpm'),
            "image/x-sun-raster" : (self.__tr("Sun Raster Format"), '.ras'),
        }

        # User settings
        self.user_settings = UserSettings()
        self.user_settings.load()
        self.user_settings.debug()
        #self.cur_printer = self.user_settings.last_used_printer

        self.initUi()

        QTimer.singleShot(0, self.updateSelectFaxPage)


    def initUi(self):
        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.BackButton, SIGNAL("clicked()"), self.BackButton_clicked)
        self.connect(self.NextButton, SIGNAL("clicked()"), self.NextButton_clicked)

        self.initSelectFaxPage()
        self.initCoverpagePage()
        self.initFilesPage()
        self.initRecipientsPage()
        self.initSendFaxPage()

        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('prog', '48x48')))
        
        self.StackedWidget.setCurrentIndex(0)


    #
    # Select Fax Page
    #

    def initSelectFaxPage(self):
        self.FaxComboBox.setType(PRINTERNAMECOMBOBOX_TYPE_FAX_ONLY)
        self.connect(self.FaxComboBox, SIGNAL("PrinterNameComboBox_currentChanged"), self.FaxComboBox_currentChanged)
        self.connect(self.FaxComboBox, SIGNAL("PrinterNameComboBox_noPrinters"), self.FaxComboBox_noPrinters)
        self.connect(self.FaxOptionsButton, SIGNAL("clicked()"), self.FaxOptionsButton_clicked)
        self.connect(self.FaxSetupButton, SIGNAL("clicked()"), self.FaxSetupButton_clicked)


    def updateSelectFaxPage(self):
        self.BackButton.setEnabled(False)
        self.updateStepText(PAGE_SELECT_FAX)
        self.FaxComboBox.updateUi()


    def FaxComboBox_currentChanged(self, device_uri, printer_name):
        print device_uri, printer_name
        self.printer_name = printer_name
        self.device_uri = device_uri


    def FaxComboBox_noPrinters(self):
        FailureUI(self, self.__tr("<b>No fax installed fax devices found.</b><p>Please setup a fax device and try again.</p><p>Click <i>OK</i> to exit.</p>"))
        self.close()


    def FaxOptionsButton_clicked(self):
        dlg = PrintSettingsDialog(self, self.printer_name, fax_mode=True)
        dlg.exec_()


    def FaxSetupButton_clicked(self):
        dlg = FaxSetupDialog(self, self.device_uri)
        dlg.exec_()

    #
    # Coverpage Page
    #

    def initCoverpagePage(self):
        pass

    def updateCoverpagePage(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.updateStepText(PAGE_COVERPAGE)
            self.BackButton.setEnabled(False)
        finally:
            QApplication.restoreOverrideCursor()


    # 
    # Files Page
    #

    def initFilesPage(self):
        self.FilesTable.setType(FILETABLE_TYPE_FAX)
        self.connect(self.FilesTable, SIGNAL("isEmpty"), self.FilesTable_isEmpty)
        self.connect(self.FilesTable, SIGNAL("isNotEmpty"), self.FilesTable_isNotEmpty)


    def updateFilesPage(self):
        self.FilesTable.updateUi(False)

        self.restoreNextButton()
        self.NextButton.setEnabled(self.FilesTable.isNotEmpty())
        self.BackButton.setEnabled(True)
        self.updateStepText(PAGE_FILES)


    def FilesTable_isEmpty(self):
        self.NextButton.setEnabled(False)


    def FilesTable_isNotEmpty(self):
        self.NextButton.setEnabled(True)


    #
    # Recipients Page
    #

    def initRecipientsPage(self):
        pass

    def updateRecipientsPage(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.updateStepText(PAGE_RECIPIENTS)
            self.restoreNextButton()

        finally:
            QApplication.restoreOverrideCursor()


    #
    # Send Fax Page
    #

    def initSendFaxPage(self):
        pass

    def updateSendFaxPage(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.updateStepText(PAGE_SEND_FAX)
            self.NextButton.setText(self.__tr("Send Fax"))

        finally:
            QApplication.restoreOverrideCursor()


    #
    # Fax
    #

    def executeSendFax(self):
        print "fax"


    #
    # Misc    
    #

    def CancelButton_clicked(self):
        self.close()

    def BackButton_clicked(self):
        p = self.StackedWidget.currentIndex()
        if p == PAGE_SELECT_FAX:
            log.error("Invalid!")

        elif p == PAGE_COVERPAGE:
            log.error("Invalid!")

        elif p == PAGE_FILES:
            self.StackedWidget.setCurrentIndex(PAGE_COVERPAGE)
            self.updateCoverpagePage()

        elif p == PAGE_RECIPIENTS:
            self.StackedWidget.setCurrentIndex(PAGE_FILES)
            self.updateFilesPage()

        elif p == PAGE_SEND_FAX:
            self.StackedWidget.setCurrentIndex(PAGE_RECIPIENTS)
            self.updateRecipientsPage()


    def NextButton_clicked(self):
        p = self.StackedWidget.currentIndex()
        if p == PAGE_SELECT_FAX:
            self.StackedWidget.setCurrentIndex(PAGE_COVERPAGE)
            self.updateCoverpagePage()

        elif p == PAGE_COVERPAGE:
            self.StackedWidget.setCurrentIndex(PAGE_FILES)
            self.updateFilesPage()

        elif p == PAGE_FILES:
            self.StackedWidget.setCurrentIndex(PAGE_RECIPIENTS)
            self.updateRecipientsPage()

        elif p == PAGE_RECIPIENTS:
            self.StackedWidget.setCurrentIndex(PAGE_SEND_FAX)
            self.updateSendFaxPage()

        elif p == PAGE_SEND_FAX:
            self.executeSendFax()


    def updateStepText(self, p):
        self.StepText.setText(self.__tr("Step %1 of %2").arg(p+1).arg(PAGE_MAX+1))


    def restoreNextButton(self):
        self.NextButton.setText(self.__tr("Next >"))


    def __tr(self,s,c = None):
        return qApp.translate("SendFaxDialog",s,c)


