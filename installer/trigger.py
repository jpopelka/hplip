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

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('.'))
from base import utils

if not os.geteuid() == 0:
    print "You must be root to run this utility."
    sys.exit(1)
    
sys.exit(0)

cycle = 0
for f1 in utils.walkFiles('/sys', recurse=True, abs_paths=True, return_folders=False, pattern='uevent'):
    if 'usb' in f1:
        try:
            f0 = file(f1, 'w')
            f0.write("add")
            f0.close()
        except IOError:
            pass
    
    cycle += 1
    if cycle > 5000:
        break
        

