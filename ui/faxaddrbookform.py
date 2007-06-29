# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
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

import sys, os, os.path, socket

from base.g import *
from base import utils, service

try:
    from fax import fax
except ImportError:
    # This can fail on Python < 2.3 due to the datetime module
    log.error("Fax address book disabled - Python 2.3+ required.")
    sys.exit(1)


from qt import *
from faxaddrbookform_base import FaxAddrBookForm_base
from faxaddrbookeditform_base import FaxAddrBookEditForm_base
from faxaddrbookgroupsform_base import FaxAddrBookGroupsForm_base
from faxaddrbookgroupeditform_base import FaxAddrBookGroupEditForm_base

# globals
db = None # kirbybase instance

# **************************************************************************** #

class AddressBookItem(QListViewItem):

    def __init__(self, parent, abe):
        QListViewItem.__init__(self, parent)
        self.abe = abe
        self.recno = abe.recno
        self.setText(0, abe.name)
        self.setText(1, abe.title)
        self.setText(2, abe.firstname)
        self.setText(3, abe.lastname)
        self.setText(4, abe.fax)
        self.setText(5, ', '.join(abe.group_list))
        self.setText(6, abe.notes)


class GroupValidator(QValidator):
    def __init__(self, parent=None, name=None):
        QValidator.__init__(self, parent, name)

    def validate(self, input, pos):
        input = str(input)
        if input.find(',') > 0:
            return QValidator.Invalid, pos
        elif len(input) > 50:
            return QValidator.Invalid, pos
        else:
            return QValidator.Acceptable, pos


class PhoneNumValidator(QValidator):
    def __init__(self, parent=None, name=None):
        QValidator.__init__(self, parent, name)

    def validate(self, input, pos):
        input = str(input)
        if not input:
            return QValidator.Acceptable, pos
        elif input[pos-1] not in '0123456789-(+) *#':
            return QValidator.Invalid, pos
        elif len(input) > 50:
            return QValidator.Invalid, pos
        else:
            return QValidator.Acceptable, pos


# **************************************************************************** #

class FaxAddrBookGroupEditForm(FaxAddrBookGroupEditForm_base):

    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        FaxAddrBookGroupEditForm_base.__init__(self,parent,name,modal,fl)
        self.edit_mode = False
        self.okButton.setEnabled(True)
        self.all_groups = db.AllGroups()
        self.groupnameEdit.setValidator(GroupValidator(self.groupnameEdit))

    def setDlgData(self, group_name):
        self.edit_mode = True
        self.groupnameEdit.setText(group_name)
        self.groupnameEdit.setReadOnly(True)
        self.setEntries(group_name)

    def setEntries(self, group_name=''):
        self.entriesListView.clear()

        all_entries = db.AllRecordEntries()

        for e in all_entries:
            i = QCheckListItem(self.entriesListView, e.name, QCheckListItem.CheckBox)

            if group_name and group_name in e.group_list:
                i.setState(QCheckListItem.On)

        self.CheckOKButton()


    def getDlgData(self):
        group_name = str(self.groupnameEdit.text())
        entries = []

        i = self.entriesListView.firstChild()

        while i is not None:
            if i.isOn():
                entries.append(str(i.text()))

            i = i.itemBelow()

        return group_name, entries


    def groupnameEdit_textChanged(self,a0):
        self.CheckOKButton()


    def entriesListView_clicked(self,a0):
        self.CheckOKButton()


    def CheckOKButton(self):
        group_name = str(self.groupnameEdit.text())

        if not group_name or \
            (not self.edit_mode and group_name in self.all_groups):

            self.okButton.setEnabled(False)
            return

        i = self.entriesListView.firstChild()

        while i is not None:
            if i.isOn():
                break

            i = i.itemBelow()

        else:
            self.okButton.setEnabled(False)
            return

        self.okButton.setEnabled(True)

# **************************************************************************** #

class FaxAddrBookGroupsForm(FaxAddrBookGroupsForm_base):

    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        FaxAddrBookGroupsForm_base.__init__(self,parent,name,modal,fl)

        self.current = None
        QTimer.singleShot(0, self.InitialUpdate)


    def InitialUpdate(self):
        self.UpdateList()


    def UpdateList(self):
        self.groupListView.clear()
        first_rec = None
        all_groups = db.AllGroups()

        if len(all_groups):

            for group in all_groups:
                i = QListViewItem(self.groupListView, group,
                                  ', '.join(db.GroupEntries(group)))

                if first_rec is None:
                    first_rec = i

            self.groupListView.setCurrentItem(i)
            self.current = i

            self.editButton.setEnabled(True)
            self.deleteButton.setEnabled(True)

        else:
            self.editButton.setEnabled(False)
            self.deleteButton.setEnabled(False)


    def newButton_clicked(self):
        dlg = FaxAddrBookGroupEditForm(self)
        dlg.setEntries()
        if dlg.exec_loop() == QDialog.Accepted:
            group_name, entries = dlg.getDlgData()
            db.UpdateGroupEntries(group_name, entries)
            self.UpdateList()

    def editButton_clicked(self):
        dlg = FaxAddrBookGroupEditForm(self)
        group_name = str(self.current.text(0))
        dlg.setDlgData(group_name)
        if dlg.exec_loop() == QDialog.Accepted:
            group_name, entries = dlg.getDlgData()
            db.UpdateGroupEntries(group_name, entries)
            self.UpdateList()


    def deleteButton_clicked(self):
        x = QMessageBox.critical(self,
                                 self.caption(),
                                 "<b>Annoying Confirmation: Are you sure you want to delete this group?</b>" ,
                                  QMessageBox.Yes,
                                  QMessageBox.No | QMessageBox.Default,
                                  QMessageBox.NoButton)
        if x == QMessageBox.Yes:
            db.DeleteGroup(str(self.current.text(0)))
            self.UpdateList()


    def groupListView_currentChanged(self, a0):
        self.current = a0


    def groupListView_doubleClicked(self, a0):
        self.editButton_clicked()


    def groupListView_rightButtonClicked(self, item, pos, a2):
        popup = QPopupMenu(self)

        popup.insertItem(self.__tr("New..."), self.newButton_clicked)

        if item is not None:
            popup.insertItem(self.__tr("Edit..."), self.editButton_clicked)
            popup.insertItem(self.__tr("Delete..."), self.deleteButton_clicked)

        popup.insertSeparator()
        popup.insertItem(self.__tr("Refresh List"), self.UpdateList)
        popup.popup(pos)

    def __tr(self,s,c = None):
        return qApp.translate("FAB",s,c)


# **************************************************************************** #


class FaxAddrBookEditForm(FaxAddrBookEditForm_base):

    def __init__(self, editing=True, parent = None,name = None,modal = 0,fl = 0):
        FaxAddrBookEditForm_base.__init__(self,parent,name,modal,fl)
        self.recno = -1
        self.editing = editing
        self.faxEdit.setValidator(PhoneNumValidator(self.faxEdit))
        self.initial_nickname = ''
        self.OKButton.setEnabled(self.editing)

    def setDlgData(self, abe):
        self.initial_nickname = abe.name
        self.recno = abe.recno
        self.titleEdit.setText(abe.title)
        self.firstnameEdit.setText(abe.firstname)
        self.lastnameEdit.setText(abe.lastname)
        self.faxEdit.setText(abe.fax)
        self.notesEdit.setText(abe.notes)
        self.nicknameEdit.setText(abe.name)
        self.setGroups(abe.group_list)

    def setGroups(self, entry_groups=[]):
        self.groupListView.clear()

        for g in db.AllGroups():
            i = QCheckListItem(self.groupListView, g, QCheckListItem.CheckBox)

            if g in entry_groups:
                i.setState(QCheckListItem.On)

    def getDlgData(self):
        in_groups = []
        i = self.groupListView.firstChild()

        while i is not None:
            if i.isOn():
                in_groups.append(str(i.text()))
            i = i.itemBelow()

        return fax.AddressBookEntry((
            self.recno,
            str(self.nicknameEdit.text()),
            str(self.titleEdit.text()),
            str(self.firstnameEdit.text()),
            str(self.lastnameEdit.text()),
            str(self.faxEdit.text()),
            ', '.join(in_groups),
            str(self.notesEdit.text())))


    def firstnameEdit_textChanged(self,a0):
        pass


    def lastnameEdit_textChanged(self,a0):
        pass


    def groupsButton2_clicked(self): # New Group...
        new_group_name, ok = QInputDialog.getText(self.__tr("New Fax Group"),
                                                   self.__tr("New Group Name:"))

        if ok and len(new_group_name):
            new_group_name = str(new_group_name)
            abe = db.GetEntryByRecno(self.recno)

            if new_group_name not in abe.group_list:
                abe.group_list.append(new_group_name)
                db.update(['recno'], [self.recno], [','.join(abe.group_list)], ['groups'])
                self.setGroups(abe.group_list)


    def nicknameEdit_textChanged(self, nickname):
        self.CheckOKButton(nickname, None)


    def faxEdit_textChanged(self, fax):
        self.CheckOKButton(None, fax)


    def CheckOKButton(self, nickname=None, fax=None):
        if nickname is None:
            nickname = str(self.nicknameEdit.text())

        if fax is None:
            fax = str(self.faxEdit.text())

        ok = bool(len(nickname) and len(fax))

        if nickname:
            for x in db.AllRecordEntries():
                if nickname == x.name and nickname != self.initial_nickname:
                    ok = False

        self.OKButton.setEnabled(ok)


    def __tr(self,s,c = None):
        return qApp.translate("FAB",s,c)

# **************************************************************************** #

class FaxAddrBookForm(FaxAddrBookForm_base):

    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        FaxAddrBookForm_base.__init__(self,parent,name,modal,fl)

        icon = QPixmap(os.path.join(prop.image_dir, 'HPmenu.png'))
        self.setIcon(icon)

        global db
        db =  fax.FaxAddressBook()
        self.init_problem = False
        self.current = None

        try:
            invalids = db.validate()
        except:
            invalids = True

        if invalids:
            log.error("Fax address book file is invalid")

            if type(invalids) == type([]):
                log.error(invalids)

            self.FailureUI(self.__tr("<b>Fax address book file %s is invalid.</b><p>Please check the file for problems." % db.filename()))
            self.init_problem = True

        db.pack()

        self.all_groups = []

        try:
            self.hpssd_sock = service.startup()
        except Error:
            log.error("Unable to connect to HPLIP I/O (hpssd).")
            self.init_problem = True

        QTimer.singleShot(0, self.InitialUpdate)


    def InitialUpdate(self):
        if self.init_problem:
            self.close()
            return

        self.UpdateList()


    def UpdateList(self):
        self.addressListView.clear()
        first_rec = None
        all_entries = db.AllRecordEntries()
        log.debug("Number of records is: %d" % len(all_entries))

        if len(all_entries) > 0:

            for abe in all_entries:
                i = AddressBookItem(self.addressListView, abe)

                if first_rec is None:
                    first_rec = i

            self.addressListView.setCurrentItem(i)
            self.current = i

            self.editButton.setEnabled(True)
            self.deleteButton.setEnabled(True)

        else:
            self.editButton.setEnabled(False)
            self.deleteButton.setEnabled(False)


    def groupButton_clicked(self):
        FaxAddrBookGroupsForm(self).exec_loop()
        self.sendUpdateEvent()
        self.UpdateList()

    def newButton_clicked(self):
        dlg = FaxAddrBookEditForm(False, self)
        dlg.setGroups()
        dlg.groupsButton2.setEnabled(False)
        if dlg.exec_loop() == QDialog.Accepted:
            db.insert(dlg.getDlgData())
            self.sendUpdateEvent()
            self.UpdateList()

    def CurrentRecordEntry(self):
        return fax.AddressBookEntry(db.select(['recno'], [self.current.recno])[0])

    def editButton_clicked(self):
        dlg = FaxAddrBookEditForm(True, self)
        dlg.setDlgData(self.CurrentRecordEntry())
        if dlg.exec_loop() == QDialog.Accepted:
            db.update(['recno'], [self.current.recno], dlg.getDlgData())
            self.sendUpdateEvent()
            self.UpdateList()


    def deleteButton_clicked(self):
        x = QMessageBox.critical(self,
                                 self.caption(),
                                 "<b>Annoying Confirmation: Are you sure you want to delete this address book entry?</b>" ,
                                  QMessageBox.Yes,
                                  QMessageBox.No | QMessageBox.Default,
                                  QMessageBox.NoButton)
        if x == QMessageBox.Yes:
            db.delete(['recno'], [self.current.recno])
            self.UpdateList()
            self.sendUpdateEvent()


    def addressListView_rightButtonClicked(self, item, pos, a2):
        popup = QPopupMenu(self)

        popup.insertItem(self.__tr("New..."), self.newButton_clicked)

        if item is not None:
            popup.insertItem(self.__tr("Edit..."), self.editButton_clicked)
            popup.insertItem(self.__tr("Delete..."), self.deleteButton_clicked)

        popup.insertSeparator()
        popup.insertItem(self.__tr("Refresh List"), self.UpdateList)
        popup.popup(pos)


    def addressListView_doubleClicked(self,a0):
        self.editButton_clicked()


    def addressListView_currentChanged(self,item):
        self.current = item


    def FailureUI(self, error_text):
        log.error(str(error_text).replace("<b>", "").replace("</b>", "").replace("<p>", ""))
        QMessageBox.critical(self,
                             self.caption(),
                             error_text,
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)


    def __tr(self,s,c = None):
        return qApp.translate("FAB",s,c)

    def accept(self):
        self.sendUpdateEvent()
        if self.hpssd_sock is not None:
            self.hpssd_sock.close()

        FaxAddrBookForm_base.accept(self)

    def sendUpdateEvent(self):
        if self.hpssd_sock is not None:
            service.sendEvent(self.hpssd_sock, EVENT_FAX_ADDRESS_BOOK_UPDATED)

