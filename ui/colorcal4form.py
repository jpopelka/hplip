# -*- coding: utf-8 -*-
#
# (c) Copyright 2001-2007 Hewlett-Packard Development Company, L.P.
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

from base.g import *
import os.path

from qt import *
from colorcal4form_base import ColorCal4Form_base


class ColorCal4Form(ColorCal4Form_base):

    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        ColorCal4Form_base.__init__(self,parent,name,modal,fl)
        self.gray_plot_png.setPixmap(QPixmap(os.path.join(prop.image_dir, 'type4_gray_patch.png')))
        self.color_plot_png.setPixmap(QPixmap(os.path.join(prop.image_dir, 'type4_color_patch.png')))
        self.values = [0, 0, 0, 0]

    def GrayLetterComboBox_highlighted(self,a0):
        self.values[0] = ord(str(a0)) - ord('A')

    def GrayNumberComboBox_highlighted(self,a0):
        self.values[1] = int(str(a0))-1

    def ColorLetterComboBox_highlighted(self,a0):
        self.values[2] = ord(str(a0)) - ord('P')

    def ColorNumberComboBox_highlighted(self,a0):
        self.values[3] = int(str(a0))-1

    def UseDefaultsButton_clicked(self):
        self.values = [-1, -1, -1, -1]
        self.accept()
