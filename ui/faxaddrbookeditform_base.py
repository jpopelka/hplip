# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/dwelch/linux-imaging-and-printing/src/ui/faxaddrbookeditform_base.ui'
#
# Created: Mon May 9 13:35:55 2005
#      by: The PyQt User Interface Compiler (pyuic) 3.14.1
#
# WARNING! All changes made in this file will be lost!


import sys
from qt import *


class FaxAddrBookEditForm_base(QDialog):
    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        QDialog.__init__(self,parent,name,modal,fl)

        if not name:
            self.setName("FaxAddrBookEditForm_base")


        FaxAddrBookEditForm_baseLayout = QGridLayout(self,1,1,11,6,"FaxAddrBookEditForm_baseLayout")

        self.groupListView = QListView(self,"groupListView")
        self.groupListView.addColumn(self.__tr("Group Name"))
        self.groupListView.setSelectionMode(QListView.NoSelection)

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.groupListView,5,6,2,2)

        self.notesEdit = QTextEdit(self,"notesEdit")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.notesEdit,11,11,0,4)

        self.lastnameEdit = QLineEdit(self,"lastnameEdit")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.lastnameEdit,4,4,2,4)

        self.pushButton34 = QPushButton(self,"pushButton34")

        FaxAddrBookEditForm_baseLayout.addWidget(self.pushButton34,12,3)

        self.firstnameEdit = QLineEdit(self,"firstnameEdit")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.firstnameEdit,3,3,2,4)

        self.line5 = QFrame(self,"line5")
        self.line5.setFrameShape(QFrame.HLine)
        self.line5.setFrameShadow(QFrame.Sunken)
        self.line5.setFrameShape(QFrame.HLine)

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.line5,9,9,0,4)

        self.OKButton = QPushButton(self,"OKButton")
        self.OKButton.setEnabled(0)

        FaxAddrBookEditForm_baseLayout.addWidget(self.OKButton,12,4)

        self.textLabel1 = QLabel(self,"textLabel1")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.textLabel1,3,3,0,1)
        spacer34 = QSpacerItem(20,61,QSizePolicy.Minimum,QSizePolicy.Expanding)
        FaxAddrBookEditForm_baseLayout.addItem(spacer34,5,3)

        self.titleEdit = QLineEdit(self,"titleEdit")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.titleEdit,2,2,2,4)

        self.groupsButton2 = QPushButton(self,"groupsButton2")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.groupsButton2,6,6,3,4)

        self.textLabel4 = QLabel(self,"textLabel4")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.textLabel4,5,6,0,1)

        self.textLabel2 = QLabel(self,"textLabel2")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.textLabel2,4,4,0,1)

        self.textLabel7 = QLabel(self,"textLabel7")

        FaxAddrBookEditForm_baseLayout.addWidget(self.textLabel7,8,0)

        self.textLabel6 = QLabel(self,"textLabel6")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.textLabel6,10,10,0,4)

        self.textLabel5 = QLabel(self,"textLabel5")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.textLabel5,2,2,0,1)
        spacer31 = QSpacerItem(401,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        FaxAddrBookEditForm_baseLayout.addMultiCell(spacer31,12,12,0,2)

        self.textLabel3 = QLabel(self,"textLabel3")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.textLabel3,0,0,0,1)

        self.nicknameEdit = QLineEdit(self,"nicknameEdit")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.nicknameEdit,0,0,2,4)

        self.line12 = QFrame(self,"line12")
        self.line12.setFrameShape(QFrame.HLine)
        self.line12.setFrameShadow(QFrame.Sunken)
        self.line12.setFrameShape(QFrame.HLine)

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.line12,1,1,0,4)

        self.faxEdit = QLineEdit(self,"faxEdit")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.faxEdit,8,8,1,4)

        self.line5_2 = QFrame(self,"line5_2")
        self.line5_2.setFrameShape(QFrame.HLine)
        self.line5_2.setFrameShadow(QFrame.Sunken)
        self.line5_2.setFrameShape(QFrame.HLine)

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.line5_2,7,7,0,4)

        self.line5_2_2 = QFrame(self,"line5_2_2")
        self.line5_2_2.setFrameShape(QFrame.HLine)
        self.line5_2_2.setFrameShadow(QFrame.Sunken)
        self.line5_2_2.setFrameShape(QFrame.HLine)

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.line5_2_2,13,13,0,4)

        self.textLabel12 = QLabel(self,"textLabel12")

        FaxAddrBookEditForm_baseLayout.addMultiCellWidget(self.textLabel12,14,14,0,4)

        self.languageChange()

        self.resize(QSize(479,551).expandedTo(self.minimumSizeHint()))
        self.clearWState(Qt.WState_Polished)

        self.connect(self.pushButton34,SIGNAL("clicked()"),self.reject)
        self.connect(self.OKButton,SIGNAL("clicked()"),self.accept)
        self.connect(self.firstnameEdit,SIGNAL("textChanged(const QString&)"),self.firstnameEdit_textChanged)
        self.connect(self.lastnameEdit,SIGNAL("textChanged(const QString&)"),self.lastnameEdit_textChanged)
        self.connect(self.groupsButton2,SIGNAL("clicked()"),self.groupsButton2_clicked)
        self.connect(self.nicknameEdit,SIGNAL("textChanged(const QString&)"),self.nicknameEdit_textChanged)
        self.connect(self.faxEdit,SIGNAL("textChanged(const QString&)"),self.faxEdit_textChanged)

        self.setTabOrder(self.nicknameEdit,self.titleEdit)
        self.setTabOrder(self.titleEdit,self.firstnameEdit)
        self.setTabOrder(self.firstnameEdit,self.lastnameEdit)
        self.setTabOrder(self.lastnameEdit,self.faxEdit)
        self.setTabOrder(self.faxEdit,self.notesEdit)
        self.setTabOrder(self.notesEdit,self.pushButton34)
        self.setTabOrder(self.pushButton34,self.OKButton)


    def languageChange(self):
        self.setCaption(self.__tr("HP Device Manager - Fax Address Book Entry"))
        self.groupListView.header().setLabel(0,self.__tr("Group Name"))
        self.pushButton34.setText(self.__tr("Cancel"))
        self.OKButton.setText(self.__tr("OK"))
        self.textLabel1.setText(self.__tr("First Name:"))
        self.groupsButton2.setText(self.__tr("New Group..."))
        self.textLabel4.setText(self.__tr("Member of Group(s):"))
        self.textLabel2.setText(self.__tr("Last Name:"))
        self.textLabel7.setText(self.__tr("<b>Fax Number:</b>"))
        self.textLabel6.setText(self.__tr("Notes/Other Information:"))
        self.textLabel5.setText(self.__tr("Title:"))
        self.textLabel3.setText(self.__tr("<b>Nickname:</b>"))
        self.textLabel12.setText(self.__tr("Note: Items in <b>bold</b> are required fields."))


    def firstnameEdit_textChanged(self,a0):
        print "FaxAddrBookEditForm_base.firstnameEdit_textChanged(const QString&): Not implemented yet"

    def lastnameEdit_textChanged(self,a0):
        print "FaxAddrBookEditForm_base.lastnameEdit_textChanged(const QString&): Not implemented yet"

    def checkBox3_toggled(self,a0):
        print "FaxAddrBookEditForm_base.checkBox3_toggled(bool): Not implemented yet"

    def isGroupCheckBox_toggled(self,a0):
        print "FaxAddrBookEditForm_base.isGroupCheckBox_toggled(bool): Not implemented yet"

    def groupsButton2_clicked(self):
        print "FaxAddrBookEditForm_base.groupsButton2_clicked(): Not implemented yet"

    def nicknameEdit_textChanged(self,a0):
        print "FaxAddrBookEditForm_base.nicknameEdit_textChanged(const QString&): Not implemented yet"

    def faxEdit_textChanged(self,a0):
        print "FaxAddrBookEditForm_base.faxEdit_textChanged(const QString&): Not implemented yet"

    def __tr(self,s,c = None):
        return qApp.translate("FaxAddrBookEditForm_base",s,c)

if __name__ == "__main__":
    a = QApplication(sys.argv)
    QObject.connect(a,SIGNAL("lastWindowClosed()"),a,SLOT("quit()"))
    w = FaxAddrBookEditForm_base()
    a.setMainWidget(w)
    w.show()
    a.exec_loop()
