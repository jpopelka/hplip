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
# Authors: Don Welch

# Local
from base.g import *
from base import device, utils

# Std Lib
import sys
import os
import os.path

# Qt
from qt import *
from pluginform_base import PluginForm_base
from waitform import WaitForm


class PluginForm(PluginForm_base):
    def __init__(self, core, norm_model, plugin, device_uri, plugin_lib, fw_download, 
                 parent = None, name = None, modal = 0, fl = 0):
        
        PluginForm_base.__init__(self,parent,name,modal,fl)
        
        icon = QPixmap(os.path.join(prop.image_dir, 'HPmenu.png'))
        self.setIcon(icon)
        
        self.setTitleFont(QFont("Helvetica", 16))
        
        self.sourceGroup.setButton(0)
        self.browsePushButton.setEnabled(False)
        self.pathLineEdit.setEnabled(False)
        
        self.downloadText = self.__tr("Agree to License, Download and Install Plug-in")
        self.setTitle(self.InstallPage, self.downloadText)
        self.installPushButton.setText(self.downloadText)
        self.bg = self.pathLineEdit.paletteBackgroundColor()
        self.download = True
        self.path = u''
        self.norm_model = norm_model
        self.plugin = plugin
        self.waitdlg = None
        self.device_uri = device_uri
        self.plugin_lib = plugin_lib
        self.fw_download = fw_download
        self.core = core
        
        
    def showPage(self, page):
        if page is self.SourcePage:
            self.setFinishEnabled(self.SourcePage, False)
            self.setHelpEnabled(self.SourcePage, False)
            
            if self.plugin == PLUGIN_OPTIONAL:
                self.textLabel1.setText(self.__tr("""An optional driver plug-in is available to enhance the operation of this printer. You may skip this installation, download the plug-in directly from an HP authorized server, or, if you already have a copy of the file, you can specify a path to the file."""))
                self.setTitle(self.SourcePage, self.__tr("Optional Driver Plug-in Available"))
                self.skipRadioButton.setEnabled(True)
        
        elif page is self.InstallPage:
            self.setBackEnabled(self.InstallPage, False)
            self.setFinishEnabled(self.SourcePage, False)
            self.setHelpEnabled(self.InstallPage, False)
        
        QWizard.showPage(self, page)
    
    def sourceGroup_clicked(self, opt):
        if opt == 0: # download
            self.browsePushButton.setEnabled(False)
            self.setFinishEnabled(self.SourcePage, False)
            self.pathLineEdit.setEnabled(False)
            self.setTitle(self.InstallPage, self.downloadText)
            self.installPushButton.setText(self.downloadText)
            self.download = True
            self.setNextEnabled(self.SourcePage, True)
            
        elif opt == 1: # local file
            self.browsePushButton.setEnabled(True)
            self.setFinishEnabled(self.SourcePage, False)
            self.pathLineEdit.setEnabled(True)
            s = self.__tr("Agree to License and Install Plug-in")
            self.setTitle(self.InstallPage, s)
            self.installPushButton.setText(s)
            self.download = False
            self.checkPath()
            
        else: # skip
            self.browsePushButton.setEnabled(False)
            self.pathLineEdit.setEnabled(False)
            self.download = False
            self.setNextEnabled(self.SourcePage, False)
            self.setFinishEnabled(self.SourcePage, True)
        
        
    def browsePushButton_clicked(self):
        workingDirectory = user_cfg.last_used.working_dir

        if not workingDirectory or not os.path.exists(workingDirectory):
            workingDirectory = os.path.expanduser("~")

        log.debug("workingDirectory: %s" % workingDirectory)

        dlg = QFileDialog(workingDirectory, self.__tr("HPLIP Plug-in (*.plugin)"), None, None, True)

        dlg.setCaption("openfile")
        dlg.setMode(QFileDialog.ExistingFile)
        dlg.show()

        if dlg.exec_loop() == QDialog.Accepted:
                results = dlg.selectedFile()
                workingDirectory = unicode(dlg.dir().absPath())
                log.debug("results: %s" % results)
                log.debug("workingDirectory: %s" % workingDirectory)

                user_cfg.last_used.working_dir = workingDirectory

                if results:
                    self.path = unicode(results)
                    self.pathLineEdit.setText(self.path)
        

    def pathLineEdit_textChanged(self,a0):
        self.path = unicode(a0)
        self.checkPath()
        
    def checkPath(self):
        if not self.download and self.path and \
            self.path.endswith('.plugin') and os.path.exists(self.path):
            
            self.pathLineEdit.setPaletteBackgroundColor(self.bg)
            self.setNextEnabled(self.SourcePage, True)
        else:
            self.pathLineEdit.setPaletteBackgroundColor(QColor(0xff, 0x99, 0x99))
            self.setNextEnabled(self.SourcePage, False)
        

    def cancelled(self):
        print "Cancel!"
        # TODO: How to cancel urllib.urlretrieve? (use urlopen())
        
    def download_callback(self, c, s, t):
        if c:
            h1 = utils.format_bytes(c*s)
            h2 = utils.format_bytes(t)
            self.waitdlg.setMessage(self.__tr("Downloaded %1 of %2").arg(h1).arg(h2))
            log.debug("Downloaded %s of %s" % (h1, h2))
        
        
    def download_callback(self, blocks_xfered, block_size, total_size):
        #print blocks_xfered, block_size, total_size
        pass
        
    def installPushButton_clicked(self):
        self.waitdlg = WaitForm(0, self.__tr("Initializing..."), None, self, modal=0)
        self.waitdlg.show()
        qApp.processEvents()
        
        try:
            core = self.core
            if self.download:
                log.debug("Checking for network connection...")
                self.waitdlg.setMessage(self.__tr("Checking for network connection..."))
                ok = core.check_network_connection()
                
                if ok:
                    self.waitdlg.setMessage(self.__tr("Downloading configuration..."))
                    log.debug("Downloading configuration...")
                    url, size, checksum, timestamp, ok = core.get_plugin_info(self.norm_model, 
                        self.download_callback)
                        
                    log.debug("url= %s" % url)
                    log.debug("size=%d" % size)
                    log.debug("checksum=%s" % checksum)
                    log.debug("timestamp=%f" % timestamp)
                    
                    if url and size and checksum and timestamp and ok:
                        log.debug("Downloading plug-in...")
                        self.waitdlg.setMessage(self.__tr("Downloading plug-in..."))
                        
                        ok, plugin_file = core.download_plugin(self.norm_model, url, size, 
                            checksum, timestamp, self.download_callback)
                        
                        if not ok:
                            self.FailureUI(self.__tr("<b>An error occured downloading plugin file.</b><p>Please check your network connection try again."))
                            self.reject()
                            return
                
                else:
                    self.FailureUI(self.__tr("<b>No network connection found.</b><p>Please check your network connection try again."))
                    self.reject()
                    return
                    
            
            else: # local path
                ok = core.copy_plugin(self.norm_model, self.path)
                
                if not ok:
                    self.FailureUI(self.__tr("<b>Plugin copy failed.</b>"))
                    self.reject()
                    return
                
                        
            if ok:
                log.debug("Installing plug-in...")
                self.waitdlg.setMessage(self.__tr("Installing plug-in..."))
                ok = core.install_plugin(self.norm_model, self.plugin_lib)
                
                if not ok:
                    self.FailureUI(self.__tr("<b>Plug-in install failed.</b><p>"))
                    self.reject()
                    return
                    
                else:
                    log.debug("Plug-in installation complete.")
                    
                    # Download firmware if needed
                    if self.fw_download:
                        self.waitdlg.setMessage(self.__tr("Downloading firmware..."))
                        try:
                            d = device.Device(self.device_uri)
                        except Error:
                            self.FailureUI(self.__tr("<b>An error occured downloading firmware file.</b><p>Please check your printer and try again."))
                            self.reject()
                            return
                        
                        if d.downloadFirmware():
                            log.debug("Done.")
                            
                        d.close()            
        
        finally:
            if self.waitdlg is not None:
                self.waitdlg.hide()
                self.waitdlg.close()
                self.waitdlg = None
                
        self.accept()

        
    def reject(self):
        QWizard.reject(self)
        
    def accept(self):
        QWizard.accept(self)
        
    def FailureUI(self, error_text):
        log.error(unicode(error_text).replace("<b>", "").replace("</b>", "").replace("<p>", " "))
        QMessageBox.critical(self,
                             self.caption(),
                             error_text,
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)
        
    
    def __tr(self,s,c = None):
        return qApp.translate("PluginForm",s,c)
        
