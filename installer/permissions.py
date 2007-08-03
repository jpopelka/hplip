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

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('.'))
from base import utils

mode_pat = re.compile("""MODE\s*=\s*\"(\d\d\d\d)\"""",  re.IGNORECASE)
subsystem_pat = re.compile("""SUBSYSTEM\s*==\s*\"usb_device\"""", re.IGNORECASE)

udev_dir = '/etc/udev/rules.d'

if not os.geteuid() == 0:
    print "You must be root to run this utility."
    sys.exit(1)

found = False
for f1 in utils.walkFiles(udev_dir, recurse=True, abs_paths=True, return_folders=False, pattern='*.rules'):
    state = 1
    f3 = file(f1, 'r').readlines()
    for f2 in f3:
        if state == 1: # Looking for SUBSYSTEM=="usb_device"
            d = subsystem_pat.search(f2)
            if d is not None and not f2.strip().startswith("#"):
                print "Found 'usb_device' on line: %s" % f2.strip()
                s = mode_pat.search(f2)
                
                if s is not None:
                    found = True # Found MODE="0xxx" on current line
                    break
                
                elif f2.strip().endswith("\\"): # Line continuation, keep looking...
                    state = 2 # looking for MODE="0xxx" on subsequent lines
                
                else:
                    state = 1 # Not found on this line, and no continuation, keep looking...
                      
        elif state == 2: # looking for MODE="0xxx" on subsequent lines
            print "Found usb_device, looking for MODE..."
            s = mode_pat.search(f2)
            if s is not None and not f2.strip().startswith("#"):
                print "Found 'MODE' on line: %s" % f2.strip()
                found = True # Found MODE="0xxx" on a subsequent line to "usb_device"
                break
            
            elif f2.strip().endswith("\\"):
                print "Skipping line: %s" % f2.strip()
                state = 2 # Keep looking
            
            else:
                state = 1 # Not found, look for another usb_device line
        
    if found:
        break
    
if found:
    print "Found usb_device MODE in file: %s" % f1
    
    mode = int(s.group(1), 8)
    print "Existing mode=0%o" % mode
    
    if mode & 0660 != 0660:
        mode |= 0660
        print "New mode=0%o" % mode
        
        # Make a backup of the file
        import shutil
        shutil.copyfile(f1, f1 + '.hplip.bak')
        print "File backed-up to %s" % (f1 + '.hplip.bak')
        
        f4 = file(f1, 'w')
        state = 1
        for f5 in f3:
            if state == 1: # Looking for SUBSYSTEM=="usb_device"
                d = subsystem_pat.search(f5)
                if d is not None and not f5.strip().startswith("#"):
                    s = mode_pat.search(f5)
                    
                    if s is not None:
                        f6 = mode_pat.sub('MODE="0%o"' % mode, f5, 0)
                        print "Replacing line %s with %s" % (f5, f6)
                        f4.write(f6)
                    
                    elif f5.strip().endswith("\\"): # Line continuation, keep looking...
                        f4.write(f5)
                        state = 2 # looking for MODE="0xxx" on subsequent lines
                    
                    else:
                        f4.write(f5)
                        state = 1 # Not found on this line, and no continuation, keep looking...
                else:
                    f4.write(f5)
                          
            elif state == 2: # looking for MODE="0xxx" on subsequent lines
                s = mode_pat.search(f5)
                if s is not None and not f5.strip().startswith("#"):
                    f6 = mode_pat.sub('MODE="0%o"' % mode, f5, 0)
                    print "Replacing line %s with %s" % (f5, f6)
                    f4.write(f6)
                
                elif f5.strip().endswith("\\"):
                    f4.write(f5)
                    state = 2 # Keep looking
                
                else:
                    f4.write(f5)
                    state = 1 # Not found, look for another usb_device line
            
        f4.close()
            
    else:
        print "No change to mode needed."
else:
    print "Line not found."
    
sys.exit(0)
    

        

