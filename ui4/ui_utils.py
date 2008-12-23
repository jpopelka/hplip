# -*- coding: utf-8 -*-
#
# (c) Copyright 2001-2008 Hewlett-Packard Development Company, L.P.
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

# Std Lib
import os.path
import re
import os

# Local
from base.g import *
from base.codes import *
from base import utils

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

pat_html_remove = re.compile("(?is)<.*?>", re.I)

# databaseChanged signal values (for FABWindow)
FAB_NAME_ADD = 0  # s1 - new name
FAB_NAME_RENAME = 1 # s1 - old name, s2 - new name
FAB_NAME_REMOVE = 2 # s1 - removed name
FAB_NAME_DETAILS_CHANGED = 3 # s1 - name
FAB_GROUP_ADD = 4 # s1 - new group
FAB_GROUP_RENAME = 5 # s1 - old group, s2 - new group
FAB_GROUP_REMOVE = 6 # s1 - removed group
FAB_GROUP_MEMBERSHIP_CHANGED = 7 # s1 - group


def __translate(t):
    return QApplication.translate("ui_utils", t, None, QApplication.UnicodeUTF8)


def beginWaitCursor():
    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))


def endWaitCursor():
    QApplication.restoreOverrideCursor()


# TODO: Cache pixmaps
def load_pixmap(name, subdir=None, resize_to=None):
    name = ''.join([os.path.splitext(name)[0], '.png'])

    if subdir is None:
        dir = prop.image_dir
        ldir = os.path.join(os.getcwd(), 'data', 'images')
    else:
        dir = os.path.join(prop.image_dir, subdir)
        ldir = os.path.join(os.getcwd(), 'data', 'images', subdir)

    #print dir, ldir
    for d in [dir, ldir]:
        f = os.path.join(d, name)
        if os.path.exists(f):
            if resize_to is not None:
                img = QImage(f)
                x, y = resize_to
                return QPixmap.fromImage(img.scaled(x, y, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
            else:
                return QPixmap(f)

        for w in utils.walkFiles(dir, recurse=True, abs_paths=True, return_folders=False, pattern=name):
            if resize_to is not None:
                img = QImage(w)
                x, y = resize_to
                return QPixmap.fromImage(img.scaled(x, y, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
            else:
                return QPixmap(w)

    log.error("Pixmap '%s' not found!" % name)
    return QPixmap()

loadPixmap = load_pixmap


class UserSettings(QSettings):
    def __init__(self):
        QSettings.__init__(self, os.path.join(prop.user_dir,  'hplip.conf'),  QSettings.IniFormat)
        #self.hide_tray_when_inactive = False
        self.systray_visible = SYSTRAY_VISIBLE_SHOW_ALWAYS
        self.last_used_device_uri = ''
        self.last_used_printer = ''
        self.last_used_working_dir = os.path.expanduser('~')
        self.version = ''
        self.date_time = ''
        self.auto_refresh = False
        self.auto_refresh_rate = 30
        self.auto_refresh_type = 1
        self.polling_interval = 5
        self.polling = True
        self.device_list = []
        self.loadDefaults()


    def __setup(self,  cmds):
        for c in cmds:
            basename = c.split()[0]
            path = utils.which(basename)
            if path:
                return ' '.join([os.path.join(path, basename), ' '.join(c.split()[1:])])

        return ''

    def loadDefaults(self):
        #self.cmd_print = self.__setup(['hp-print -p%PRINTER',
        #                               'kprinter -P%PRINTER% --system cups',
        #                               'gtklp -P%PRINTER%',
        #                               'xpp -P%PRINTER%'])

        self.cmd_scan = self.__setup(['xsane -V %SANE_URI%', 'kooka', 'xscanimage'])
        #self.cmd_pcard = self.__setup(['hp-unload -d%DEVICE_URI%'])
        #self.cmd_fax = self.__setup(['hp-sendfax -p%PRINTER%'])
        #self.cmd_copy = self.__setup(['hp-makecopies -d%DEVICE_URI%'])
        #self.cmd_faxsetup = self.__setup(['hp-faxsetup -d$FAX_URI%'])
        self.cmd_fab = self.__setup(['hp-fab'])
        #self.cmd_align = self.__setup(['hp-align -d%DEVICE_URI%'])
        #self.cmd_pqdiag = self.__setup(['hp-pqdiag -d%DEVICE_URI%'])
        #self.cmd_colorcal = self.__setup(['hp-colorcal -d%DEVICE_URI%'])
        #self.cmd_testpage = self.__setup(['hp-testpage -p%PRINTER%'])
        #self.cmd_devicesetup = self.__setup(['hp-devicesetup -d%DEVICE_URI%'])
        #self.cmd_clean = self.__setup(['hp-clean -d%DEVICE_URI%'])
        #self.cmd_linefeedcal = self.__setup(['hp-linefeedcal -d%DEVICE_URI%'])
        #self.cmd_firmware = self.__setup(['hp-firmware -d%DEVICE_URI%'])
        #self.cmd_plugin = self.__setup(['hp-plugin -d%DEVICE_URI%'])
        #self.cmd_info = self.__setup(['hp-info -d%DEVICE_URI%'])


    def load(self):
        log.debug("Loading user settings...")

        self.beginGroup("settings")
        #self.hide_tray_when_inactive = bool(self.value("hide_tray_when_inactive").toBool()) or self.hide_tray_when_inactive
        i, ok = self.value("systray_visible").toInt()
        if ok:
            self.systray_visible = i

        self.endGroup()

        self.beginGroup("last_used")
        self.last_used_device_uri = unicode(self.value("device_uri").toString()) or self.last_used_device_uri
        self.last_used_printer = unicode(self.value("printer").toString()) or self.last_used_printer
        self.last_used_working_dir = unicode(self.value("working_dir").toString()) or self.last_used_working_dir
        self.endGroup()

        self.beginGroup("commands")
        #self.cmd_print = unicode(self.value("prnt").toString()) or self.cmd_print
        #self.cmd_copy = unicode(self.value("cpy").toString()) or self.cmd_copy
        #self.cmd_fax = unicode(self.value("fax").toString()) or self.cmd_fax
        self.cmd_scan = unicode(self.value("scan").toString()) or self.cmd_scan
        #self.cmd_pcard = unicode(self.value("pcard").toString()) or self.cmd_pcard
        #self.cmd_fab = unicode(self.value("fab").toString()) or self.cmd_fab
        self.endGroup()

        self.beginGroup("refresh")
        self.auto_refresh_rate = int(self.value("rate").toString() or self.auto_refresh_rate)
        self.auto_refresh = bool(self.value("enable").toBool())
        self.auto_refresh_type = int(self.value("type").toString() or self.auto_refresh_type)
        self.endGroup()

        self.beginGroup("installation")
        self.version = unicode(self.value("version").toString())
        self.date_time = unicode(self.value("date_time").toString())
        self.endGroup()

        self.beginGroup("polling")
        self.polling = bool(self.value("enable").toBool())
        self.polling_interval = int(self.value("interval").toString() or self.polling_interval)
        self.polling_device_list = unicode(self.value("device_list").toString() or '').split(u',')
        self.endGroup()


    def save(self):
        log.debug("Saving user settings...")

        self.beginGroup("settings")
        #self.setValue("hide_tray_when_inactive",  QVariant(self.hide_tray_when_inactive))
        i = QVariant(self.systray_visible)
        #print i.toInt()
        self.setValue("systray_visible", QVariant(self.systray_visible))
        self.endGroup()

        self.beginGroup("last_used")
        self.setValue("device_uri",  QVariant(self.last_used_device_uri))
        self.setValue("printer", QVariant(self.last_used_printer))
        self.setValue("working_dir", QVariant(self.last_used_working_dir))
        self.endGroup()

        self.beginGroup("commands")
        #self.setValue("prnt",  QVariant(self.cmd_print))
        #self.setValue("cpy",  QVariant(self.cmd_copy))
        #self.setValue("fax",  QVariant(self.cmd_fax))
        self.setValue("scan",  QVariant(self.cmd_scan))
        #self.setValue("pcard",  QVariant(self.cmd_pcard))
        #self.setValue("fab",  QVariant(self.cmd_fab))
        self.endGroup()

        self.beginGroup("refresh")
        self.setValue("rate", QVariant(self.auto_refresh_rate))
        self.setValue("enable", QVariant(self.auto_refresh))
        self.setValue("type", QVariant(self.auto_refresh_type))
        self.endGroup()

        self.beginGroup("polling")
        self.setValue("enable", QVariant(self.polling))
        self.setValue("interval", QVariant(self.polling_interval))
        self.setValue("device_list", QVariant(u','.join(self.polling_device_list)))
        self.endGroup()


    def debug(self):
        #log.debug("Print command: %s" % self.cmd_print)
        #log.debug("PCard command: %s" % self.cmd_pcard)
        #log.debug("Fax command: %s" % self.cmd_fax)
        log.debug("FAB command: %s" % self.cmd_fab)
        #log.debug("Copy command: %s " % self.cmd_copy)
        log.debug("Scan command: %s" % self.cmd_scan)
        log.debug("Auto refresh: %s" % self.auto_refresh)
        log.debug("Auto refresh rate: %s" % self.auto_refresh_rate)
        log.debug("Auto refresh type: %s" % self.auto_refresh_type)
        #log.debug("Hide tray when inactive: %s" % self.hide_tray_when_inactive)
        log.debug("Systray visible: %d" % self.systray_visible)
        log.debug("Last used device URI: %s" % self.last_used_device_uri)
        log.debug("Last used printer: %s" % self.last_used_printer)
        log.debug("Last used working dir: %s" % self.last_used_working_dir)


def su_sudo():
    su_sudo_str = None

    if utils.which('kdesu'):
        su_sudo_str = 'kdesu -- %s'

    elif utils.which('gnomesu'):
        su_sudo_str = 'gnomesu -c "%s"'

    elif utils.which('gksu'):
        su_sudo_str = 'gksu "%s"'

    return su_sudo_str



DEFAULT_TITLE =  __translate("HP Device Manager")

#QApplication.translate("ui_utils", "HPLIP Device Manager", None, QApplication.UnicodeUTF8)

def FailureUI(parent, error_text, title_text=None):
    log.error(pat_html_remove.sub(' ', unicode(error_text)))

    if title_text is None:
        if parent is not None:
            title_text = parent.windowTitle()
        else:
            title_text = DEFAULT_TITLE

    QMessageBox.critical(parent,
        title_text,
        error_text,
        QMessageBox.Ok,
        QMessageBox.NoButton,
        QMessageBox.NoButton)

showFailureUi = FailureUI


def WarningUI(parent,  warn_text, title_text=None):
    log.warn(pat_html_remove.sub(' ', unicode(warn_text)))

    if title_text is None:
        if parent is not None:
            title_text = parent.windowTitle()
        else:
            title_text = DEFAULT_TITLE


    QMessageBox.warning(parent,
        title_text,
        warn_text,
        QMessageBox.Ok,
        QMessageBox.NoButton,
        QMessageBox.NoButton)

showWarningUi = WarningUI


def SuccessUI(parent, text, title_text=None):
    log.info(pat_html_remove.sub(' ', unicode(text)))

    if title_text is None:
        if parent is not None:
            title_text = parent.windowTitle()
        else:
            title_text = DEFAULT_TITLE


    QMessageBox.information(parent,
        title_text,
        text,
        QMessageBox.Ok,
        QMessageBox.NoButton,
        QMessageBox.NoButton)

showSuccessUi = SuccessUI


def CheckDeviceUI(parent, title_text=None):
    text = __translate("<b>Unable to communicate with device or device is in an error state.</b><p>Please check device setup and try again.</p>")
    return FailureUI(parent, text, title_text)

checkDeviceUi = CheckDeviceUI


class PrinterNameValidator(QValidator):
    def __init__(self, parent=None):
        QValidator.__init__(self, parent)

    def validate(self, input, pos):
        input = unicode(input)

        if not input:
            return QValidator.Acceptable, pos

        if input[pos-1] in u"""~`!@#$%^&*()-=+[]{}()\\/,.<>?'\";:| """:
            return QValidator.Invalid, pos

        # TODO: How to determine if unicode char is "printable" and acceptable
        # to CUPS?
        #elif input != utils.printable(input):
        #    return QValidator.Invalid, pos

        return QValidator.Acceptable, pos



class PhoneNumValidator(QValidator):
    def __init__(self, parent=None):
        QValidator.__init__(self, parent)

    def validate(self, input, pos):
        input = unicode(input)

        if not input:
            return QValidator.Acceptable, pos

        if input[pos-1] not in u'0123456789-(+).,#* ':
            return QValidator.Invalid, pos

        return QValidator.Acceptable, pos


class AddressBookNameValidator(QValidator):
    def __init__(self, db, parent=None):
        QValidator.__init__(self, parent)
        self.db = db

    def validate(self, input, pos):
        input = unicode(input)

        if not input:
            return QValidator.Acceptable, pos

        if input in self.db.get_all_names():
            return QValidator.Invalid, pos

        if input[pos-1] in u'''|\\/"''': # | is the drag 'n drop separator
            return QValidator.Invalid, pos

        return QValidator.Acceptable, pos



MIME_TYPES_DESC = \
{
    "application/pdf" : (__translate("PDF Document"), '.pdf'),
    "application/postscript" : (__translate("Postscript Document"), '.ps'),
    "application/vnd.hp-HPGL" : (__translate("HP Graphics Language File"), '.hgl, .hpg, .plt, .prn'),
    "application/x-cshell" : (__translate("C Shell Script"), '.csh, .sh'),
    "application/x-csource" : (__translate("C Source Code"), '.c'),
    "text/cpp": (__translate("C++ Source Code"), '.cpp, .cxx'),
    "application/x-perl" : (__translate("Perl Script"), '.pl'),
    "application/x-python" : (__translate("Python Program"), '.py'),
    "application/x-shell" : (__translate("Shell Script"), '.sh'),
    "text/plain" : (__translate("Plain Text"), '.txt, .log'),
    "text/html" : (__translate("HTML Dcoument"), '.htm, .html'),
    "image/gif" : (__translate("GIF Image"), '.gif'),
    "image/png" : (__translate("PNG Image"), '.png'),
    "image/jpeg" : (__translate("JPEG Image"), '.jpg, .jpeg'),
    "image/tiff" : (__translate("TIFF Image"), '.tif, .tiff'),
    "image/x-bitmap" : (__translate("Bitmap (BMP) Image"), '.bmp'),
    "image/x-bmp" : (__translate("Bitmap (BMP) Image"), '.bmp'),
    "image/x-photocd" : (__translate("Photo CD Image"), '.pcd'),
    "image/x-portable-anymap" : (__translate("Portable Image (PNM)"), '.pnm'),
    "image/x-portable-bitmap" : (__translate("Portable B&W Image (PBM)"), '.pbm'),
    "image/x-portable-graymap" : (__translate("Portable Grayscale Image (PGM)"), '.pgm'),
    "image/x-portable-pixmap" : (__translate("Portable Color Image (PPM)"), '.ppm'),
    "image/x-sgi-rgb" : (__translate("SGI RGB"), '.rgb'),
    "image/x-xbitmap" : (__translate("X11 Bitmap (XBM)"), '.xbm'),
    "image/x-xpixmap" : (__translate("X11 Pixmap (XPM)"), '.xpm'),
    "image/x-sun-raster" : (__translate("Sun Raster Format"), '.ras'),
    "application/hplip-fax" : (__translate("HPLIP Fax File"), '.g3, .g4'),
}

# pixmaps for status list(s) (inkjet, laserjet)
status_icons = None

def getStatusListIcon(error_state):
    global status_icons
    if status_icons is None:
        status_icons = {
          ERROR_STATE_CLEAR : (load_pixmap('idle', '16x16'), load_pixmap('idle', '16x16')),
          ERROR_STATE_BUSY : (load_pixmap('busy', '16x16'), load_pixmap('busy', '16x16')),
          ERROR_STATE_ERROR : (load_pixmap('error', '16x16'), load_pixmap('error', '16x16')),
          ERROR_STATE_LOW_SUPPLIES : (load_pixmap('inkdrop', '16x16'), load_pixmap('toner', '16x16')),
          ERROR_STATE_OK : (load_pixmap('ok', '16x16'), load_pixmap('ok', '16x16')),
          ERROR_STATE_WARNING : (load_pixmap('warning', '16x16'), load_pixmap('warning', '16x16')),
          ERROR_STATE_LOW_PAPER: (load_pixmap('paper', '16x16'), load_pixmap('paper', '16x16')),
          ERROR_STATE_PRINTING : (load_pixmap("print", '16x16'), load_pixmap("print", '16x16')),
          ERROR_STATE_SCANNING : (load_pixmap("scan", '16x16'), load_pixmap("scan", '16x16')),
          ERROR_STATE_PHOTOCARD : (load_pixmap("pcard", '16x16'), load_pixmap("pcard", '16x16')),
          ERROR_STATE_FAXING : (load_pixmap("fax", '16x16'), load_pixmap("fax", '16x16')),
          ERROR_STATE_COPYING :  (load_pixmap("makecopies", '16x16'), load_pixmap("makecopies", '16x16')),
        }

    return status_icons.get(error_state, status_icons[ERROR_STATE_CLEAR])

# pixmaps for device icons (inkjet, laserjet)
overlay_icons = None

def getStatusOverlayIcon(error_state):
    global overlay_icons
    if overlay_icons is None:
        overlay_icons = {
            ERROR_STATE_CLEAR : (None, None),
            ERROR_STATE_BUSY : (load_pixmap('busy', '16x16'), load_pixmap('busy', '16x16')),
            ERROR_STATE_ERROR : (load_pixmap('error', '16x16'), load_pixmap('error', '16x16')),
            ERROR_STATE_LOW_SUPPLIES : (load_pixmap('inkdrop', '16x16'), load_pixmap('toner', '16x16')),
            ERROR_STATE_OK : (load_pixmap('ok', '16x16'), load_pixmap('ok', '16x16')),
            ERROR_STATE_WARNING : (load_pixmap('warning', '16x16'), load_pixmap('warning', '16x16')),
            ERROR_STATE_LOW_PAPER: (load_pixmap('paper', '16x16'), load_pixmap('paper', '16x16')),
            ERROR_STATE_PRINTING : (load_pixmap('busy', '16x16'), load_pixmap('busy', '16x16')),
            ERROR_STATE_SCANNING : (load_pixmap('busy', '16x16'), load_pixmap('busy', '16x16')),
            ERROR_STATE_PHOTOCARD : (load_pixmap('busy', '16x16'), load_pixmap('busy', '16x16')),
            ERROR_STATE_FAXING : (load_pixmap('busy', '16x16'), load_pixmap('busy', '16x16')),
            ERROR_STATE_COPYING : (load_pixmap('busy', '16x16'), load_pixmap('busy', '16x16')),
            ERROR_STATE_REFRESHING : (load_pixmap('refresh1', '16x16'), load_pixmap('refresh1', '16x16')),
        }

    return overlay_icons.get(error_state, overlay_icons[ERROR_STATE_CLEAR])


NUM_REPRS = {
      1 : __translate("one"),
      2 : __translate("two"),
      3 : __translate("three"),
      4 : __translate("four"),
      5 : __translate("five"),
      6 : __translate("six"),
      7 : __translate("seven"),
      8 : __translate("eight"),
      9 : __translate("nine"),
      10 : __translate("ten"),
      11 : __translate("eleven"),
      12 : __translate("twelve")
}

UNIT_NAMES = {
    "year" : (__translate("year"), __translate("years")),
    "month" : (__translate("month"), __translate("months")),
    "week" : (__translate("week"), __translate("weeks")),
    "day" : (__translate("day"), __translate("days")),
    "hour" : (__translate("hour"), __translate("hours")),
    "minute" : (__translate("minute"), __translate("minutes")),
    "second" : (__translate("second"), __translate("seconds")),
}


def getTimeDeltaDesc(past):
    t1 = QDateTime()
    t1.setTime_t(int(past))
    t2 = QDateTime.currentDateTime()
    delta = t1.secsTo(t2)
    return __translate("(%1 ago)").arg(stringify(delta))


# "Nicely readable timedelta"
# Credit: Bjorn Lindqvist
# ASPN Python Recipe 498062
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/498062
# Note: Modified from recipe
def getSecondsInUnits(seconds):
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


def stringify(seconds):
    amount, unit_name = getSecondsInUnits(seconds)

    try:
        i18n_amount = NUM_REPRS[amount]
    except KeyError:
        i18n_amount = unicode(amount)

    if amount == 1:
        i18n_unit = UNIT_NAMES[unit_name][0]
    else:
        i18n_unit = UNIT_NAMES[unit_name][1]

    return QString("%1 %2").arg(i18n_amount).arg(i18n_unit)


