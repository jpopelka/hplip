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

# Qt
from qt import *
from scrollview import ScrollView

# Std Lib
import os.path, os
import time

try:
    import datetime
    have_datetime = True
except ImportError:
    have_datetime = False



class ScrollStatusView(ScrollView):
    def __init__(self,parent = None,name = None,fl = 0):
        ScrollView.__init__(self,parent,name,fl)

        self.warning_pix = QPixmap(os.path.join(prop.image_dir, "warning.png"))
        self.error_pix = QPixmap(os.path.join(prop.image_dir, "error.png"))
        self.ok_pix = QPixmap(os.path.join(prop.image_dir, "ok.png"))
        self.lowink_pix = QPixmap(os.path.join(prop.image_dir, 'inkdrop.png'))
        self.lowtoner_pix = QPixmap(os.path.join(prop.image_dir, 'toner.png'))
        self.busy_pix = QPixmap(os.path.join(prop.image_dir, 'busy.png'))
        self.lowpaper_pix = QPixmap(os.path.join(prop.image_dir, 'paper.png'))
        self.idle_pix = QPixmap(os.path.join(prop.image_dir, 'idle.png'))

        self.ScanPixmap = QPixmap(os.path.join(prop.image_dir, "scan_icon.png"))
        self.PrintPixmap = QPixmap(os.path.join(prop.image_dir, "print_icon.png"))
        self.SendFaxPixmap =QPixmap(os.path.join(prop.image_dir, "fax_icon.png"))
        self.PhotoCardPixmap = QPixmap(os.path.join(prop.image_dir, "pcard_icon.png"))
        self.MakeCopiesPixmap = QPixmap(os.path.join(prop.image_dir, "makecopies_icon.png"))

        self.STATUS_ICONS = { ERROR_STATE_CLEAR : (self.idle_pix, self.idle_pix),
                              ERROR_STATE_BUSY : (self.busy_pix, self.busy_pix),
                              ERROR_STATE_ERROR : (self.error_pix, self.error_pix),
                              ERROR_STATE_LOW_SUPPLIES : (self.lowink_pix, self.lowtoner_pix),
                              ERROR_STATE_OK : (self.ok_pix, self.ok_pix),
                              ERROR_STATE_WARNING : (self.warning_pix, self.warning_pix),
                              ERROR_STATE_LOW_PAPER: (self.lowpaper_pix, self.lowpaper_pix),
                              ERROR_STATE_PRINTING : (self.PrintPixmap, self.PrintPixmap),
                              ERROR_STATE_SCANNING : (self.ScanPixmap, self.ScanPixmap),
                              ERROR_STATE_PHOTOCARD : (self.PhotoCardPixmap, self.PrintPixmap),
                              ERROR_STATE_FAXING : (self.SendFaxPixmap, self.SendFaxPixmap),
                              ERROR_STATE_COPYING :  (self.MakeCopiesPixmap, self.MakeCopiesPixmap),
                            }

        self.unit_names = { "year" : (self.__tr("year"), self.__tr("years")),
                            "month" : (self.__tr("month"), self.__tr("months")),
                            "week" : (self.__tr("week"), self.__tr("weeks")),
                            "day" : (self.__tr("day"), self.__tr("days")),
                            "hour" : (self.__tr("hour"), self.__tr("hours")),
                            "minute" : (self.__tr("minute"), self.__tr("minutes")),
                            "second" : (self.__tr("second"), self.__tr("seconds")),
                            }

        self.num_repr = { 1 : self.__tr("one"),
                          2 : self.__tr("two"),
                          3 : self.__tr("three"),
                          4 : self.__tr("four"),
                          5 : self.__tr("five"),
                          6 : self.__tr("six"),
                          7 : self.__tr("seven"),
                          8 : self.__tr("eight"),
                          9 : self.__tr("nine"),
                          10 : self.__tr("ten"),
                          11 : self.__tr("eleven"),
                          12 : self.__tr("twelve")
                          }

    def fillControls(self):
        ScrollView.fillControls(self)
        self.row = 0
        
        for x in self.cur_device.hist:
            self.addItem(x)

    def addItem(self, hist):
        yr, mt, dy, hr, mi, sec, wd, yd, dst, job_id, user, ec, ess, esl = hist

        if self.row == 0:
            desc = self.__tr("(most recent)")

        else:
            if have_datetime:
                desc = self.getTimeDeltaDesc(hist[:9])
            else:
                desc = ''

        # TODO: In Qt4.x, use QLocale.toString(date, format)
        tt = QString("<b>%1 %2</b>").arg(QDateTime (QDate(yr, mt, dy), QTime(hr, mi, sec)).toString()).arg(desc).stripWhiteSpace()
        
        self.addGroupHeading(unicode(tt), tt)
        
        widget = self.getWidget()
        
        layout38 = QGridLayout(widget,1,1,5,10,"layout38")
        layout38.setColStretch(0, 1)
        layout38.setColStretch(1, 10)
        layout38.setColStretch(2, 2)
        
        spacer15 = QSpacerItem(30,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout38.addItem(spacer15,0,2)

        icon = QLabel(widget,"icon")
        icon.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed,0,0,icon.sizePolicy().hasHeightForWidth()))
        icon.setMinimumSize(QSize(32,32))
        icon.setMaximumSize(QSize(32,32))
        icon.setScaledContents(1)

        layout38.addWidget(icon,0,0)

        layout11_2 = QVBoxLayout(None,0,6,"layout11_2")

        essText = QLabel(widget,"essTextLabel")
        essText.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Preferred,0,0,essText.sizePolicy().hasHeightForWidth()))
        essText.setAlignment(QLabel.WordBreak | QLabel.AlignVCenter)
        essText.setFrameShape(self.frame_shape)
        layout11_2.addWidget(essText)

        eslText = QLabel(widget,"eslTextLabel")
        eslText.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Preferred,0,0,eslText.sizePolicy().hasHeightForWidth()))
        eslText.setAlignment(QLabel.WordBreak | QLabel.AlignVCenter)
        eslText.setFrameShape(self.frame_shape)
        layout11_2.addWidget(eslText)
        
        layout38.addLayout(layout11_2,0,1)

        layout12_2 = QGridLayout(None,1,1,5,10,"layout12_2")

        userTextLabel = QLabel(widget,"userLabel")
        layout12_2.addWidget(userTextLabel,0,1)

        jobIDTextLabel = QLabel(widget,"jobLabel")
        layout12_2.addWidget(jobIDTextLabel,1,1)

        userText = QLabel(widget,"user")
        layout12_2.addWidget(userText,0,2)

        codeTextLabel = QLabel(widget,"codeLabel")
        layout12_2.addWidget(codeTextLabel,2,1)

        jobIDText = QLabel(widget,"job")
        layout12_2.addWidget(jobIDText,1,2)

        codeText = QLabel(widget,"code")
        layout12_2.addWidget(codeText,2,2)

        line6 = QFrame(self,"line6")
        line6.setFrameShape(QFrame.VLine)
        layout12_2.addMultiCellWidget(line6,0,2,0,0)

        layout38.addLayout(layout12_2,0,3)

        ess = qApp.translate("StringTable", ess)
        essText.setText(ess)
        
        esl = qApp.translate("StringTable", esl)
        eslText.setText(esl)

        userTextLabel.setText(self.__tr("User:"))
        userText.setText(user)

        jobIDTextLabel.setText(self.__tr("Job ID:"))
        if job_id <= 0:
            jobIDText.setText(self.__tr("n/a"))
        else:
            jobIDText.setText(str(job_id))

        codeTextLabel.setText(self.__tr("Code:"))
        codeText.setText(unicode(ec))

        error_state = STATUS_TO_ERROR_STATE_MAP.get(ec, ERROR_STATE_CLEAR)
        
        try:
            tech_type = self.cur_device.tech_type
        except AttributeError:
            tech_type = TECH_TYPE_NONE

        if tech_type in (TECH_TYPE_COLOR_INK, TECH_TYPE_MONO_INK):
            status_pix = self.STATUS_ICONS[error_state][0] # ink
        else:
            status_pix = self.STATUS_ICONS[error_state][1] # laser

        if status_pix is not None:
            icon.setPixmap(status_pix)

        self.row += 1
        self.addWidget(widget, str(self.row))


    def getTimeDeltaDesc(self, past):
        delta = datetime.datetime(*time.localtime()[:7]) - datetime.datetime(*past[:7])
        return self.__tr("(about %1 ago)").arg(self.stringify(delta))


    # "Nicely readable timedelta"
    # Credit: Bjorn Lindqvist
    # ASPN Python Recipe 498062 
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/498062
    # Note: Modified from recipe
    def seconds_in_units(self, seconds):
        unit_limits = [("year", 31536000),
                       ("month", 2592000),
                       ("week", 604800),
                       ("day", 86400),
                       ("hour", 3600),
                       ("minute", 60)]

        for unit_name, limit in unit_limits:
            if seconds >= limit:
                amount = int(round(float(seconds) / limit))
                return amount, unit_name

        return seconds, "second"

    def stringify(self, td):
        seconds = td.days * 3600 * 24 + td.seconds
        amount, unit_name = self.seconds_in_units(seconds)

        try:
            i18n_amount = self.num_repr[amount]
        except KeyError:
            i18n_amount = unicode(amount)

        if amount == 1:
            i18n_unit = self.unit_names[unit_name][0]
        else:
            i18n_unit = self.unit_names[unit_name][1]

        return "%s %s" % (i18n_amount, i18n_unit)


    def __tr(self,s,c = None):
        return qApp.translate("ScrollStatusView",s,c)
        
