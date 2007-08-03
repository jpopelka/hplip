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

# Local
from base.g import *
from base import utils
from prnt import cups

# Qt
from qt import *
from scrollview import ScrollView

# Std Lib
import os.path, os



class ScrollSuppliesView(ScrollView):
    def __init__(self,parent = None,name = None,fl = 0):
        ScrollView.__init__(self,parent,name,fl)

        self.pix_battery = QPixmap(os.path.join(prop.image_dir, 'icon_battery.png'))

        yellow = "#ffff00"
        light_yellow = "#ffffcc"
        cyan = "#00ffff"
        light_cyan = "#ccffff"
        magenta = "#ff00ff"
        light_magenta = "#ffccff"
        black = "#000000"
        blue = "#0000ff"
        dark_grey = "#808080"
        light_grey = "#c0c0c0"
        
        self.TYPE_TO_PIX_MAP = {
                               AGENT_TYPE_UNSPECIFIED : [black],
                               AGENT_TYPE_BLACK: [black],
                               AGENT_TYPE_CMY: [cyan, magenta, yellow],
                               AGENT_TYPE_KCM: [light_cyan, light_magenta, light_yellow],
                               AGENT_TYPE_GGK: [dark_grey],
                               AGENT_TYPE_YELLOW: [yellow],
                               AGENT_TYPE_MAGENTA: [magenta],
                               AGENT_TYPE_CYAN : [cyan],
                               AGENT_TYPE_CYAN_LOW: [light_cyan],
                               AGENT_TYPE_YELLOW_LOW: [light_yellow],
                               AGENT_TYPE_MAGENTA_LOW: [light_magenta],
                               AGENT_TYPE_BLUE: [blue],
                               AGENT_TYPE_KCMY_CM: [yellow, cyan, magenta],
                               AGENT_TYPE_LC_LM: [light_cyan, light_magenta],
                               #AGENT_TYPE_Y_M: [yellow, magenta],
                               #AGENT_TYPE_C_K: [black, cyan],
                               AGENT_TYPE_LG_PK: [light_grey, dark_grey],
                               AGENT_TYPE_LG: [light_grey],
                               AGENT_TYPE_G: [dark_grey],
                               AGENT_TYPE_PG: [light_grey],
                               AGENT_TYPE_C_M: [cyan, magenta],
                               AGENT_TYPE_K_Y: [black, yellow],
                               }

    def fillControls(self):
        ScrollView.fillControls(self)
        
        if self.cur_device is not None and \
            self.cur_device.supported and \
            self.cur_device.status_type != STATUS_TYPE_NONE and \
            self.cur_device.device_state != DEVICE_STATE_NOT_FOUND:

            try:
                self.cur_device.sorted_supplies
            except AttributeError:                
                self.cur_device.sorted_supplies = []

            if not self.cur_device.sorted_supplies:
                a = 1
                while True:
                    try:
                        agent_type = int(self.cur_device.dq['agent%d-type' % a])
                        agent_kind = int(self.cur_device.dq['agent%d-kind' % a])
                    except KeyError:
                        break
                    else:
                        self.cur_device.sorted_supplies.append((a, agent_kind, agent_type))

                    a += 1

                self.cur_device.sorted_supplies.sort(lambda x, y: cmp(x[2], y[2]) or cmp(x[1], y[1]))

            for x in self.cur_device.sorted_supplies:
                a, agent_kind, agent_type = x
                agent_level = int(self.cur_device.dq['agent%d-level' % a])
                agent_sku = str(self.cur_device.dq['agent%d-sku' % a])
                agent_desc = self.cur_device.dq['agent%d-desc' % a]
                agent_health_desc = self.cur_device.dq['agent%d-health-desc' % a]

                self.addItem("agent %d" % a, "<b>"+agent_desc+"</b>",
                                          agent_sku, agent_health_desc, 
                                          agent_kind, agent_type, agent_level)
                                          

        else:
            if not self.cur_device.supported:
                
                self.addGroupHeading("not_supported", self.__tr("ERROR: Device not supported."))
            
            elif self.cur_device.status_type == STATUS_TYPE_NONE:
                
                self.addGroupHeading("not_found", self.__tr("ERROR: Supplies status is not supported on this device."))
                
            else:
                self.addGroupHeading("not_found", self.__tr("ERROR: Device not found. Please check connection and power-on device."))

                
    def getIcon(self, agent_kind, agent_type):
        if agent_kind in (AGENT_KIND_SUPPLY,
                          AGENT_KIND_HEAD,
                          AGENT_KIND_HEAD_AND_SUPPLY,
                          AGENT_KIND_TONER_CARTRIDGE):

            map = self.TYPE_TO_PIX_MAP[agent_type]
            
            if isinstance(map, list):
                map_len = len(map)
                pix = QPixmap(32, 32) #, -1, QPixmap.DefaultOptim)
                pix.fill(qApp.palette().color(QPalette.Active, QColorGroup.Background))
                p = QPainter()
                p.begin(pix)
                p.setBackgroundMode(Qt.OpaqueMode)
                
                if map_len == 1:
                    p.setPen(QColor(map[0]))
                    p.setBrush(QBrush(QColor(map[0]), Qt.SolidPattern))
                    p.drawPie(8, 8, 16, 16, 0, 5760)
                
                elif map_len == 2:
                    p.setPen(QColor(map[0]))
                    p.setBrush(QBrush(QColor(map[0]), Qt.SolidPattern))
                    p.drawPie(4, 8, 16, 16, 0, 5760)
                    
                    p.setPen(QColor(map[1]))
                    p.setBrush(QBrush(QColor(map[1]), Qt.SolidPattern))
                    p.drawPie(12, 8, 16, 16, 0, 5760)
                
                elif map_len == 3:
                    p.setPen(QColor(map[2]))
                    p.setBrush(QBrush(QColor(map[2]), Qt.SolidPattern))
                    p.drawPie(12, 12, 16, 16, 0, 5760)
                
                    p.setPen(QColor(map[1]))
                    p.setBrush(QBrush(QColor(map[1]), Qt.SolidPattern))
                    p.drawPie(4, 12, 16, 16, 0, 5760)
                    
                    p.setPen(QColor(map[0]))
                    p.setBrush(QBrush(QColor(map[0]), Qt.SolidPattern))
                    p.drawPie(8, 4, 16, 16, 0, 5760)
                
                p.end()
                return pix
            
            else:
                return map

        elif agent_kind == AGENT_KIND_INT_BATTERY:
                return self.pix_battery


    def createBarGraph(self, percent, agent_type, w=100, h=18):
        fw = w/100*percent
        px = QPixmap(w, h)
        px.fill(qApp.palette().color(QPalette.Active, QColorGroup.Background))
        
        pp = QPainter(px)
        pp.setPen(Qt.black)
        pp.setBackgroundColor(qApp.palette().color(QPalette.Active, QColorGroup.Base))

        map = self.TYPE_TO_PIX_MAP[agent_type]
        map_len = len(map)
        
        if map_len == 1 or map_len > 3:
            pp.fillRect(0, 0, fw, h, QBrush(QColor(map[0])))

        elif map_len == 2:
            h2 = h / 2
            pp.fillRect(0, 0, fw, h2, QBrush(QColor(map[0])))
            pp.fillRect(0, h2, fw, h, QBrush(QColor(map[1])))
            
        elif map_len == 3:
            h3 = h / 3
            h23 = 2 * h3
            pp.fillRect(0, 0, fw, h3, QBrush(QColor(map[0])))
            pp.fillRect(0, h3, fw, h23, QBrush(QColor(map[1])))
            pp.fillRect(0, h23, fw, h, QBrush(QColor(map[2])))

        # draw black frame
        pp.drawRect(0, 0, w, h)

        if percent > 75 and agent_type in \
          (AGENT_TYPE_BLACK, AGENT_TYPE_UNSPECIFIED, AGENT_TYPE_BLUE):
            pp.setPen(Qt.white)

        # 75% ticks
        w1 = 3 * w / 4
        h6 = h / 6
        pp.drawLine(w1, 0, w1, h6)
        pp.drawLine(w1, h, w1, h-h6)

        if percent > 50 and agent_type in \
          (AGENT_TYPE_BLACK, AGENT_TYPE_UNSPECIFIED, AGENT_TYPE_BLUE):
            pp.setPen(Qt.white)

        # 50% ticks
        w2 = w / 2
        h4 = h / 4
        pp.drawLine(w2, 0, w2, h4)
        pp.drawLine(w2, h, w2, h-h4)

        if percent > 25 and agent_type in \
          (AGENT_TYPE_BLACK, AGENT_TYPE_UNSPECIFIED, AGENT_TYPE_BLUE):
            pp.setPen(Qt.white)

        # 25% ticks
        w4 = w / 4
        pp.drawLine(w4, 0, w4, h6)
        pp.drawLine(w4, h, w4, h-h6)

        return px   


    def addItem(self, name, title_text, part_num_text, status_text, 
                agent_kind, agent_type, percent):

        self.addGroupHeading(title_text, title_text)
        
        widget = self.getWidget()
        layout1 = QGridLayout(widget,1,1,5,10,"layout1")

        spacer1 = QSpacerItem(20,20,QSizePolicy.Preferred,QSizePolicy.Minimum)
        layout1.addItem(spacer1,0,3)

        barGraph = QLabel(widget,"barGraph")
        barGraph.setSizePolicy(QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred,0,0,
            barGraph.sizePolicy().hasHeightForWidth()))

        barGraph.setMinimumSize(QSize(100,18))
        barGraph.setMaximumSize(QSize(100,18))
        barGraph.setScaledContents(1)
        layout1.addMultiCellWidget(barGraph,0,0,4,5)

        #titleText = QLabel(widget,"titleText")
        #layout1.addMultiCellWidget(titleText,0,0,0,2)

        #line1 = QFrame(widget,"line1")
        #line1.setFrameShape(QFrame.HLine)
        #layout1.addMultiCellWidget(line1,2,2,0,5)

        spacer2 = QSpacerItem(20,20,QSizePolicy.Preferred,QSizePolicy.Minimum)
        layout1.addMultiCell(spacer2,1,1,2,4)

        statusText = QLabel(widget,"statusText")
        statusText.setFrameShape(self.frame_shape)
        layout1.addWidget(statusText,1,5)

        icon = QLabel(widget,"icon")
        icon.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed,0,0,
            icon.sizePolicy().hasHeightForWidth()))

        icon.setMinimumSize(QSize(32,32))
        icon.setMaximumSize(QSize(32,32))
        icon.setScaledContents(1)
        layout1.addWidget(icon,0,0)

        partNumText = QLabel(widget,"partNumText")
        partNumText.setFrameShape(self.frame_shape)
        partNumText.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Preferred,0,0,
            partNumText.sizePolicy().hasHeightForWidth()))

        partNumText.setAlignment(QLabel.WordBreak | QLabel.AlignVCenter)
        layout1.addWidget(partNumText,0,1)                

        #titleText.setText(title_text)
        
        if part_num_text:
            partNumText.setText(self.__tr("Part No. %1").arg(part_num_text))
        
        statusText.setText(status_text)

        # Bar graph level
        if agent_kind in (AGENT_KIND_SUPPLY,
                          #AGENT_KIND_HEAD,
                          AGENT_KIND_HEAD_AND_SUPPLY,
                          AGENT_KIND_TONER_CARTRIDGE,
                          AGENT_KIND_MAINT_KIT,
                          AGENT_KIND_ADF_KIT,
                          AGENT_KIND_INT_BATTERY,
                          AGENT_KIND_DRUM_KIT,
                          ):

            barGraph.setPixmap(self.createBarGraph(percent, agent_type))

        # Color icon
        if agent_kind in (AGENT_KIND_SUPPLY,
                          AGENT_KIND_HEAD,
                          AGENT_KIND_HEAD_AND_SUPPLY,
                          AGENT_KIND_TONER_CARTRIDGE,
                          #AGENT_KIND_MAINT_KIT,
                          #AGENT_KIND_ADF_KIT,
                          AGENT_KIND_INT_BATTERY,
                          #AGENT_KIND_DRUM_KIT,
                          ):

            pix = self.getIcon(agent_kind, agent_type)

            if pix is not None:
                icon.setPixmap(pix)

        self.addWidget(widget, name)


    def __tr(self,s,c = None):
        return qApp.translate("ScrollSuppliesView",s,c)

