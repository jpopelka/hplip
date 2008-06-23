# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2008 Hewlett-Packard Development Company, L.P.
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
# Author: Don Welch
#

from base.g import *
from installer import core_install
from base import device
        
from qt import *
from pluginform2_base import PluginForm2_base

class PluginForm2(PluginForm2_base):
    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        PluginForm2_base.__init__(self,parent,name,modal,fl)
        self.path = None
        #self.version = sys_cfg.hplip.version
        self.version = '.'.join(sys_cfg.hplip.version.split('.')[:3])
        #print self.version
        self.bg = self.pathLineEdit.paletteBackgroundColor()
        
        self.titleTextLabel.setFont(QFont('Helvetica', 16))
        
        self.sourceGroup.emit(SIGNAL("clicked(int)"), (0,))
        
    def sourceGroup_clicked(self, item):
        self.pathLineEdit.setEnabled(item == 1)
        self.browsePushButton.setEnabled(item == 1)
        
        #if item == 1 and 
        #    self.actionPushButton.setText(self.__tr("Download and Install"))
            
        if item == 0: # download
            QToolTip.remove(self.pathLineEdit)
            self.actionPushButton.setText(self.__tr("Download and Install"))
            self.actionPushButton.setEnabled(True)
            self.path = None
        else: # path
            self.path = unicode(self.pathLineEdit.text())
            self.pathLineEdit.emit(SIGNAL("textChanged(const QString&)"), (self.path,)) 
            
            if self.path.startswith(u"http://"):
                self.actionPushButton.setText(self.__tr("Download and Install"))
            else:   
                self.actionPushButton.setText(self.__tr("Copy and Install"))
            
            
    def browsePushButton_clicked(self):
        workingDirectory = user_cfg.last_used.working_dir

        if not workingDirectory or not os.path.exists(workingDirectory):
            workingDirectory = os.path.expanduser("~")

        log.debug("workingDirectory: %s" % workingDirectory)

        dlg = QFileDialog(workingDirectory, self.__tr("HPLIP %s Plug-in (*.run)" % 
            self.version), None, None, True)

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
                    
                    
    def pathLineEdit_textChanged(self, path):
        path, ok = unicode(path), True
        
        if not path.startswith(u'http://'):
            self.actionPushButton.setText(self.__tr("Copy and Install"))
            
            if not path or not os.path.exists(path):
                #log.error("File '%s' not found." % path)
                QToolTip.add(self.pathLineEdit, self.__tr('File not found.'))
                ok = False
                
            elif os.path.basename(path) != u'hplip-%s-plugin.run' % self.version:
                log.error("Incorrect file: %s (should be: %s)" % (path, 'hplip-%s-plugin.run' % self.version))
                QToolTip.add(self.pathLineEdit, self.__tr("Incorrect file. Must be '%1'")\
                    .arg('hplip-%s-plugin.run' % self.version))
                    
                ok = False
        
        else:
            self.actionPushButton.setText(self.__tr("Download and Install"))
            
        self.actionPushButton.setEnabled(ok)
        
        if not ok:
            self.pathLineEdit.setPaletteBackgroundColor(QColor(0xff, 0x99, 0x99))
            
        else:
            QToolTip.remove(self.pathLineEdit)
            self.pathLineEdit.setPaletteBackgroundColor(self.bg)
            self.path = path
            
            
    def actionPushButton_clicked(self):
        core = core_install.CoreInstall()
        core.set_plugin_version() #self.version)

        if self.path is None: # download
            # read plugin.conf (local or on sf.net) to get plugin_path (http://)
            plugin_conf_url = core.get_plugin_conf_url()
            
            if plugin_conf_url.startswith('file://'):
                #tui.header("COPY CONFIGURATION")
                pass
            else:
                pass #tui.header("DOWNLOAD CONFIGURATION")
                
                log.info("Checking for network connection...")
                ok = core.check_network_connection()
                
                if not ok:
                    log.error("Network connection not detected.")
                    #sys.exit(1)
                    self.FailureUI(self.__tr("Network connection not detected."))
                    #return
                    self.close()
                    return
                
            
            log.info("Downloading configuration file from: %s" % plugin_conf_url)
            #pm = tui.ProgressMeter("Downloading configuration:")
            
            self.path, size, checksum, timestamp, ok = core.get_plugin_info(plugin_conf_url, 
                self.plugin_download_callback)
            
            print self.path, size, checksum, timestamp, ok
            
            #sys.exit(1)
            
            if not self.path.startswith('http://') and not self.path.startswith('file://'):
                self.path = 'file://' + self.path
        
        
        else: # path
            if not self.path.startswith('http://'):
                self.path = 'file://' + self.path
                
            size, checksum, timestamp = 0, '', 0
            
        
        if self.path.startswith('file://'):
            #tui.header("COPY PLUGIN")
            pass
        else:
            #tui.header("DOWNLOAD PLUGIN")
            
            log.info("Checking for network connection...")
            ok = core.check_network_connection()
            
            if not ok:
                log.error("Network connection not detected.")
                self.FailureUI(self.__tr("Network connection not detected."))
                self.close()
                return
    
        log.info("Downloading plug-in from: %s" % self.path)
        #pm = tui.ProgressMeter("Downloading plug-in:")
        
        ok, local_plugin = core.download_plugin(self.path, size, checksum, timestamp, 
            self.plugin_download_callback)
            
        #print
        
        if not ok:
            log.error("Plug-in download failed: %s" % local_plugin)
            self.FailureUI(self.__tr("Plug-in download failed."))
            #sys.exit(1)
            self.close()
            return
        
        #tui.header("INSTALLING PLUG-IN")
        
        if not core.run_plugin(GUI_MODE, self.plugin_install_callback):
            self.FailureUI(self.__tr("Plug-in install failed."))
            self.close()
            return
        
        cups_devices = device.getSupportedCUPSDevices(['hp']) #, 'hpfax'])
        #print cups_devices
        
        for dev in cups_devices:
            mq = device.queryModelByURI(dev)
            
            if mq.get('fw-download', False):
                
                # Download firmware if needed
                log.info(log.bold("\nDownloading firmware to device %s..." % dev))
                try:
                    d = device.Device(dev)
                except Error:
                    log.error("Error opening device.")
                    #sys.exit(1)
                    continue

                if d.downloadFirmware():
                    log.info("Firmware download successful.\n")

                d.close()
        
        
        self.SuccessUI("Plug-in install successful.")
        self.close()
        
    
    def FailureUI(self, error_text):
        QMessageBox.critical(self,
            self.caption(),
            error_text,
            QMessageBox.Ok,
            QMessageBox.NoButton,
            QMessageBox.NoButton)
            
    def SuccessUI(self, text):
        QMessageBox.information(self,
                             self.caption(),
                             text,
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)
            
        

    def plugin_download_callback(self, c, s, t):
        #pm.update(int(100*c*s/t), 
        #         utils.format_bytes(c*s))
        #print s
        pass

             
    def plugin_install_callback(self, s):
        print s
    
    
    def cancelPushButton_clicked(self):
        self.close()


    def __tr(self,s,c = None):
        return qApp.translate("PluginForm_base",s,c)
