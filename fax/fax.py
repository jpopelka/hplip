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

from __future__ import generators

# Std Lib
import sys
import os
import threading
import cPickle
import time
from cStringIO import StringIO
import struct

# Local
from base.g import *
from base.codes import *
from base import device, utils, msg, service, msg
from base.kirbybase import KirbyBase
from prnt import cups


try:
    import coverpages
except ImportError:
    pass
    
# Update queue values (Send thread ==> UI)
STATUS_IDLE = 0
STATUS_PROCESSING_FILES = 1
STATUS_DIALING = 2
STATUS_CONNECTING = 3
STATUS_SENDING = 4
STATUS_COMPLETED = 5
STATUS_CREATING_COVER_PAGE = 6
STATUS_ERROR = 7
STATUS_BUSY = 8
STATUS_CLEANUP = 9

# Event queue values (UI ==> Send thread)
EVENT_FAX_SEND_CANCELED = 1
# Other values in queue are:
#EVENT_FAX_RENDER_COMPLETE_BEGIN = 8010
#EVENT_FAX_RENDER_COMPLETE_SENDDATA = 8011
#EVENT_FAX_RENDER_COMPLETE_END = 8012

# **************************************************************************** #
# HPLIP G3 Fax File Format (big endian)
#
# #==============================================#
# # File Header: Total 28 bytes                  #
# #..............................................#
# # Magic bytes: 8 bytes ("hplip_g3")            #
# # Format version: 8 bits (1)                   #
# # Total pages in file(=p): 32 bits             #
# # Hort DPI: 16 bits (200 or 300)               #
# # Vert DPI: 16 bits (100, 200, or 300)         #
# # Page Size: 8 bits (0=Unk, 1=Letter, 2=A4,    #
# #                    3=Legal)                  #
# # Resolution: 8 bits (0=Unk, 1=Std, 2=Fine,    #
# #                     3=300DPI)                #
# # Encoding: 8 bits (2=MH, 4=MMR, 7=JPEG)       #
# # Reserved1: 32 bits (0)                       #
# # Reserved2: 32 bits (0)                       #
# #----------------------------------------------#
# # Page 1 Header: Total 24 bytes                #
# #..............................................#
# # Page number: 32 bits (1 based)               #
# # Pixels per row: 32 bits                      #
# # Rows this page: 32 bits                      #
# # Image bytes this page(=x): 32 bits           #
# # Thumbnail bytes this page(=y): 32 bits       #
# #  (thumbnail not present if y == 0)           #
# #  (encoding?)                                 #
# #     letter: 134 px wide x 173 px high        #
# #     legal:  134 px wide x 221 px high        #
# #     a4 :    134 px wide x 190 px high        #
# # Reserved3: 32 bits (0)                       #
# #..............................................#
# # Image data: x bytes                          #
# #..............................................#
# # Thumbnail data: y bytes (if present)         #
# #----------------------------------------------#
# # Page 2 Header: Total 24 bytes                #
# #..............................................#
# # Image Data                                   #
# #..............................................#
# # Thumbnail data (if present)                  #
# #----------------------------------------------#
# # ... Pages 3 - (p-1) ...                      #
# #----------------------------------------------#
# # Page p Header: Total 24 bytes                #
# #..............................................#
# # Image Data                                   #
# #..............................................#
# # Thumbnail data (if present)                  #
# #==============================================#
#

FILE_HEADER_SIZE = 28
PAGE_HEADER_SIZE = 24
    

# **************************************************************************** #
class FaxAddressBook2(object): # Pickle based address book
    def __init__(self):
        self._data = {}
        #
        # { 'name' : {'name': 'name',
        #             'firstname' : u'', 
        #             'lastname': u',
        #             'title' : u'', 
        #             'fax': u'',
        #             'groups' : [u'', u'', ...],
        #             'notes' : u'', } ...
        # }
        #
        self.load()

    def load(self):
        self._fab = os.path.join(prop.user_dir, "fab.pickle")
        old_fab = os.path.join(prop.user_dir, "fab.db")

        # Load the existing pickle if present
        if os.path.exists(self._fab):
            pickle_file = open(self._fab, "r")
            self._data = cPickle.load(pickle_file)
            pickle_file.close()

        elif os.path.exists(old_fab): # convert old KirbyBase file
            db = FaxAddressBook()
            all_entries = db.AllRecordEntries()

            for e in all_entries:
                try:
                    self.set(e.name, e.title, e.firstname, e.lastname,
                             e.fax, e.group_list, e.notes)
                except UnicodeDecodeError:
                    self.set(e.name.decode('utf-8'), 
                             e.title.decode('utf-8'),
                             e.firstname.decode('utf-8'),
                             e.lastname.decode('utf-8'),
                             e.fax.decode('utf-8'),
                             e.group_list, 
                             e.notes.decode('utf-8'))
            self.save()

        else:
            self.save() # save the empty file to create the file


    def set(self, name, title, firstname, lastname, fax, groups, notes):
        try:
            grps = [unicode(s) for s in groups]
        except UnicodeDecodeError:
            grps = [unicode(s.decode('utf-8')) for s in groups]

        self._data[unicode(name)] = {'name' : unicode(name),
                                    'title': unicode(title), 
                                    'firstname': unicode(firstname),
                                    'lastname': unicode(lastname),
                                    'fax': unicode(fax), 
                                    'notes': unicode(notes),
                                    'groups': grps}

        self.save()

    insert = set

    def get(self, name):
        return self._data.get(name, None)

    select = get

    def get_all_groups(self):
        all_groups = []
        for e, v in self._data.items():
            for g in v['groups']:
                if g not in all_groups:
                    all_groups.append(g)
        return all_groups

    def get_all_records(self):
        return self._data

    def get_all_names(self):
        return self._data.keys()

    def save(self):
        try:
            pickle_file = open(self._fab, "w")
            cPickle.dump(self._data, pickle_file, cPickle.HIGHEST_PROTOCOL)
            pickle_file.close()
        except IOError:
            log.error("I/O error saving fab file.")

    def clear(self):
        self._data = {}

    def delete(self, name):
        if name in self._data: #self.current
            del self._data[name]
            return True

        return False

    def last_modification_time(self):
        try:
            return os.stat(self._fab).st_mtime
        except OSError:
            return 0

    def update_groups(self, group, members):
        for e, v in self._data.items():
            if v['name'] in members: # membership indicated
                if not group in v['groups']:
                    v['groups'].append(unicode(group))
            else:
                if group in v['groups']:
                    v['groups'].remove(unicode(group))

    def delete_group(self, group):
        for e, v in self._data.items():
            if group in v['groups']:
                v['groups'].remove(unicode(group))

    def group_members(self, group):
        members = []
        for e, v in self._data.items():
            if group in v['groups']:
                members.append(e)
        return members


# **************************************************************************** #

# DEPRECATED: TO BE REMOVED
class FaxAddressBook(KirbyBase): # KirbyBase based address book
    def __init__(self):
        KirbyBase.__init__(self)
        # Transitional code to handle moving of db file
        t1 = os.path.expanduser('~/.hplip.fab') # old location #1
        t2 = os.path.expanduser('~/hpfax/hplip.fab') # old location #2
        self._fab = os.path.join(prop.user_dir, 'fab.db') # new location
        log.debug("fab.db: %s" % self._fab)

        if os.path.exists(t1) and not os.path.exists(self._fab):
            import shutil
            log.debug("Copying %s to %s..." % (t1, self._fab))
            shutil.move(t1, self._fab)

        elif os.path.exists(t2) and not os.path.exists(self._fab):
            import shutil
            log.debug("Copying %s to %s..." % (t2, self._fab))
            shutil.move(t2, self._fab)

        if not os.path.exists(self._fab):
            log.debug("Creating new fax address book: %s" % self._fab)
            self.create()

    def create(self):
        return KirbyBase.create(self, self._fab,
            ['name:str',
             'title:str',
             'firstname:str',
             'lastname:str',
             'fax:str',
             'groups:str', # comma sep list of group names
             'notes:str'])

    def filename(self):
        return self._fab

    def last_modification_time(self):
        return os.stat(self._fab).st_mtime

    def close(self):
        return KirbyBase.close(self)

    def insert(self, values):
        return KirbyBase.insert(self, self._fab, values)

    def insertBatch(self, batchRecords):
        return KirbyBase.insertBatch(self, self._fab, batchRecords)

    def update(self, fields, searchData, updates, filter=None, useRegExp=False):
        return KirbyBase.update(self, self._fab, fields, searchData, updates, filter, useRegExp)

    def delete(self, fields, searchData, useRegExp=False):
        return KirbyBase.delete(self, self._fab, fields, searchData, useRegExp)

    def select(self, fields, searchData, filter=None, useRegExp=False, sortFields=[],
        sortDesc=[], returnType='list', rptSettings=[0,False]):
        return KirbyBase.select(self, self._fab, fields, searchData, filter,
            useRegExp, sortFields, sortDesc, returnType, rptSettings)

    def pack(self):
        return KirbyBase.pack(self, self._fab)

    def validate(self):
        return KirbyBase.validate(self, self._fab)

    def drop(self):
        return KirbyBase.drop(self, self._fab)

    def getFieldNames(self):
        return KirbyBase.getFieldNames(self, self._fab)

    def getFieldTypes(self):
        return KirbyBase.getFieldTypes(self, self._fab)

    def len(self):
        return KirbyBase.len(self, self._fab)

    def GetEntryByRecno(self, recno):
        return AddressBookEntry(self.select(['recno'], [recno])[0])

    def AllRecords(self):
        return self.select(['recno'], ['*'])

    def AllRecordEntries(self):
        return [AddressBookEntry(rec) for rec in self.select(['recno'], ['*'])]

    def GroupEntries(self, group):
        return [abe.name for abe in self.AllRecordEntries() if group in abe.group_list]

    def AllGroups(self):
        temp = {}
        for abe in self.AllRecordEntries():
            for g in abe.group_list:
                temp.setdefault(g)

        return temp.keys()

    def UpdateGroupEntries(self, group_name, member_entries):
        for entry in self.AllRecordEntries():

            if entry.name in member_entries: # membership indicated

                if not group_name in entry.group_list: # entry already member of group
                    # add it
                    entry.group_list.append(group_name)
                    self.update(['recno'], [entry.recno], [','.join(entry.group_list)], ['groups'])
            else:

                if group_name in entry.group_list: # remove from entry
                    entry.group_list.remove(group_name)
                    self.update(['recno'], [entry.recno], [','.join(entry.group_list)], ['groups'])

    def DeleteGroup(self, group_name):
        for entry in self.AllRecordEntries():
            if group_name in entry.group_list:
                entry.group_list.remove(group_name)
                self.update(['recno'], [entry.recno], [','.join(entry.group_list)], ['groups'])


# **************************************************************************** #
# DEPRECATED: TO BE REMOVED
class AddressBookEntry(object):
    def __init__(self, rec=None):
        if rec is not None:
            rec = [x or '' for x in rec]
            self.recno, self.name, \
            self.title, self.firstname, self.lastname, \
            self.fax, self.groups, self.notes = rec
            self.group_list = []

            if len(self.groups):
                for g in self.groups.split(','):
                    self.group_list.append(g.strip())

    def __str__(self):
        return "Recno=%d, Name=%s, Title=%s, First=%s, Last=%s, Fax=%s, Groups=%s, Notes=%s\n" % \
            (self.recno, self.name, self.title, self.firstname,
              self.lastname, self.fax, self.group_list, self.notes)


# **************************************************************************** #
class FaxDevice(device.Device):

    def __init__(self, device_uri=None, printer_name=None,
                 hpssd_sock=None, callback=None, 
                 fax_type=FAX_TYPE_NONE):

        device.Device.__init__(self, device_uri, printer_name,
                               hpssd_sock, callback)

        self.send_fax_thread = None
        self.upload_log_thread = None
        self.fax_type = fax_type
        #self.fax_type = self.mq['fax-type']

    def setPhoneNum(self, num):
        raise AttributeError
        #return self.setPML(pml.OID_FAX_LOCAL_PHONE_NUM, str(num))

    def getPhoneNum(self):
        raise AttributeError
        #return utils.printable(str(self.getPML(pml.OID_FAX_LOCAL_PHONE_NUM)[1]))

    phone_num = property(getPhoneNum, setPhoneNum)


    def setStationName(self, name):
        raise AttributeError
        #return self.setPML(pml.OID_FAX_STATION_NAME, str(name))

    def getStationName(self):
        raise AttributeError
        #return utils.printable(str(self.getPML(pml.OID_FAX_STATION_NAME)[1]))

    station_name = property(getStationName, setStationName)

    def setDateAndTime(self):
        raise AttributeError
##        t = time.localtime()
##        p = struct.pack("BBBBBBB", t[0]-2000, t[1], t[2], t[6]+1, t[3], t[4], t[5])
##        log.debug(repr(p))
##        return self.setPML(pml.OID_DATE_AND_TIME, p)

    def uploadLog(self):
        raise AttributeError
##        if not self.isUloadLogActive():
##            self.upload_log_thread = UploadLogThread(self)
##            self.upload_log_thread.start()
##            return True
##        else:
##            return False

    def isUploadLogActive(self):
        raise AttributeError

    def waitForUploadLogThread(self):
        raise AttributeError

    def sendFaxes(self, phone_num_list, fax_file_list, cover_message='', cover_re='', 
                  cover_func=None, preserve_formatting=False, printer_name='', 
                  update_queue=None, event_queue=None):

        raise AttributeError

    def isSendFaxActive(self):
        if self.send_fax_thread is not None:
            return self.send_fax_thread.isAlive()
        else:
            return False

    def waitForSendFaxThread(self):
        if self.send_fax_thread is not None and \
            self.send_fax_thread.isAlive():

            try:
                self.send_fax_thread.join()
            except KeyboardInterrupt:
                pass


# **************************************************************************** #

def getFaxDevice(device_uri=None, printer_name=None,
                 hpssd_sock=None, callback=None, 
                 fax_type=FAX_TYPE_NONE):
                 
    if fax_type == FAX_TYPE_NONE:
        if device_uri is None and printer_name is not None:
            printers = cups.getPrinters()
    
            for p in printers:
                if p.name.lower() == printer_name.lower():
                    device_uri = p.device_uri
                    break
            else:
                raise Error(ERROR_DEVICE_NOT_FOUND)
                
        if device_uri is not None:
            mq = device.queryModelByURI(device_uri)
            fax_type = mq['fax-type']
            
    log.debug("fax-type=%d" % fax_type)
                    
    if fax_type in (FAX_TYPE_BLACK_SEND_EARLY_OPEN, FAX_TYPE_BLACK_SEND_LATE_OPEN):
        from pmlfax import PMLFaxDevice
        return PMLFaxDevice(device_uri, printer_name, hpssd_sock, callback, fax_type)

    else:
        raise Error(ERROR_DEVICE_DOES_NOT_SUPPORT_OPERATION)



# **************************************************************************** #

# TODO: Define these in only 1 place!
STATE_DONE = 0
STATE_ABORTED = 10
STATE_SUCCESS = 20
STATE_BUSY = 25
STATE_READ_SENDER_INFO = 30
STATE_PRERENDER = 40
STATE_COUNT_PAGES = 50
STATE_NEXT_RECIPIENT = 60
STATE_COVER_PAGE = 70
STATE_SINGLE_FILE = 80
STATE_MERGE_FILES = 90
STATE_SINGLE_FILE = 100
STATE_SEND_FAX = 110
STATE_CLEANUP = 120
STATE_ERROR = 130 
    
class FaxSendThread(threading.Thread):
    def __init__(self, dev, phone_num_list, fax_file_list, 
                 cover_message='', cover_re='', cover_func=None, preserve_formatting=False,
                 printer_name='', update_queue=None, event_queue=None):

        threading.Thread.__init__(self)
        self.dev = dev # device.Device
        self.phone_num_list = phone_num_list
        self.fax_file_list = fax_file_list
        self.update_queue = update_queue
        self.event_queue = event_queue
        self.cover_message = cover_message
        self.cover_re = cover_re
        self.cover_func = cover_func
        self.current_printer = printer_name
        self.stream = StringIO()  
        self.prev_update = ''
        self.remove_temp_file = False
        self.preserve_formatting = preserve_formatting
        self.results = {} # {'file' : error_code,...}
        self.cover_page_present = False
        self.recipient_file_list = []
        self.f = None # final file of fax data to send (pages merged)
        self.job_hort_dpi = 0
        self.job_hort_dpi = 0
        self.job_vert_dpi = 0
        self.job_page_size = 0
        self.job_resolution = 0
        self.job_encoding = 0


    def pre_render(self, state):
        # pre-render each page that needs rendering
        # except for the cover page
        self.cover_page_present = False
        log.debug(self.fax_file_list)

        for fax_file in self.fax_file_list: # (file, type, desc, title)
            fax_file_name, fax_file_type, fax_file_desc, \
                fax_file_title, fax_file_pages = fax_file

            if fax_file_type == "application/hplip-fax-coverpage": # render later
                self.cover_page_present = True
                log.debug("Skipping coverpage")

            #if fax_file_type == "application/hplip-fax": # already rendered
            else:
                self.rendered_file_list.append((fax_file_name, "application/hplip-fax",
                    "HP Fax", fax_file_title))

                log.debug("Processing pre-rendered file: %s (%d pages)" % 
                    (fax_file_name, fax_file_pages))

            if self.check_for_cancel():
                state = STATE_ABORTED

        log.debug(self.rendered_file_list)  

        if self.check_for_cancel():
            state = STATE_ABORTED

        return state


    def count_pages(self, state):
        self.recipient_file_list = self.rendered_file_list[:]
        log.debug("Counting total pages...")
        self.job_total_pages = 0
        log.debug(self.recipient_file_list)

        i = 0
        for fax_file in self.recipient_file_list: # (file, type, desc, title)
            fax_file_name = fax_file[0]
            log.debug("Processing file (counting pages): %s..." % fax_file_name)

            #self.write_queue((STATUS_PROCESSING_FILES, self.job_total_pages, ''))

            if os.path.exists(fax_file_name):
                self.results[fax_file_name] = ERROR_SUCCESS
                fax_file_fd = file(fax_file_name, 'r')
                header = fax_file_fd.read(FILE_HEADER_SIZE)

                magic, version, total_pages, hort_dpi, vert_dpi, page_size, \
                    resolution, encoding, reserved1, reserved2 = \
                        self.decode_fax_header(header)

                if magic != 'hplip_g3':
                    log.error("Invalid file header. Bad magic.")
                    self.results[fax_file_name] = ERROR_FAX_INVALID_FAX_FILE
                    state = STATE_ERROR
                    continue

                if not i:
                    self.job_hort_dpi, self.job_vert_dpi, self.job_page_size, \
                        self.job_resolution, self.job_encoding = \
                        hort_dpi, vert_dpi, page_size, resolution, encoding

                    i += 1
                else:
                    if self.job_hort_dpi != hort_dpi or \
                        self.job_vert_dpi != vert_dpi or \
                        self.job_page_size != page_size or \
                        self.job_resolution != resolution or \
                        self.job_encoding != encoding:

                        log.error("Incompatible options for file: %s" % fax_file_name)
                        self.results[fax_file_name] = ERROR_FAX_INCOMPATIBLE_OPTIONS
                        state = STATE_ERROR


                log.debug("Magic=%s Ver=%d Pages=%d hDPI=%d vDPI=%d Size=%d Res=%d Enc=%d" %
                          (magic, version, total_pages, hort_dpi, 
                           vert_dpi, page_size, resolution, encoding))

                self.job_total_pages += total_pages

                fax_file_fd.close()

            else:
                log.error("Unable to find HP Fax file: %s" % fax_file_name)
                self.results[fax_file_name] = ERROR_FAX_FILE_NOT_FOUND
                state = STATE_ERROR
                break

            if self.check_for_cancel():
                state = STATE_ABORTED
                break


        if self.cover_page_present:
            self.job_total_pages += 1 # Cover pages are truncated to 1 page

        log.debug("Total fax pages=%d" % self.job_total_pages)

        return state


    def cover_page(self,  recipient):
        if self.job_total_pages > 1:
            state = STATE_MERGE_FILES
        else:
            state = STATE_SINGLE_FILE

        if self.cover_page_present:
            log.debug("Creating cover page for recipient: %s" % recipient['name'])
            fax_file, canceled = self.render_cover_page(recipient)

            if canceled:
                state = STATE_ABORTED
            elif not fax_file:
                state = STATE_ERROR # timeout
            else:
                self.recipient_file_list.insert(0, (fax_file, "application/hplip-fax", 
                                                    "HP Fax", 'Cover Page'))

                log.debug("Cover page G3 file: %s" % fax_file)

                self.results[fax_file] = ERROR_SUCCESS

        return state

    def single_file(self, state):
        state = STATE_SEND_FAX

        log.debug("Processing single file...")

        self.f = self.recipient_file_list[0][0]

        try:
            f_fd = file(self.f, 'r')
        except IOError:
            log.error("Unable to open fax file: %s" % self.f)
            state = STATE_ERROR
        else:
            header = f_fd.read(FILE_HEADER_SIZE)

            magic, version, total_pages, hort_dpi, vert_dpi, page_size, \
                resolution, encoding, reserved1, reserved2 = self.decode_fax_header(header)

            self.results[self.f] = ERROR_SUCCESS

            if magic != 'hplip_g3':
                log.error("Invalid file header. Bad magic.")
                self.results[self.f] = ERROR_FAX_INVALID_FAX_FILE
                state = STATE_ERROR

            log.debug("Magic=%s Ver=%d Pages=%d hDPI=%d vDPI=%d Size=%d Res=%d Enc=%d" %
                      (magic, version, total_pages, hort_dpi, vert_dpi, 
                       page_size, resolution, encoding))

            f_fd.close()

        return state


    def merge_files(self, state):
        log.debug("%s State: Merge multiple files" % ("*"*20))
        log.debug(self.recipient_file_list)
        log.debug("Merging g3 files...")
        self.remove_temp_file = True

        if self.job_total_pages:
            f_fd, self.f = utils.make_temp_file()
            log.debug("Temp file=%s" % self.f)

            data = struct.pack(">8sBIHHBBBII", "hplip_g3", 1L, self.job_total_pages,  
                self.job_hort_dpi, self.job_vert_dpi, self.job_page_size, 
                self.job_resolution, self.job_encoding, 
                0L, 0L)

            os.write(f_fd, data)

            job_page_num = 1

            for fax_file in self.recipient_file_list:
                fax_file_name = fax_file[0]
                log.debug("Processing file: %s..." % fax_file_name)

                if self.results[fax_file_name] == ERROR_SUCCESS:
                    fax_file_fd = file(fax_file_name, 'r')
                    header = fax_file_fd.read(FILE_HEADER_SIZE)

                    magic, version, total_pages, hort_dpi, vert_dpi, page_size, \
                        resolution, encoding, reserved1, reserved2 = self.decode_fax_header(header)

                    if magic != 'hplip_g3':
                        log.error("Invalid file header. Bad magic.")
                        state = STATE_ERROR
                        break

                    log.debug("Magic=%s Ver=%d Pages=%d hDPI=%d vDPI=%d Size=%d Res=%d Enc=%d" %
                              (magic, version, total_pages, hort_dpi, vert_dpi, page_size, resolution, encoding))

                    for p in range(total_pages):
                        header = fax_file_fd.read(PAGE_HEADER_SIZE)

                        page_num, ppr, rpp, bytes_to_read, thumbnail_bytes, reserved2 = \
                            self.decode_page_header(header)

                        if page_num == -1:
                            log.error("Page header error")
                            state - STATE_ERROR
                            break

                        header = struct.pack(">IIIIII", job_page_num, ppr, rpp, bytes_to_read, thumbnail_bytes, 0L)
                        os.write(f_fd, header)

                        self.write_queue((STATUS_PROCESSING_FILES, job_page_num, ''))

                        log.debug("Page=%d PPR=%d RPP=%d BPP=%d Thumb=%s" %
                                  (page_num, ppr, rpp, bytes_to_read, thumbnail_bytes))                    

                        os.write(f_fd, fax_file_fd.read(bytes_to_read))
                        job_page_num += 1

                    fax_file_fd.close()

                    if self.check_for_cancel():
                        state = STATE_ABORTED
                        break

                else:
                    log.error("Skipping file: %s" % fax_file_name)
                    continue

            os.close(f_fd)
            log.debug("Total pages=%d" % self.job_total_pages)

        return state


    def next_recipient_gen(self):
        for a in self.phone_num_list:
            yield a


    def render_file(self, path, title, mime_type, force_single_page=False):
        all_pages = True 
        page_range = ''
        page_set = 0
        nup = 1

        cups.resetOptions()

        if mime_type in ["application/x-cshell",
                         "application/x-perl",
                         "application/x-python",
                         "application/x-shell",
                         "text/plain",]:

            cups.addOption('prettyprint')

        if nup > 1:
            cups.addOption('number-up=%d' % nup)

        if force_single_page:
            cups.addOption('page-ranges=1') # Force coverpage to 1 page

        sent_job_id = cups.printFile(self.current_printer, path, title)
        cups.resetOptions()

        log.debug("Job ID=%d" % sent_job_id)    
        job_id = 0

        time.sleep(1)

        fax_file = ''
        complete = False

        try:
            sock = service.startup()
        except Error:
            return '', True   

        end_time = time.time() + 120.0 
        while time.time() < end_time:
            log.debug("Waiting for fax...")
            fields, data, result_code = \
                msg.xmitMessage(sock, "FaxCheck", None,
                                     {"username": prop.username,
                                     })

            if result_code == ERROR_FAX_PROCESSING:
                log.debug("Fax is being rendered...")

            elif result_code == ERROR_FAX_READY:
                break

            if self.check_for_cancel():
                log.error("Render canceled. Canceling job #%d..." % sent_job_id)
                cups.cancelJob(sent_job_id)
                sock.close()
                return '', True

            time.sleep(1)

        else:
            log.error("Timeout waiting for rendering. Canceling job #%d..." % sent_job_id)
            cups.cancelJob(sent_job_id)
            return '', False

        fd, fax_file = utils.make_temp_file()

        while True:
            log.debug("Transfering fax data...")
            fields, data, result_code = \
                msg.xmitMessage(sock, "FaxGetData", None,
                                     {"username": prop.username,
                                      "job-id": sent_job_id,
                                     })

            if data and result_code == ERROR_SUCCESS:
                os.write(fd, data)

            else:
                complete = True
                break

            if self.check_for_cancel():
                log.error("Render canceled. Canceling job #%d..." % sent_job_id)
                cups.cancelJob(sent_job_id)
                os.close(fd)
                sock.close()
                return '', True


        os.close(fd)
        sock.close()

        return fax_file, False


    def check_for_cancel(self):
        canceled = False
        while self.event_queue.qsize():
            try:
                event = self.event_queue.get(0)
                if event[0] == EVENT_FAX_SEND_CANCELED:
                    canceled = True
                    log.debug("Cancel pressed!")
            except Queue.Empty:
                break

        return canceled

    def render_cover_page(self, a):
        log.debug("Creating cover page...")

        pdf = self.cover_func(page_size=coverpages.PAGE_SIZE_LETTER,
                              total_pages=self.job_total_pages, 

                              recipient_name=a['name'], 
                              recipient_phone='', # ???
                              recipient_fax=a['fax'], 

                              sender_name=self.sender_name, 
                              sender_phone=user_cfg.fax.voice_phone, 
                              sender_fax=self.sender_fax,
                              sender_email=user_cfg.fax.email_address, 

                              regarding=self.cover_re, 
                              message=self.cover_message,
                              preserve_formatting=self.preserve_formatting)

        log.debug("PDF File=%s" % pdf)
        fax_file, canceled = self.render_file(pdf, 'Cover Page', "application/pdf", 
            force_single_page=True) 

        try:
            os.remove(pdf)
        except IOError:
            pass

        return fax_file, canceled


    def write_queue(self, message):
        if self.update_queue is not None and message != self.prev_update:
            self.update_queue.put(message)
            time.sleep(0)
            self.prev_update = message

