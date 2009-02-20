# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui4/mimetypesdialog_base.ui'
#
# Created: Tue Feb 17 11:36:13 2009
#      by: PyQt4 UI code generator 4.3.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MimeTypesDialog_base(object):
    def setupUi(self, MimeTypesDialog_base):
        MimeTypesDialog_base.setObjectName("MimeTypesDialog_base")
        MimeTypesDialog_base.resize(QtCore.QSize(QtCore.QRect(0,0,500,540).size()).expandedTo(MimeTypesDialog_base.minimumSizeHint()))

        self.gridlayout = QtGui.QGridLayout(MimeTypesDialog_base)
        self.gridlayout.setObjectName("gridlayout")

        self.textLabel3_2 = QtGui.QLabel(MimeTypesDialog_base)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textLabel3_2.sizePolicy().hasHeightForWidth())
        self.textLabel3_2.setSizePolicy(sizePolicy)
        self.textLabel3_2.setWordWrap(False)
        self.textLabel3_2.setObjectName("textLabel3_2")
        self.gridlayout.addWidget(self.textLabel3_2,0,0,1,2)

        self.line1_2 = QtGui.QFrame(MimeTypesDialog_base)
        self.line1_2.setFrameShape(QtGui.QFrame.HLine)
        self.line1_2.setFrameShadow(QtGui.QFrame.Sunken)
        self.line1_2.setObjectName("line1_2")
        self.gridlayout.addWidget(self.line1_2,1,0,1,2)

        self.TypesTableWidget = QtGui.QTableWidget(MimeTypesDialog_base)
        self.TypesTableWidget.setAlternatingRowColors(True)
        self.TypesTableWidget.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.TypesTableWidget.setObjectName("TypesTableWidget")
        self.gridlayout.addWidget(self.TypesTableWidget,2,0,1,2)

        self.textLabel1 = QtGui.QLabel(MimeTypesDialog_base)
        self.textLabel1.setWordWrap(True)
        self.textLabel1.setObjectName("textLabel1")
        self.gridlayout.addWidget(self.textLabel1,3,0,1,2)

        spacerItem = QtGui.QSpacerItem(301,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem,4,0,1,1)

        self.pushButton10 = QtGui.QPushButton(MimeTypesDialog_base)
        self.pushButton10.setObjectName("pushButton10")
        self.gridlayout.addWidget(self.pushButton10,4,1,1,1)

        self.retranslateUi(MimeTypesDialog_base)
        QtCore.QObject.connect(self.pushButton10,QtCore.SIGNAL("clicked()"),MimeTypesDialog_base.accept)
        QtCore.QMetaObject.connectSlotsByName(MimeTypesDialog_base)

    def retranslateUi(self, MimeTypesDialog_base):
        MimeTypesDialog_base.setWindowTitle(QtGui.QApplication.translate("MimeTypesDialog_base", "HP Device Manager - MIME Types", None, QtGui.QApplication.UnicodeUTF8))
        self.textLabel3_2.setText(QtGui.QApplication.translate("MimeTypesDialog_base", "<b>File/document types that can be added to the file list.</b>", None, QtGui.QApplication.UnicodeUTF8))
        self.TypesTableWidget.clear()
        self.TypesTableWidget.setColumnCount(3)
        self.TypesTableWidget.setRowCount(0)

        headerItem = QtGui.QTableWidgetItem()
        headerItem.setText(QtGui.QApplication.translate("MimeTypesDialog_base", "MIME Type", None, QtGui.QApplication.UnicodeUTF8))
        self.TypesTableWidget.setHorizontalHeaderItem(0,headerItem)

        headerItem1 = QtGui.QTableWidgetItem()
        headerItem1.setText(QtGui.QApplication.translate("MimeTypesDialog_base", "Description", None, QtGui.QApplication.UnicodeUTF8))
        self.TypesTableWidget.setHorizontalHeaderItem(1,headerItem1)

        headerItem2 = QtGui.QTableWidgetItem()
        headerItem2.setText(QtGui.QApplication.translate("MimeTypesDialog_base", "Usual File Extension(s)", None, QtGui.QApplication.UnicodeUTF8))
        self.TypesTableWidget.setHorizontalHeaderItem(2,headerItem2)
        self.textLabel1.setText(QtGui.QApplication.translate("MimeTypesDialog_base", "<i>Note: To print or fax file/document types that do not appear on this list, print the document from the application that created it through the appropriate CUPS printer.</i>", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButton10.setText(QtGui.QApplication.translate("MimeTypesDialog_base", "OK", None, QtGui.QApplication.UnicodeUTF8))

