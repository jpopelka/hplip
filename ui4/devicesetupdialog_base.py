# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui4/devicesetupdialog_base.ui'
#
# Created: Thu Oct 30 15:47:07 2008
#      by: PyQt4 UI code generator 4.3.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(QtCore.QSize(QtCore.QRect(0,0,600,500).size()).expandedTo(Dialog.minimumSizeHint()))

        self.gridlayout = QtGui.QGridLayout(Dialog)
        self.gridlayout.setObjectName("gridlayout")

        self.label = QtGui.QLabel(Dialog)

        font = QtGui.QFont()
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.gridlayout.addWidget(self.label,0,0,1,1)

        self.line = QtGui.QFrame(Dialog)
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName("line")
        self.gridlayout.addWidget(self.line,1,0,1,3)

        self.DeviceComboBox = DeviceUriComboBox(Dialog)
        self.DeviceComboBox.setObjectName("DeviceComboBox")
        self.gridlayout.addWidget(self.DeviceComboBox,2,0,1,3)

        spacerItem = QtGui.QSpacerItem(20,301,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.gridlayout.addItem(spacerItem,3,0,1,1)

        spacerItem1 = QtGui.QSpacerItem(361,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem1,4,0,1,1)

        self.ApplyButton = QtGui.QPushButton(Dialog)
        self.ApplyButton.setObjectName("ApplyButton")
        self.gridlayout.addWidget(self.ApplyButton,4,1,1,1)

        self.CancelButton = QtGui.QPushButton(Dialog)
        self.CancelButton.setObjectName("CancelButton")
        self.gridlayout.addWidget(self.CancelButton,4,2,1,1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "HP Device Manager - Device Setup", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Device Setup", None, QtGui.QApplication.UnicodeUTF8))
        self.ApplyButton.setText(QtGui.QApplication.translate("Dialog", "Apply", None, QtGui.QApplication.UnicodeUTF8))
        self.CancelButton.setText(QtGui.QApplication.translate("Dialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))

from deviceuricombobox import DeviceUriComboBox
