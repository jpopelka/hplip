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

from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.flowables import Preformatted
from reportlab.platypus.doctemplate import *
#from reportlab.rl_config import TTFSearchPath
from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.platypus.tables import Table, TableStyle
from reportlab.lib.pagesizes import letter, legal, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
#from reportlab.pdfbase import pdfmetrics
#from reportlab.pdfbase.ttfonts import TTFont
from time import localtime, strftime
import warnings
warnings.simplefilter('ignore', DeprecationWarning)

if __name__ ==  "__main__":
    import sys
    sys.path.append("..")
    
from base.g import *
from base import utils

PAGE_SIZE_LETTER = 'letter'
PAGE_SIZE_LEGAL = 'legal'
PAGE_SIZE_A4 = 'a4'

def escape(s):
    return s.replace("&", "&amp;").replace(">", "&gt;").replace("<", "&lt;")
    

def createStandardCoverPage(page_size=PAGE_SIZE_LETTER,
                            total_pages=1, 
                            recipient_name='', 
                            recipient_phone='', 
                            recipient_fax='', 
                            sender_name='', 
                            sender_phone='',
                            sender_fax='', 
                            sender_email='', 
                            regarding='', 
                            message='',
                            preserve_formatting=False,
                            output=None):

    s = getSampleStyleSheet()

    story = []

    #print prop.locale
    #TTFSearchPath.append('/usr/share/fonts/truetype/arphic')
    #pdfmetrics.registerFont(TTFont('UMing', 'uming.ttf'))

    ps = ParagraphStyle(name="title", 
                        parent=None, 
                        fontName='helvetica-bold',
                        #fontName='STSong-Light',
                        #fontName = 'UMing',
                        fontSize=36,
                        )

    story.append(Paragraph("Fax", ps))

    story.append(Spacer(1, inch))

    ps = ParagraphStyle(name='normal',
                        fontName='Times-Roman',
                        #fontName='STSong-Light',
                        #fontName='UMing',
                        fontSize=12) 

    recipient_name_label = Paragraph("To:", ps)
    recipient_name_text = Paragraph(escape(recipient_name[:64]), ps)

    recipient_fax_label = Paragraph("Fax:", ps)
    recipient_fax_text = Paragraph(escape(recipient_fax[:64]), ps)

    recipient_phone_label = Paragraph("Phone:", ps)
    recipient_phone_text = Paragraph(escape(recipient_phone[:64]), ps)


    sender_name_label = Paragraph("From:", ps)
    sender_name_text = Paragraph(escape(sender_name[:64]), ps)

    sender_phone_label = Paragraph("Phone:", ps)
    sender_phone_text = Paragraph(escape(sender_phone[:64]), ps)

    sender_email_label = Paragraph("Email:", ps)
    sender_email_text = Paragraph(escape(sender_email[:64]), ps)


    regarding_label = Paragraph("Regarding:", ps)
    regarding_text = Paragraph(escape(regarding[:128]), ps)

    date_time_label = Paragraph("Date:", ps)
    date_time_text = Paragraph(strftime("%a, %d %b %Y %H:%M:%S (%Z)", localtime()), ps)

    total_pages_label = Paragraph("Total Pages:", ps)
    total_pages_text = Paragraph("%d" % total_pages, ps)

    data = [[recipient_name_label, recipient_name_text, sender_name_label, sender_name_text],
            [recipient_fax_label, recipient_fax_text, sender_phone_label, sender_phone_text],
            [date_time_label, date_time_text, sender_email_label, sender_email_text],
            [regarding_label, regarding_text, total_pages_label, total_pages_text]]

    LIST_STYLE = TableStyle([('LINEABOVE', (0,0), (-1,0), 2, colors.black),
                             ('LINEABOVE', (0,1), (-1,-1), 0.25, colors.black),
                             ('LINEBELOW', (0,-1), (-1,-1), 2, colors.black),
                             ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                             ('VALIGN', (0, 0), (-1, -1), 'TOP'), 
                            ])

    t = Table(data, style=LIST_STYLE)

    story.append(t)

    if message:
        MSG_STYLE = TableStyle([('LINEABOVE', (0,0), (-1,0), 2, colors.black),
                                 ('LINEABOVE', (0,1), (-1,-1), 0.25, colors.black),
                                 ('LINEBELOW', (0,-1), (-1,-1), 2, colors.black),
                                 ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                                 ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                 ('SPAN', (-2, 1), (-1, -1)), 
                                ])

        story.append(Spacer(1, 0.5*inch))

        if preserve_formatting:
            message = '\n'.join(message[:2048].splitlines()[:32])
            
            data = [[Paragraph("Comments/Notes:", ps), ''],
                    [Preformatted(escape(message), ps), ''],]
        else:
            data = [[Paragraph("Comments/Notes:", ps), ''],
                    [Paragraph(escape(message[:2048]), ps), ''],]

        t = Table(data, style=MSG_STYLE)

        story.append(t)

    if page_size == PAGE_SIZE_LETTER:
        pgsz = letter
    elif page_size == PAGE_SIZE_LEGAL:
        pgsz = legal
    else:
        pgsz = A4

    if output is None:
        f_fd, f = utils.make_temp_file()
    else:
        f = output

    doc = SimpleDocTemplate(f, pagesize=pgsz)
    doc.build(story)

    return f



#            { "name" : (function, "thumbnail.png"), ... }    
COVERPAGES = { "basic": (createStandardCoverPage, 'standard_coverpage.png'),
             }

             
if __name__ ==  "__main__":
    createStandardCoverPage(page_size=PAGE_SIZE_LETTER,
                                total_pages=1, 
                                recipient_name='法国', 
                                recipient_phone='1234', 
                                recipient_fax='4321', 
                                sender_name='Don', 
                                sender_phone='1234',
                                sender_fax='5678', 
                                sender_email='test@hplip.sf.net', 
                                regarding='Test', 
                                message='Message',
                                preserve_formatting=False,
                                output="output.pdf")
                                

