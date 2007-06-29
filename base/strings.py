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

# string_table := { 'string_id' : ( 'short', 'long' ), ... }

# string_id's for error codes are the string form of the error code
# Strings that need localization use lambda : _( 'string' ) form.
# Strings that refer to other strings, use '%reference%' form.
# Blank strings use '' form.

string_table = {

'unknown'   :       (lambda : _('Unknown'),
                      lambda : _('Unknown')),

'try_again' :       ('',
                      lambda : _('Please correct the problem and try again.')),

'press_continue' :  ('',
                      lambda : _('Please correct the problem and press continue on the printer.')),

'500' :             (lambda : _('The printer has started a print job.'),
                     ''),

'501' :             (lambda : _('Print job has completed.'),
                     ''),

'600' :             (lambda : _('Started rendering a fax job.'),
                     ''),

'601' :             (lambda : _('Rendering job completed.'),
                     ''),

'1000' :            (lambda : _('The printer is idle.'),
                      ''),

'1001' :            (lambda : _('The printer is busy.'),
                     ''),

'1002' :            (lambda : _('The print job is continuing.'),
                      ''),

'1003' :            (lambda : _('Turning off.'),
                      ''),

'1004' :            (lambda : _('Report printing.'),
                      ''),

'1005' :            (lambda : _('Canceling.'),
                      ''),

'1006' :            ('%5002%',
                      '%try_again%'),

'1007' :            (lambda : _('Waiting for ink to dry.'),
                      ''),

'1008' :            (lambda : _('Pen change.'),
                     ''),

'1009' :            (lambda : _('The printer is out of paper.'),
                      lambda : _('Please load more paper and follow the instructions on the front panel (if any) to continue printing.')),

'1010' :            (lambda : _('Banner eject needed.'),
                      ''),

'1011' :            (lambda : _('Banner mismatch.'),
                      '%try_again%'),

'1012' :            (lambda : _('Photo mismatch.'),
                      '%try_again%'),

'1013' :            (lambda : _('Duplex mismatch.'),
                      '%try_again'),

'1014' :            (lambda : _('Paper or cartridge carriage jammed.'),
                      lambda : _('Please clear the jam and press continue on the printer.')),

'1015' :            ('%1014%',
                      '%1014%'),

'1016' :            ('%1014%',
                      '%1014%'),

'1017' :            (lambda : _('There is a problem with a cartridge.'),
                      '%press_continue%'),

'1018' :            ('%unknown_error%',
                      '%try_again%'),

'1019' :            (lambda : _('Powering down.'),
                      ''),

'1020' :            (lambda : _('Front panel test.'),
                      ''),

'1021' :            (lambda : _('Clean out tray missing.'),
                      '%try_again%'),

'1022' :            (lambda : _('Output bin full.'),
                      '%try_again%'),

'1023' :            (lambda : _('Media size mismatch.'),
                      '%try_again%'),

'1024' :            (lambda : _('Duplexer is jammed.'),
                      '%1014%'),

'1025' :            ('%1014%',
                      '%1014%'),

'1026' :            (lambda : _('An ink cartridge is out of ink.'),
                      '%try_again%'),

'1027' :            (lambda : _('Internal device error.'),
                      '%try_again%'),

'1028' :            ('%1014%',
                      '%1014%'),

'1029' :            (lambda : _('Second tray missing.'),
                      '%try_again%'),

'1030' :            (lambda : _('Duplexer missing.'),
                      '%try_again%'),

'1031' :            (lambda : _('Rear tray missing.'),
                      '%try_again%'),

'1032' :            (lambda : _('Cartridge not latched.'),
                      '%try_again%'),

'1033' :            (lambda : _('Battery very low.'),
                      '%try_again%'),

'1034' :            ('%1017%',
                      '%try_again%'),

'1035' :            (lambda : _('Output tray closed.'),
                      '%try_again%'),

'1036' :            (lambda : _('Manual feed blocked.'),
                      '%1014%'),

'1037' :            (lambda : _('Rear feed blocked.'),
                      '%1014%'),

'1038' :            (lambda : _('Second tray out of paper.'),
                      '%1009%'),

'1039' :            (lambda : _('Input tray locked.'),
                      '%try_again%'),

'1040' :            (lambda : _('Non-HP ink.'),
                      '%try_again%'),

'1041' :            (lambda : _('Pen calibration needs resume.'),
                      '%press_continue%'),

'1042' :            (lambda : _('Media type mismatch.'),
                      '%try_again%'),

'1043' :            (lambda : _('Custom media mismatch.'),
                      '%try_again%'),

'1044' :            (lambda : _('Pen cleaning in progress.'),
                      ''),

'1045' :            (lambda : _('Pen checking in progress.'),
                      ''),

'1501' :            (lambda : _('Black cartridge is low on ink'),
                                ''),

'1502' :            (lambda : _('Tri-color cartridge is low on ink'),
                                ''),

'1503' :            (lambda : _('Photo cartridge is low on ink'),
                                ''),

'1504' :            (lambda : _('Cyan cartridge is low on ink'),
                                ''),

'1505' :            (lambda : _('Magenta cartridge is low on ink'),
                                ''),

'1506' :            (lambda : _('Yellow cartridge is low on ink'),
                                ''),

'1507' :            (lambda : _('Photo cyan cartridge is low on ink'),
                                ''),

'1508' :            (lambda : _('Photo magenta cartridge is low on ink'),
                                ''),

'1509' :            (lambda : _('Photo yellow cartridge is low on ink'),
                                ''),

'1510' :            (lambda : _('Photo gray cartridge is low on ink'),
                                ''),

'1511' :            (lambda : _('Photo blue cartridge is low on ink'),
                                ''),

'1601' :            (lambda : _('Black cartridge is low on toner'),
                                ''),

'1604' :            (lambda : _('Cyan cartridge is low on toner'),
                                ''),

'1605' :            (lambda : _('Magenta cartridge is low on toner'),
                                ''),

'1606' :            (lambda : _('Yellow cartridge is low on toner'),
                                ''),

'1800' :            (lambda : _('Warming up.'),
                      ''),

'1801' :            (lambda : _('Low paper.'),
                      ''),

'1802' :            (lambda : _('Door open.'),
                      '%try_again%'),

'1803' :            (lambda : _('Offline.'),
                      ''),

'1804' :            (lambda : _('Low toner.'),
                      ''),

'1805' :            (lambda : _('No toner.'),
                      '%try_again%'),

'1806' :            (lambda : _('Service request.'),
                      '%try_again%'),

'1807' :            (lambda : _('Fuser error.'),
                      '%try_again%'),

'1900' :            (lambda : _('Unsupported printer model.'),
                      ''),

'2000' :            (lambda : _('Scan job started.'),
                      ''),

'2001' :            (lambda : _('Scan job completed.'),
                      ''),

'2002' :            (lambda : _('Scan job failed.'),
                      '%try_again%'),

'3000' :            (lambda : _('Fax job started.'),
                      ''),

'3001' :            (lambda : _('Fax job complete.'),
                      ''),

'3002' :            (lambda : _('Fax job failed.'),
                      '%try_again%'),

'3003' :            (lambda : _('Fax job canceled.'),
                      ''),

'3004' :            (lambda : _('Fax send job continuing.'),
                      ''),

'3005' :            (lambda : _('Fax receive job continuing.'),
                      ''),

'4000' :            (lambda : _('Copy job started.'),
                      ''),

'4001' :            (lambda : _('Copy job complete.'),
                      ''),

'4002' :            (lambda : _('Copy job failed.'),
                      '%try_again%'),

'4003' :            (lambda : _('Copy job canceled.'),
                      ''),

'5002' :            (lambda : _('Device is powered down or unplugged.'),
                      '%5012%'),

'5012' :            (lambda : _('Device communication error.'),
                      '%try_again%'),

'5021' :            (lambda : _('Device is busy.'),
                      ''),

'5022' :            (lambda : _('No data.'),
                      ''),

'5030' :            ('%unknown_error%',
                      '%try_again%'),

'5031' :            ('%5021%',
                      ''),

'5033' :            (lambda : _('Unsupported I/O bus.'),
                      '%try_again%'),

'5034' :            (lambda : _('Device does not support requested operation.'),
                      '%try_again%'),

'5052' :            (lambda : _('To send a fax you must run hp-sendfax first.'),
                      'Run hp-sendfax now to continue. Fax will resume within 10 seconds.'),

'6000' :            (lambda : _('Photocard unload started.'),
                      ''),

'6001' :            (lambda : _('Photocard unload ended.'),
                      ''),

'6002' :            (lambda : _('Photocard unload failed.'),
                      lambda : _('Make sure photocard is inserted properly and try again.')),

'6003' :            (lambda : _('Unable to mount photocard on device.'),
                      '%6002%'),

'6004' :            (lambda : _('Photocard unloaded successfully.'),
                      ''),

'unknown_error' :   (lambda : _('Unknown error.'),
                      ''),

'print' :           (lambda : _('Print'),
                      ''),

'scan' :            (lambda : _('Scan'),
                      ''),

'send_fax' :        (lambda : _('Send fax'),
                      ''),

'make_copies' :     (lambda : _('Make copies'),
                      ''),

'access_photo_cards' :    (lambda : _('Access photo cards'),
                           ''),

'agent_invalid_invalid' : (lambda : _('Invalid/missing'),
                            ''),

'agent_invalid_supply' :  (lambda : _('Invalid/missing ink cartridge'),
                            ''),

'agent_invalid_cartridge':(lambda : _('Invalid/missing cartridge'),
                            ''),

'agent_invalid_head' :    (lambda : _('Invalid/missing print head'),
                            ''),

'agent_unknown_unknown' : ('%unknown%',
                            ''),

'agent_unspecified_battery' : ('Battery',
                            ''),

'agent_black_head' :      (lambda : _('Black print head'),
                            ''),

'agent_black_supply' :    (lambda : _('Black ink cartridge'),
                            ''),

'agent_black_cartridge' : (lambda : _('Black cartridge'),
                            ''),

'agent_cmy_head' :        (lambda : _('Tri-color print head'),
                            ''),

'agent_cmy_supply' :      (lambda : _('Tri-color ink cartridge'),
                            ''),

'agent_cmy_cartridge' :   (lambda : _('Tri-color cartridge'),
                            ''),

'agent_kcm_head' :        (lambda : _('Photo print head'),
                            ''),

'agent_kcm_supply' :      (lambda : _('Photo ink cartridge'),
                            ''),

'agent_kcm_cartridge' :   (lambda : _('Photo cartridge'),
                            ''),

'agent_cyan_head' :       (lambda : _('Cyan print head'),
                            ''),

'agent_cyan_supply' :     (lambda : _('Cyan ink cartridge'),
                            ''),

'agent_cyan_cartridge' :  (lambda : _('Cyan cartridge'),
                            ''),

'agent_magenta_head' :    (lambda : _('Magenta print head'),
                            ''),

'agent_magenta_supply' :  (lambda : _('Magenta ink cartridge'),
                            ''),

'agent_magenta_cartridge':(lambda : _('Magenta cartridge'),
                            ''),

'agent_yellow_head' :     (lambda : _('Yellow print head'),
                            ''),

'agent_yellow_supply' :   (lambda : _('Yellow ink cartridge'),
                            ''),

'agent_yellow_cartridge': (lambda : _('Yellow cartridge'),
                            ''),

'agent_photo_cyan_head' :       (lambda : _('Photo cyan print head'),
                                   ''),

'agent_photo_cyan_supply' :     (lambda : _('Photo cyan ink cartridge'),
                                  ''),

'agent_photo_cyan_cartridge' :  (lambda : _('Photo cyan cartridge'),
                                  ''),

'agent_photo_magenta_head' :    (lambda : _('Photo magenta print head'),
                                  ''),

'agent_photo_magenta_supply' :  (lambda : _('Photo magenta ink cartridge'),
                                  ''),

'agent_photo_magenta_cartridge':(lambda : _('Photo magenta cartridge'),
                                  ''),

'agent_photo_yellow_head' :     (lambda : _('Photo yellow print head'),
                                  ''),

'agent_photo_yellow_supply' :   (lambda : _('Photo yellow ink cartridge'),
                                  ''),

'agent_photo_yellow_cartridge': (lambda : _('Photo yellow cartridge'),
                                  ''),

'agent_photo_gray_head' :       (lambda : _('Photo gray print head'),
                                   ''),

'agent_photo_gray_supply' :     (lambda : _('Photo gray ink cartridge'),
                                  ''),

'agent_photo_gray_cartridge' :  (lambda : _('Photo gray cartridge'),
                                  ''),

'agent_photo_blue_head' :       (lambda : _('Photo blue print head'),
                                   ''),

'agent_photo_blue_supply' :     (lambda : _('Photo blue ink cartridge'),
                                  ''),

'agent_photo_blue_cartridge' :  (lambda : _('Photo blue cartridge'),
                                  ''),

'agent_kcmy_cm_head' :          (lambda : _('Print head'),
                                  ''),

'agent_photo_cyan_and_photo_magenta_head' : (lambda : _('Photo magenta and photo cyan print head'),
                                            ''),

'agent_yellow_and_magenta_head' :           (lambda : _('Magenta and yellow print head'), 
                                            '' ),

'agent_cyan_and_black_head' :               (lambda : _('Black and cyan print head'),
                                            '' ),

'agent_light_gray_and_photo_black_head' :    (lambda : _('Light gray and photo black print head'),
                                            '' ),

'agent_light_gray_supply' :                 (lambda : _('Light gray ink cartridge'), # LG
                                            '' ),

'agent_medium_gray_supply' :                (lambda : _('Medium gray ink cartridge'), 
                                            '' ),

'agent_photo_gray_supply' :                 (lambda : _('Photo black ink cartridge'), # PK
                                            '' ),
                                            
'agent_cyan_and_magenta_head' :             (lambda : _('Cyan and magenta print head'),
                                             ''),

'agent_black_and_yellow_head' :             (lambda : _('Black and yellow print head'),
                                             ''),

'agent_black_toner' :           (lambda : _('Black toner cartridge'),
                                ''),

'agent_cyan_toner' :            (lambda : _('Cyan toner cartridge'),
                                  ''),

'agent_magenta_toner' :         (lambda : _('Magenta toner cartridge'),
                                  ''),

'agent_yellow_toner' :          (lambda : _('Yellow toner cartridge'),
                                  ''),

'agent_unspecified_maint_kit' : (lambda : _('Maintenance kit (fuser)'),
                                  ''),

'agent_unspecified_adf_kit'   : (lambda : _('Document feeder (ADF) kit'),
                                  ''),

'agent_unspecified_drum_kit'   : (lambda : _('Drum maintenance kit'),
                                  ''),

'agent_unspecified_transfer_kit'   : (lambda : _('Image transfer kit'),
                                  ''),

'agent_health_unknown'     : ('Unknown',
                               ''),

'agent_health_ok'          : (lambda : _('Good/OK'),
                               ''),

'agent_health_fair_moderate' : (lambda : _('Fair/Moderate'),
                               ''),

'agent_health_misinstalled': (lambda : _('Not installed'),
                               ''),

'agent_health_incorrect'   : (lambda : _('Incorrect'),
                               ''),

'agent_health_failed'      : (lambda : _('Failed'),
                               ''),

'agent_health_overtemp'      : (lambda : _('Overheated'),
                               ''),

'agent_health_discharging'      : (lambda : _('Discharging'),
                               ''),

'agent_health_charging'      : (lambda : _('Charging'),
                               ''),

'agent_level_unknown'      : ('%unknown%',
                               ''),

'agent_level_low'          : (lambda : _('Low'),
                               ''),

'agent_level_out'          : (lambda : _('Very low'),
                               ''),

'email_test_subject'      : (lambda : _('HPLIP: Email alert test message'),
                               ''),

'email_test_message'      : (lambda : _('This email is to test the functionality of HPLIP email alerts.'),
                               ''),

'email_alert_subject'      : (lambda : _('HPLIP: Error/alert on device: '),
                             ''),

}


