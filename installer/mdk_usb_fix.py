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

import os
import os.path
import sys
import re

if not os.geteuid() == 0:
    print "You must be root to run this utility."
    sys.exit(1)

# Phase 1
# Edit "/etc/cups/cupsd.conf" and change the line from "Group sys" to
# "Group lp". This allows the "hp" backend to run as "lp" group during
# CUPS print jobs.

cups_conf = "/etc/cups/cupsd.conf"
cups_pat = re.compile("""^Group\s*(.*)""", re.IGNORECASE)

f1 = file(cups_conf, 'r')
lines = f1.readlines()
f1.close()

change_needed = False
for l in lines:
    s = cups_pat.search(l)
    if not l.startswith("#") and s is not None:
        change_needed = True 

if change_needed:
    import shutil
    shutil.copyfile(cups_conf, cups_conf + '.hplip.bak')
    print "/etc/cups/cupsd.conf backed up to /etc/cups/cupsd.conf.hplip.bak"
    f3 = file(cups_conf, 'w')
    for l in lines:
        s = cups_pat.search(l)
        if not l.startswith("#") and s is not None:
            print "Replacing line in /etc/cups/cupsd.conf."
            f3.write("# Line changed by HPLIP. Old line:\n")
            print "Old line: ", l
            f3.write("# %s" % l)
            f3.write("# New line:\n")
            print "New line: Group lp"
            f3.write("Group lp\n")
            print "CUPS will need to be restarted for changes to take effect."
        else:
            f3.write(l)
            
    f3.close()
else:
    print "No change needed to /etc/cups/cupsd/conf"


# Phase 2
# Change the PAM policy that re-assigns all libusb devices to the
# "console" user. 

if os.path.exists("/etc/security/condole.perms.d"):
    try:
        file("/etc/security/console.perms.d/55-hplip.perms", 'w').write("""<usb>=/dev/usb/dabusb* /dev/usb/mdc800* /dev/usb/rio500 /dev/ttyUSB*
        
    <console>  0660 <usb>        0660 root.usb
    """)
    except IOError, e:
        print "Could not create 55-hplip.perms file: %s" % e
    else:
        print "File 55-hplip.perms written. USB devices will need to be replugged or triggered for the changes to take effect."
else:
    print "Console perms directory does not exist. 55-hplip.perms file not written."
    
sys.exit(0)

