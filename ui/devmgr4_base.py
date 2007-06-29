# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/devmgr4_base.ui'
#
# Created: Mon May 21 16:06:42 2007
#      by: The PyQt User Interface Compiler (pyuic) 3.17
#
# WARNING! All changes made in this file will be lost!


from qt import *


class DevMgr4_base(QMainWindow):
    def __init__(self,parent = None,name = None,fl = 0):
        QMainWindow.__init__(self,parent,name,fl)
        self.statusBar()

        if not name:
            self.setName("DevMgr4_base")


        self.setCentralWidget(QWidget(self,"qt_central_widget"))
        DevMgr4_baseLayout = QGridLayout(self.centralWidget(),1,1,11,6,"DevMgr4_baseLayout")

        self.splitter2 = QSplitter(self.centralWidget(),"splitter2")
        self.splitter2.setOrientation(QSplitter.Horizontal)
        self.splitter2.setOpaqueResize(1)

        self.DeviceList = QIconView(self.splitter2,"DeviceList")
        self.DeviceList.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,QSizePolicy.Preferred,0,0,self.DeviceList.sizePolicy().hasHeightForWidth()))
        self.DeviceList.setMaximumSize(QSize(32767,32767))
        self.DeviceList.setResizePolicy(QIconView.Manual)
        self.DeviceList.setArrangement(QIconView.TopToBottom)
        self.DeviceList.setResizeMode(QIconView.Adjust)

        self.Tabs = QTabWidget(self.splitter2,"Tabs")

        self.FunctionsTab = QWidget(self.Tabs,"FunctionsTab")
        self.Tabs.insertTab(self.FunctionsTab,QString.fromLatin1(""))

        self.StatusTab = QWidget(self.Tabs,"StatusTab")
        self.Tabs.insertTab(self.StatusTab,QString.fromLatin1(""))

        self.SuppliesTab = QWidget(self.Tabs,"SuppliesTab")
        self.Tabs.insertTab(self.SuppliesTab,QString.fromLatin1(""))

        self.MaintTab = QWidget(self.Tabs,"MaintTab")
        self.Tabs.insertTab(self.MaintTab,QString.fromLatin1(""))

        self.PrintSettingsTab = QWidget(self.Tabs,"PrintSettingsTab")
        self.Tabs.insertTab(self.PrintSettingsTab,QString.fromLatin1(""))

        self.PrintJobsTab = QWidget(self.Tabs,"PrintJobsTab")
        self.Tabs.insertTab(self.PrintJobsTab,QString.fromLatin1(""))

        DevMgr4_baseLayout.addWidget(self.splitter2,0,0)

        self.helpContentsAction = QAction(self,"helpContentsAction")
        self.helpIndexAction = QAction(self,"helpIndexAction")
        self.helpIndexAction.setEnabled(0)
        self.helpAboutAction = QAction(self,"helpAboutAction")
        self.deviceRescanAction = QAction(self,"deviceRescanAction")
        self.deviceExitAction = QAction(self,"deviceExitAction")
        self.settingsPopupAlertsAction = QAction(self,"settingsPopupAlertsAction")
        self.settingsEmailAlertsAction = QAction(self,"settingsEmailAlertsAction")
        self.settingsConfigure = QAction(self,"settingsConfigure")
        self.deviceRefreshAll = QAction(self,"deviceRefreshAll")
        self.autoRefresh = QAction(self,"autoRefresh")
        self.autoRefresh.setToggleAction(1)
        self.autoRefresh.setOn(1)
        self.setupDevice = QAction(self,"setupDevice")
        self.setupDevice.setEnabled(0)
        self.viewSupportAction = QAction(self,"viewSupportAction")
        self.deviceInstallAction = QAction(self,"deviceInstallAction")
        self.deviceRemoveAction = QAction(self,"deviceRemoveAction")




        self.MenuBar = QMenuBar(self,"MenuBar")

        self.MenuBar.setAcceptDrops(0)

        self.Device = QPopupMenu(self)
        self.setupDevice.addTo(self.Device)
        self.Device.insertSeparator()
        self.deviceRescanAction.addTo(self.Device)
        self.deviceRefreshAll.addTo(self.Device)
        self.Device.insertSeparator()
        self.deviceInstallAction.addTo(self.Device)
        self.deviceRemoveAction.addTo(self.Device)
        self.Device.insertSeparator()
        self.deviceExitAction.addTo(self.Device)
        self.MenuBar.insertItem(QString(""),self.Device,2)

        self.Configure = QPopupMenu(self)
        self.settingsConfigure.addTo(self.Configure)
        self.MenuBar.insertItem(QString(""),self.Configure,3)

        self.helpMenu = QPopupMenu(self)
        self.helpContentsAction.addTo(self.helpMenu)
        self.helpMenu.insertSeparator()
        self.helpAboutAction.addTo(self.helpMenu)
        self.MenuBar.insertItem(QString(""),self.helpMenu,4)

        self.MenuBar.insertSeparator(5)


        self.languageChange()

        self.resize(QSize(812,518).expandedTo(self.minimumSizeHint()))
        self.clearWState(Qt.WState_Polished)

        self.connect(self.helpIndexAction,SIGNAL("activated()"),self.helpIndex)
        self.connect(self.helpContentsAction,SIGNAL("activated()"),self.helpContents)
        self.connect(self.helpAboutAction,SIGNAL("activated()"),self.helpAbout)
        self.connect(self.deviceExitAction,SIGNAL("activated()"),self.close)
        self.connect(self.deviceRescanAction,SIGNAL("activated()"),self.deviceRescanAction_activated)
        self.connect(self.settingsEmailAlertsAction,SIGNAL("activated()"),self.settingsEmailAlertsAction_activated)
        self.connect(self.settingsConfigure,SIGNAL("activated()"),self.settingsConfigure_activated)
        self.connect(self.DeviceList,SIGNAL("currentChanged(QIconViewItem*)"),self.DeviceList_currentChanged)
        self.connect(self.deviceRefreshAll,SIGNAL("activated()"),self.deviceRefreshAll_activated)
        self.connect(self.DeviceList,SIGNAL("clicked(QIconViewItem*)"),self.DeviceList_clicked)
        self.connect(self.autoRefresh,SIGNAL("toggled(bool)"),self.autoRefresh_toggled)
        self.connect(self.DeviceList,SIGNAL("rightButtonClicked(QIconViewItem*,const QPoint&)"),self.DeviceList_rightButtonClicked)
        self.connect(self.setupDevice,SIGNAL("activated()"),self.setupDevice_activated)
        self.connect(self.viewSupportAction,SIGNAL("activated()"),self.viewSupportAction_activated)
        self.connect(self.deviceInstallAction,SIGNAL("activated()"),self.deviceInstallAction_activated)
        self.connect(self.deviceRemoveAction,SIGNAL("activated()"),self.deviceRemoveAction_activated)
        self.connect(self.Tabs,SIGNAL("currentChanged(QWidget*)"),self.Tabs_currentChanged)
        self.connect(self.DeviceList,SIGNAL("onItem(QIconViewItem*)"),self.DeviceList_onItem)


    def languageChange(self):
        self.setCaption(self.__tr("HP Device Manager"))
        self.Tabs.changeTab(self.FunctionsTab,self.__tr("Functions"))
        self.Tabs.changeTab(self.StatusTab,self.__tr("Status"))
        self.Tabs.changeTab(self.SuppliesTab,self.__tr("Supplies"))
        self.Tabs.changeTab(self.MaintTab,self.__tr("Tools"))
        self.Tabs.changeTab(self.PrintSettingsTab,self.__tr("Print Settings"))
        self.Tabs.changeTab(self.PrintJobsTab,self.__tr("Print Control"))
        self.helpContentsAction.setText(self.__tr("Contents"))
        self.helpContentsAction.setMenuText(self.__tr("&Contents..."))
        self.helpContentsAction.setToolTip(self.__tr("Help Contents (F1)"))
        self.helpContentsAction.setAccel(self.__tr("F1"))
        self.helpIndexAction.setText(self.__tr("Index"))
        self.helpIndexAction.setMenuText(self.__tr("&Index..."))
        self.helpIndexAction.setAccel(QString.null)
        self.helpAboutAction.setText(self.__tr("&About..."))
        self.helpAboutAction.setMenuText(self.__tr("&About..."))
        self.helpAboutAction.setToolTip(self.__tr("About HP Device Manager..."))
        self.deviceRescanAction.setText(self.__tr("Refresh Device"))
        self.deviceRescanAction.setMenuText(self.__tr("Refresh Device"))
        self.deviceRescanAction.setToolTip(self.__tr("Refresh Device (F5)"))
        self.deviceRescanAction.setAccel(self.__tr("F5"))
        self.deviceExitAction.setText(self.__tr("Exit"))
        self.deviceExitAction.setMenuText(self.__tr("Exit"))
        self.deviceExitAction.setToolTip(self.__tr("Exit HP Device Manager"))
        self.deviceExitAction.setAccel(self.__tr("Ctrl+Q"))
        self.settingsPopupAlertsAction.setText(self.__tr("Popup Alerts..."))
        self.settingsPopupAlertsAction.setMenuText(self.__tr("Popup alerts..."))
        self.settingsPopupAlertsAction.setToolTip(self.__tr("Configure popup alerts"))
        self.settingsEmailAlertsAction.setText(self.__tr("Email alerts..."))
        self.settingsEmailAlertsAction.setMenuText(self.__tr("Email alerts..."))
        self.settingsEmailAlertsAction.setToolTip(self.__tr("Configure email alerts"))
        self.settingsConfigure.setText(self.__tr("Settings..."))
        self.settingsConfigure.setAccel(self.__tr("F2"))
        self.deviceRefreshAll.setText(self.__tr("Refresh All"))
        self.deviceRefreshAll.setAccel(self.__tr("F6"))
        self.autoRefresh.setText(self.__tr("Auto Refresh"))
        self.autoRefresh.setToolTip(self.__tr("Turn on/off Auto Refresh (Ctrl+A)"))
        self.autoRefresh.setAccel(self.__tr("Ctrl+A"))
        self.setupDevice.setText(self.__tr("Action"))
        self.setupDevice.setMenuText(self.__tr("Settings..."))
        self.setupDevice.setToolTip(self.__tr("Device Settings (F3)"))
        self.setupDevice.setAccel(self.__tr("F3"))
        self.viewSupportAction.setText(self.__tr("Support..."))
        self.deviceInstallAction.setText(self.__tr("Setup New Device..."))
        self.deviceInstallAction.setMenuText(self.__tr("Setup New Device..."))
        self.deviceInstallAction.setAccel(self.__tr("Ins"))
        self.deviceRemoveAction.setText(self.__tr("Remove Device..."))
        self.deviceRemoveAction.setMenuText(self.__tr("Remove Device..."))
        self.deviceRemoveAction.setAccel(self.__tr("Del"))
        if self.MenuBar.findItem(2):
            self.MenuBar.findItem(2).setText(self.__tr("Device"))
        if self.MenuBar.findItem(3):
            self.MenuBar.findItem(3).setText(self.__tr("Configure"))
        if self.MenuBar.findItem(4):
            self.MenuBar.findItem(4).setText(self.__tr("&Help"))


    def fileNew(self):
        print "DevMgr4_base.fileNew(): Not implemented yet"

    def fileOpen(self):
        print "DevMgr4_base.fileOpen(): Not implemented yet"

    def fileSave(self):
        print "DevMgr4_base.fileSave(): Not implemented yet"

    def fileSaveAs(self):
        print "DevMgr4_base.fileSaveAs(): Not implemented yet"

    def filePrint(self):
        print "DevMgr4_base.filePrint(): Not implemented yet"

    def fileExit(self):
        print "DevMgr4_base.fileExit(): Not implemented yet"

    def editUndo(self):
        print "DevMgr4_base.editUndo(): Not implemented yet"

    def editRedo(self):
        print "DevMgr4_base.editRedo(): Not implemented yet"

    def editCut(self):
        print "DevMgr4_base.editCut(): Not implemented yet"

    def editCopy(self):
        print "DevMgr4_base.editCopy(): Not implemented yet"

    def editPaste(self):
        print "DevMgr4_base.editPaste(): Not implemented yet"

    def editFind(self):
        print "DevMgr4_base.editFind(): Not implemented yet"

    def helpIndex(self):
        print "DevMgr4_base.helpIndex(): Not implemented yet"

    def helpContents(self):
        print "DevMgr4_base.helpContents(): Not implemented yet"

    def helpAbout(self):
        print "DevMgr4_base.helpAbout(): Not implemented yet"

    def deviceRescanAction_activated(self):
        print "DevMgr4_base.deviceRescanAction_activated(): Not implemented yet"

    def settingsEmailAlertsAction_activated(self):
        print "DevMgr4_base.settingsEmailAlertsAction_activated(): Not implemented yet"

    def DeviceList_currentChanged(self,a0):
        print "DevMgr4_base.DeviceList_currentChanged(QIconViewItem*): Not implemented yet"

    def CleanPensButton_clicked(self):
        print "DevMgr4_base.CleanPensButton_clicked(): Not implemented yet"

    def AlignPensButton_clicked(self):
        print "DevMgr4_base.AlignPensButton_clicked(): Not implemented yet"

    def PrintTestPageButton_clicked(self):
        print "DevMgr4_base.PrintTestPageButton_clicked(): Not implemented yet"

    def AdvancedInfoButton_clicked(self):
        print "DevMgr4_base.AdvancedInfoButton_clicked(): Not implemented yet"

    def ColorCalibrationButton_clicked(self):
        print "DevMgr4_base.ColorCalibrationButton_clicked(): Not implemented yet"

    def settingsConfigure_activated(self):
        print "DevMgr4_base.settingsConfigure_activated(): Not implemented yet"

    def PrintButton_clicked(self):
        print "DevMgr4_base.PrintButton_clicked(): Not implemented yet"

    def ScanButton_clicked(self):
        print "DevMgr4_base.ScanButton_clicked(): Not implemented yet"

    def PCardButton_clicked(self):
        print "DevMgr4_base.PCardButton_clicked(): Not implemented yet"

    def SendFaxButton_clicked(self):
        print "DevMgr4_base.SendFaxButton_clicked(): Not implemented yet"

    def MakeCopiesButton_clicked(self):
        print "DevMgr4_base.MakeCopiesButton_clicked(): Not implemented yet"

    def ConfigureFeaturesButton_clicked(self):
        print "DevMgr4_base.ConfigureFeaturesButton_clicked(): Not implemented yet"

    def CancelJobButton_clicked(self):
        print "DevMgr4_base.CancelJobButton_clicked(): Not implemented yet"

    def deviceRefreshAll_activated(self):
        print "DevMgr4_base.deviceRefreshAll_activated(): Not implemented yet"

    def DeviceList_clicked(self,a0):
        print "DevMgr4_base.DeviceList_clicked(QIconViewItem*): Not implemented yet"

    def autoRefresh_toggled(self,a0):
        print "DevMgr4_base.autoRefresh_toggled(bool): Not implemented yet"

    def PrintJobList_currentChanged(self,a0):
        print "DevMgr4_base.PrintJobList_currentChanged(QListViewItem*): Not implemented yet"

    def CancelPrintJobButton_clicked(self):
        print "DevMgr4_base.CancelPrintJobButton_clicked(): Not implemented yet"

    def PrintJobList_selectionChanged(self,a0):
        print "DevMgr4_base.PrintJobList_selectionChanged(QListViewItem*): Not implemented yet"

    def DeviceList_rightButtonClicked(self,a0,a1):
        print "DevMgr4_base.DeviceList_rightButtonClicked(QIconViewItem*,const QPoint&): Not implemented yet"

    def OpenEmbeddedBrowserButton_clicked(self):
        print "DevMgr4_base.OpenEmbeddedBrowserButton_clicked(): Not implemented yet"

    def deviceSettingsButton_clicked(self):
        print "DevMgr4_base.deviceSettingsButton_clicked(): Not implemented yet"

    def faxSetupWizardButton_clicked(self):
        print "DevMgr4_base.faxSetupWizardButton_clicked(): Not implemented yet"

    def faxSettingsButton_clicked(self):
        print "DevMgr4_base.faxSettingsButton_clicked(): Not implemented yet"

    def setupDevice_activated(self):
        print "DevMgr4_base.setupDevice_activated(): Not implemented yet"

    def viewSupportAction_activated(self):
        print "DevMgr4_base.viewSupportAction_activated(): Not implemented yet"

    def installDevice_activated(self):
        print "DevMgr4_base.installDevice_activated(): Not implemented yet"

    def deviceInstallAction_activated(self):
        print "DevMgr4_base.deviceInstallAction_activated(): Not implemented yet"

    def deviceRemoveAction_activated(self):
        print "DevMgr4_base.deviceRemoveAction_activated(): Not implemented yet"

    def Tabs_currentChanged(self,a0):
        print "DevMgr4_base.Tabs_currentChanged(QWidget*): Not implemented yet"

    def DeviceList_onItem(self,a0):
        print "DevMgr4_base.DeviceList_onItem(QIconViewItem*): Not implemented yet"

    def __tr(self,s,c = None):
        return qApp.translate("DevMgr4_base",s,c)
