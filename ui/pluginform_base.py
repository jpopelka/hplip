# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/pluginform_base.ui'
#
# Created: Fri Sep 21 09:24:18 2007
#      by: The PyQt User Interface Compiler (pyuic) 3.17
#
# WARNING! All changes made in this file will be lost!


from qt import *


class PluginForm_base(QWizard):
    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        QWizard.__init__(self,parent,name,modal,fl)

        if not name:
            self.setName("PluginForm_base")



        self.SourcePage = QWidget(self,"SourcePage")
        SourcePageLayout = QGridLayout(self.SourcePage,1,1,11,6,"SourcePageLayout")

        self.textLabel1 = QLabel(self.SourcePage,"textLabel1")
        self.textLabel1.setAlignment(QLabel.WordBreak | QLabel.AlignVCenter)

        SourcePageLayout.addWidget(self.textLabel1,0,0)
        spacer9 = QSpacerItem(20,60,QSizePolicy.Minimum,QSizePolicy.Expanding)
        SourcePageLayout.addItem(spacer9,3,0)

        self.sourceGroup = QButtonGroup(self.SourcePage,"sourceGroup")
        self.sourceGroup.setColumnLayout(0,Qt.Vertical)
        self.sourceGroup.layout().setSpacing(6)
        self.sourceGroup.layout().setMargin(11)
        sourceGroupLayout = QGridLayout(self.sourceGroup.layout())
        sourceGroupLayout.setAlignment(Qt.AlignTop)

        self.radioButton5 = QRadioButton(self.sourceGroup,"radioButton5")
        self.sourceGroup.insert( self.radioButton5,1)

        sourceGroupLayout.addWidget(self.radioButton5,1,0)

        self.pathLineEdit = QLineEdit(self.sourceGroup,"pathLineEdit")
        self.pathLineEdit.setEnabled(0)

        sourceGroupLayout.addWidget(self.pathLineEdit,2,0)

        self.browsePushButton = QPushButton(self.sourceGroup,"browsePushButton")
        self.browsePushButton.setEnabled(0)

        sourceGroupLayout.addWidget(self.browsePushButton,2,1)

        self.radioButton4 = QRadioButton(self.sourceGroup,"radioButton4")
        self.radioButton4.setChecked(1)
        self.sourceGroup.insert( self.radioButton4,0)

        sourceGroupLayout.addWidget(self.radioButton4,0,0)

        SourcePageLayout.addWidget(self.sourceGroup,2,0)
        spacer2 = QSpacerItem(20,21,QSizePolicy.Minimum,QSizePolicy.Expanding)
        SourcePageLayout.addItem(spacer2,1,0)
        self.addPage(self.SourcePage,QString(""))

        self.InstallPage = QWidget(self,"InstallPage")
        InstallPageLayout = QGridLayout(self.InstallPage,1,1,11,6,"InstallPageLayout")

        self.installPushButton = QPushButton(self.InstallPage,"installPushButton")

        InstallPageLayout.addWidget(self.installPushButton,2,0)

        self.textLabel2 = QLabel(self.InstallPage,"textLabel2")

        InstallPageLayout.addWidget(self.textLabel2,1,0)

        self.licenseTextEdit = QTextEdit(self.InstallPage,"licenseTextEdit")
        self.licenseTextEdit.setWordWrap(QTextEdit.WidgetWidth)
        self.licenseTextEdit.setReadOnly(1)

        InstallPageLayout.addWidget(self.licenseTextEdit,0,0)
        self.addPage(self.InstallPage,QString(""))

        self.languageChange()

        self.resize(QSize(597,398).expandedTo(self.minimumSizeHint()))
        self.clearWState(Qt.WState_Polished)

        self.connect(self.sourceGroup,SIGNAL("clicked(int)"),self.sourceGroup_clicked)
        self.connect(self.browsePushButton,SIGNAL("clicked()"),self.browsePushButton_clicked)
        self.connect(self.pathLineEdit,SIGNAL("textChanged(const QString&)"),self.pathLineEdit_textChanged)
        self.connect(self.installPushButton,SIGNAL("clicked()"),self.installPushButton_clicked)


    def languageChange(self):
        self.setCaption(self.__tr("HP Device Manager - Plug-in Installer"))
        self.textLabel1.setText(self.__tr("An additional driver plug-in is required to operate this printer. You may download the plug-in directly from an HP authorized server, or, if you already have a copy of the file, you can specify a path to the file."))
        self.sourceGroup.setTitle(self.__tr("Plug-in Source"))
        self.radioButton5.setText(self.__tr("Use an exisiting copy of the plug-in file (advanced):"))
        self.browsePushButton.setText(self.__tr("Browse..."))
        self.radioButton4.setText(self.__tr("Download the plug-in from an HP authorized server (recommended)"))
        self.setTitle(self.SourcePage,self.__tr("Driver Plug-in Required"))
        self.installPushButton.setText(QString.null)
        self.textLabel2.setText(self.__tr("By installing the driver plug-in, you are agreeing to this license agreement."))
        self.licenseTextEdit.setText(self.__tr("<b>LICENSE TERMS FOR HP Linux Imaging and Printing (HPLIP) Driver Plug-in</b>\n"
"<p>\n"
"These License Terms govern your Use of the HPLIP Driver Plug-in Software (the \"Software\"). USE OF THE SOFTWARE INCLUDING, WITHOUT LIMITATION, ANY DOCUMENTATION, IS SUBJECT TO THESE LICENSE TERMS AND THE APPLICABLE AS-IS WARRANTY STATEMENT.  BY DOWNLOADING AND INSTALLING THE SOFTWARE, YOU ARE AGREEING TO BE BOUND BY THESE TERMS. IF YOU DO NOT AGREE TO ALL OF THESE TERMS, DO NOT DOWNLOAD AND INSTALL THE SOFTWARE ON YOUR SYSTEM.\n"
"<p>\n"
"<b>1. License Grant.</b>    HP grants you a license to Use one copy of the Software with HP printing products only.  \"Use\" includes using, storing, loading, installing, executing, and displaying the Software.  You may not modify the Software or disable any licensing or control features of the Software.\n"
"<p>\n"
"<b>2. Ownership.</b>   The Software is owned and copyrighted by HP or its third party suppliers.  Your license confers no title to, or ownership in, the Software and is not a sale of any rights in the Software.  HP's third party suppliers may protect their rights in the Software in the event of any violation of these license terms.\n"
"<p>\n"
"<b>3. Copies and Adaptations.</b>   You may only make copies or adaptations of the Software for archival purposes or when copying or adaptation is an essential step in the authorized Use of the Software. You must reproduce all copyright notices in the original Software on all copies or adaptations. You may not copy the Software onto any public network.\n"
"<p>\n"
"<b>4. No Disassembly.</b>   You may not Disassemble the Software unless HP's prior written consent is obtained.  \"Disassemble\" includes disassembling, decompiling, decrypting, and reverse engineering.   In some jurisdictions, HP's consent may not be required for limited Disassembly.  Upon request, you will provide HP with reasonably detailed information regarding any Disassembly.\n"
"<p>\n"
"<b>5. No Transfer.</b>   You may not assign, sublicense or otherwise transfer all or any part of these License Terms or the Software.\n"
"<p>\n"
"<b>6. Termination.</b>   HP may terminate your license, upon notice, for failure to comply with any of these License Terms.  Upon termination, you must immediately destroy the Software, together with all copies, adaptations and merged portions in any form.\n"
"<p>\n"
"<b>7. Export Requirements.</b>   You may not export or re-export the Software or any copy or adaptation in violation of any applicable laws or regulations.\n"
"<p>\n"
"<b>8. U.S. Government Restricted Rights.</b>   The Software has been developed entirely at private expense.  It is delivered and licensed, as defined in any applicable DFARS, FARS, or other equivalent federal agency regulation or contract clause, as either \"commercial computer software\" or \"restricted computer software\", whichever is applicable.  You have only those rights provided for such Software by the applicable clause or regulation or by these License Terms.\n"
"<p>\n"
"<b>9. DISCLAIMER OF WARRANTIES.</b>   TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, HP AND ITS SUPPLIERS PROVIDE THE SOFTWARE \"AS IS\" AND WITH ALL FAULTS, AND HEREBY DISCLAIM ALL OTHER WARRANTIES AND CONDITIONS, EITHER EXPRESS, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, WARRANTIES OF TITLE AND NON-INFRINGEMENT, ANY IMPLIED WARRANTIES, DUTIES OR CONDITIONS OF MERCHANTABILITY, OF FITNESS FOR A PARTICULAR PURPOSE, AND OF LACK OF VIRUSES ALL WITH REGARD TO THE SOFTWARE.  Some states/jurisdictions do not allow exclusion of implied warranties or limitations on the duration of implied warranties, so the above disclaimer may not apply to you in its entirety.\n"
"<p>\n"
"<b>10. LIMITATION OF LIABILITY.</b>  Notwithstanding any damages that you might incur, the entire liability of HP and any of its suppliers under any provision of this agreement and your exclusive remedy for all of the foregoing shall be limited to the greater of the amount actually paid by you separately for the Software or U.S. $5.00.  TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL HP OR ITS SUPPLIERS BE LIABLE FOR ANY SPECIAL, INCIDENTAL, INDIRECT, OR CONSEQUENTIAL DAMAGES WHATSOEVER (INCLUDING, BUT NOT LIMITED TO, DAMAGES FOR LOSS OF PROFITS OR CONFIDENTIAL OR OTHER INFORMATION, FOR BUSINESS INTERRUPTION, FOR PERSONAL INJURY, FOR LOSS OF PRIVACY ARISING OUT OF OR IN ANY WAY RELATED TO THE USE OF OR INABILITY TO USE THE SOFTWARE, OR OTHERWISE IN CONNECTION WITH ANY PROVISION OF THIS AGREEMENT, EVEN IF HP OR ANY SUPPLIER HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES AND EVEN IF THE REMEDY FAILS OF ITS ESSENTIAL PURPOSE.  Some states/jurisdictions do not allow the exclusion or limitation of incidental or consequential damages, so the above limitation or exclusion may not apply to you.\n"
""))
        self.setTitle(self.InstallPage,self.__tr("Install Driver Plug-in"))


    def sourceGroup_clicked(self,a0):
        print "PluginForm_base.sourceGroup_clicked(int): Not implemented yet"

    def browsePushButton_clicked(self):
        print "PluginForm_base.browsePushButton_clicked(): Not implemented yet"

    def pathLineEdit_textChanged(self,a0):
        print "PluginForm_base.pathLineEdit_textChanged(const QString&): Not implemented yet"

    def downloadPushButton_clicked(self):
        print "PluginForm_base.downloadPushButton_clicked(): Not implemented yet"

    def installPushButton_clicked(self):
        print "PluginForm_base.installPushButton_clicked(): Not implemented yet"

    def __tr(self,s,c = None):
        return qApp.translate("PluginForm_base",s,c)
