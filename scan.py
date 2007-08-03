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

from __future__ import division

__version__ = '0.5'
__title__ = 'Scan Utility'
__doc__ = "SANE-based scan utility for HPLIP." 

# Std Lib
import sys, os, os.path, getopt, signal, time, socket

# Local
from base.g import *
#from base.msg import *
from base import tui
import base.utils as utils
from base import device, service

log.set_module('hp-scan')

prop.prog = sys.argv[0]

device_uri = None
username = prop.username
mode = GUI_MODE
mode_specified = False
res = 300
scan_mode = 'color'
tlx = None
tly = None
brx = None
bry = None
units = "mm"
output = ''
dest = []
email_from = ''
email_to = []
email_subject = 'hp-scan from %s' % socket.gethostname()
email_note = ''
fax = ''
resize = 100
contrast = 0
brightness = 0
printer = ''
page_size = ''
size_desc = ''
page_units = 'mm'
valid_res = (75, 150, 300, 600, 1200, 2400, 4800)
default_res = 300
scanner_compression = 'JPEG'


PAGE_SIZES = { # in mm
    '5x7' : (127, 178, "5x7 photo", 'in'),
    '4x6' : (102, 152, "4x6 photo", 'in'),
    '3x5' : (76, 127, "3x5 index card", 'in'),
    'a2_env' : (111, 146, "A2 Envelope", 'in'),
    'a3' : (297, 420, "A3", 'mm'),
    "a4" : (210, 297, "A4", 'mm'),
    "a5" : (148, 210, "A5", 'mm'),
    "a6" : (105, 148, "A6", 'mm'),
    "b4" : (257, 364, "B4", 'mm'),
    "b5" : (182, 257, "B5", 'mm'),
    "c6_env" : (114, 162, "C6 Envelope", 'in'),
    "dl_env" : (110, 220, "DL Envelope", 'in'),
    "exec" : (184, 267, "Executive", 'in'),
    "flsa" : (216, 330, "Flsa", 'mm'),
    "higaki" : (100, 148, "Hagaki", 'mm'),
    "japan_env_3" : (120, 235, "Japanese Envelope #3", 'mm'),
    "japan_env_4" : (90, 205, "Japanese Envelope #4", 'mm'),
    "legal" : (215, 356, "Legal", 'in'),
    "letter" : (215, 279, "Letter", 'in'),
    "no_10_env" : (105, 241, "Number 10 Envelope", 'in'),
    "oufufu-hagaki" : (148, 200, "Oufuku-Hagaki", 'mm'),
    "photo" : (102, 152, "Photo", 'in'),
    "super_b" : (330, 483, "Super B", 'in'),
    }

USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-scan [SANE-DEVICE-URI] [MODE] [-n OPTIONS] [OPTIONS]", "", "summary", True),
         ("[SANE-DEVICE-URI]", "", "header", False),
         ("SANE device URI:", "-d<sane_device_uri> or --device=<sane_device_uri>", "option", False),
         ("", "URI format: hpaio:/<bus>/<model>?<identification>", "option", False),

         utils.USAGE_SPACE,
         ("[MODE]", "", "header", False),
         ("Enter graphical UI mode:", "-u or --gui (Default)", "option", False),
         ("Run in non-interactive mode:", "-n or --non-interactive", "option", False),

         utils.USAGE_SPACE,
         ("[-n OPTIONS] (General) (Not applicable to GUI mode)", "", "header", False),
         ("Scan destinations:", "-s<dest_list> or --dest=<dest_list>", "option", False),
         ("", "where <dest_list> is a comma separated list containing one or more of: 'file'\*, ", "option", False),
         ("", "'viewer', 'editor', 'pdf', 'fax', or 'print'. Use only commas between values, no spaces.", "option", False), 
         ("Scan mode:", "-m<mode> or --mode=<mode>. Where <mode> is 'color'\*, 'gray' or 'lineart'.", "option", False),
         ("Scanning resolution:", "-r<resolution_in_dpi> or --res=<resolution_in_dpi> or --resolution=<resolution_in_dpi>", "option", False),
         ("", "where <resolution_in_dpi> is %s (300 is default)." % ', '.join([str(x) for x in valid_res]), "option", False),
         ("Image resize:", "--resize=<scale_in_%> (min=1%, max=400%, default=100%)", "option", False),
         ("Image contrast:", "--contrast=<contrast>", "option", False),

         utils.USAGE_SPACE,
         ("[-n OPTIONS] (Scan area) (Not applicable to GUI mode)", "", "header", False),
         ("Specify the units for area/box measurements:", "-t<units> or --units=<units>", "option", False),
         ("", "where <units> is 'mm'\*, 'cm', 'in', 'px', or 'pt' ('mm' is default).", "option", False),
         ("Scan area:", "-a<tlx>,<tly>,<brx>,<bry> or --area=<tlx>,<tly>,<brx>,<bry>", "option", False),
         ("", "Coordinates are relative to the upper left corner of the scan area.", "option", False),
         ("", "Units for tlx, tly, brx, and bry are specified by -t/--units (default is 'mm').", "option", False),
         ("", "Use only commas between values, no spaces.", "option", False),
         ("Scan box:", "--box=<tlx>,<tly>,<width>,<height>", "option", False),
         ("", "tlx and tly coordinates are relative to the upper left corner of the scan area.", "option", False),
         ("", "Units for tlx, tly, width, and height are specified by -t/--units (default is 'mm').", "option", False),         
         ("", "Use only commas between values, no spaces.", "option", False),
         ("Top left x of the scan area:", "--tlx=<tlx>", "option", False),
         ("", "Coordinates are relative to the upper left corner of the scan area.", "option", False),
         ("", "Units are specified by -t/--units (default is 'mm').", "option", False),
         ("Top left y of the scan area:", "--tly=<tly>", "option", False),
         ("", "Coordinates are relative to the upper left corner of the scan area.", "option", False),
         ("", "Units are specified by -t/--units (default is 'mm').", "option", False),
         ("Bottom right x of the scan area:", "--brx=<brx>", "option", False),
         ("", "Coordinates are relative to the upper left corner of the scan area.", "option", False),
         ("", "Units are specified by -t/--units (default is 'mm').", "option", False),
         ("Bottom right y   of the scan area:", "--bry=<bry>", "option", False),
         ("", "Coordinates are relative to the upper left corner of the scan area.", "option", False),
         ("", "Units are specified by -t/--units (default is 'mm').", "option", False),
         ("Specify the scan area based on a paper size:", "--size=<paper size name>", "option", False),
         ("", "where <paper size name> is one of: %s" % ', '.join(PAGE_SIZES.keys()), "option", False), 
         utils.USAGE_SPACE,
         ("[-n OPTIONS] ('file' dest) (Not applicable to GUI mode)", "", "header", False),
         ("Filename for 'file' destination:", "-o<file> or -f<file> or --file=<file> or --output=<file>", "option", False),

         utils.USAGE_SPACE,
         ("[-n OPTIONS] ('pdf' dest) (Not applicable to GUI mode)", "", "header", False),

         ("PDF viewer application:", "--pdf=<pdf_viewer>", "option", False),
         utils.USAGE_SPACE,
         ("[-n OPTIONS] ('viewer' dest) (Not applicable to GUI mode)", "", "header", False),

         ("Image viewer application:", "-v<viewer> or --viewer=<viewer>", "option", False),
         utils.USAGE_SPACE,
         ("[-n OPTIONS] ('editor' dest) (Not applicable to GUI mode)", "", "header", False),
         ("Image editor application:", "-e<editor> or --editor=<editor>", "option", False),
         utils.USAGE_SPACE,

         ("[-n OPTIONS] ('email' dest) (Not applicable to GUI mode)", "", "header", False),
         ("From: address for 'email' dest:", "--email-from=<email_from_address> (required for 'email' dest.)", "option", False),

         ("To: address for 'email' dest:", "--email-to=<email__to_address> (required for 'email' dest.)", "option", False),
         ("Email subject for 'email' dest:", '--email-subject="<subject>"', "option", False),
         ("", 'Use double quotes (") around the subject if it contains space characters.', "option", False),
         ("Note or message for the 'email' dest:", '--email-msg="<msg>" or --email-note="<note>"', "option", False),
         ("", 'Use double quotes (") around the note/message if it contains space characters.', "option", False),

         utils.USAGE_SPACE,
         ("[-n OPTIONS] ('fax' dest) (Not applicable to GUI mode)", "", "header", False),
         ("Fax queue/printer:", "--fax=<fax_printer_name>", "option", False),
         utils.USAGE_SPACE,
         ("[-n OPTIONS] ('printer' dest) (Not applicable to GUI mode)", "", "header", False),
         ("Printer queue/printer:", "--printer=<printer_name>", "option", False),
         utils.USAGE_SPACE,
         ("[-n OPTIONS] (advanced) (Not applicable to GUI mode)", "", "header", False),
         ("Set the scanner compression mode:", "-x<mode> or --compression=<mode>, <mode>='raw', 'none' or 'jpeg' ('jpeg' is default) ('raw' and 'none' are equivalent)", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_NOTES,
         ("1. If no dest is provided, the 'file' dest will be automatically invoked.", "", "note", False),
         ("2. If applications for viewer, editor, or pdf viewer are not provided, reasonable defaults will be used.", "", "note", False),
         ("3. If --printer is not specified, the CUPS default will be used if available.", "", "note", False),
         ("4. If an output file is not specified with the 'file' dest, a reasonable default will be used.", "", "note", False),
         ("5. Some options may not be valid on some scanning devices.", "", "note", False),
         ("6. The following features are not yet implemented: GUI mode, ADF scanning, batch scanning, film/negative scanning, contrast adjustment, brightness adjustment, autocrop, resize to axb, resize to xKB, ", "", "note", False),

         utils.USAGE_SPACE,
         utils.USAGE_EXAMPLES,
         ("Quickly (low-res) scan entire page in color to file:", "$ hp-scan -n -r75",  "example", False),
         ("Scan upper left 1in corner and send as email:", '$ hp-scan -n --box=0,0,1,1 -tin -semail --email-from=foo@bar.org --email-to=bar@foo.org --email-note="Test scan" --email-subject="Test scan email"', "example", False),
         ("Scan entire page in 300dpi grayscale and then edit:", "$ hp-scan -n -seditor -mgray",  "example", False),
         ("Launch the hp-scan GUI:", "$ hp-scan",  "example", False),
         ("Scan into The GIMP:", "$ hp-scan -n --editor=gimp",  "example", False),
        ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-scan', __version__)
    sys.exit(0)





viewer = ''
viewer_list = ['kview', 'display', 'gwenview', 'eog', 'kuickshow',]
for v in viewer_list:
    vv = utils.which(v)
    if vv:
        viewer = os.path.join(vv, v)
        break


editor = ''
editor_list = ['kolourpaint', 'gimp', 'krita', 'cinepaint', 'mirage',]
for e in editor_list:
    ee = utils.which(e)
    if ee:
        editor = os.path.join(ee, e)
        break

pdf_viewer = ''
pdf_viewer_list = ['kpdf', 'acroread', 'xpdf', 'evince',]
for v in pdf_viewer_list:
    vv = utils.which(v)
    if vv:
        pdf_viewer = os.path.join(vv, v)
        break

try:
    opts, args = getopt.getopt(sys.argv[1:],'l:hd:p:b:gunr:m:t:o:s:f:v:e:c:a:x:', 
        ['device=', 'printer=', 'level=', 
         'help', 'help-rest', 
         'help-man', 'logfile=', 
         'gui', 'non-interactive', 'logging=',
          'help-desc', 'resolution=', 'res=', 'mode=',
          'tlx=', 'tly=', 'brx=', 'bry=', 'units=', 
          'area=', 'box=', 'output=', 'dest=', 'destination=',
          'file=', 'pdf=', 'viewer=', 'editor=',
          'email-from=', 'email-to=', 'resize=',
          'email-subject=', 'email-note=', 'email-msg=',
          'contrast=', 'brightness=', 'size=', 'compression='])



except getopt.GetoptError, e:
    log.error(e)
    sys.exit(1)

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    if o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-d', '--device'):
        device_uri = a

    elif o in ('-n', '--non-interactive'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-n or -u).")
            sys.exit(1)

        mode = NON_INTERACTIVE_MODE
        mode_specified = True

    elif o in ('-u', '--gui'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-n or -u).")
            sys.exit(1)

        mode = GUI_MODE
        mode_specified = True

    elif o in ('-x', '--compression'):
        a = a.strip().lower()

        if a in ('jpeg', 'jpg'):
            scanner_compression = 'JPEG'

        elif a in ('raw', 'none'):
            scanner_compression = 'None'

        else:
            log.error("Invalid compression value. Valid values are 'jpeg', 'raw', and 'none'.")
            log.error("Using default value of 'jpeg'.")
            scanner_compression = 'JPEG'

    elif o in ('-m', '--mode'):
        a = a.strip().lower()

        if a in ('color', 'colour'):
            scan_mode = 'color'

        elif a in ('lineart', 'bw', 'b&w'):
            scan_mode = 'lineart'

        elif a in ('gray', 'grayscale', 'grey', 'greyscale'):
            scan_mode = 'gray'

        else:
            log.error("Invalid mode. Using default of 'color'.")
            log.error("Valid modes are 'color', 'lineart', or 'gray'.")
            scan_mode = 'color'

    elif o in ('--res', '--resolution', '-r'):
        try:
            r = int(a.strip())
        except ValueError:
            log.error("Invalid resolution. Using default of %s dpi." % default_res)
            log.error("Valid resolutions are %s dpi." % ', '.join([str(x) for x in valid_res]))
            res = default_res
        else:
            if r in valid_res: 
                res = r
            else:
                res = valid_res[0]
                min_dist = sys.maxint
                for x in valid_res: 
                    if abs(r-x) < min_dist:
                        min_dist = abs(r-x)
                        res = x

                log.warn("Invalid resolution. Using closest valid resolution of %d dpi" % res)
                log.error("Valid resolutions are %s dpi." % ', '.join([str(x) for x in valid_res]))

    elif o in ('-t', '--units'):
        a = a.strip().lower()

        if a in ('in', 'inch', 'inches'):
            units = 'in'

        elif a in ('mm', 'milimeter', 'milimeters', 'millimetre', 'millimetres'):
            units = 'mm'

        elif a in ('cm', 'centimeter', 'centimeters', 'centimetre', 'centimetres'):
            units = 'cm'

        elif a in ('px', 'pixel', 'pixels', 'pel', 'pels'):
            units = 'px'

        elif a in ('pt', 'point', 'points'):
            units = 'pt'

        else:
            log.error("Invalid units. Using default of mm.")
            units = 'mm'

    elif o == '--tlx':
        a = a.strip().lower()
        try:
            f = float(a)
        except ValueError:
            log.error("Invalid value for tlx.")
        else:
            tlx = f

    elif o == '--tly':
        a = a.strip().lower()
        try:
            f = float(a)
        except ValueError:
            log.error("Invalid value for tly.")
        else:
            tly = f

    elif o == '--brx':
        a = a.strip().lower()
        try:
            f = float(a)
        except ValueError:
            log.error("Invalid value for brx.")
        else:
            brx = f

    elif o == '--bry':
        a = a.strip().lower()
        try:
            f = float(a)
        except ValueError:
            log.error("Invalid value for bry.")
        else:
            bry = f

    elif o in ('-a', '--area'): # tlx, tly, brx, bry
        a = a.strip().lower()
        try:
            tlx, tly, brx, bry = a.split(',')[:4]
        except ValueError:
            log.error("Invalid scan area. Using defaults.")
        else:
            try:
                tlx = float(tlx)
            except ValueError:
                log.error("Invalid value for tlx. Using defaults.")
                tlx = None

            try:
                tly = float(tly)
            except ValueError:
                log.error("Invalid value for tly. Using defaults.")
                tly = None

            try:
                brx = float(brx)
            except ValueError:
                log.error("Invalid value for brx. Using defaults.")
                brx = None

            try:
                bry = float(bry)
            except ValueError:
                log.error("Invalid value for bry. Using defaults.")
                bry = None

    elif o == '--box': # tlx, tly, w, h
        a = a.strip().lower()
        try:
            tlx, tly, width, height = a.split(',')[:4]
        except ValueError:
            log.error("Invalid scan area. Using defaults.")
        else:
            try:
                tlx = float(tlx)
            except ValueError:
                log.error("Invalid value for tlx. Using defaults.")
                tlx = None

            try:
                tly = float(tly)
            except ValueError:
                log.error("Invalid value for tly. Using defaults.")
                tly = None

            if tlx is not None:
                try:
                    brx = float(width) + tlx
                except ValueError:
                    log.error("Invalid value for width. Using defaults.")
                    brx = None
            else:
                log.error("Cannot calculate brx since tlx is invalid. Using defaults.")
                brx = None

            if tly is not None:
                try:
                    bry = float(height) + tly
                except ValueError:
                    log.error("Invalid value for height. Using defaults.")
                    bry = None    
            else:
                log.error("Cannot calculate bry since tly is invalid. Using defaults.")
                bry = None

    elif o == '--size':
        size = a.strip().lower()
        if size in PAGE_SIZES:
            brx, bry, size_desc, page_units = PAGE_SIZES[size]
            tlx, tly = 0, 0
            page_size = size
        else:
            log.error("Invalid page size. Valid page sizes are: %s" % ', '.join(PAGE_SIZES.keys()))
            log.error("Using defaults.")

    elif o in ('-o', '--output', '-f', '--file'):
        output = os.path.abspath(os.path.normpath(os.path.expanduser(a.strip())))

        try:
            ext = os.path.splitext(output)[1]
        except IndexError:
            log.error("Invalid filename extension.")
            output = ''
            if 'file' in dest:
                dest.remove('file')
        else:
            if ext.lower() not in ('.jpg', '.png'):
                log.error("Only JPG (.jpg) and PNG (.png) output files are supported.")
                output = ''
                if 'file' in dest:
                    dest.remove('file')
            else:
                if os.path.exists(output):
                    log.warn("Output file '%s' exists. File will be overwritten." % output)

                if 'file' not in dest:
                    dest.append('file')

    elif o in ('-s', '--dest', '--destination'):
        a = a.strip().lower().split(',')
        for aa in a:
            aa = aa.strip()
            if aa in ('file', 'fax', 'viewer', 'editor', 'printer', 'print', 'email', 'pdf') \
                and aa not in dest:
                if aa == 'print': aa = 'printer'
                dest.append(aa)

    elif o in ('-v', '--viewer'):
        a = a.strip()
        b = utils.which(a)
        if not b:
            log.error("Viewer application not found.")
        else:
            viewer = os.path.join(b, a)
            if 'viewer' not in dest:
                dest.append('viewer')

    elif o in ('-e', '--editor'):
        a = a.strip()
        b = utils.which(a)
        if not b:
            log.error("Editor application not found.")
        else:
            editor = os.path.join(b, a)
            if 'editor' not in dest:
                dest.append('editor')

    elif o == '--pdf':
        a = a.strip()
        b = utils.which(a)
        if not b:
            log.error("PDF viewer application not found.")
        else:
            pdf_viewer = os.path.join(b, a)
            if 'pdf' not in dest:
                dest.append('pdf')

    elif o in ('-p', '--printer'):
        pp = a.strip()
        from prnt import cups
        printer_list = cups.getPrinters()
        found = False
        for p in printer_list:
            if p.name == pp:
                found = True
                printer = pp
                break

        if found: 
            if 'printer' not in dest:
                dest.append('printer')
        else:
            log.error("Unknown/invalid printer name: %s" % printer)

    elif o == '--email-to':
        email_to = a.split(',')
        if 'email' not in dest:
            dest.append('email')

    elif o == '--email-from':
        email_from = a
        if 'email' not in dest:
            dest.append('email')

    elif o == '--email-subject':
        email_subject = a
        if 'email' not in dest:
            dest.append('email')

    elif o in ('--email-note', '--email-msg'):
        email_note = a
        if 'email' not in dest:
            dest.append('email')

    elif o == '--resize':
        a = a.replace("%", "")
        try:
            resize = int(a)
        except ValueError:
            resize = 100
            log.error("Invalid resize value. Using default of 100%.")

    elif o in ('-b', '--brightness'):
        pass

    elif o in ('-c', '--contrast'):
        try:
            contrast = int(a.strip())
        except ValueError:
            log.error("Invalid contrast value. Using default of 100.")
            contrast = 100


utils.log_title(__title__, __version__)

if 'printer' in dest and not printer:
    from prnt import cups
    printer = cups.getDefaultPrinter()

    if printer is not None:
        log.warn("Print destination enabled with no printer specified.")
        log.warn("Using CUPS default printer '%s'." % printer)
    else:
        log.error("Print destination enabled with no printer specified.")
        log.error("No CUPS default printer found. Disabling 'print' destination.")
        dest.remove("printer")

if not dest:
    log.warn("No destinations specified. Adding 'file' destination by default.")
    dest.append('file')

if 'file' in dest and not output:
    log.warn("File destination enabled with no output file specified.")

    if scan_mode == 'gray':
        output = utils.createSequencedFilename("hpscan", ".png")
    else:
        output = utils.createSequencedFilename("hpscan", ".jpg")

    log.warn("Defaulting to '%s'." % output)

try:
    output_type = os.path.splitext(output)[1].lower()
except IndexError:
    output_type = ''

if scan_mode == 'gray' and output_type and output_type != '.png':
    log.error("Grayscale scans must be saved in PNG file format. To save in other formats, set the 'editor' destination and save the image from the editor.")
    sys.exit(1)

if 'email' in dest and (not email_from or not email_to):
    log.error("Email specified, but email to and/or email from address(es) were not specified.")
    log.error("Disabling 'email' destination.")
    dest.remove("email")

if page_size:
    units = 'mm'

if units == 'in':
    if tlx is not None: tlx = tlx * 25.4
    if tly is not None: tly = tly * 25.4
    if brx is not None: brx = brx * 25.4
    if bry is not None: bry = bry * 25.4

elif units == 'cm':
    if tlx is not None: tlx = tlx * 10.0
    if tly is not None: tly = tly * 10.0
    if brx is not None: brx = brx * 10.0
    if bry is not None: bry = bry * 10.0

elif units == 'pt':
    if tlx is not None: tlx = tlx * 0.3528
    if tly is not None: tly = tly * 0.3528
    if brx is not None: brx = brx * 0.3528
    if bry is not None: bry = bry * 0.3528

elif units == 'px':
    log.warn("Units set to pixels. Using resolution of %ddpi for area calculations." % res)
    if tlx is not None: tlx = tlx / res * 25.4
    if tly is not None: tly = tly / res * 25.4
    if brx is not None: brx = brx / res * 25.4
    if bry is not None: bry = bry / res * 25.4

if tlx is not None and brx is not None and tlx >= brx:
    log.error("Invalid values for tlx (%d) and brx (%d) (tlx>=brx). Using defaults." % (tlx, brx))
    tlx = brx = None

if tly is not None and bry is not None and tly >= bry:
    log.error("Invalid values for tly (%d) and bry (%d) (tly>=bry). Using defaults." % (tly, bry))
    tly = bry = None




# Security: Do *not* create files that other users can muck around with
os.umask (0037)

if not prop.scan_build:
    log.error("Scanning disabled in build. Exiting")
    sys.exit(1)

if mode == GUI_MODE:
    log.error("GUI mode is not implemented yet. Please use -n. Refer to 'hp-scan -h' for help.")
    sys.exit(1)

    if not prop.gui_build:
        log.warn("GUI mode disabled in build. Reverting to interactive mode.")
        mode = NON_INTERACTIVE_MODE

    elif not os.getenv('DISPLAY'):
        log.warn("No display found. Reverting to interactive mode.")
        mode = NON_INTERACTIVE_MODE

    elif not utils.checkPyQtImport():
        log.warn("PyQt init failed. Reverting to interactive mode.")
        mode = NON_INTERACTIVE_MODE

if mode == GUI_MODE:
    app = None
    sendfax = None

    from qt import *

    # UI Forms
    from ui.scanform import ScanForm

    try:
        hpssd_sock = service.startup()
    except Error:
        log.error("Unable to connect to HPLIP I/O (hpssd).")
        sys.exit(1)

    # create the main application object
    app = QApplication(sys.argv)

    loc = user_cfg.ui.get("loc", "system")
    if loc.lower() == 'system':
        loc = str(QTextCodec.locale())
        log.debug("Using system locale: %s" % loc)

    if loc.lower() != 'c':
        log.debug("Trying to load .qm file for %s locale." % loc)
        trans = QTranslator(None)
        qm_file = 'hplip_%s.qm' % loc
        log.debug("Name of .qm file: %s" % qm_file)
        loaded = trans.load(qm_file, prop.localization_dir)

        if loaded:
            app.installTranslator(trans)
        else:
            loc = 'c'
    else:
        loc = 'c'

    if loc == 'c':
        log.debug("Using default 'C' locale")
    else:
        log.debug("Using locale: %s" % loc)

    scanui = ScanForm(hpssd_sock,
                         device_uri,  
                         printer_name, 
                         args) 

    app.setMainWidget(scanui)

    pid = os.getpid()
    log.debug('pid=%d' % pid)

    scanui.show()

    signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    try:
        log.debug("Starting GUI loop...")
        app.exec_loop()
    except KeyboardInterrupt:
        pass
    except:
        log.exception()

else: # NON_INTERACTIVE_MODE
    #import struct, Queue
    import Queue
    from scan import sane
    import scanext
    import cStringIO
    import popen2

    try:
        import Image
    except ImportError:
        log.error("'hp-scan -n' requires the Python Imaging Library (PIL). Please install it and try again or run 'hp-scan -u' instead.")
        sys.exit(1)

    try:
        hpssd_sock = service.startup()
    except Error:
        log.error("Unable to connect to HPLIP I/O (hpssd).")
        sys.exit(1)

    sane.init()
    devices = sane.getDevices()

    if not device_uri:
        if len(devices) == 0:
            log.error("No scanning devices found.")
            sys.exit(1)

        elif len(devices) == 1:
            device_uri = devices[0][0]

        else:
            log.info(log.bold("\nChoose device:\n"))

            max_deviceid_size = 0
            for d in devices:
                max_deviceid_size = max(len(d[0]), max_deviceid_size)

            formatter = utils.TextFormatter(
                    (
                        {'width': 4},
                        {'width': max_deviceid_size, 'margin': 2},
                    )
                )

            log.info(formatter.compose(("Num.", "Device URI")))
            log.info(formatter.compose(('-'*4, '-'*(max_deviceid_size))))

            i = 0
            for d in devices:
                log.info(formatter.compose((str(i), d[0])))
                i += 1

            ok, x = tui.enter_range("\nEnter number 0...%d for device (q=quit) ?" % (i-1), 0, (i-1))
            if not ok: sys.exit(0)
            device_uri = devices[x][0]


    log.info(log.bold("Using device %s" % device_uri))
    log.info("Opening connection to device...")

    try:
        device = sane.openDevice(device_uri)
    except scanext.error, e:
        log.error(e)
        sys.exit(1)

    #print device.options

    tlx = device.getOptionObj('tl-x').limitAndSet(tlx)
    tly = device.getOptionObj('tl-y').limitAndSet(tly)
    brx = device.getOptionObj('br-x').limitAndSet(brx)
    bry = device.getOptionObj('br-y').limitAndSet(bry)

    scan_area = (brx - tlx) * (bry - tly) # mm^2
    scan_px = scan_area * res * res / 645.16 # res is in DPI

    if scan_mode == 'color':
        scan_size = scan_px * 3 # 3 bytes/px
    else:
        scan_size = scan_px # 1 byte/px

    if scan_size > 52428800: # 50MB
        if res > 600:
            log.warn("Using resolutions greater than 600 dpi will cause very large files to be created.")
        else:
            log.warn("The scan current parameters will cause very large files to be created.")

        log.warn("This can cause the scan to take a long time to complete and may cause your system to slow down.")
        log.warn("Approx. number of bytes to read from scanner: %s" % utils.format_bytes(scan_size, True))

    res = device.getOptionObj('resolution').limitAndSet(res)

    device.setOption('compression', scanner_compression)

    if brx - tlx <= 0.0 or bry - tly <= 0.0:
        log.error("Invalid scan area.")
        sys.exit(1)

    log.info("")
    log.info("Resolution: %ddpi" % res)
    log.info("Mode: %s" % scan_mode)
    log.info("Compression: %s" % scanner_compression)
    log.info("Scan area (mm):")
    log.info("  Top left (x,y): (%fmm, %fmm)" % (tlx, tly))
    log.info("  Bottom right (x,y): (%fmm, %fmm)" % (brx, bry))
    log.info("  Width: %fmm" % (brx - tlx))
    log.info("  Height: %fmm" % (bry - tly))

    if page_size:
        units = page_units # for display purposes only
        log.info("Page size: %s" % size_desc)
        if units != 'mm':
            log.note("This scan area below in '%s' units may not be exact due to rounding errors." % units)

    if units == 'in':
        log.info("Scan area (in):")
        log.info("  Top left (x,y): (%fin, %fin)" % (tlx/25.4, tly/25.4))
        log.info("  Bottom right (x,y): (%fin, %fin)" % (brx/25.4, bry/25.4))
        log.info("  Width: %fin" % ((brx - tlx)/25.4))
        log.info("  Height: %fin" % ((bry - tly)/25.4))

    elif units == 'cm':
        log.info("Scan area (cm):")
        log.info("  Top left (x,y): (%fcm, %fcm)" % (tlx/10.0, tly/10.0))
        log.info("  Bottom right (x,y): (%fcm, %fcm)" % (brx/10.0, bry/10.0))
        log.info("  Width: %fcm" % ((brx - tlx)/10.0))
        log.info("  Height: %fcm" % ((bry - tly)/10.0))

    elif units == 'px':
        log.info("Scan area (px @ %ddpi):" % res)
        log.info("  Top left (x,y): (%fpx, %fpx)" % (tlx*res/25.4, tly*res/25.4))
        log.info("  Bottom right (x,y): (%fpx, %fpx)" % (brx*res/25.4, bry*res/25.4))
        log.info("  Width: %fpx" % ((brx - tlx)*res/25.4))
        log.info("  Height: %fpx" % ((bry - tly)*res/25.4))

    elif units == 'pt':
        log.info("Scan area (pt):")
        log.info("  Top left (x,y): (%fpt, %fpt)" % (tlx/0.3528, tly/0.3528))
        log.info("  Bottom right (x,y): (%fpt, %fpt)" % (brx/0.3528, bry/0.3528))
        log.info("  Width: %fpt" % ((brx - tlx)/0.3528))
        log.info("  Height: %fpt" % ((bry - tly)/0.3528))

    log.info("Destination(s): %s" % ', '.join(dest))

    if 'file' in dest:
        log.info("Output file: %s" % output)

    update_queue = Queue.Queue()
    event_queue = Queue.Queue()

    device.setOption("mode", scan_mode)
    device.setOption("resolution", res)

    log.info("\nWarming up...")
    bytes_read = 0
    try:
        try:
            try:
                ok, expected_bytes = device.startScan("RGBA", update_queue, event_queue)
            except scanext.error, e:
                log.error(e)
                sys.exit(1)

            log.info("Scanning...")
            log.info("Expecting to read %s from scanner." % utils.format_bytes(expected_bytes))
            cleanup_spinner()
            log.info("")
            
            pm = tui.ProgressMeter("Reading data:")

            while device.isScanActive():
                while update_queue.qsize():
                    try:
                        status, bytes_read = update_queue.get(0)
                        
                        if status != scanext.SANE_STATUS_GOOD:
                            log.error("SANE error %d" % status)
                            sys.exit(1)

                    except Queue.Empty:
                        break

                pm.update(int(100*bytes_read/expected_bytes), 
                    utils.format_bytes(bytes_read))

                time.sleep(0.5)
                
        except KeyboardInterrupt:
            log.error("Aborted.")
            sys.exit(1)

        while update_queue.qsize():
            status, bytes_read = update_queue.get(0)
            
            pm.update(int(100*bytes_read/expected_bytes), 
                utils.format_bytes(bytes_read))

            if status != scanext.SANE_STATUS_GOOD:
                log.error("SANE error %d" % status)
                sys.exit(1)
            
            
        log.info("")

        if bytes_read:
            log.info("Read %s from scanner." % utils.format_bytes(bytes_read))

            buffer, format, format_name, pixels_per_line, \
                lines, depth, bytes_per_line, pad_bytes, total_read = device.getScan()

            if scan_mode == 'color':
                im = Image.frombuffer('RGBA', (pixels_per_line, lines), buffer.read(), 
                    'raw', 'RGBA', 0, 1)

            elif scan_mode == 'gray':
                im = Image.frombuffer('RGBA', (pixels_per_line, lines), buffer.read(), 
                    'raw', 'RGBA', 0, 1).convert('P')

            elif scan_mode == 'lineart':
                im = Image.frombuffer('RGBA', (pixels_per_line, lines), buffer.read(), 
                    'raw', 'RGBA', 0, 1).convert('L')
                    
        else:
            log.error("No data read.")
            sys.exit(1)

    finally:
        log.info("Closing device.")
        device.freeScan()
        sane.deInit()

    if resize != 100:
        if resize < 1 or resize > 400:
            log.error("Resize parameter is incorrect. Resize must be 0% < resize < 400%.")
            log.error("Using resize value of 100%.")
        else:
            new_w = pixels_per_line * resize / 100
            new_h = lines * resize / 100
            log.info("Resizing from %dx%d to %dx%d..." % (pixels_per_line, lines, new_w, new_h))
            im = im.resize((new_w, new_h), Image.ANTIALIAS)

    file_saved = False
    if 'file' in dest:
        log.info("\nOutputting to destination 'file':")
        log.info("Saving to file %s" % output)

        try:
            im.save(output)
        except IOError, e:
            log.error("Error saving file: %s" % e)

            try:
                os.remove(output)
            except OSError:
                pass

            sys.exit(1)

        file_saved = True
        dest.remove("file")

    temp_saved = False
    if ('editor' in dest or 'viewer' in dest or 'email' in dest or 'printer' in dest) \
        and not file_saved:
        
        output_fd, output = utils.make_temp_file(suffix='.png')
        try:
            im.save(output)
        except IOError, e:
            log.error("Error saving temporary file: %s" % e)

            try:
                os.remove(output)
            except OSError:
                pass

            sys.exit(1)

        os.close(output_fd) 
        temp_saved = True      

    for d in dest:
        log.info("\nSending to destination '%s':" % d)

        if d == 'fax':
            log.error("fax: Not implemented yet.")

        elif d == 'pdf':
            try:
                from reportlab.pdfgen import canvas
            except ImportError:
                log.error("PDF output requires ReportLab.")
                continue

            tlx_max = device.getOptionObj('tl-x').constraint[1]
            bry_max = device.getOptionObj('br-y').constraint[1]

            pdf_output = utils.createSequencedFilename("hpscan", ".pdf")
            c = canvas.Canvas(pdf_output, (tlx_max/0.3528, bry_max/0.3528))

            try:
                c.drawInlineImage(im, (tlx/0.3528), ((bry_max/0.3528)-(bry/0.3528)), 
                    width=None,height=None)
            except NameError:
                log.error("A problem has occurred with PDF generation. This is a known bug in ReportLab. Please update your install of ReportLab to version 2.0 or greater.")
                continue

            c.showPage()
            log.info("Saving to file %s" % pdf_output)
            c.save()
            log.info("Viewing PDF file in %s" % pdf_viewer)
            os.system("%s %s &" % (pdf_viewer, pdf_output))

        elif d == 'printer':
            hp_print = utils.which("hp-print")
            if hp_print:
                cmd = 'hp-print %s &' % output
            else:
                cmd = "python ./print.py %s &" % output
                
            os.system(cmd)

        elif d == 'email':
            try:
                from email.mime.image import MIMEImage
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
            except ImportError:
                log.error("hp-scan email destination requires Python 2.2+.")
                continue

            msg = MIMEMultipart()
            msg['Subject'] = email_subject
            msg['From'] = email_from
            msg['To'] = ','.join(email_to)
            msg.preamble = 'Scanned using hp-scan'

            if email_note:
                txt = MIMEText(email_note)
                msg.attach(txt)

            if file_saved:
                txt = MIMEText("attached: %s: %dx%d %s PNG image." % 
                    (os.path.basename(output), pixels_per_line, lines, scan_mode))
            else:
                txt = MIMEText("attached: %dx%d %s PNG image." % (pixels_per_line, lines, scan_mode))

            msg.attach(txt) 

            fp = open(output, 'r')
            img = MIMEImage(fp.read())
            fp.close()

            if file_saved:
                img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(output))

            msg.attach(img)

            sendmail = utils.which("sendmail")

            if sendmail:
                sendmail = os.path.join(sendmail, 'sendmail')
                sendmail += ' -t -r %s' % email_from

                log.debug(sendmail)
                std_out, std_in, std_err = popen2.popen3(sendmail) 
                std_in.write(msg.as_string())
                std_in.close()

                while True:
                    update_spinner()
                    r, w, e = select.select([std_err], [], [], 1.0)

                    if r:
                        break

                cleanup_spinner()

                if r:
                    err = std_err.read()
                    if err:
                        log.error(repr(err))

            else:
                log.error("Mail send failed. 'sendmail' not found.")

        elif d == 'viewer':
            if viewer:
                log.info("Viewing file in %s" % viewer)
                os.system("%s %s &" % (viewer, output))
            else:
                log.error("Viewer not found.")

        elif d == 'editor':
            if editor:
                log.info("Editing file in %s" % editor)
                os.system("%s %s &" % (editor, output))
            else:
                log.error("Editor not found.")

    sys.exit(0)

