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
# Authors: Don Welch
#


# Std Lib
import sys

# Local
from base.g import *
from base import utils
from prnt import cups
from base.codes import *
from ui_utils import *

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *



class RangeValidator(QValidator):
    def __init__(self, parent=None, name=None):
        QValidator.__init__(self, parent) #, name)


    def validate(self, input, pos):
        for x in unicode(input)[pos-1:]:
            if x not in u'0123456789,- ':
                return QValidator.Invalid, pos

        return QValidator.Acceptable, pos
        
        

class OptionComboBox(QComboBox):
    def __init__(self, rw, parent, name, group, option, choices, default, 
                 typ=cups.PPD_UI_PICKONE, other=None, job_option=False):
        QComboBox.__init__(self, parent)
        # rw?
        self.group = group
        self.option = option
        self.choices = choices
        self.default = default
        self.typ = typ
        self.other = other
        self.job_option = job_option
        self.setObjectName(name)
        
        #print self, self.option, self.job_option


    def setDefaultPushbutton(self, pushbutton):
        self.pushbutton = pushbutton
        
        
    def setOther(self, other):
        self.other = other



class OptionSpinBox(QSpinBox):
    def __init__(self,  parent, name, group, option, default, job_option=False):
        QSpinBox.__init__(self, parent)
        self.group = group
        self.option = option
        self.default = default
        self.job_option = job_option
        self.setObjectName(name)


    def setDefaultPushbutton(self, pushbutton):
        self.pushbutton = pushbutton



class OptionRadioButton(QRadioButton):
    def __init__(self, parent, name, group, option, default, job_option=False):
        QRadioButton.__init__(self, parent)
        self.group = group
        self.option = option
        self.default = default
        self.job_option = job_option
        self.setObjectName(name)


    def setDefaultPushbutton(self, pushbutton):
        self.pushbutton = pushbutton
        


class DefaultPushButton(QPushButton):
    def __init__(self,  parent, name, group, option, choices, 
                 default, control, typ, job_option=False):
        QPushButton.__init__(self, parent)
        self.group = group
        self.option = option
        self.default = default
        self.control = control
        self.typ = typ
        self.choices = choices
        self.job_option = job_option
        self.setObjectName(name)


#class PageRangeRadioButton(QRadioButton):
#    def __init__(self, parent, page_range_edit):
#        QRadioButton.__init__(self, parent):
#            self.page_range_edit = page_range_edit
            
            
class PageRangeRadioButton(QRadioButton):
    def __init__(self, parent, name, group, option, default): #, edit_control=None ):
        QRadioButton.__init__(self, parent)
        self.group = group
        self.option = option
        self.default = default
        self.job_option = True
        self.setObjectName(name)
        
        
    def setRangeEdit(self, edit_control):
        self.edit_control = edit_control
        
        
    def setDefaultPushbutton(self, pushbutton):
        self.pushbutton = pushbutton
        


class PrintSettingsToolbox(QToolBox):
    def __init__(self, parent, include_job_options=False):
        QToolBox.__init__(self, parent)
        self.include_job_options = include_job_options
        self.plus_icon = QIcon(load_pixmap('plus', '16x16'))
        self.minus_icon = QIcon(load_pixmap('minus', '16x16'))
        self.last_item = 0
        self.job_options = {}
        
        self.connect(self, SIGNAL("currentChanged(int)"), self.PrintSettingsToolbox_currentChanged)
        
        
    def getPrintCommands(self, file_list=None):
        # File list: [(path, mime_type, mime_desc), ...]
        if file_list is None or not file_list:
            return []
        
        print_commands = []
        
        try:
            copies = int(self.job_options['copies'])
        except ValueError:
            copies = 1
            
        if copies < 1:
            copies = 1
        elif copies > 99:
            copies = 99
            
        #page_range = unicode(self.pageRangeEdit.text())
        page_range = self.job_options['pagerange']
        
        try:
            x = utils.expand_range(page_range)
        except ValueError:
            log.error("Invalid page range: %s" % page_range)
            return []
            
        all_pages = not page_range
        #page_set = int(self.pageSetComboBox.currentItem())
        page_set = self.job_options['pageset']

        cups.resetOptions()
        cups.openPPD(self.cur_printer)
        current_options = dict(cups.getOptions())
        cups.closePPD()

        nup = int(current_options.get("number-up", 1))
        psnup = utils.which('psnup')

        for p, t, d in file_list:
            alt_nup = (nup > 1 and t == 'application/postscript' and psnup)

            if utils.which('lpr'):
                if alt_nup:
                    cmd = ' '.join(['psnup', '-%d' % nup, ''.join(['"', p, '"']), '| lpr -P', self.cur_printer])
                else:
                    cmd = ' '.join(['lpr -P', self.cur_printer])

                if copies > 1:
                    cmd = ' '.join([cmd, '-#%d' % copies])

            else: # lp
                if alt_nup:
                    cmd = ' '.join(['psnup', '-%d' % nup, ''.join(['"', p, '"']), '| lp -c -d', self.cur_printer])
                else:
                    cmd = ' '.join(['lp -c -d', self.cur_printer])

                if copies > 1:
                    cmd = ' '.join([cmd, '-n%d' % copies])


            if not all_pages and page_range:
                cmd = ' '.join([cmd, '-o page-ranges=%s' % page_range])

            if page_set:
                cmd = ' '.join([cmd, '-o page-set=%s' % page_set])

            
            # Job Storage
            # self.job_storage_mode = (0=Off, 1=P&H, 2=PJ, 3=QC, 4=SJ)
            # self.job_storage_pin = u"" (dddd)
            # self.job_storage_use_pin = True|False
            # self.job_storage_username = u""
            # self.job_storage_auto_username = True|False
            # self.job_storage_jobname = u""
            # self.job_storage_auto_jobname = True|False
            # self.job_storage_job_exist = (0=replace, 1=job name+(1-99))
            
#            if self.job_storage_avail: 
#                if self.job_storage_mode: # On
#                    
#                    if self.job_storage_mode == 1: # Proof and Hold
#                        cmd = ' '.join([cmd, '-o HOLD=PROOF'])
#                        
#                    elif self.job_storage_mode == 2: # Private Job
#                        if self.job_storage_use_pin:
#                            cmd = ' '.join([cmd, '-o HOLD=ON'])
#                            cmd = ' '.join([cmd, '-o HOLDTYPE=PRIVATE'])
#                            cmd = ' '.join([cmd, '-o HOLDKEY=%s' % self.job_storage_pin.encode('ascii')])
#                        else:
#                            cmd = ' '.join([cmd, '-o HOLD=PROOF'])
#                            cmd = ' '.join([cmd, '-o HOLDTYPE=PRIVATE'])
#                        
#                    elif self.job_storage_mode == 3: # Quick Copy
#                        cmd = ' '.join([cmd, '-o HOLD=ON'])
#                        cmd = ' '.join([cmd, '-o HOLDTYPE=PUBLIC'])
#
#                    elif self.job_storage_mode == 4: # Store Job
#                        if self.job_storage_use_pin:
#                            cmd = ' '.join([cmd, '-o HOLD=STORE'])
#                            cmd = ' '.join([cmd, '-o HOLDTYPE=PRIVATE'])
#                            cmd = ' '.join([cmd, '-o HOLDKEY=%s' % self.job_storage_pin.encode('ascii')])
#                        else:
#                            cmd = ' '.join([cmd, '-o HOLD=STORE'])
#                        
#                    cmd = ' '.join([cmd, '-o USERNAME=%s' % self.job_storage_username.encode('ascii')\
#                        .replace(" ", "_")])
#                    
#                    cmd = ' '.join([cmd, '-o JOBNAME=%s' % self.job_storage_jobname.encode('ascii')\
#                        .replace(" ", "_")])
#                    
#                    if self.job_storage_job_exist == 1:
#                        cmd = ' '.join([cmd, '-o DUPLICATEJOB=APPEND']) 
#                    else:
#                        cmd = ' '.join([cmd, '-o DUPLICATEJOB=REPLACE'])
#                
#                else: # Off
#                    cmd = ' '.join([cmd, '-o HOLD=OFF'])
            
            
            if not alt_nup:
                cmd = ''.join([cmd, ' "', p, '"'])
                
            print_commands.append(cmd)
        
        return print_commands
        
        
    def PrintSettingsToolbox_currentChanged(self, i):
        if i != -1:
            self.setItemIcon(self.last_item, self.plus_icon)
            self.setItemIcon(i, self.minus_icon)
            self.last_item = i
        

    def updateUi(self, cur_device, cur_printer):
        #print "PrintSettingsToolbox.updateUi(%s, %s)" % (cur_device, cur_printer)
        self.cur_device = cur_device
        self.cur_printer = cur_printer
        
        while self.count():
            self.removeItem(0)
    
        self.loading = True
        cups.resetOptions()
        cups.openPPD(self.cur_printer)

        try:
            if 1:
            #try:
                current_options = dict(cups.getOptions())
                
                if self.include_job_options:
                    self.beginControlGroup("job_options", self.__tr("Job Options"))
                    
                    # Num. copies (SPINNER)
                    try:
                        current = int(current_options.get('copies', '1'))
                    except ValueError:
                        current = 1
                    
                    self.addControlRow("copies", self.__tr("Number of copies"),
                        cups.UI_SPINNER, current, (1, 99), 1, job_option=True)
                    self.job_options['copies'] = current
                    
                    # page range RADIO + RANGE (custom)
                    current = current_options.get('pagerange', '')
                    
                    self.addControlRow("pagerange", self.__tr("Page Range"),
                        cups.UI_PAGE_RANGE, current, None, None, job_option=True)
                    
                    self.job_options['pagerange'] = current
                        
                    # page set (COMBO/PICKONE)
                    current = current_options.get('pageset', '')
                    self.addControlRow("pageset", self.__tr("Page Set"),
                        cups.PPD_UI_PICKONE, current, 
                        [('', self.__tr("All pages")),
                         ('even', self.__tr("Even pages")),
                         ('odd', self.__tr("Odd pages"))], '', job_option=True)
                    
                    self.job_options['pageset'] = current
#                    if current == u'even':
#                        self.job_options["pageset"] = PAGE_SET_EVEN
#                    elif current == u'odd':
#                        self.job_options["pageset"] = PAGE_SET_ODD
#                    else:
#                        self.job_options["pageset"] = PAGE_SET_ALL
                    
                    self.endControlGroup() # job_options
                
                if not self.cur_device.device_type == DEVICE_TYPE_FAX:
                    self.beginControlGroup("basic", self.__tr("Basic"))
    
                    # Basic
                        # PageSize (in PPD section)
                        # orientation-requested
                        # sides
                        # outputorder
                        # Collate
                    
                    current = current_options.get('orientation-requested', '3')
    
                    self.addControlRow("orientation-requested", self.__tr("Page Orientation"), 
                        cups.PPD_UI_PICKONE, current, 
                        [('3', self.__tr('Portrait')), 
                         ('4', self.__tr('Landscape')), 
                         ('5', self.__tr('Reverse landscape')), 
                         ('6', self.__tr('Reverse portrait'))], '3')
    
                    log.debug("Option: orientation-requested")
                    log.debug("Current value: %s" % current)
    
                    duplexer = self.cur_device.dq.get('duplexer', 0)
                    log.debug("Duplexer = %d" % duplexer)
    
                    if duplexer:
                        current = current_options.get('sides', 'one-sided')
                        self.addControlRow("sides", 
                            self.__tr("Duplex (Print on both sides of the page)"), 
                            cups.PPD_UI_PICKONE, current, 
                            [('one-sided',self.__tr('Single sided')), 
                             ('two-sided-long-edge', self.__tr('Two sided (long edge)')), 
                             ('two-sided-short-edge', self.__tr('Two sided (short edge)'))], 'one-sided')
    
                        log.debug("Option: sides")
                        log.debug("Current value: %s" % current)
    
                    current = current_options.get('outputorder', 'normal')
    
                    self.addControlRow("outputorder", 
                        self.__tr("Output Order (Print last page first)"), 
                        cups.PPD_UI_PICKONE, current, 
                        [('normal', self.__tr('Normal (Print first page first)')), 
                         ('reverse', self.__tr('Reversed (Print last page first)'))], 'normal')
    
                    log.debug("Option: outputorder")
                    log.debug("Current value: %s" % current)
    
                    current = int(utils.to_bool(current_options.get('Collate', '0')))
    
                    self.addControlRow("Collate", 
                        self.__tr("Collate (Group together multiple copies)"), 
                        cups.PPD_UI_BOOLEAN, current, 
                        [], 0)
    
                    log.debug("Option: Collate")
                    log.debug("Current value: %s" % current)

                    self.endControlGroup()
                
                groups = cups.getGroupList()

                #print groups
                
                for g in groups:
                    if 'jobretention' in g.lower():
                        log.debug("HPJobRetention skipped.")
                        continue                    
                    
                    text, num_subgroups = cups.getGroup(g) 
                    read_only = 'install' in g.lower()
                    
                    try:
                        text = text.decode('utf-8')
                    except UnicodeDecodeError:
                        pass
                    
                    if g.lower() == 'printoutmode':
                        text = self.__tr("Quality (also see 'Printout Mode' under 'General')")
                    
                    self.beginControlGroup(g, QString(text))
                    
                    log.debug("  Text: %s" % unicode(text))
                    log.debug("Num subgroups: %d" % num_subgroups)

                    options = cups.getOptionList(g)

                    #print options
                    
                    for o in options:
                        log.debug("  Option: %s" % repr(o))

                        if 'pageregion' in o.lower():
                            log.debug("Page Region skipped.")
                            continue

                        option_text, defchoice, conflicted, ui  = cups.getOption(g, o)

                        try:
                            option_text = option_text.decode('utf-8')
                        except UnicodeDecodeError:
                            pass
                        
                        if o.lower() == 'quality':
                            option_text = self.__tr("Quality")
                                                    
                        log.debug("    Text: %s" % repr(option_text))
                        log.debug("    Defchoice: %s" % repr(defchoice))

                        choices = cups.getChoiceList(g, o)

                        value = None
                        choice_data = []
                        for c in choices:
                            log.debug("    Choice: %s" % repr(c))

                            # TODO: Add custom paper size controls
                            if 'pagesize' in o.lower() and 'custom' in c.lower():
                                log.debug("Skipped.")
                                continue

                            choice_text, marked = cups.getChoice(g, o, c)

                            try:
                                choice_text = choice_text.decode('utf-8')
                            except UnicodeDecodeError:
                                pass
                            
                            log.debug("      Text: %s" % repr(choice_text))

                            if marked:
                                value = c

                            choice_data.append((c, choice_text))

                        self.addControlRow(o, option_text, ui, value, choice_data, defchoice, read_only)
                    
                    self.endControlGroup()
                        
##                        if 'pagesize' in o.lower(): # and 'custom' in c.lower():
##                            current = 0.0
##                            width_widget = self.addControlRow(widget, "custom", "custom-width", self.__tr("Custom Paper Width"), cups.UI_UNITS_SPINNER,
##                                current, (0.0, 0.0), 0.0) 
##                            
##                            current = 0.0
##                            height_widget = self.addControlRow("custom", "custom-height", self.__tr("Custom Paper Height"), cups.UI_UNITS_SPINNER,
##                                current, (0.0, 0.0), 0.0) 
##                                
##                            if value.lower() == 'custom':
##                                pass

                # N-Up
                    # number-up
                    # number-up-layout
                    # page-border

                self.beginControlGroup("nup", self.__tr("N-Up (Multiple document pages per printed page)"))
                current = current_options.get('number-up', '1')

                self.addControlRow("number-up", self.__tr("Pages per Sheet"), 
                    cups.PPD_UI_PICKONE, current, 
                    [('1', self.__tr('1 sheet per page')), 
                     ('2', self.__tr('2 sheets per page')), 
                     ('4', self.__tr('4 sheets per page'))], '1')

                log.debug("  Option: number-up")
                log.debug("  Current value: %s" % current)

                current = current_options.get('number-up-layout', 'lrtb')

                self.addControlRow("number-up-layout", self.__tr("Layout"), 
                    cups.PPD_UI_PICKONE, current, 
                    [('btlr', self.__tr('Bottom to top, left to right')), 
                     ('btrl', self.__tr('Bottom to top, right to left')), 
                     ('lrbt', self.__tr('Left to right, bottom to top')), 
                     ('lrtb', self.__tr('Left to right, top to bottom')),
                     ('rlbt', self.__tr('Right to left, bottom to top')), 
                     ('rltb', self.__tr('Right to left, top to bottom')),
                     ('tblr', self.__tr('Top to bottom, left to right')), 
                     ('tbrl', self.__tr('Top to bottom, right to left')) ], 'lrtb')

                log.debug("  Option: number-up-layout")
                log.debug("  Current value: %s" % current)

                current = current_options.get('page-border', 'none')

                self.addControlRow("page-border", 
                    self.__tr("Printed Border Around Each Page"), 
                    cups.PPD_UI_PICKONE, current,
                    [('double', self.__tr("Two thin borders")), 
                     ("double-thick", self.__tr("Two thick borders")),
                     ("none", self.__tr("No border")), 
                     ("single", self.__tr("One thin border")), 
                     ("single-thick", self.__tr("One thick border"))], 'none')

                log.debug("  Option: page-border")
                log.debug("  Current value: %s" % current)
                
                self.endControlGroup()
                
                # Adjustment
                    # brightness
                    # gamma

                if not self.cur_device.device_type == DEVICE_TYPE_FAX:
                    self.beginControlGroup("adjustment", self.__tr("Printout Appearance"))

                    current = int(current_options.get('brightness', 100))
    
                    log.debug("  Option: brightness")
                    log.debug("  Current value: %s" % current)
    
                    self.addControlRow("brightness", self.__tr("Brightness"),
                        cups.UI_SPINNER, current, (0, 200), 100, suffix=" %")
    
                    current = int(current_options.get('gamma', 1000))
    
                    log.debug("  Option: gamma")
                    log.debug("  Current value: %s" % current)
    
                    self.addControlRow("gamma", self.__tr("Gamma"), cups.UI_SPINNER, current,
                        (1, 10000), 1000)
                        
                    self.endControlGroup()
                    
                # Margins (pts)
                    # page-left
                    # page-right
                    # page-top
                    # page-bottom

##                if 0:
##                    # TODO: cupsPPDPageSize() fails on LaserJets. How do we get margins in this case? Defaults?
##                    # PPD file for LJs has a HWMargin entry...
##                    page, page_width, page_len, left, bottom, right, top = cups.getPPDPageSize()
##
##                    right = page_width - right
##                    top = page_len - top
##
##                    self.addGroupHeading("margins", self.__tr("Margins"))
##                    current_top = current_options.get('page-top', 0) # pts
##                    current_bottom = current_options.get('page-bottom', 0) # pts
##                    current_left = current_options.get('page-left', 0) # pts
##                    current_right = current_options.get('page-right', 0) # pts
##
##                    log.debug("  Option: page-top")
##                    log.debug("  Current value: %s" % current_top)
##
##                    self.addControlRow("margins", "page-top", self.__tr("Top margin"), 
##                        cups.UI_UNITS_SPINNER, current_top,
##                        (0, page_len), top)
##
##                    self.addControlRow("margins", "page-bottom", self.__tr("Bottom margin"), 
##                        cups.UI_UNITS_SPINNER, current_bottom,
##                        (0, page_len), bottom)
##
##                    self.addControlRow("margins", "page-left", self.__tr("Right margin"), 
##                        cups.UI_UNITS_SPINNER, current_left,
##                        (0, page_width), left)
##
##                    self.addControlRow("margins", "page-right", self.__tr("Left margin"), 
##                        cups.UI_UNITS_SPINNER, current_right,
##                        (0, page_width), right)

                # Image Printing
                    # position
                    # natural-scaling
                    # saturation
                    # hue

                self.beginControlGroup("image", self.__tr("Image Printing"))

                current = current_options.get('fitplot', 'false')
                
                self.addControlRow("fitplot", 
                    self.__tr("Fit to Page"), 
                    cups.PPD_UI_BOOLEAN, current, 
                    [], 0)
                
                current = current_options.get('position', 'center')

                self.addControlRow("position", self.__tr("Position on Page"), 
                    cups.PPD_UI_PICKONE, current, 
                    [('center', self.__tr('Centered')), 
                     ('top', self.__tr('Top')), 
                     ('left', self.__tr('Left')), 
                     ('right', self.__tr('Right')), 
                     ('top-left', self.__tr('Top left')), 
                     ('top-right', self.__tr('Top right')), 
                     ('bottom', self.__tr('Bottom')),
                     ('bottom-left', self.__tr('Bottom left')), 
                     ('bottom-right', self.__tr('Bottom right'))], 'center')

                log.debug("  Option: position")
                log.debug("  Current value: %s" % current)

                if not self.cur_device.device_type == DEVICE_TYPE_FAX:
                    current = int(current_options.get('saturation', 100))
    
                    log.debug("  Option: saturation")
                    log.debug("  Current value: %s" % current)
    
                    self.addControlRow("saturation", self.__tr("Saturation"), 
                        cups.UI_SPINNER, current, (0, 200), 100, suffix=" %")
    
                    current = int(current_options.get('hue', 0))
    
                    log.debug("  Option: hue")
                    log.debug("  Current value: %s" % current)
    
                    self.addControlRow("hue", self.__tr("Hue (color shift/rotation)"), 
                        cups.UI_SPINNER, current,
                        (-100, 100), 0)

                current = int(current_options.get('natural-scaling', 100))

                log.debug("  Option: natural-scaling")
                log.debug("  Current value: %s" % current)

                self.addControlRow("natural-scaling", 
                    self.__tr('"Natural" Scaling (relative to image)'), 
                    cups.UI_SPINNER, current, (1, 800), 100, suffix=" %")

                current = int(current_options.get('scaling', 100))

                log.debug("  Option: scaling")
                log.debug("  Current value: %s" % current)

                self.addControlRow("scaling", self.__tr("Scaling (relative to page)"), 
                    cups.UI_SPINNER, current,
                    (1, 800), 100, suffix=" %")

                self.endControlGroup()
                
                # Misc
                    # PrettyPrint
                    # job-sheets
                    # mirror

                self.beginControlGroup("misc", self.__tr("Miscellaneous"))

                log.debug("Group: Misc")

                current = int(utils.to_bool(current_options.get('prettyprint', '0')))

                self.addControlRow("prettyprint", 
                    self.__tr('"Pretty Print" Text Documents (Add headers and formatting)'),
                    cups.PPD_UI_BOOLEAN, current, [], 0)

                log.debug("  Option: prettyprint")
                log.debug("  Current value: %s" % current)

                if not self.cur_device.device_type == DEVICE_TYPE_FAX:
                    current = current_options.get('job-sheets', 'none').split(',')
                    
                    try:
                        start = current[0]
                    except IndexError:
                        start = 'none'
                        
                    try:
                        end = current[1]
                    except IndexError:
                        end = 'none'
                    
                    # TODO: Look for locally installed banner pages beyond the default CUPS ones?
                    self.addControlRow("job-sheets", self.__tr("Banner Pages"), cups.UI_BANNER_JOB_SHEETS, 
                        (start, end), 
                        [("none", self.__tr("No banner page")), 
                         ('classified', self.__tr("Classified")), 
                         ('confidential', self.__tr("Confidential")),
                         ('secret', self.__tr("Secret")), 
                         ('standard', self.__tr("Standard")), 
                         ('topsecret', self.__tr("Top secret")), 
                         ('unclassified', self.__tr("Unclassified"))], ('none', 'none'))
                    
                    log.debug("  Option: job-sheets")
                    log.debug("  Current value: %s,%s" % (start, end))

                current = int(utils.to_bool(current_options.get('mirror', '0')))

                self.addControlRow("mirror", self.__tr('Mirror Printing'),
                    cups.PPD_UI_BOOLEAN, current, [], 0)

                log.debug("  Option: mirror")
                log.debug("  Current value: %s" % current)
                
                self.job_storage_avail = self.cur_device.mq['job-storage'] == JOB_STORAGE_ENABLE
            
                self.endControlGroup()
                
                # TODO: Job control
                # use: self.job_options['xxx'] so that values can be picked up by getPrintCommand()
                
#                if self.job_storage_avail:
#                    self.addGroupHeading("jobstorage", self.__tr("Job Storage and Secure Printing"))
#                    self.addJobStorage(current_options)
                    

            #except Exception, e:
                #log.exception()
            #    pass

        finally:
            cups.closePPD()
            self.loading = False
            

    
    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    
    def beginControlGroup(self, group, text):
        log.debug("BeginGroup: %s" % group)
        self.row = 0
        self.widget = QWidget()
        self.gridlayout = QGridLayout(self.widget)
        self.group = group
        self.text = text
        
        
    def endControlGroup(self):
        log.debug("EndGroup: %s" % self.group)
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.row += 1
        self.gridlayout.addItem(spacer, self.row, 0, 1, 1)
        i = self.addItem(self.widget, self.text)
        
        if i:
            self.setItemIcon(i, self.plus_icon)
        else:
            self.setItemIcon(i, self.minus_icon)
            
        self.widget, self.gridlayout = None, None
        
        
    def addControlRow(self, option, text, typ, value, choices, default, read_only=False, suffix="", job_option=False):
        #print self.widget, self.gridlayout, self.row, self.group, option, text, typ
        
        if typ == cups.PPD_UI_BOOLEAN: # () On (*) Off widget
            HBoxLayout = QHBoxLayout()
            HBoxLayout.setObjectName("HBoxLayout")
            
            OptionLabel = QLabel(self.widget)
            OptionLabel.setObjectName("OptionLabel")
            HBoxLayout.addWidget(OptionLabel)

            SpacerItem = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            HBoxLayout.addItem(SpacerItem)

            #GroupBox = QGroupBox(self.widget)
            GroupBox = QFrame(self.widget) 
            #name, group, option, default, job_option=False):
            #GroupBox = OptionGroupFrame(self.widget, "groupbox", self.group, option, default, job_option)

            gridlayout1 = QGridLayout(GroupBox)
            OnRadioButton = OptionRadioButton(GroupBox, "OnRadioButton", self.group, 
                                              option, default, job_option)
            gridlayout1.addWidget(OnRadioButton,0,0,1,1)
            OffRadioButton = OptionRadioButton(GroupBox, "OffRadioButton", self.group,
                                               option, default, job_option)
            gridlayout1.addWidget(OffRadioButton,0,1,1,1)
            HBoxLayout.addWidget(GroupBox)

            DefaultButton = DefaultPushButton(self.widget, "defaultPushButton", self.group, option, 
                choices, default, (OnRadioButton, OffRadioButton), typ, job_option)   
                
            #GroupBox.setDefaultPushbutton(DefaultButton)
            OnRadioButton.setDefaultPushbutton(DefaultButton)
            OffRadioButton.setDefaultPushbutton(DefaultButton)
                
            HBoxLayout.addWidget(DefaultButton)
            self.gridlayout.addLayout(HBoxLayout, self.row, 0, 1, 1)

            OptionLabel.setText(text)
            OnRadioButton.setText(self.__tr("On"))
            OffRadioButton.setText(self.__tr("Off"))
#            
            DefaultButton.setText("Default")
            
            if value == default:
                DefaultButton.setEnabled(False)
#                
            self.connect(DefaultButton, SIGNAL("clicked()"), self.DefaultButton_clicked)
            self.connect(OnRadioButton, SIGNAL("toggled(bool)"), self.BoolRadioButtons_clicked)
            #self.connect(buttonGroup, SIGNAL("clicked(int)"), self.optionButtonGroup_clicked)
#
#            x = self.__tr('Off')
#            if default:
#                x = self.__tr('On')
#
            if value:
                #buttonGroup.setButton(1)
                OnRadioButton.setChecked(True)
            else:
                #buttonGroup.setButton(0)
                OffRadioButton.setChecked(True)
#            
            if read_only:
                OnRadioButton.setEnabled(False)
                OffRadioButton.setEnabled(False)
                DefaultButton.setEnabled(False)
#            else:
#                QToolTip.add(defaultPushButton, self.__tr('Set to default value of "%1".').arg(x))
#            
            

        elif typ == cups.PPD_UI_PICKONE: # Combo box widget
            #print option, job_option
            HBoxLayout = QHBoxLayout()
            HBoxLayout.setObjectName("HBoxLayout")
            
            OptionLabel = QLabel(self.widget)
            OptionLabel.setObjectName("OptionLabel")
            HBoxLayout.addWidget(OptionLabel)

            SpacerItem = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            HBoxLayout.addItem(SpacerItem)
            
            #def __init__(self, rw, parent, name, group, option, choices, default, 
            #     typ=cups.PPD_UI_PICKONE, other=None, job_option=False):
            
            ComboBox = OptionComboBox(0, self.widget, "ComboBox", self.group, option, choices, default, typ, None, job_option)
            HBoxLayout.addWidget(ComboBox)

            DefaultButton = DefaultPushButton(self.widget,"DefaultButton", self.group, option, 
                choices, default, ComboBox, typ, job_option)

            ComboBox.setDefaultPushbutton(DefaultButton)
            HBoxLayout.addWidget(DefaultButton)
            
            self.gridlayout.addLayout(HBoxLayout, self.row, 0, 1, 1)

            OptionLabel.setText(text)
            DefaultButton.setText("Default")

            i, x, y = 0, None, None
            for c, t in choices:
                d = c.lower()
                if value is not None and d == value.lower():
                    x = i

                if d == default.lower():
                    y = t

                ComboBox.insertItem(i, t)
                i += 1

            if x is not None:
                ComboBox.setCurrentIndex(x)
            else:
                ComboBox.setCurrentIndex(0)

            if value is not None and value.lower() == default.lower():
                DefaultButton.setEnabled(False)
                
            #self.linkPrintoutModeAndQuality(option, value)
#
#            if read_only:
#                optionComboBox.setEnabled(False)
#                defaultPushButton.setEnabled(False)
#            elif y is not None:
#                QToolTip.add(defaultPushButton, self.__tr('Set to default value of "%1".').arg(y))
#
            self.connect(DefaultButton, SIGNAL("clicked()"), self.DefaultButton_clicked)
            self.connect(ComboBox, SIGNAL("highlighted(const QString &)"), self.ComboBox_highlighted)
#            
#            control = optionComboBox

        elif typ == cups.UI_SPINNER: # Spinner widget
        
            HBoxLayout = QHBoxLayout()
            HBoxLayout.setObjectName("HBoxLayout")
            
            OptionLabel = QLabel(self.widget)
            OptionLabel.setObjectName("OptionLabel")
            HBoxLayout.addWidget(OptionLabel)

            SpacerItem = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            HBoxLayout.addItem(SpacerItem)
        
            SpinBox = OptionSpinBox(self.widget,"SpinBox", self.group, option, default, job_option)
            HBoxLayout.addWidget(SpinBox)
            
            DefaultButton = DefaultPushButton(self.widget,"DefaultButton", self.group, option, 
                choices, default, SpinBox, typ, job_option)

            SpinBox.setDefaultPushbutton(DefaultButton)
            HBoxLayout.addWidget(DefaultButton)
            
            self.gridlayout.addLayout(HBoxLayout, self.row, 0, 1, 1)
            
            min, max = choices
            SpinBox.setMinimum(min)
            SpinBox.setMaximum(max)
            SpinBox.setValue(value)
#
            if suffix:
                SpinBox.setSuffix(suffix)
#
            OptionLabel.setText(text)
            DefaultButton.setText("Default")
#
            self.connect(SpinBox, SIGNAL("valueChanged(int)"), self.SpinBox_valueChanged)
            self.connect(DefaultButton, SIGNAL("clicked()"), self.DefaultButton_clicked)
#
            #if value == default:
            DefaultButton.setEnabled(not value == default)
#
            if read_only:
                SpinBox.setEnabled(False)
                DefaultButton.setEnabled(False)
#            else:
#                QToolTip.add(defaultPushButton, 
#                    self.__tr('Set to default value of "%1".').arg(default))
#
        elif typ == cups.UI_BANNER_JOB_SHEETS:  # Job sheets widget
            HBoxLayout = QHBoxLayout()
            HBoxLayout.setObjectName("HBoxLayout")
            
            OptionLabel = QLabel(self.widget)
            OptionLabel.setObjectName("OptionLabel")
            HBoxLayout.addWidget(OptionLabel)

            SpacerItem = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            HBoxLayout.addItem(SpacerItem)
            
            StartLabel = QLabel(self.widget)
            HBoxLayout.addWidget(StartLabel)
            
            StartComboBox = OptionComboBox(0, self.widget, "StartComboBox", self.group, 
                "start", choices, default, typ)
                
            HBoxLayout.addWidget(StartComboBox)
    
            EndLabel = QLabel(self.widget)
            HBoxLayout.addWidget(EndLabel)
            
            EndComboBox = OptionComboBox(0, self.widget, "EndComboBox", self.group, "end", choices, 
                default, typ, StartComboBox)
                
            HBoxLayout.addWidget(EndComboBox) 
            
            StartComboBox.setOther(EndComboBox)
    
            DefaultButton = DefaultPushButton(self.widget, "DefaultButton", self.group, option, choices, 
                default, (StartComboBox, EndComboBox), typ, job_option)
            
            HBoxLayout.addWidget(DefaultButton) 

            self.gridlayout.addLayout(HBoxLayout, self.row, 0, 1, 1)

            StartComboBox.setDefaultPushbutton(DefaultButton)
            EndComboBox.setDefaultPushbutton(DefaultButton)
            
            OptionLabel.setText(text)
            DefaultButton.setText("Default")
          
            StartLabel.setText(self.__tr("Start:"))
            EndLabel.setText(self.__tr("End:"))

            s, e, y, z = None, None, None, None
            for c, t in choices:
                d = c.lower()
                if value is not None:
                    if d == value[0].lower():
                        s = t
                    
                    if d == value[1].lower():
                        e = t

                if d == default[0].lower():
                    y = t
                    
                if d == default[1].lower():
                    z = t

                StartComboBox.insertItem(0, t)
                EndComboBox.insertItem(0, t)

            if s is not None:
                StartComboBox.setCurrentIndex(StartComboBox.findText(s))
                
            if e is not None:
                EndComboBox.setCurrentIndex(EndComboBox.findText(e))

            if value is not None and \
                value[0].lower() == default[0].lower() and \
                value[1].lower() == default[1].lower():
                
                DefaultButton.setEnabled(False)

#            if y is not None and z is not None:
#                QToolTip.add(defaultPushButton, self.__tr('Set to default value of "Start: %1, End: %2".').arg(y).arg(z))
#
            self.connect(StartComboBox, SIGNAL("activated(const QString&)"), self.BannerComboBox_activated)
            self.connect(EndComboBox, SIGNAL("activated(const QString&)"), self.BannerComboBox_activated)
            self.connect(DefaultButton, SIGNAL("clicked()"), self.DefaultButton_clicked)
#            
        elif typ == cups.PPD_UI_PICKMANY:
            log.error("Unrecognized type: pickmany")

        elif typ == cups.UI_UNITS_SPINNER:
            log.error("Unrecognized type: units spinner")
            
        elif typ == cups.UI_PAGE_RANGE:
            HBoxLayout = QHBoxLayout()
            HBoxLayout.setObjectName("HBoxLayout")
            
            OptionLabel = QLabel(self.widget)
            OptionLabel.setObjectName("OptionLabel")
            HBoxLayout.addWidget(OptionLabel)

            SpacerItem = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            HBoxLayout.addItem(SpacerItem)

            GroupBox = QFrame(self.widget)

            gridlayout1 = QGridLayout(GroupBox)
            
            AllRadioButton = PageRangeRadioButton(GroupBox, "AllRadioButton", 
                                               self.group, option, default)
            
            gridlayout1.addWidget(AllRadioButton,0,0,1,1)
            RangeRadioButton = PageRangeRadioButton(GroupBox, "RangeRadioButton", 
                                                 self.group, option, default)
            
            gridlayout1.addWidget(RangeRadioButton,0,1,1,1)
            HBoxLayout.addWidget(GroupBox)
            
            PageRangeEdit = QLineEdit(self.widget)
            HBoxLayout.addWidget(PageRangeEdit)
            PageRangeEdit.setValidator(RangeValidator(PageRangeEdit))
            
            AllRadioButton.setRangeEdit(PageRangeEdit)
            RangeRadioButton.setRangeEdit(PageRangeEdit)

            DefaultButton = DefaultPushButton(self.widget, "defaultPushButton", self.group, option, 
                choices, default, (AllRadioButton, RangeRadioButton, PageRangeEdit), typ, job_option)   
                
            AllRadioButton.setDefaultPushbutton(DefaultButton)
            RangeRadioButton.setDefaultPushbutton(DefaultButton)
            
            HBoxLayout.addWidget(DefaultButton)
            self.gridlayout.addLayout(HBoxLayout, self.row, 0, 1, 1)

            OptionLabel.setText(text)
            AllRadioButton.setText(self.__tr("All pages"))
            RangeRadioButton.setText(self.__tr("Page Range:"))
           
            DefaultButton.setText("Default")
            DefaultButton.setEnabled(False)
            
            AllRadioButton.setChecked(True)
            PageRangeEdit.setEnabled(False)
            
            # TODO: Set current
            
            self.connect(AllRadioButton, SIGNAL("toggled(bool)"), self.PageRangeAllRadio_toggled)
            self.connect(RangeRadioButton, SIGNAL("toggled(bool)"), self.PageRangeRangeRadio_toggled)
            self.connect(DefaultButton, SIGNAL("clicked()"), self.DefaultButton_clicked)
            self.connect(PageRangeEdit, SIGNAL("textChanged(const QString &)"), self.PageRangeEdit_textChanged)
            self.connect(PageRangeEdit, SIGNAL("editingFinished()"), self.PageRangeEdit_editingFinished)
        
        else:
            log.error("Invalid UI value: %s/%s" % (self.group, option))

        self.row += 1
        
        
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

    def BannerComboBox_activated(self, a): # cups.UI_BANNER_JOB_SHEETS
        a = unicode(a)
        sender = self.sender()
        choice = None
        
        start, end = None, None
        for c, t in sender.choices:
            if t == a:
                start = c
                break
                
        for c, t in sender.other.choices:
            if t == sender.other.currentText():
                end = c
                break
            
        if sender.option == 'end':
            start, end = end, start

        if start is not None and \
            end is not None and \
            start.lower() == sender.default[0].lower() and \
            end.lower() == sender.default[1].lower():
                self.removePrinterOption('job-sheets')
                sender.pushbutton.setEnabled(False)
        else:
            sender.pushbutton.setEnabled(True)
            
            if start is not None and \
                end is not None:
                
                self.setPrinterOption('job-sheets', ','.join([start, end]))
        
    
    #def ComboBox_activated(self, a): # PPD_UI_PICKONE
    def ComboBox_highlighted(self, t):
        t = unicode(t)
        sender = self.sender()
        choice = None
        
        #print sender, sender.option, sender.job_option
                
        choice = None
        for c, a in sender.choices:
            if a == t:
                choice = c
                break

        if choice is not None and choice == sender.default:
            if sender.job_option:
                self.job_options[sender.option] = sender.default
            else:
                self.removePrinterOption(sender.option)
            sender.pushbutton.setEnabled(False)
        
        else:
            sender.pushbutton.setEnabled(True)

            if choice is not None:
                if sender.job_option:
                    self.job_options[sender.option] = choice
                else:
                    self.setPrinterOption(sender.option, choice)
                    
            #self.linkPrintoutModeAndQuality(sender.option, choice)

    
#    def linkPrintoutModeAndQuality(self, option, choice):
#        if option.lower() == 'quality' and \
#            choice is not None:
#            
#            try:
#                c = self.items['o:PrintoutMode'].control
#            except KeyError:
#                return
#            else:
#                if c is not None:
#                    if choice.lower() == 'fromprintoutmode':
#                        # from printoutmode selected
#                        # determine printoutmode option combo enable state
#                        c.setEnabled(True)
#                        QToolTip.remove(c)
#                        a = unicode(c.currentText())
#                        
#                        # determine printoutmode default button state
#                        link_choice = None
#                        for x, t in c.choices:
#                            if t == a:
#                                link_choice = x
#                                break
#                
#                        if link_choice is not None and \
#                            link_choice.lower() == c.default.lower():
#                            
#                            c.pushbutton.setEnabled(False)
#                        else:
#                            c.pushbutton.setEnabled(True)
#                    
#                    else: # fromprintoutmode not selected, disable printoutmode
#                        c.setEnabled(False)
#                        QToolTip.add(c, self.__tr("""Set Quality to "Controlled by 'Printout Mode'" to enable."""))
#                        c.pushbutton.setEnabled(False)
#                            

    def SpinBox_valueChanged(self, i): # cups.UI_SPINNER
        sender = self.sender()

        if not sender.job_option:
            if i == sender.default:
                self.removePrinterOption(sender.option)
                sender.pushbutton.setEnabled(False)
            else:
                sender.pushbutton.setEnabled(True)
                self.setPrinterOption(sender.option, str(i))
        
        else:
            try:
                self.job_options[sender.option] = int(i)
            except ValueError:
                self.job_options[sender.option] = sender.default

            
    def BoolRadioButtons_clicked(self, b): # cups.PPD_UI_BOOLEAN
        sender = self.sender()
        b = int(b)

        if b == sender.default:
            self.removePrinterOption(sender.option)
            sender.pushbutton.setEnabled(False)
        else:
            sender.pushbutton.setEnabled(True)

            if b:
                self.setPrinterOption(sender.option, "true")
            else:
                self.setPrinterOption(sender.option, "false")
        

    def DefaultButton_clicked(self):
        sender = self.sender()
        sender.setEnabled(False)
        
        if sender.typ == cups.PPD_UI_BOOLEAN: # () On  (*) Off
            if sender.default:
                sender.control[0].setChecked(True)
                sender.control[0].setFocus(Qt.OtherFocusReason)
            else:
                sender.control[1].setChecked(True)
                sender.control[1].setFocus(Qt.OtherFocusReason)
                
            if not sender.job_option:
                self.removePrinterOption(sender.option)

        elif sender.typ == cups.PPD_UI_PICKONE: # [     >]
            choice, text = None, None

            for c, t in sender.choices:
                if c == sender.default:
                    choice = c
                    text = t
                    self.job_options[sender.option] = t
                    break

            if choice is not None:
                if not sender.job_option:
                    self.removePrinterOption(sender.option)
                
                #for i, y in enumerate(sender.control.
                #sender.control.setCurrentText(text)
                
                #self.linkPrintoutModeAndQuality(sender.option, choice) # XXXXXXXXXXXXXXXXXXXXXXXx
                sender.control.setFocus(Qt.OtherFocusReason)

        elif sender.typ == cups.UI_SPINNER: # [  <>]
            sender.control.setValue(sender.default)
            if not sender.job_option:
                self.removePrinterOption(sender.option)
            
            sender.control.setFocus(Qt.OtherFocusReason)
            
        elif sender.typ == cups.UI_BANNER_JOB_SHEETS: # start: [     >]  end: [     >]
            start, end, start_text, end_text = None, None, None, None
            for c, t in sender.choices:
                if c == sender.default[0]:
                    start = c
                    start_text = t
                
                if c == sender.default[1]:
                    end = c
                    end_text = t
                    
            if start is not None:
                sender.control[0].setCurrentText(start_text)
                
            if end is not None:
                sender.control[1].setCurrentText(end_text)
                
            if not sender.job_option:
                self.removePrinterOption('job-sheets')
            
            sender.control.setFocus(Qt.OtherFocusReason)
        
        elif sender.typ == cups.UI_PAGE_RANGE: # (*) All () Pages: [    ]
            sender.control[0].setChecked(True) # all radio button
            sender.control[0].setFocus(Qt.OtherFocusReason)
            sender.control[2].setEnabled(False) # range edit box
            
        
    def PageRangeAllRadio_toggled(self, b):
        if b:
            sender = self.sender()
            sender.edit_control.setEnabled(False)
            sender.pushbutton.setEnabled(False)
            self.job_options['pagerange'] = ''


    def PageRangeRangeRadio_toggled(self, b):
        if b:
            sender = self.sender()
            sender.pushbutton.setEnabled(True)
            sender.edit_control.setEnabled(True)    
            self.job_options['pagerange'] = unicode(sender.edit_control.text())
        
        
    def PageRangeEdit_editingFinished(self):
        sender, x = self.sender(), []
        t, ok = unicode(sender.text()), True
        try:
            x = utils.expand_range(t)
        except ValueError:
            ok = False
            
        if ok:
            if 0 in x:
                ok = False
            
            if ok:
                for y in x:
                    if y > 999:
                        ok = False
                        break 
            
        if ok:
            t = utils.collapse_range(x)
            sender.setText(QString(t))
            self.job_options['pagerange'] = t
        
        else:
            self.job_options['pagerange'] = ''
            log.error("Invalid page range: %s" % t)
            FailureUI(self, self.__tr("<b>Invalid page range.</b><p>Please enter a range using page numbers (1-999), dashes, and commas. For example: 1-2,3,5-7</p>"))
            sender.setFocus(Qt.OtherFocusReason)
        
        
    def PageRangeEdit_textChanged(self, t):
        sender, x, t = self.sender(), [], unicode(t)
        try:
            x = utils.expand_range(t)
        except ValueError:
            self.job_options['pagerange'] = ''
            log.error("Invalid page range: %s" % t)
        else:
            self.job_options['pagerange'] = t
     
     
    #
    # Printer I/O
    #
        
    def setPrinterOption(self, option, value):
        log.debug("setPrinterOption(%s, %s)" % (option, value))
        cups.openPPD(self.cur_printer)

        try:
            cups.addOption("%s=%s" % (option, value))
            cups.setOptions()
        finally:
            cups.closePPD()

    def removePrinterOption(self, option):
        log.debug("removePrinterOption(%s)" % option)
        cups.openPPD(self.cur_printer)

        try:
            cups.removeOption(option)
            cups.setOptions()
        finally:
            cups.closePPD()
        
    
    def __tr(self,s,c = None):
        return qApp.translate("PrintSettingsToolbox",s,c)
