# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui4/systrayframe_base.ui'
#
# Created: Mon Dec 15 16:59:01 2008
#      by: PyQt4 UI code generator 4.3.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(QtCore.QSize(QtCore.QRect(0,0,500,540).size()).expandedTo(Dialog.minimumSizeHint()))

        self.gridlayout = QtGui.QGridLayout(Dialog)
        self.gridlayout.setObjectName("gridlayout")

        self.frame = QtGui.QFrame(Dialog)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")

        self.gridlayout1 = QtGui.QGridLayout(self.frame)
        self.gridlayout1.setObjectName("gridlayout1")

        self.groupBox_2 = QtGui.QGroupBox(self.frame)
        self.groupBox_2.setObjectName("groupBox_2")

        self.gridlayout2 = QtGui.QGridLayout(self.groupBox_2)
        self.gridlayout2.setObjectName("gridlayout2")

        self.radioButton = QtGui.QRadioButton(self.groupBox_2)
        self.radioButton.setObjectName("radioButton")
        self.gridlayout2.addWidget(self.radioButton,0,0,1,1)

        self.radioButton_2 = QtGui.QRadioButton(self.groupBox_2)
        self.radioButton_2.setObjectName("radioButton_2")
        self.gridlayout2.addWidget(self.radioButton_2,1,0,1,1)

        self.radioButton_3 = QtGui.QRadioButton(self.groupBox_2)
        self.radioButton_3.setObjectName("radioButton_3")
        self.gridlayout2.addWidget(self.radioButton_3,2,0,1,1)
        self.gridlayout1.addWidget(self.groupBox_2,0,0,1,1)

        self.groupBox = QtGui.QGroupBox(self.frame)
        self.groupBox.setCheckable(True)
        self.groupBox.setObjectName("groupBox")

        self.gridlayout3 = QtGui.QGridLayout(self.groupBox)
        self.gridlayout3.setObjectName("gridlayout3")

        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.gridlayout3.addWidget(self.label,0,0,1,1)

        self.listWidget = QtGui.QListWidget(self.groupBox)
        self.listWidget.setObjectName("listWidget")
        self.gridlayout3.addWidget(self.listWidget,1,0,1,1)
        self.gridlayout1.addWidget(self.groupBox,1,0,1,1)
        self.gridlayout.addWidget(self.frame,0,0,1,1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Dialog", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_2.setTitle(QtGui.QApplication.translate("Dialog", "System tray icon visibility", None, QtGui.QApplication.UnicodeUTF8))
        self.radioButton.setText(QtGui.QApplication.translate("Dialog", "Always show", None, QtGui.QApplication.UnicodeUTF8))
        self.radioButton_2.setText(QtGui.QApplication.translate("Dialog", "Hide when inactive", None, QtGui.QApplication.UnicodeUTF8))
        self.radioButton_3.setText(QtGui.QApplication.translate("Dialog", "Always hide", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("Dialog", "Monitor button presses on devices", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Devices to Monitor:", None, QtGui.QApplication.UnicodeUTF8))

