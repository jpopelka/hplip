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
import sys, os, os.path, mmap, struct, time, threading, Queue, socket
from cStringIO import StringIO
import cPickle

# Local
from base.g import *
from base.codes import *
from base import device, utils, status, pml, msg, service
from base.kirbybase import KirbyBase
from prnt import cups

try:
    import coverpages
except ImportError:
    pass

# **************************************************************************** #

# Page flags 
PAGE_FLAG_NONE = 0x00
PAGE_FLAG_NEW_PAGE = 0x01
PAGE_FLAG_END_PAGE = 0x02
PAGE_FLAG_NEW_DOC = 0x04
PAGE_FLAG_END_DOC = 0x08
PAGE_FLAG_END_STREAM = 0x10

MAJOR_VER = 2
MINOR_VER = 0

MFPDTF_RASTER_BITMAP  = 0 # Not used
MFPDTF_RASTER_GRAYMAP = 1 # Not used
MFPDTF_RASTER_MH      = 2 # OfficeJets B&W Fax
MFPDTF_RASTER_MR      = 3 # Not used
MFPDTF_RASTER_MMR     = 4 # LaserJets B&W Fax
MFPDTF_RASTER_RGB     = 5 # Not used
MFPDTF_RASTER_YCC411  = 6 # Not used
MFPDTF_RASTER_JPEG    = 7 # Color Fax
MFPDTF_RASTER_PCL     = 8 # Not used
MFPDTF_RASTER_NOT     = 9 # Not used

# Data types for FH
DT_UNKNOWN       = 0
DT_FAX_IMAGES    = 1
DT_SCANNED_IMAGES= 2
DT_DIAL_STRINGS  = 3
DT_DEMO_PAGES    = 4
DT_SPEED_DIALS   = 5
DT_FAX_LOGS      = 6
DT_CFG_PARMS     = 7
DT_LANG_STRS     = 8
DT_JUNK_FAX_CSIDS= 9  
DT_REPORT_STRS   = 10  
DT_FONTS         = 11
DT_TTI_BITMAP    = 12
DT_COUNTERS      = 13
DT_DEF_PARMS     = 14  
DT_SCAN_OPTIONS  = 15
DT_FW_JOB_TABLE  = 17

# Raster data record types
RT_START_PAGE = 0
RT_RASTER = 1
RT_END_PAGE = 2

# FH
FIXED_HEADER_SIZE = 8

# Variants
IMAGE_VARIANT_HEADER_SIZE = 10
DIAL_STRINGS_VARIANT_HEADER_SIZE = 6
FAX_IMAGE_VARIANT_HEADER_SIZE = 74

# Data records
SOP_RECORD_SIZE = 36
RASTER_RECORD_SIZE = 4
EOP_RECORD_SIZE = 12
DIAL_STRING_RECORD_SIZE = 51

# Page flags 
PAGE_FLAG_NEW_PAGE = 0x01
PAGE_FLAG_END_PAGE = 0x02
PAGE_FLAG_NEW_DOC = 0x04
PAGE_FLAG_END_DOC = 0x08
PAGE_FLAG_END_STREAM = 0x10

# Fax data variant header data source
SRC_UNKNOWN = 0
SRC_HOST = 2
SRC_SCANNER = 5
SRC_HOST_THEN_SCANNER = 6
SRC_SCANNER_THEN_HOST = 7

# Fax data variant header TTI header control
TTI_NONE = 0
TTI_PREPENDED_TO_IMAGE = 1
TTI_OVERLAYED_ON_IMAGE = 2

RASTER_DATA_SIZE = 504

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


# **************************************************************************** #
class FaxDevice(device.Device):

    def __init__(self, device_uri=None, printer_name=None,
                 hpssd_sock=None, callback=None):

        device.Device.__init__(self, device_uri, printer_name,
                               hpssd_sock, callback)

        self.send_fax_thread = None
        self.upload_log_thread = None

    def setPhoneNum(self, num):
        return self.setPML(pml.OID_FAX_LOCAL_PHONE_NUM, str(num))

    def getPhoneNum(self):
        return utils.printable(str(self.getPML(pml.OID_FAX_LOCAL_PHONE_NUM)[1]))

    phone_num = property(getPhoneNum, setPhoneNum, doc="OID_FAX_LOCAL_PHONE_NUM")


    def setStationName(self, name):
        return self.setPML(pml.OID_FAX_STATION_NAME, str(name))

    def getStationName(self):
        return utils.printable(str(self.getPML(pml.OID_FAX_STATION_NAME)[1]))

    station_name = property(getStationName, setStationName, doc="OID_FAX_STATION_NAME")

    def setDateAndTime(self):
        t = time.localtime()
        p = struct.pack("BBBBBBB", t[0]-2000, t[1], t[2], t[6]+1, t[3], t[4], t[5])
        log.debug(repr(p))
        return self.setPML(pml.OID_DATE_AND_TIME, p)

    def uploadLog(self):
        if not self.isUloadLogActive():
            self.upload_log_thread = UploadLogThread(self)
            self.upload_log_thread.start()
            return True
        else:
            return False

    def isUploadLogActive(self):
        if self.upload_log_thread is not None:
            return self.upload_log_thread.isAlive()
        else:
            return False

    def waitForUploadLogThread(self):
        if self.upload_log_thread is not None and \
            self.upload_log_thread.isAlive():

            self.upload_log_thread.join()


    def sendFaxes(self, phone_num_list, fax_file_list, cover_message='', cover_re='', 
                  cover_func=None, preserve_formatting=False, printer_name='', 
                  update_queue=None, event_queue=None):

        if not self.isSendFaxActive():
            self.send_fax_thread = FaxSendThread(self, phone_num_list, fax_file_list, 
                                                 cover_message, cover_re, cover_func, preserve_formatting, 
                                                 printer_name, update_queue, event_queue)
            self.send_fax_thread.start()
            return True
        else:
            return False


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


class UploadLogThread(threading.Thread):
    def __init__(self, dev):
        threading.Thread.__init__(self)
        self.dev = dev


    def run(self):
        STATE_DONE = 0
        STATE_ABORT = 10
        STATE_SUCCESS = 20
        STATE_BUSY = 25
        STATE_DEVICE_OPEN = 28
        STATE_CHECK_IDLE = 30
        STATE_REQUEST_START = 40
        STATE_WAIT_FOR_ACTIVE = 50
        STATE_UPLOAD_DATA = 60
        STATE_DEVICE_CLOSE = 70

        state = STATE_CHECK_IDLE

        while state != STATE_DONE: # --------------------------------- Log upload state machine
            if state == STATE_ABORT: 
                pass
            elif state == STATE_SUCCESS:
                pass
            elif state == STATE_BUSY:
                pass

            elif state == STATE_DEVICE_OPEN: # --------------------------------- Open device (28)
                state = STATE_REQUEST_START
                try:
                    self.dev.open()
                except Error, e:
                    log.error("Unable to open device (%s)." % e.msg)
                    state = STATE_ERROR
                else:
                    try:
                        dev.setPML(pml.OID_UPLOAD_TIMEOUT, pml.DEFAULT_UPLOAD_TIMEOUT)
                    except Error:
                        state = STATE_ERROR

            elif state == STATE_CHECK_IDLE: # --------------------------------- Check idle (30)
                state = STATE_REQUEST_START
                ul_state = self.getCfgUploadState()

                if ul_state != pml.UPDN_STATE_IDLE:
                    state = STATE_BUSY


            elif state == STATE_REQUEST_START: # --------------------------------- Request start (40)
                state = STATE_WAIT_FOR_ACTIVE
                self.dev.setPML(pml.OID_FAX_CFG_UPLOAD_DATA_TYPE, pml.FAX_CFG_UPLOAD_DATA_TYPE_FAXLOGS)
                self.dev.setPML(pml.OID_DEVICE_CFG_UPLOAD, pml.UPDN_STATE_REQSTART)

            elif state == STATE_WAIT_FOR_ACTIVE: # --------------------------------- Wait for active state (50)
                state = STATE_UPLOAD_DATA

                tries = 0
                while True:
                    tries += 1
                    ul_state = self.getCfgUploadState()

                    if ul_state == pml.UPDN_STATE_XFERACTIVE:
                        break

                    if ul_state in (pml.UPDN_STATE_ERRORABORT, pml.UPDN_STATE_XFERDONE):
                        log.error("Cfg upload aborted!")
                        state = STATE_ERROR
                        break

                    if tries > 10:
                        state = STATE_ERROR
                        log.error("Unable to get into active state!")
                        break

                    time.sleep(0.5)

            elif state == STATE_UPLOAD_DATA: # --------------------------------- Upload log data (60)
                pass

            elif state == STATE_DEVICE_CLOSE: # --------------------------------- Close device (70)
                self.dev.close()




class FaxSendThread(threading.Thread):
    def __init__(self, dev, phone_num_list, fax_file_list, 
                 cover_message='', cover_re='', cover_func=None, preserve_formatting=False,
                 printer_name='', update_queue=None, event_queue=None):

        threading.Thread.__init__(self)
        self.dev = dev
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


    def run(self):
        results = {} # {'file' : error_code,...}

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

        next_recipient = self.next_recipient_gen()

        state = STATE_READ_SENDER_INFO
        self.rendered_file_list = []

        while state != STATE_DONE: # --------------------------------- Fax state machine
            if self.check_for_cancel():
                state = STATE_ABORTED

            log.debug("STATE=(%d, 0, 0)" % state)

            if state == STATE_ABORTED: # --------------------------------- Aborted (10, 0, 0)
                log.error("Aborted by user.")
                self.write_queue((STATUS_IDLE, 0, ''))
                state = STATE_CLEANUP


            elif state == STATE_SUCCESS: # --------------------------------- Success (20, 0, 0)
                log.debug("Success.")
                self.write_queue((STATUS_COMPLETED, 0, ''))
                state = STATE_CLEANUP


            elif state == STATE_ERROR: # --------------------------------- Error (130, 0, 0)
                log.error("Error, aborting.")
                self.write_queue((STATUS_ERROR, 0, ''))
                state = STATE_CLEANUP


            elif state == STATE_BUSY: # --------------------------------- Busy (25, 0, 0)
                log.error("Device busy, aborting.")
                self.write_queue((STATUS_BUSY, 0, ''))
                state = STATE_CLEANUP


            elif state == STATE_READ_SENDER_INFO: # --------------------------------- Get sender info (30, 0, 0)
                log.debug("%s State: Get sender info" % ("*"*20))
                state = STATE_PRERENDER
                try:
                    try:
                        self.dev.open()
                    except Error, e:
                        log.error("Unable to open device (%s)." % e.msg)
                        state = STATE_ERROR
                    else:
                        try:
                            self.sender_name = self.dev.station_name
                            log.debug("Sender name=%s" % self.sender_name)
                            self.sender_fax = self.dev.phone_num
                            log.debug("Sender fax=%s" % self.sender_fax)
                        except Error:
                            log.error("PML get failed!")
                            state = STATE_ERROR

                finally:
                    self.dev.close()


            elif state == STATE_PRERENDER: # --------------------------------- Pre-render non-G3 files (40, 0, 0)
                log.debug("%s State: Pre-render non-G3 files" % ("*"*20))
                # pre-render each page that needs rendering
                # except for the cover page
                state = STATE_COUNT_PAGES
                cover_page_present = False
                log.debug(self.fax_file_list)

                for fax_file in self.fax_file_list: # (file, type, desc, title)
                    fax_file_name, fax_file_type, fax_file_desc, fax_file_title, fax_file_pages = fax_file

                    if fax_file_type == "application/hplip-fax-coverpage": # render later
                        cover_page_present = True
                        log.debug("Skipping coverpage")

                    #if fax_file_type == "application/hplip-fax": # already rendered
                    else:
                        self.rendered_file_list.append((fax_file_name, "application/hplip-fax", "HP Fax", fax_file_title))
                        log.debug("Processing pre-rendered file: %s (%d pages)" % (fax_file_name, fax_file_pages))

                    if self.check_for_cancel():
                        state = STATE_ABORTED

                log.debug(self.rendered_file_list)


            elif state == STATE_COUNT_PAGES: # --------------------------------- Get total page count (50, 0, 0)
                log.debug("%s State: Get total page count" % ("*"*20))
                state = STATE_NEXT_RECIPIENT
                recipient_file_list = self.rendered_file_list[:]
                log.debug("Counting total pages...")
                self.job_total_pages = 0
                log.debug(recipient_file_list)

                i = 0
                for fax_file in recipient_file_list: # (file, type, desc, title)
                    fax_file_name = fax_file[0]
                    log.debug("Processing file (counting pages): %s..." % fax_file_name)

                    #self.write_queue((STATUS_PROCESSING_FILES, self.job_total_pages, ''))

                    if os.path.exists(fax_file_name):
                        results[fax_file_name] = ERROR_SUCCESS
                        fax_file_fd = file(fax_file_name, 'r')
                        header = fax_file_fd.read(FILE_HEADER_SIZE)

                        magic, version, total_pages, hort_dpi, vert_dpi, page_size, \
                            resolution, encoding, reserved1, reserved2 = self.decode_fax_header(header)

                        if magic != 'hplip_g3':
                            log.error("Invalid file header. Bad magic.")
                            results[fax_file_name] = ERROR_FAX_INVALID_FAX_FILE
                            state = STATE_ERROR
                            continue

                        if not i:
                            job_hort_dpi, job_vert_dpi, job_page_size, job_resolution, job_encoding = \
                                hort_dpi, vert_dpi, page_size, resolution, encoding
                            i += 1
                        else:
                            if job_hort_dpi != hort_dpi or \
                                job_vert_dpi != vert_dpi or \
                                job_page_size != page_size or \
                                job_resolution != resolution or \
                                job_encoding != encoding:

                                log.error("Incompatible options for file: %s" % fax_file_name)
                                results[fax_file_name] = ERROR_FAX_INCOMPATIBLE_OPTIONS
                                state = STATE_ERROR


                        log.debug("Magic=%s Ver=%d Pages=%d hDPI=%d vDPI=%d Size=%d Res=%d Enc=%d" %
                                  (magic, version, total_pages, hort_dpi, vert_dpi, page_size, resolution, encoding))

                        self.job_total_pages += total_pages

                        fax_file_fd.close()

                    else:
                        log.error("Unable to find HP Fax file: %s" % fax_file_name)
                        results[fax_file_name] = ERROR_FAX_FILE_NOT_FOUND
                        state = STATE_ERROR
                        break

                    if self.check_for_cancel():
                        state = STATE_ABORTED
                        break


                if cover_page_present:
                    self.job_total_pages += 1 # Cover pages are truncated to 1 page

                log.debug("Total fax pages=%d" % self.job_total_pages)                        


            elif state == STATE_NEXT_RECIPIENT: # --------------------------------- Loop for multiple recipients (60, 0, 0)
                log.debug("%s State: Next recipient" % ("*"*20))
                state = STATE_COVER_PAGE

                try:
                    recipient = next_recipient.next()
                    #print recipient
                    log.debug("Processing for recipient %s" % recipient['name'])
                except StopIteration:
                    state = STATE_SUCCESS
                    log.debug("Last recipient.")
                    continue

                recipient_file_list = self.rendered_file_list[:]


            elif state == STATE_COVER_PAGE: # --------------------------------- Create cover page (70, 0, 0)
                log.debug("%s State: Render cover page" % ("*"*20))

                if self.job_total_pages > 1:
                    state = STATE_MERGE_FILES
                else:
                    state = STATE_SINGLE_FILE

                if cover_page_present:
                    log.debug("Creating cover page for recipient: %s" % recipient['name'])
                    fax_file, canceled = self.render_cover_page(recipient)

                    if canceled:
                        state = STATE_ABORTED
                    elif not fax_file:
                        state = STATE_ERROR # timeout
                    else:
                        recipient_file_list.insert(0, (fax_file, "application/hplip-fax", 
                            "HP Fax", 'Cover Page'))
                            
                        log.debug("Cover page G3 file: %s" % fax_file)

                        results[fax_file] = ERROR_SUCCESS


            elif state == STATE_SINGLE_FILE: # --------------------------------- Special case for single file (no merge) (80, 0, 0)
                log.debug("%s State: Handle single file" % ("*"*20))
                state = STATE_SEND_FAX

                log.debug("Processing single file...")

                f = recipient_file_list[0][0]

                try:
                    f_fd = file(f, 'r')
                except IOError:
                    log.error("Unable to open fax file: %s" % f)
                    state = STATE_ERROR
                else:
                    header = f_fd.read(FILE_HEADER_SIZE)

                    magic, version, total_pages, hort_dpi, vert_dpi, page_size, \
                        resolution, encoding, reserved1, reserved2 = self.decode_fax_header(header)

                    results[f] = ERROR_SUCCESS

                    if magic != 'hplip_g3':
                        log.error("Invalid file header. Bad magic.")
                        results[f] = ERROR_FAX_INVALID_FAX_FILE
                        state = STATE_ERROR

                    log.debug("Magic=%s Ver=%d Pages=%d hDPI=%d vDPI=%d Size=%d Res=%d Enc=%d" %
                              (magic, version, total_pages, hort_dpi, vert_dpi, page_size, resolution, encoding))

                    f_fd.close()


            elif state == STATE_MERGE_FILES: # --------------------------------- Merge multiple G3 files (90, 0, 0)
                log.debug("%s State: Merge multiple files" % ("*"*20))
                log.debug(recipient_file_list)
                log.debug("Merging g3 files...")
                state = STATE_SEND_FAX
                self.remove_temp_file = True

                if self.job_total_pages:
                    f_fd, f = utils.make_temp_file()
                    log.debug("Temp file=%s" % f)

                    data = struct.pack(">8sBIHHBBBII", "hplip_g3", 1L, self.job_total_pages,  
                        job_hort_dpi, job_vert_dpi, job_page_size, job_resolution, job_encoding, 
                        0L, 0L)

                    os.write(f_fd, data)

                    job_page_num = 1

                    for fax_file in recipient_file_list:
                        fax_file_name = fax_file[0]
                        log.debug("Processing file: %s..." % fax_file_name)

                        if results[fax_file_name] == ERROR_SUCCESS:
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


            elif state == STATE_SEND_FAX: # --------------------------------- Send fax state machine (110, 0, 0)
                log.debug("%s State: Send fax" % ("*"*20))
                state = STATE_NEXT_RECIPIENT

                FAX_SEND_STATE_DONE = 0
                FAX_SEND_STATE_ABORT = 10
                FAX_SEND_STATE_ERROR = 20
                FAX_SEND_STATE_BUSY = 25
                FAX_SEND_STATE_SUCCESS = 30
                FAX_SEND_STATE_DEVICE_OPEN = 40
                FAX_SEND_STATE_SET_TOKEN = 50
                FAX_SEND_STATE_EARLY_OPEN = 60
                FAX_SEND_STATE_SET_PARAMS = 70
                FAX_SEND_STATE_CHECK_IDLE = 80
                FAX_SEND_STATE_START_REQUEST = 90
                FAX_SEND_STATE_LATE_OPEN = 100
                FAX_SEND_STATE_SEND_DIAL_STRINGS = 110
                FAX_SEND_STATE_SEND_FAX_HEADER = 120
                FAX_SEND_STATE_SEND_PAGES = 130
                FAX_SEND_STATE_SEND_END_OF_STREAM = 140
                FAX_SEND_STATE_WAIT_FOR_COMPLETE = 150
                FAX_SEND_STATE_RESET_TOKEN = 160
                FAX_SEND_STATE_CLOSE_SESSION = 170

                monitor_state = False
                fax_send_state = FAX_SEND_STATE_DEVICE_OPEN

                while fax_send_state != FAX_SEND_STATE_DONE:

                    if self.check_for_cancel():
                        log.error("Fax send aborted.")
                        fax_send_state = FAX_SEND_STATE_ABORT

                    if monitor_state:
                        fax_state = self.getFaxDownloadState() 
                        if not fax_state in (pml.UPDN_STATE_XFERACTIVE, pml.UPDN_STATE_XFERDONE):
                            log.error("D/L error state=%d" % fax_state)
                            fax_send_state = FAX_SEND_STATE_ERROR
                            state = STATE_ERROR

                    log.debug("STATE=(%d, %d, 0)" % (STATE_SEND_FAX, fax_send_state))

                    if fax_send_state == FAX_SEND_STATE_ABORT: # -------------- Abort (110, 10, 0)
                        # TODO: Set D/L state to ???
                        monitor_state = False
                        fax_send_state = FAX_SEND_STATE_RESET_TOKEN
                        state = STATE_ABORTED

                    elif fax_send_state == FAX_SEND_STATE_ERROR: # -------------- Error (110, 20, 0)
                        log.error("Fax send error.")
                        monitor_state = False

                        fax_send_state = FAX_SEND_STATE_RESET_TOKEN
                        state = STATE_ERROR

                        #fax_send_state = FAX_SEND_STATE_DONE
                        #state = STATE_NEXT_RECIPIENT


                    elif fax_send_state == FAX_SEND_STATE_BUSY: # -------------- Busy (110, 25, 0)
                        log.error("Fax device busy.")
                        monitor_state = False
                        fax_send_state = FAX_SEND_STATE_RESET_TOKEN
                        state = STATE_BUSY

                    elif fax_send_state == FAX_SEND_STATE_SUCCESS: # -------------- Success (110, 30, 0)
                        log.debug("Fax send success.")
                        monitor_state = False
                        fax_send_state = FAX_SEND_STATE_RESET_TOKEN
                        state = STATE_NEXT_RECIPIENT

                    elif fax_send_state == FAX_SEND_STATE_DEVICE_OPEN: # -------------- Device open (110, 40, 0)
                        log.debug("%s State: Open device" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_SET_TOKEN
                        try:
                            self.dev.open()
                        except Error, e:
                            log.error("Unable to open device (%s)." % e.msg)
                            fax_send_state = FAX_SEND_STATE_ERROR
                        else:
                            if self.dev.device_state == DEVICE_STATE_NOT_FOUND:
                                fax_send_state = FAX_SEND_STATE_ERROR

                    elif fax_send_state == FAX_SEND_STATE_SET_TOKEN: # -------------- Acquire fax token (110, 50, 0)
                        log.debug("%s State: Acquire fax token" % ("*"*20))
                        try:
                            result_code, token = self.dev.getPML(pml.OID_FAX_TOKEN)
                        except Error:
                            log.debug("Unable to acquire fax token (1).")
                            fax_send_state = FAX_SEND_STATE_EARLY_OPEN
                        else:
                            if result_code > pml.ERROR_MAX_OK:
                                fax_send_state = FAX_SEND_STATE_EARLY_OPEN
                                log.debug("Skipping token acquisition.")
                            else:
                                token = time.strftime("%d%m%Y%H:%M:%S", time.gmtime())
                                log.debug("Setting token: %s" % token)
                                try:
                                    self.dev.setPML(pml.OID_FAX_TOKEN, token)
                                except Error:
                                    log.error("Unable to acquire fax token (2).")
                                    fax_send_state = FAX_SEND_STATE_ERROR
                                else:
                                    result_code, check_token = self.dev.getPML(pml.OID_FAX_TOKEN)

                                    if check_token == token:
                                        fax_send_state = FAX_SEND_STATE_EARLY_OPEN
                                    else:
                                        log.error("Unable to acquire fax token (3).")
                                        fax_send_state = FAX_SEND_STATE_ERROR


                    elif fax_send_state == FAX_SEND_STATE_EARLY_OPEN: # -------------- Early open (newer models) (110, 60, 0)
                        log.debug("%s State: Early open" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_CHECK_IDLE

                        if self.dev.fax_type == FAX_TYPE_BLACK_SEND_EARLY_OPEN: # newer
                            log.debug("Opening fax channel.")
                            try:
                                self.dev.openFax()
                            except Error, e:
                                log.error("Unable to open channel (%s)." % e.msg)
                                fax_send_state = FAX_SEND_STATE_ERROR
                        else:
                            log.debug("Skipped.")


                    elif fax_send_state == FAX_SEND_STATE_CHECK_IDLE: # -------------- Check for initial idle (110, 80, 0)
                        log.debug("%s State: Check idle" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_START_REQUEST

                        dl_state = self.getFaxDownloadState()
                        tx_status = self.getFaxJobTxStatus()
                        rx_status = self.getFaxJobRxStatus()

                        if ((dl_state == pml.UPDN_STATE_IDLE or \
                            dl_state == pml.UPDN_STATE_ERRORABORT or \
                            dl_state == pml.UPDN_STATE_XFERDONE) and \
                            (tx_status == pml.FAXJOB_TX_STATUS_IDLE or tx_status == pml.FAXJOB_TX_STATUS_DONE) and \
                            (rx_status == pml.FAXJOB_RX_STATUS_IDLE or rx_status == pml.FAXJOB_RX_STATUS_DONE)):

                            if state == pml.UPDN_STATE_IDLE:
                                log.debug("Starting in idle state")
                            else:
                                log.debug("Reseting to idle...")
                                self.dev.setPML(pml.OID_FAX_DOWNLOAD, pml.UPDN_STATE_IDLE)
                                time.sleep(0.5)
                        else:
                            fax_send_state = FAX_SEND_STATE_BUSY

                    elif fax_send_state == FAX_SEND_STATE_START_REQUEST: # -------------- Request fax start (110, 90, 0) 
                        log.debug("%s State: Request start" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_SET_PARAMS

                        dl_state = self.getFaxDownloadState()

                        if dl_state == pml.UPDN_STATE_IDLE:
                            self.dev.setPML(pml.OID_FAX_DOWNLOAD, pml.UPDN_STATE_REQSTART)
                            time.sleep(1)

                            log.debug("Waiting for active state...")
                            i = 0

                            while i < 10:
                                log.debug("Try: %d" % i)
                                try:
                                    dl_state = self.getFaxDownloadState()
                                except Error:
                                    log.error("PML/SNMP error")
                                    fax_send_state = FAX_SEND_STATE_ERROR
                                    break

                                if dl_state == pml.UPDN_STATE_XFERACTIVE:
                                    break

                                time.sleep(1)
                                self.dev.setPML(pml.OID_FAX_DOWNLOAD, pml.UPDN_STATE_REQSTART)

                                i += 1

                            else:  
                                log.error("Could not get into active state!")
                                fax_send_state = FAX_SEND_STATE_BUSY

                            monitor_state = True

                        else:
                            log.error("Could not get into idle state!")
                            fax_send_state = FAX_SEND_STATE_BUSY


                    elif fax_send_state == FAX_SEND_STATE_SET_PARAMS: # -------------- Set fax send params (110, 70, 0)
                        log.debug("%s State: Set params" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_LATE_OPEN

                        try:
                            self.dev.setPML(pml.OID_DEV_DOWNLOAD_TIMEOUT, pml.DEFAULT_DOWNLOAD_TIMEOUT)
                            self.dev.setPML(pml.OID_FAXJOB_TX_TYPE, pml.FAXJOB_TX_TYPE_HOST_ONLY)
                            log.debug("Setting date and time on device.")                            
                            self.dev.setDateAndTime() 
                        except Error, e:
                            log.error("PML/SNMP error (%s)" % e.msg)
                            fax_send_state = FAX_SEND_STATE_ERROR


                    elif fax_send_state == FAX_SEND_STATE_LATE_OPEN: # -------------- Late open (older models) (110, 100, 0)
                        log.debug("%s State: Late open" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_SEND_DIAL_STRINGS

                        if self.dev.fax_type == FAX_TYPE_BLACK_SEND_LATE_OPEN: # older
                            log.debug("Opening fax channel.")
                            try:
                                self.dev.openFax()
                            except Error:
                                log.error("Unable to open channel.")
                                fax_send_state = FAX_SEND_STATE_ERROR
                        else:
                            log.debug("Skipped.")


                    elif fax_send_state == FAX_SEND_STATE_SEND_DIAL_STRINGS: # -------------- Dial strings (110, 110, 0)
                        log.debug("%s State: Send dial strings" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_SEND_FAX_HEADER

                        log.debug("Dialing: %s" % recipient['fax'])

                        log.debug("Sending dial strings...")
                        self.create_mfpdtf_fixed_header(DT_DIAL_STRINGS, True, 
                            PAGE_FLAG_NEW_DOC | PAGE_FLAG_END_DOC | PAGE_FLAG_END_STREAM) # 0x1c on Windows, we were sending 0x0c
                        #print recipient
                        self.create_mfpdtf_dial_strings(recipient['fax'].encode('ascii'))

                        try:
                            self.write_stream()
                        except Error:
                            log.error("Channel write error.")
                            fax_send_state = FAX_SEND_STATE_ERROR


                    elif fax_send_state == FAX_SEND_STATE_SEND_FAX_HEADER: # -------------- Fax header (110, 120, 0)
                        log.debug("%s State: Send fax header" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_SEND_PAGES

                        try:
                            ff = file(f, 'r')
                        except IOError:
                            log.error("Unable to read fax file.")
                            fax_send_state = FAX_SEND_STATE_ERROR
                            continue

                        try:
                            header = ff.read(FILE_HEADER_SIZE)
                        except IOError:
                            log.error("Unable to read fax file.")
                            fax_send_state = FAX_SEND_STATE_ERROR
                            continue

                        magic, version, total_pages, hort_dpi, vert_dpi, page_size, \
                            resolution, encoding, reserved1, reserved2 = self.decode_fax_header(header)


                        if magic != 'hplip_g3':
                            log.error("Invalid file header. Bad magic.")
                            fax_send_state = FAX_SEND_STATE_ERROR
                        else:
                            log.debug("Magic=%s Ver=%d Pages=%d hDPI=%d vDPI=%d Size=%d Res=%d Enc=%d" %
                                      (magic, version, total_pages, hort_dpi, vert_dpi, page_size, resolution, encoding))

                            log.debug("Sending fax header...")
                            self.create_mfpdtf_fixed_header(DT_FAX_IMAGES, True, PAGE_FLAG_NEW_DOC)
                            self.create_mfpdtf_fax_header(total_pages)

                            try:
                                self.write_stream()
                            except Error:
                                log.error("Unable to write to channel.")
                                fax_send_state = FAX_SEND_STATE_ERROR


                    elif fax_send_state == FAX_SEND_STATE_SEND_PAGES:  # --------------------------------- Send fax pages state machine (110, 130, 0)
                        log.debug("%s State: Send pages" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_SEND_END_OF_STREAM
                        page = StringIO()

                        for p in range(total_pages):

                            if self.check_for_cancel():
                                fax_send_state = FAX_SEND_STATE_ABORT

                            if fax_send_state == FAX_SEND_STATE_ABORT:
                                break

                            try:
                                header = ff.read(PAGE_HEADER_SIZE)
                            except IOError:
                                log.error("Unable to read fax file.")
                                fax_send_state = FAX_SEND_STATE_ERROR
                                continue

                            page_num, ppr, rpp, bytes_to_read, thumbnail_bytes, reserved2 = \
                                self.decode_page_header(header)

                            log.debug("Page=%d PPR=%d RPP=%d BPP=%d Thumb=%d" %
                                      (page_num, ppr, rpp, bytes_to_read, thumbnail_bytes))

                            page.write(ff.read(bytes_to_read))
                            thumbnail = ff.read(thumbnail_bytes) # thrown away for now (should be 0 read)
                            page.seek(0)

                            self.create_mfpdtf_fixed_header(DT_FAX_IMAGES, page_flags=PAGE_FLAG_NEW_PAGE)
                            self.create_sop_record(page_num, hort_dpi, vert_dpi, ppr, rpp, encoding)

                            try:
                                data = page.read(RASTER_DATA_SIZE)
                            except IOError:
                                log.error("Unable to read fax file.")
                                fax_send_state = FAX_SEND_STATE_ERROR
                                continue

                            if data == '':
                                log.error("No data!")
                                fax_send_state = FAX_SEND_STATE_ERROR
                                continue

                            self.create_raster_data_record(data)
                            total_read = RASTER_DATA_SIZE

                            while True:
                                data = page.read(RASTER_DATA_SIZE)
                                total_read += RASTER_DATA_SIZE

                                self.getFaxDownloadState()

                                if data == '':
                                    self.create_eop_record(rpp)

                                    try:
                                        self.write_stream()
                                    except Error:
                                        log.error("Channel write error.")
                                        fax_send_state = FAX_SEND_STATE_ERROR
                                    break

                                else:
                                    try:
                                        self.write_stream()
                                    except Error:
                                        log.error("Channel write error.")
                                        fax_send_state = FAX_SEND_STATE_ERROR
                                        break

                                status = self.getFaxJobTxStatus()
                                while status  == pml.FAXJOB_TX_STATUS_DIALING:
                                    self.write_queue((STATUS_DIALING, 0, recipient['fax']))
                                    time.sleep(1.0)

                                    if self.check_for_cancel():
                                        fax_send_state = FAX_SEND_STATE_ABORT
                                        break

                                    dl_state = self.getFaxDownloadState()
                                    if dl_state == pml.UPDN_STATE_ERRORABORT:
                                        fax_send_state = FAX_SEND_STATE_ERROR
                                        break

                                    status = self.getFaxJobTxStatus()

                                if fax_send_state not in (FAX_SEND_STATE_ABORT, FAX_SEND_STATE_ERROR):

                                    while status  == pml.FAXJOB_TX_STATUS_CONNECTING: 
                                        self.write_queue((STATUS_CONNECTING, 0, recipient['fax']))
                                        time.sleep(1.0)

                                        if self.check_for_cancel():
                                            fax_send_state = FAX_SEND_STATE_ABORT
                                            break

                                        dl_state = self.getFaxDownloadState()
                                        if dl_state == pml.UPDN_STATE_ERRORABORT:
                                            fax_send_state = FAX_SEND_STATE_ERROR
                                            break

                                        status = self.getFaxJobTxStatus()

                                if status == pml.FAXJOB_TX_STATUS_TRANSMITTING:    
                                    self.write_queue((STATUS_SENDING, page_num, recipient['fax']))

                                self.create_mfpdtf_fixed_header(DT_FAX_IMAGES, page_flags=0)
                                self.create_raster_data_record(data)

                                if fax_send_state in (FAX_SEND_STATE_ABORT, FAX_SEND_STATE_ERROR):
                                    break

                            page.truncate(0)
                            page.seek(0)                


                    elif fax_send_state == FAX_SEND_STATE_SEND_END_OF_STREAM: # -------------- EOS (110, 140, 0)
                        log.debug("%s State: Send EOS" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_WAIT_FOR_COMPLETE
                        log.debug("End of stream...")
                        self.create_mfpdtf_fixed_header(DT_FAX_IMAGES, False, PAGE_FLAG_END_STREAM)

                        try:
                            self.write_stream()
                        except Error:
                            log.error("Channel write error.")
                            fax_send_state = FAX_SEND_STATE_ERROR

                        monitor_state = False


                    elif fax_send_state == FAX_SEND_STATE_WAIT_FOR_COMPLETE: # -------------- Wait for complete (110, 150, 0)
                        log.debug("%s State: Wait for completion" % ("*"*20))

                        fax_send_state = FAX_SEND_STATE_WAIT_FOR_COMPLETE

                        time.sleep(1.0)
                        status = self.getFaxJobTxStatus()

                        if status == pml.FAXJOB_TX_STATUS_DIALING:
                                self.write_queue((STATUS_DIALING, 0, recipient['fax']))

                        elif status == pml.FAXJOB_TX_STATUS_TRANSMITTING:    
                            self.write_queue((STATUS_SENDING, page_num, recipient['fax']))

                        elif status in (pml.FAXJOB_TX_STATUS_DONE, pml.FAXJOB_RX_STATUS_IDLE):
                            fax_send_state = FAX_SEND_STATE_RESET_TOKEN
                            state = STATE_NEXT_RECIPIENT

                        else:
                            self.write_queue((STATUS_SENDING, page_num, recipient['fax']))


                    elif fax_send_state == FAX_SEND_STATE_RESET_TOKEN: # -------------- Release fax token (110, 160, 0)
                        self.write_queue((STATUS_CLEANUP, 0, ''))
                        log.debug("%s State: Release fax token" % ("*"*20))

                        try:
                            self.dev.setPML(pml.OID_FAX_TOKEN, '\x00'*16)
                        except Error:
                            log.error("Unable to release fax token.")

                        fax_send_state = FAX_SEND_STATE_CLOSE_SESSION


                    elif fax_send_state == FAX_SEND_STATE_CLOSE_SESSION: # -------------- Close session (110, 170, 0)
                        log.debug("%s State: Close session" % ("*"*20))
                        fax_send_state = FAX_SEND_STATE_DONE
                        log.debug("Closing session...")

                        try:
                            mm.close()
                        except NameError:
                            pass

                        try:
                            ff.close()
                        except NameError:
                            pass

                        if self.dev.fax_type == FAX_TYPE_BLACK_SEND_LATE_OPEN:
                            log.debug("Closing fax channel.")
                            self.dev.closeFax()

                        self.dev.setPML(pml.OID_FAX_DOWNLOAD, pml.UPDN_STATE_IDLE)

                        time.sleep(1)

                        if self.dev.fax_type == FAX_TYPE_BLACK_SEND_EARLY_OPEN:
                            log.debug("Closing fax channel.")
                            self.dev.closeFax()

                        self.dev.close()


            elif state == STATE_CLEANUP: # --------------------------------- Cleanup (120, 0, 0)
                log.debug("%s State: Cleanup" % ("*"*20))

                if self.remove_temp_file:
                    log.debug("Removing merged file: %s" % f)
                    try:
                        os.remove(f)
                        log.debug("Removed")
                    except OSError:
                        log.debug("Not found")

                state = STATE_DONE



# --------------------------------- Support functions

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

    def getFaxDownloadState(self):
        result_code, state = self.dev.getPML(pml.OID_FAX_DOWNLOAD)
        if state:
            log.debug("D/L State=%d (%s)" % (state, pml.UPDN_STATE_STR.get(state, 'Unknown')))
            return state
        else:
            return pml.UPDN_STATE_ERRORABORT

    def getFaxJobTxStatus(self):
        result_code, status = self.dev.getPML(pml.OID_FAXJOB_TX_STATUS)
        if status:
            log.debug("Tx Status=%d (%s)" % (status, pml.FAXJOB_TX_STATUS_STR.get(status, 'Unknown')))
            return status
        else:
            return pml.FAXJOB_TX_STATUS_IDLE

    def getFaxJobRxStatus(self):
        result_code, status = self.dev.getPML(pml.OID_FAXJOB_RX_STATUS)
        if status:
            log.debug("Rx Status=%d (%s)" % (status, pml.FAXJOB_RX_STATUS_STR.get(status, 'Unknown')))
            return status
        else:
            return pml.FAXJOB_RX_STATUS_IDLE

    def getCfgUploadState(self):
        result_code, state = self.dev.getPML(pml.OID_DEVICE_CFG_UPLOAD)
        if state:
            log.debug("Cfg Upload State = %d (%s)" % (state, pml.UPDN_STATE_STR.get(state, 'Unknown')))
            return state
        else:
            return pml.UPDN_STATE_ERRORABORT

    def create_mfpdtf_fixed_header(self, data_type, send_variant=False, page_flags=0):
        header_len = FIXED_HEADER_SIZE

        if send_variant:
            if data_type == DT_DIAL_STRINGS:
                    header_len += DIAL_STRINGS_VARIANT_HEADER_SIZE

            elif data_type == DT_FAX_IMAGES:
                header_len += FAX_IMAGE_VARIANT_HEADER_SIZE

        self.stream.write(struct.pack("<IHBB", 
                          0, header_len, data_type, page_flags))


    def create_mfpdtf_dial_strings(self, number):
        self.stream.write(struct.pack("<BBHH51s", 
                          MAJOR_VER, MINOR_VER,
                          1, 51, number[:51]))


    def adjust_fixed_header_block_size(self):
        size = self.stream.tell()
        self.stream.seek(0)
        self.stream.write(struct.pack("<I", size))


    def create_sop_record(self, page_num, hort_dpi, vert_dpi, ppr, rpp, encoding, bpp=1):
        self.stream.write(struct.pack("<BBHHHIHHHHHHIHHHH",
                            RT_START_PAGE, encoding, page_num,
                            ppr, bpp,
                            rpp, 0x00, hort_dpi, 0x00, vert_dpi,
                            ppr, bpp,
                            rpp, 0x00, hort_dpi, 0x00, vert_dpi))


    def create_eop_record(self, rpp):
        self.stream.write(struct.pack("<BBBBII",
                            RT_END_PAGE, 0, 0, 0, 
                            rpp, 0,))


    def create_raster_data_record(self, data):
        assert len(data) <= RASTER_DATA_SIZE
        self.stream.write(struct.pack("<BBH",
                        RT_RASTER, 0, len(data),))
        self.stream.write(data)


    def create_mfpdtf_fax_header(self, total_pages):
        self.stream.write(struct.pack("<BBBHBI20s20s20sI", 
                            MAJOR_VER, MINOR_VER, SRC_HOST, total_pages, 
                            TTI_PREPENDED_TO_IMAGE, 0, '', '', '', 0))


    def write_stream(self):
        self.adjust_fixed_header_block_size() 
        self.dev.writeFax(self.stream.getvalue())
        self.stream.truncate(0)
        self.stream.seek(0)    


    def decode_fax_header(self, header):
        try:
            return struct.unpack(">8sBIHHBBBII", header)
        except struct.error:
            return -1, -1, -1, -1, -1, -1, -1, -1, -1, -1

    def decode_page_header(self, header):
        try:
            return struct.unpack(">IIIIII", header)
        except struct.error:
            return -1, -1, -1, -1, -1, -1
