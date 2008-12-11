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


# Std Lib
import sys
import os.path
import os

# Local
from base.g import *
from base import utils, magic
from prnt import cups
from base.codes import *
from ui_utils import *

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

FILETABLE_TYPE_PRINT = 0
FILETABLE_TYPE_FAX = 1

class FileTable(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.working_dir = os.path.expanduser('~')
        self.initUi()
        self.file_list = []
        self.typ = FILETABLE_TYPE_PRINT
        self.selected_filename = None
        
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
        
        
    def initUi(self):
        self.gridlayout = QGridLayout(self)
        self.gridlayout.setObjectName("gridlayout")
        self.FileTable = QTableWidget(self)
        self.FileTable.setObjectName("FileTable")
        self.gridlayout.addWidget(self.FileTable,0,0,1,6)
        self.AddFileButton = QPushButton(self)
        self.AddFileButton.setObjectName("AddFileButton")
        self.gridlayout.addWidget(self.AddFileButton,1,0,1,1)
        self.RemoveFileButton = QPushButton(self)
        self.RemoveFileButton.setObjectName("RemoveFileButton")
        self.gridlayout.addWidget(self.RemoveFileButton,1,1,1,1)
        self.MoveFileUpButton = QPushButton(self)
        self.MoveFileUpButton.setObjectName("MoveFileUpButton")
        self.gridlayout.addWidget(self.MoveFileUpButton,1,2,1,1)
        self.MoveFileDownButton = QPushButton(self)
        self.MoveFileDownButton.setObjectName("MoveFileDownButton")
        self.gridlayout.addWidget(self.MoveFileDownButton,1,3,1,1)
        spacerItem = QSpacerItem(91,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem,1,4,1,1)
        self.ShowTypesButton = QPushButton(self)
        self.ShowTypesButton.setObjectName("ShowTypesButton")
        self.gridlayout.addWidget(self.ShowTypesButton,1,5,1,1) 
        self.AddFileButton.setText(self.__tr("Add..."))
        self.AddFileButton.setIcon(QIcon(load_pixmap('list_add', '16x16')))
        self.connect(self.AddFileButton, SIGNAL("clicked()"), self.AddFileButton_clicked)
        self.RemoveFileButton.setIcon(QIcon(load_pixmap('list_remove-disabled', '16x16')))
        self.RemoveFileButton.setText(self.__tr("Remove"))
        self.connect(self.RemoveFileButton, SIGNAL("clicked()"), self.RemoveFileButton_clicked)
        self.MoveFileUpButton.setText(self.__tr("Move Up"))
        self.MoveFileUpButton.setIcon(QIcon(load_pixmap('up-disabled', '16x16')))
        self.connect(self.MoveFileUpButton, SIGNAL("clicked()"), self.MoveFileUpButton_clicked)
        self.MoveFileDownButton.setText(self.__tr("Move Down"))
        self.MoveFileDownButton.setIcon(QIcon(load_pixmap('down-disabled', '16x16')))
        self.connect(self.MoveFileDownButton, SIGNAL("clicked()"), self.MoveFileDownButton_clicked)
        self.ShowTypesButton.setText(self.__tr("Show Valid Types..."))
        self.ShowTypesButton.setIcon(QIcon(load_pixmap('mimetypes', '16x16')))
        self.connect(self.ShowTypesButton, SIGNAL("clicked()"), self.ShowTypesButton_clicked)
        self.FileTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.connect(self.FileTable, SIGNAL("customContextMenuRequested(const QPoint &)"), 
            self.FileTable_customContextMenuRequested)
            
        self.headers = [self.__tr("Name"), self.__tr("Type"), self.__tr("Folder/Path")]
        self.FileTable.setSortingEnabled(False)
        self.connect(self.FileTable, SIGNAL("itemSelectionChanged()"), self.FileTable_itemSelectionChanged)
        
        
    def setWorkingDir(self, d):
        if os.path.exists(d):
            self.working_dir = d
            
            
    def getWorkingDir(self):
        if self.file_list:
            self.working_dir = os.path.pathname(self.file_list[-1])
        return self.working_dir
        
        
    def setType(self, t):
        self.typ = t
        
        
    def isNotEmpty(self):
        return len(self.file_list)
        
        
    def FileTable_itemSelectionChanged(self):
        self.selected_filename = self.currentFilename()
        print self.selected_filename

            
    def updateUi(self, show_add_file_if_empty=True):
        self.FileTable.clear()
        self.FileTable.setRowCount(len(self.file_list))
        self.FileTable.setColumnCount(0)
        
        if self.file_list:
            self.emit(SIGNAL("isNotEmpty"))
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            try:
                selected = None
                self.FileTable.setColumnCount(len(self.headers))
                self.FileTable.setHorizontalHeaderLabels(self.headers)
                flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
                
                for row, f in enumerate(self.file_list):
                    filename, mime_type, mime_type_desc = f
                    
                    # Filename (basename)
                    i = QTableWidgetItem(os.path.basename(filename))
                    i.setData(Qt.UserRole, QVariant(filename))
                    i.setFlags(flags)
                    
                    if self.selected_filename is not None and \
                        self.selected_filename == filename:
                        selected = i
                    
                    self.FileTable.setItem(row, 0, i)
                    
                    # MIME type
                    i = QTableWidgetItem(mime_type_desc)
                    i.setFlags(flags)
                    self.FileTable.setItem(row, 1, i)
                    
                    # path/folder
                    i = QTableWidgetItem(os.path.dirname(filename))
                    i.setFlags(flags)
                    self.FileTable.setItem(row, 2, i)
                    
                self.FileTable.resizeColumnsToContents()
                
                if selected is None:
                    selected = self.FileTable.item(0, 0)
                    
                selected.setSelected(True)
                self.FileTable.setCurrentItem(selected)
            
            finally:
                QApplication.restoreOverrideCursor()
                
            self.RemoveFileButton.setEnabled(True)
            i = self.FileTable.currentRow()
            self.MoveFileDownButton.setEnabled(len(self.file_list) > 1 and i != len(self.file_list)-1)
            self.MoveFileUpButton.setEnabled(len(self.file_list) > 1 and i != 0)
            
        
        else:
            self.emit(SIGNAL("isEmpty"))
            self.RemoveFileButton.setEnabled(False)
            self.MoveFileDownButton.setEnabled(False)
            self.MoveFileUpButton.setEnabled(False)
            
            if show_add_file_if_empty:
                self.AddFileButton_clicked()


    def AddFileButton_clicked(self):
        if self.typ == FILETABLE_TYPE_PRINT:
            s = self.__tr("Select File(s) to Print")
        else:
            s = self.__tr("Select File(s) to Send")
        
        files = list(QFileDialog.getOpenFileNames(self, s, 
            self.working_dir, self.__tr("All files (*)")))
        
        for f in files:
            self.addFile(unicode(f))
        
        self.updateUi(False)
        
            
    def addFile(self, f):
        log.debug("Trying to add file: %s" % f)
        if os.path.exists(f) and os.access(f, os.R_OK):
            
            mime_type = magic.mime_type(f)
            mime_type_desc = mime_type
            log.debug("File type of file %s: %s" % (f, mime_type))
            
            try:
                mime_type_desc = self.MIME_TYPES_DESC[mime_type][0]
            except KeyError:
                if self.typ == FILETABLE_TYPE_PRINT:
                    FailureUI(self, self.__tr("<b>You are trying to add a file '%1' that cannot be directly printed with this utility.</b><p>To print this file, use the print command in the application that created it.<p>Note: Click <i>Show Valid Types...</i> to view a list of compatible file types that can be directly printed from this utility.").arg(f), 
                        self.__tr("HP Device Manager"))
                else:
                    FailureUI(self, self.__tr("<b>You are trying to add a file '%1' that cannot be directly faxed with this utility.</b><p>To fax this file, use the print command in the application that created it (using the appropriate fax print queue).<p>Note: Click <i>Show Valid Types...</i> to view a list of compatible file types that can be directly added to the fax file list in this utility.").arg(f), 
                        self.__tr("HP Device Manager"))
            else:
                log.debug("Adding file %s (%s,%s)" % (f, mime_type, mime_type_desc))
                self.file_list.append((f, mime_type, mime_type_desc))
        else:
            FailureUI(self, self.__tr("<b>Unable to add file '%1' to file list (file not found or insufficient permissions).</b><p>Check the file name and try again.").arg(f), 
                self.__tr("HP Device Manager"))
        
        
    def currentFilename(self):
        i = self.FileTable.item(self.FileTable.currentRow(), 0)
        if i is None:
            return None
        return i.data(Qt.UserRole).toString()
        
        
    def RemoveFileButton_clicked(self):
        filename = self.currentFilename()
        if filename is None:
            return
        
        temp = self.file_list[:]
        index = 0
        for f, mime_type, mime_type_desc in temp:
            if f == filename:
                del self.file_list[index]
                self.updateUi(False)
                break
            index += 1
            
        
    def ShowTypesButton_clicked(self):
        print "show"
        
        
    def MoveFileUpButton_clicked(self):
        filename = self.currentFilename()
        if filename is None:
            return
        
        utils.list_move_up(self.file_list, filename, self.__compareFilenames)
        self.updateUi()


    def MoveFileDownButton_clicked(self):
        filename = self.currentFilename()
        if filename is None:
            return

        utils.list_move_down(self.file_list, filename, self.__compareFilenames)
        self.updateUi()
        
        
    def __compareFilenames(self, a, b):
        return a[0] == b
        

    def FileTable_customContextMenuRequested(self, p):
        print p
            
                
    def __tr(self,s,c = None):
        return qApp.translate("FileTable",s,c)
    
        
    
