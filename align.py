#!/usr/bin/env python
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

__version__ = '4.0'
__title__ = 'Printer Cartridge Alignment Utility'
__doc__ = "Cartridge alignment utility for HPLIP supported inkjet printers."

# Std Lib
import sys
import re
import getopt

# Local
from base.g import *
from base import device, status, utils, maint, tui
from prnt import cups

USAGE = [(__doc__, "", "name", True),
         ("""Usage: hp-align [PRINTER|DEVICE-URI] [OPTIONS]""", "", "summary", True),
         utils.USAGE_ARGS,
         utils.USAGE_DEVICE,
         utils.USAGE_PRINTER,
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         utils.USAGE_BUS1, utils.USAGE_BUS2,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_EXAMPLES,
         ("""Align CUPS printer named 'hp5550':""", """$ hp-align -php5550""",  "example", False),
         ("""Align printer with URI of 'hp:/usb/DESKJET_990C?serial=12345':""", """$ hp-align -dhp:/usb/DESKJET_990C?serial=12345""", 'example', False),
         utils.USAGE_SPACE,
         utils.USAGE_NOTES,
         utils.USAGE_STD_NOTES1, utils.USAGE_STD_NOTES2, 
         utils.USAGE_SEEALSO,
         ("hp-clean", "", "seealso", False),
         ("hp-colorcal", "", "seealso", False),
         ]


def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-align', __version__)
    sys.exit(0)

def enterAlignmentNumber(letter, hortvert, colors, line_count, maximum):
    return tui.enter_range("Enter the best aligned value for line %s (1-%d): " % 
                        (letter, maximum),
                        1,
                        maximum)

def enterPaperEdge(maximum):
    return tui.enter_range("Enter numbered arrow that is best aligned with the paper edge (1-%d): " 
                        % maximum,
                        1,
                        maximum)

def colorAdj(line, maximum):
    return tui.enter_range("Enter the numbered box on line %s that is best color matched to the background color (1-%d): " % 
                        (line, maximum),
                        1,
                        maximum)

def bothPensRequired():
    log.error("Cannot perform alignment with 0 or 1 cartridges installed.\nPlease install both cartridges and try again.")

def invalidPen():
    log.error("Invalid cartridge(s) installed.\nPlease install valid cartridges and try again.")

def invalidPen2():
    log.error("Invalid cartridge(s) installed. Cannot align with only the photo cartridge installed.\nPlease install other cartridges and try again.")

def aioUI1():
    log.info("To perform alignment, you will need the alignment page that is automatically\nprinted after you install a print cartridge.")
    log.info("If you would like to cancel, enter or 'c'")
    log.info("If you do not have this page (and need it to be printed), enter 'n'")
    log.info("If you already have this page, enter  'y'")

    ok, choice = tui.enter_choice("Enter 'c', 'y', or 'n': ", ['c', 'n', 'y'], 'n')
    return choice == 'y'

def type10and11Align(pattern, align_type):
    controls = maint.align10and11Controls(pattern, align_type)
    values = []
    s_controls = controls.keys()
    s_controls.sort()

    for line in s_controls:
        if not controls[line][0]:
            values.append(0)
        else:
            ok, value = tui.enter_range("Enter the numbered box on line %s where the inner lines best line up with the outer lines (1-%d): " 
                % (line, controls[line][1]),  1, controls[line][1])
            values.append(value)

    return values


def aioUI2():
    log.info("")
    log.info(log.bold("Follow these steps to complete the alignment:"))
    log.info("1. Place the alignment page, with the printed side facing down, ")
    log.info("   in the scanner.")
    log.info("2. Press the Enter or Scan button on the printer.")
    log.info('3. "Alignment Complete" will be displayed when the process is finished (on some models).')


try:
    opts, args = getopt.getopt(sys.argv[1:],
                                'p:d:hl:b:ag',
                                ['printer=',
                                  'device=',
                                  'help',
                                  'help-rest',
                                  'help-man',
                                  'help-desc',
                                  'logging=',
                                  'bus='
                                ]
                              )
except getopt.GetoptError:
    usage()

log.set_module("hp-align")

printer_name = None
device_uri = None
bus = device.DEFAULT_PROBE_BUS
log_level = logger.DEFAULT_LOG_LEVEL
align_debug = False

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    if o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-p', '--printer'):
        if a.startswith('*'):
            printer_name = cups.getDefault()
        else:
            printer_name = a

    elif o in ('-d', '--device'):
        device_uri = a

    elif o in ('-b', '--bus'):
        bus = a.lower().strip()
        if not device.validateBusList(bus):
            usage()

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o == '-a':
        align_debug = True



if device_uri and printer_name:
    log.error("You may not specify both a printer (-p) and a device (-d).")
    usage()

utils.log_title(__title__, __version__)

if not device_uri and not printer_name:
    try:
        device_uri = device.getInteractiveDeviceURI(bus)
        if device_uri is None:
            sys.exit(0)
    except Error:
        log.error("Error occured during interactive mode. Exiting.")
        sys.exit(0)

try:
    d = device.Device( device_uri, printer_name )
except Error, e:
    log.error("Unable to open device: %s" % e.msg)
    sys.exit(0)

if d.device_uri is None and printer_name:
    log.error("Printer '%s' not found." % printer_name)
    sys.exit(0)

if d.device_uri is None and device_uri:
    log.error("Malformed/invalid device-uri: %s" % device_uri)
    sys.exit(0)
    
user_cfg.last_used.device_uri = d.device_uri

if not d.cups_printers:
    log.error("No appropriate printer queue found for device. Please setup printer with hp-setup and try again.")
    sys.exit(1)

try:
    try:
        d.open()
    except Error:
        log.error("Device is busy or in an error state. Please check device and try again.")
        sys.exit(1)

    if d.isIdleAndNoError():
        align_type = d.mq.get('align-type', 0)
        log.debug("Alignment type=%d" % align_type)
        d.close()

        if align_type == ALIGN_TYPE_NONE:
            log.error("Alignment not supported or required by device.")
            sys.exit(0)

        if align_type == ALIGN_TYPE_AUTO:
            maint.AlignType1(d, tui.load_paper_prompt)

        elif align_type == ALIGN_TYPE_8XX:
            maint.AlignType2(d, ui.load_paper_prompt, enterAlignmentNumber,
                              bothPensRequired)

        elif align_type in (ALIGN_TYPE_9XX,ALIGN_TYPE_9XX_NO_EDGE_ALIGN):
            maint.AlignType3(d, ui.load_paper_prompt, enterAlignmentNumber,
                              enterPaperEdge, update_spinner)

        elif align_type == ALIGN_TYPE_LIDIL_AIO:
            maint.AlignType6(d, aioUI1, aioUI2, ui.load_paper_prompt)

        elif align_type == ALIGN_TYPE_DESKJET_450:
            maint.AlignType8(d, ui.load_paper_prompt, enterAlignmentNumber)

        elif align_type in (ALIGN_TYPE_LIDIL_0_3_8, ALIGN_TYPE_LIDIL_0_4_3, ALIGN_TYPE_LIDIL_VIP):

            maint.AlignxBow(d, align_type, ui.load_paper_prompt, enterAlignmentNumber, enterPaperEdge,
                             invalidPen, colorAdj)

        elif align_type  == ALIGN_TYPE_LBOW:
            maint.AlignType10(d, ui.load_paper_prompt, type10and11Align)

        elif align_type == ALIGN_TYPE_LIDIL_0_5_4:
            maint.AlignType11(d, ui.load_paper_prompt, type10and11Align, invalidPen2)
            
        elif align_type == ALIGN_TYPE_OJ_PRO:
            maint.AlignType12(d, ui.load_paper_prompt)
            

        else:
            log.error("Invalid alignment type.")

    else:
        log.error("Device is busy or in an error state. Please check device and try again.")

finally:
    d.close()

log.info("")
log.info('Done.')
