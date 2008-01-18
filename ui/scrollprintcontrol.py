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
# Author: Don Welch
#

# Local
from base.g import *
from base import utils
from prnt import cups

# Qt
from qt import *
from scrollview import ScrollView

# Std Lib
import os.path, os
import time


class CancelJobPushButton(QPushButton):
    def __init__(self, parent, name, job_id):
        QPushButton.__init__(self, parent, name)
        self.job_id = job_id


class ScrollPrintJobView(ScrollView):
    def __init__(self,parent = None,name = None,fl = 0):
        ScrollView.__init__(self,parent,name,fl)
        
        #self.heading_color = "#cccccc"
        
        self.JOB_STATES = { cups.IPP_JOB_PENDING : self.__tr("Pending"),
                            cups.IPP_JOB_HELD : self.__tr("On hold"),
                            cups.IPP_JOB_PROCESSING : self.__tr("Printing"),
                            cups.IPP_JOB_STOPPED : self.__tr("Stopped"),
                            cups.IPP_JOB_CANCELLED : self.__tr("Canceled"),
                            cups.IPP_JOB_ABORTED : self.__tr("Aborted"),
                            cups.IPP_JOB_COMPLETED : self.__tr("Completed"),
                           }

        self.warning_pix = QPixmap(os.path.join(prop.image_dir, "warning.png"))
        self.error_pix = QPixmap(os.path.join(prop.image_dir, "error.png"))
        self.ok_pix = QPixmap(os.path.join(prop.image_dir, "ok.png"))
        self.busy_pix = QPixmap(os.path.join(prop.image_dir, 'busy.png'))
        self.idle_pix = QPixmap(os.path.join(prop.image_dir, 'idle.png'))
        self.print_pix = QPixmap(os.path.join(prop.image_dir, "print_icon.png"))

        self.JOB_STATE_ICONS = { cups.IPP_JOB_PENDING: self.busy_pix,
                                 cups.IPP_JOB_HELD : self.busy_pix,
                                 cups.IPP_JOB_PROCESSING : self.print_pix,
                                 cups.IPP_JOB_STOPPED : self.warning_pix,
                                 cups.IPP_JOB_CANCELLED : self.warning_pix,
                                 cups.IPP_JOB_ABORTED : self.error_pix,
                                 cups.IPP_JOB_COMPLETED : self.ok_pix,
                                }


    def fillControls(self):
        ScrollView.fillControls(self)
        
        self.addGroupHeading("print_control", self.__tr("Print Control"))
        
        self.addPrintController()
        self.updatePrintController()

        jobs = cups.getJobs()

        num_jobs = 0
        for j in jobs:
            if j.dest.decode('utf-8') == self.cur_printer: 
                num_jobs += 1

        if num_jobs > 1:
            self.addGroupHeading("job_control", self.__tr("Job Control"))
            self.addCancelAllJobsController()
        
        if num_jobs:
            if num_jobs == 1:
                self.addGroupHeading("jobs", self.__tr("1 Active Print Job"))

            elif num_jobs > 1:
                self.addGroupHeading("jobs", self.__tr("%1 Active Print Jobs").arg(num_jobs))

            for j in jobs:
                if j.dest == self.cur_printer: 
                    self.addItem(j.dest, j.id, j.state, j.user, j.title)
            
    def addPrintController(self):
        widget = self.getWidget()

        layout1 = QGridLayout(widget,1,1,5,10,"layout1")

        layout2 = QVBoxLayout(None,10,10,"layout2")

        self.stopstartTextLabel = QLabel(widget,"stopstartTextLabel")
        self.stopstartTextLabel.setFrameShape(self.frame_shape)
        layout2.addWidget(self.stopstartTextLabel)

        self.acceptrejectTextLabel = QLabel(widget,"acceptrejectTextLabel")
        self.acceptrejectTextLabel.setFrameShape(self.frame_shape)
        layout2.addWidget(self.acceptrejectTextLabel)

        self.defaultTextLabel = QLabel(widget,"defaultTextLabel")
        self.defaultTextLabel.setFrameShape(self.frame_shape)
        layout2.addWidget(self.defaultTextLabel)

        layout1.addMultiCellLayout(layout2,2,3,0,0)

        layout3 = QVBoxLayout(None,0,6,"layout3")

        self.stopstartPushButton = QPushButton(widget,"stopstartPushButton")
        layout3.addWidget(self.stopstartPushButton)

        self.rejectacceptPushButton = QPushButton(widget,"rejectacceptPushButton")
        layout3.addWidget(self.rejectacceptPushButton)

        self.defaultPushButton = QPushButton(widget,"defaultPushButton")
        layout3.addWidget(self.defaultPushButton)
        layout1.addMultiCellLayout(layout3,2,3,2,2)
        
        spacer1 = QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout1.addItem(spacer1,3,1)
        
        spacer2 = QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout1.addItem(spacer2,2,1)

        self.connect(self.stopstartPushButton,SIGNAL("clicked()"),self.stopstartPushButton_clicked)
        self.connect(self.rejectacceptPushButton,SIGNAL("clicked()"),self.rejectacceptPushButton_clicked)
        self.connect(self.defaultPushButton,SIGNAL("clicked()"),self.defaultPushButton_clicked)

        self.addWidget(widget, "print_control")

    def updatePrintController(self):
        # default printer
        self.defaultPushButton.setText(self.__tr("Set as Default"))
        default_printer = cups.getDefaultPrinter()

        if default_printer == self.cur_printer:
            s = self.__tr("SET AS DEFAULT")
            self.defaultPushButton.setEnabled(False)
        else:
            s = self.__tr("NOT SET AS DEFAULT")
            self.defaultPushButton.setEnabled(True)

        self.defaultTextLabel.setText(self.__tr("The printer is currently: %1").arg(s))

        cups_printers = cups.getPrinters()
        for p in cups_printers:
            if p.name.decode('utf-8') == self.cur_printer:
                self.printer_state = p.state
                self.printer_accepting = p.accepting
                break

        # start/stop
        if self.printer_state == cups.IPP_PRINTER_STATE_IDLE:
            s = self.__tr("IDLE")
            self.stopstartPushButton.setText(self.__tr("Stop Printer"))

        elif self.printer_state == cups.IPP_PRINTER_STATE_PROCESSING:
            s = self.__tr("PROCESSING")
            self.stopstartPushButton.setText(self.__tr("Stop Printer"))

        else:
            s = self.__tr("STOPPED")
            self.stopstartPushButton.setText(self.__tr("Start Printer"))

        self.stopstartTextLabel.setText(self.__tr("The printer is currently: %1").arg(s))

        # reject/accept
        if self.printer_accepting:
            s = self.__tr("ACCEPTING JOBS")
            self.rejectacceptPushButton.setText(self.__tr("Reject Jobs"))
        else:
            s = self.__tr("REJECTING JOBS")
            self.rejectacceptPushButton.setText(self.__tr("Accept Jobs"))

        self.acceptrejectTextLabel.setText(self.__tr("The printer is currently: %1").arg(s))


    def stopstartPushButton_clicked(self):
        QApplication.setOverrideCursor(QApplication.waitCursor)
        try:
            if self.printer_state in (cups.IPP_PRINTER_STATE_IDLE, cups.IPP_PRINTER_STATE_PROCESSING):
                cups.stop(self.cur_printer)
            else:
                cups.start(self.cur_printer)

            self.updatePrintController()
        finally:
            QApplication.restoreOverrideCursor()

    def rejectacceptPushButton_clicked(self):
        QApplication.setOverrideCursor(QApplication.waitCursor)
        try:
            if self.printer_accepting:
                cups.reject(self.cur_printer)
            else:
                cups.accept(self.cur_printer)

            self.updatePrintController()
        finally:
            QApplication.restoreOverrideCursor()


    def defaultPushButton_clicked(self):
        QApplication.setOverrideCursor(QApplication.waitCursor)
        try:
            result = cups.setDefaultPrinter(self.cur_printer)
            if not result:
                log.error("Set default printer failed.")
            else:
                self.updatePrintController()
        finally:
            QApplication.restoreOverrideCursor()


    def addCancelAllJobsController(self):
        widget = self.getWidget()

        layout1 = QHBoxLayout(widget,10,5,"layout1")

        textLabel1 = QLabel(widget,"textLabel1")
        layout1.addWidget(textLabel1)

        spacer1 = QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout1.addItem(spacer1)

        cancelPushButton = QPushButton(widget,"cancelPushButton")
        layout1.addWidget(cancelPushButton)

        self.addWidget(widget, "job_control")

        textLabel1.setText(self.__tr("Cancel all active print jobs"))
        cancelPushButton.setText(self.__tr("Cancel All Jobs"))

        self.connect(cancelPushButton, SIGNAL("clicked()"), self.cancelAllJobs)


    def cancelAllJobs(self):
        QApplication.setOverrideCursor(QApplication.waitCursor)
        try:
            if not cups.purge(self.cur_printer):
                log.error("Cancel all jobs failed.")
            else:
                self.fillControls()
        finally:
            QApplication.restoreOverrideCursor()


    def addItem(self, dest, job_id, state, user, title):
        widget = self.getWidget()

        layout1 = QGridLayout(widget,1,1,5,10,"layout1")

        #line1 = QFrame(widget,"line1")
        #line1.setFrameShape(QFrame.HLine)

        #layout1.addMultiCellWidget(line1,3,3,0,4)

        cancelPushButton = CancelJobPushButton(widget,"cancelPushButton", job_id)
        layout1.addWidget(cancelPushButton,1,4)

        spacer1 = QSpacerItem(30,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout1.addItem(spacer1,1,3)

        icon = QLabel(widget,"icon")
        icon.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed,0,0,
            icon.sizePolicy().hasHeightForWidth()))

        icon.setMinimumSize(QSize(32,32))
        icon.setMaximumSize(QSize(32,32))
        icon.setScaledContents(1)
        layout1.addMultiCellWidget(icon,1,2,1,1)

        spacer2 = QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout1.addItem(spacer2,0,3)

        titleText = QLabel(widget,"titleText")
        titleText.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred,0,0,
            titleText.sizePolicy().hasHeightForWidth()))

        layout1.addMultiCellWidget(titleText,0,0,1,2)

        stateText = QLabel(widget,"stateText")
        stateText.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred,0,0,
            stateText.sizePolicy().hasHeightForWidth()))

        layout1.addWidget(stateText,1,2)

        jobIDText = QLabel(widget,"jobIDText")
        layout1.addWidget(jobIDText,0,4)

        titleText.setText(self.__tr("<b>%1</b>").arg(title))
        stateText.setText(self.JOB_STATES[state])
        jobIDText.setText(self.__tr("Job ID: %1").arg(job_id))
        cancelPushButton.setText(self.__tr("Cancel Job"))

        icon.setPixmap(self.JOB_STATE_ICONS[state])

        self.connect(cancelPushButton, SIGNAL("clicked()"), self.cancelJob)

        self.addWidget(widget, dest+str(job_id))


    def cancelJob(self):
        sender = self.sender()

        job_id = sender.job_id

        QApplication.setOverrideCursor(QApplication.waitCursor)
        try:
            self.cur_device.cancelJob(job_id)
            time.sleep(1)
        finally:
            QApplication.restoreOverrideCursor()

        self.fillControls()

    def __tr(self,s,c = None):
        return qApp.translate("ScrollPrintJobView",s,c)
        
