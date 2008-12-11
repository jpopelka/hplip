# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui4/cleandialog_base.ui'
#
# Created: Thu Oct 30 15:47:06 2008
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

        self.LoadPaper = LoadPaperGroupBox(Dialog)
        self.LoadPaper.setObjectName("LoadPaper")
        self.gridlayout.addWidget(self.LoadPaper,3,0,1,3)

        self.frame = QtGui.QFrame(Dialog)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")

        self.gridlayout1 = QtGui.QGridLayout(self.frame)
        self.gridlayout1.setObjectName("gridlayout1")

        self.Prompt = QtGui.QLabel(self.frame)
        self.Prompt.setTextFormat(QtCore.Qt.RichText)
        self.Prompt.setWordWrap(True)
        self.Prompt.setObjectName("Prompt")
        self.gridlayout1.addWidget(self.Prompt,0,0,1,1)
        self.gridlayout.addWidget(self.frame,4,0,1,3)

        spacerItem = QtGui.QSpacerItem(571,71,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.gridlayout.addItem(spacerItem,5,0,1,3)

        spacerItem1 = QtGui.QSpacerItem(361,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem1,6,0,1,1)

        self.CleanButton = QtGui.QPushButton(Dialog)
        self.CleanButton.setObjectName("CleanButton")
        self.gridlayout.addWidget(self.CleanButton,6,1,1,1)

        self.CancelButton = QtGui.QPushButton(Dialog)
        self.CancelButton.setObjectName("CancelButton")
        self.gridlayout.addWidget(self.CancelButton,6,2,1,1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "HP Device Manager - Clean Print Cartridges", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Clean Print Cartridges", None, QtGui.QApplication.UnicodeUTF8))
        self.Prompt.setText(QtGui.QApplication.translate("Dialog", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:\'DejaVu Sans\'; font-size:10pt;\">Click<span style=\" font-style:italic;\"> Clean</span> to begin the level %1 cleaning process.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.CleanButton.setText(QtGui.QApplication.translate("Dialog", "Clean", None, QtGui.QApplication.UnicodeUTF8))
        self.CancelButton.setText(QtGui.QApplication.translate("Dialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))

from loadpapergroupbox import LoadPaperGroupBox
from deviceuricombobox import DeviceUriComboBox
