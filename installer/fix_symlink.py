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


if not os.geteuid() == 0:
    print "You must be root to run this utility."
    sys.exit(1)

link_path = "/usr/share/foomatic/db/source/PPD"
print "Testing link:", link_path
try:
    real_path = os.path.realpath(link_path)
    print "Link target:", real_path
except OSError:
    sys.exit(1)
    
if not os.path.exists(real_path):
    try:
        print "Removing link:", link_path
        os.remove(link_path)
    except OSError:
        print "Link removal failed."
        sys.exit(1)
else:
    print "Target path exists. No action needed."
        
sys.exit(0)
    

        

