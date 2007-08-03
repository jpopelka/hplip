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

# string_table := { 'string_id' : 'short', 'long' ), ... }

# string_id's for error codes are the string form of the error code
# Strings that need localization use  (self.__tr'string' ) form.
# Strings that refer to other strings, use '%reference%' form.
# Blank strings use '' form.

class StringTable:
    def __init__(self):

        self.string_table = {
        
            'unknown'   :       (self.__tr('Unknown'),
                                 self.__tr('Unknown')),
            
            'try_again' :       ('',
                                 self.__tr('Please correct the problem and try again.')),
            
            'press_continue' :  ('',
                                 self.__tr('Please correct the problem and press continue on the printer.')),
            
            '500' :             (self.__tr('The printer has started a print job.'),
                                 ''),
            
            '501' :             (self.__tr('Print job has completed.'),
                                 ''),
            
            '600' :             (self.__tr('Started rendering a fax job.'),
                                 ''),
            
            '601' :             (self.__tr('Rendering job completed.'),
                                 ''),
            
            '1000' :            (self.__tr('The printer is idle.'),
                                  ''),
            
            '1001' :            (self.__tr('The printer is busy.'),
                                 ''),
            
            '1002' :            (self.__tr('The print job is continuing.'),
                                  ''),
            
            '1003' :            (self.__tr('Turning off.'),
                                  ''),
            
            '1004' :            (self.__tr('Report printing.'),
                                  ''),
            
            '1005' :            (self.__tr('Canceling.'),
                                  ''),
            
            '1006' :            ('%5002%',
                                '%try_again%'),
            
            '1007' :            (self.__tr('Waiting for ink to dry.'),
                                 ''),
            
            '1008' :            (self.__tr('Pen change.'),
                                 ''),
            
            '1009' :            (self.__tr('The printer is out of paper.'),
                                 self.__tr('Please load more paper and follow the instructions on the front panel (if any) to continue printing.')),
            
            '1010' :            (self.__tr('Banner eject needed.'),
                                 ''),
            
            '1011' :            (self.__tr('Banner mismatch.'),
                                 '%try_again%'),
            
            '1012' :            (self.__tr('Photo mismatch.'),
                                 '%try_again%'),
            
            '1013' :            (self.__tr('Duplex mismatch.'),
                                 '%try_again'),
            
            '1014' :            (self.__tr('Paper or cartridge carriage jammed.'),
                                 self.__tr('Please clear the jam and press continue on the printer.')),
            
            '1015' :            ('%1014%',
                                 '%1014%'),
            
            '1016' :            ('%1014%',
                                 '%1014%'),
            
            '1017' :            (self.__tr('There is a problem with a cartridge.'),
                                 '%press_continue%'),
            
            '1018' :            ('%unknown_error%',
                                  '%try_again%'),
            
            '1019' :            (self.__tr('Powering down.'),
                                 ''),
            
            '1020' :            (self.__tr('Front panel test.'),
                                 ''),
            
            '1021' :            (self.__tr('Clean out tray missing.'),
                                 '%try_again%'),
            
            '1022' :            (self.__tr('Output bin full.'),
                                 '%try_again%'),
            
            '1023' :            (self.__tr('Media size mismatch.'),
                                 '%try_again%'),
            
            '1024' :            (self.__tr('Duplexer is jammed.'),
                                 '%1014%'),
            
            '1025' :            ('%1014%',
                                 '%1014%'),
            
            '1026' :            (self.__tr('An ink cartridge is out of ink.'),
                                 '%try_again%'),
            
            '1027' :            (self.__tr('Internal device error.'),
                                 '%try_again%'),
            
            '1028' :            ('%1014%',
                                 '%1014%'),
            
            '1029' :            (self.__tr('Second tray missing.'),
                                 '%try_again%'),
            
            '1030' :            (self.__tr('Duplexer missing.'),
                                 '%try_again%'),
            
            '1031' :            (self.__tr('Rear tray missing.'),
                                 '%try_again%'),
            
            '1032' :            (self.__tr('Cartridge not latched.'),
                                 '%try_again%'),
            
            '1033' :            (self.__tr('Battery very low.'),
                                 '%try_again%'),
            
            '1034' :            ('%1017%',
                                 '%try_again%'),
            
            '1035' :            (self.__tr('Output tray closed.'),
                                 '%try_again%'),
            
            '1036' :            (self.__tr('Manual feed blocked.'),
                                 '%1014%'),
            
            '1037' :            (self.__tr('Rear feed blocked.'),
                                 '%1014%'),
            
            '1038' :            (self.__tr('Second tray out of paper.'),
                                 '%1009%'),
            
            '1039' :            (self.__tr('Input tray locked.'),
                                 '%try_again%'),
            
            '1040' :            (self.__tr('Non-HP ink.'),
                                 '%try_again%'),
            
            '1041' :            (self.__tr('Pen calibration needs resume.'),
                                 '%press_continue%'),
            
            '1042' :            (self.__tr('Media type mismatch.'),
                                 '%try_again%'),
            
            '1043' :            (self.__tr('Custom media mismatch.'),
                                 '%try_again%'),
            
            '1044' :            (self.__tr('Pen cleaning in progress.'),
                                 ''),
            
            '1045' :            (self.__tr('Pen checking in progress.'),
                                 ''),
            
            '1501' :            (self.__tr('Black cartridge is low on ink'),
                                 ''),
            
            '1502' :            (self.__tr('Tri-color cartridge is low on ink'),
                                 ''),
            
            '1503' :            (self.__tr('Photo cartridge is low on ink'),
                                 ''),
            
            '1504' :            (self.__tr('Cyan cartridge is low on ink'),
                                 ''),
            
            '1505' :            (self.__tr('Magenta cartridge is low on ink'),
                                 ''),
            
            '1506' :            (self.__tr('Yellow cartridge is low on ink'),
                                 ''),
            
            '1507' :            (self.__tr('Photo cyan cartridge is low on ink'),
                                 ''),
            
            '1508' :            (self.__tr('Photo magenta cartridge is low on ink'),
                                 ''),
            
            '1509' :            (self.__tr('Photo yellow cartridge is low on ink'),
                                 ''),
            
            '1510' :            (self.__tr('Photo gray cartridge is low on ink'),
                                 ''),
            
            '1511' :            (self.__tr('Photo blue cartridge is low on ink'),
                                 ''),
            
            '1601' :            (self.__tr('Black cartridge is low on toner'),
                                 ''),
            
            '1604' :            (self.__tr('Cyan cartridge is low on toner'),
                                 ''),
            
            '1605' :            (self.__tr('Magenta cartridge is low on toner'),
                                 ''),
            
            '1606' :            (self.__tr('Yellow cartridge is low on toner'),
                                 ''),
            
            '1800' :            (self.__tr('Warming up.'),
                                 ''),
            
            '1801' :            (self.__tr('Low paper.'),
                                 ''),
            
            '1802' :            (self.__tr('Door open.'),
                                 '%try_again%'),
            
            '1803' :            (self.__tr('Offline.'),
                                 ''),
            
            '1804' :            (self.__tr('Low toner.'),
                                 ''),
            
            '1805' :            (self.__tr('No toner.'),
                                 '%try_again%'),
            
            '1806' :            (self.__tr('Service request.'),
                                 '%try_again%'),
            
            '1807' :            (self.__tr('Fuser error.'),
                                 '%try_again%'),
            
            '1900' :            (self.__tr('Unsupported printer model.'),
                                 ''),
            
            '2000' :            (self.__tr('Scan job started.'),
                                 ''),
            
            '2001' :            (self.__tr('Scan job completed.'),
                                 ''),
            
            '2002' :            (self.__tr('Scan job failed.'),
                                 '%try_again%'),
            
            '3000' :            (self.__tr('Fax job started.'),
                                 ''),
            
            '3001' :            (self.__tr('Fax job complete.'),
                                 ''),
            
            '3002' :            (self.__tr('Fax job failed.'),
                                 '%try_again%'),
            
            '3003' :            (self.__tr('Fax job canceled.'),
                                 ''),
            
            '3004' :            (self.__tr('Fax send job continuing.'),
                                 ''),
            
            '3005' :            (self.__tr('Fax receive job continuing.'),
                                 ''),
            
            '4000' :            (self.__tr('Copy job started.'),
                                 ''),
            
            '4001' :            (self.__tr('Copy job complete.'),
                                 ''),
            
            '4002' :            (self.__tr('Copy job failed.'),
                                 '%try_again%'),
            
            '4003' :            (self.__tr('Copy job canceled.'),
                                 ''),
            
            '5002' :            (self.__tr('Device is powered down or unplugged.'),
                                 '%5012%'),
            
            '5012' :            (self.__tr('Device communication error.'),
                                 '%try_again%'),
            
            '5021' :            (self.__tr('Device is busy.'),
                                 ''),
            
            '5022' :            (self.__tr('No data.'),
                                 ''),
            
            '5030' :            ('%unknown_error%',
                                 '%try_again%'),
            
            '5031' :            ('%5021%',
                                 ''),
            
            '5033' :            (self.__tr('Unsupported I/O bus.'),
                                 '%try_again%'),
            
            '5034' :            (self.__tr('Device does not support requested operation.'),
                                 '%try_again%'),
            
            '5052' :            (self.__tr('To send a fax you must run hp-sendfax first.'),
                                 self.__tr('Run hp-sendfax now to continue. Fax will resume within 10 seconds.')),
            
            '6000' :            (self.__tr('Photocard unload started.'),
                                 ''),
            
            '6001' :            (self.__tr('Photocard unload ended.'),
                                 ''),
            
            '6002' :            (self.__tr('Photocard unload failed.'),
                                 self.__tr('Make sure photocard is inserted properly and try again.')),
            
            '6003' :            (self.__tr('Unable to mount photocard on device.'),
                                 '%6002%'),
            
            '6004' :            (self.__tr('Photocard unloaded successfully.'),
                                 ''),
            
            'unknown_error' :   (self.__tr('Unknown error.'),
                                 ''),
            
            'print' :           (self.__tr('Print'),
                                 ''),
            
            'scan' :            (self.__tr('Scan'),
                                 ''),
            
            'send_fax' :        (self.__tr('Send fax'),
                                 ''),
            
            'make_copies' :     (self.__tr('Make copies'),
                                 ''),
            
            'access_photo_cards' :    (self.__tr('Access photo cards'),
                                       ''),
            
            'agent_invalid_invalid' : (self.__tr('Invalid/missing'),
                                       ''),
            
            'agent_invalid_supply' :  (self.__tr('Invalid/missing ink cartridge'),
                                       ''),
            
            'agent_invalid_cartridge':(self.__tr('Invalid/missing cartridge'),
                                       ''),
            
            'agent_invalid_head' :    (self.__tr('Invalid/missing print head'),
                                       ''),
            
            'agent_unknown_unknown' : ('%unknown%',
                                       ''),
            
            'agent_unspecified_battery' : ('Battery',
                                           ''),
            
            'agent_black_head' :      (self.__tr('Black print head'),
                                       ''),
            
            'agent_black_supply' :    (self.__tr('Black ink cartridge'),
                                       ''),
            
            'agent_black_cartridge' : (self.__tr('Black cartridge'),
                                       ''),
            
            'agent_cmy_head' :        (self.__tr('Tri-color print head'),
                                       ''),
            
            'agent_cmy_supply' :      (self.__tr('Tri-color ink cartridge'),
                                       ''),
            
            'agent_cmy_cartridge' :   (self.__tr('Tri-color cartridge'),
                                       ''),
            
            'agent_kcm_head' :        (self.__tr('Photo print head'),
                                       ''),
            
            'agent_kcm_supply' :      (self.__tr('Photo ink cartridge'),
                                       ''),
            
            'agent_kcm_cartridge' :   (self.__tr('Photo cartridge'),
                                       ''),
            
            'agent_cyan_head' :       (self.__tr('Cyan print head'),
                                       ''),
            
            'agent_cyan_supply' :     (self.__tr('Cyan ink cartridge'),
                                       ''),
            
            'agent_cyan_cartridge' :  (self.__tr('Cyan cartridge'),
                                       ''),
            
            'agent_magenta_head' :    (self.__tr('Magenta print head'),
                                       ''),
            
            'agent_magenta_supply' :  (self.__tr('Magenta ink cartridge'),
                                       ''),
            
            'agent_magenta_cartridge':(self.__tr('Magenta cartridge'),
                                       ''),
            
            'agent_yellow_head' :     (self.__tr('Yellow print head'),
                                       ''),
            
            'agent_yellow_supply' :   (self.__tr('Yellow ink cartridge'),
                                       ''),
            
            'agent_yellow_cartridge': (self.__tr('Yellow cartridge'),
                                       ''),
            
            'agent_photo_cyan_head' :       (self.__tr('Photo cyan print head'),
                                             ''),
            
            'agent_photo_cyan_supply' :     (self.__tr('Photo cyan ink cartridge'),
                                             ''),
            
            'agent_photo_cyan_cartridge' :  (self.__tr('Photo cyan cartridge'),
                                             ''),
            
            'agent_photo_magenta_head' :    (self.__tr('Photo magenta print head'),
                                             ''),
            
            'agent_photo_magenta_supply' :  (self.__tr('Photo magenta ink cartridge'),
                                             ''),
            
            'agent_photo_magenta_cartridge':(self.__tr('Photo magenta cartridge'),
                                             ''),
            
            'agent_photo_yellow_head' :     (self.__tr('Photo yellow print head'),
                                             ''),
            
            'agent_photo_yellow_supply' :   (self.__tr('Photo yellow ink cartridge'),
                                             ''),
            
            'agent_photo_yellow_cartridge': (self.__tr('Photo yellow cartridge'),
                                             ''),
            
            'agent_photo_gray_head' :       (self.__tr('Photo gray print head'),
                                             ''),
            
            'agent_photo_gray_supply' :     (self.__tr('Photo gray ink cartridge'),
                                             ''),
            
            'agent_photo_gray_cartridge' :  (self.__tr('Photo gray cartridge'),
                                             ''),
            
            'agent_photo_blue_head' :       (self.__tr('Photo blue print head'),
                                             ''),
            
            'agent_photo_blue_supply' :     (self.__tr('Photo blue ink cartridge'),
                                             ''),
            
            'agent_photo_blue_cartridge' :  (self.__tr('Photo blue cartridge'),
                                             ''),
            
            'agent_kcmy_cm_head' :          (self.__tr('Print head'),
                                             ''),
            
            'agent_photo_cyan_and_photo_magenta_head' : (self.__tr('Photo magenta and photo cyan print head'),
                                                         ''),
            
            'agent_yellow_and_magenta_head' :           (self.__tr('Magenta and yellow print head'), 
                                                         '' ),
            
            'agent_cyan_and_black_head' :               (self.__tr('Black and cyan print head'),
                                                         '' ),
            
            'agent_light_gray_and_photo_black_head' :    (self.__tr('Light gray and photo black print head'),
                                                          '' ),
            
            'agent_light_gray_supply' :                 (self.__tr('Light gray ink cartridge'), # LG
                                                         '' ),
            
            'agent_medium_gray_supply' :                (self.__tr('Medium gray ink cartridge'), 
                                                         '' ),
            
            'agent_photo_gray_supply' :                 (self.__tr('Photo black ink cartridge'), # PK
                                                         '' ),
                                                        
            'agent_cyan_and_magenta_head' :             (self.__tr('Cyan and magenta print head'),
                                                          ''),
            
            'agent_black_and_yellow_head' :             (self.__tr('Black and yellow print head'),
                                                          ''),
            
            'agent_black_toner' :           (self.__tr('Black toner cartridge'),
                                             ''),
            
            'agent_cyan_toner' :            (self.__tr('Cyan toner cartridge'),
                                             ''),
            
            'agent_magenta_toner' :         (self.__tr('Magenta toner cartridge'),
                                             ''),
            
            'agent_yellow_toner' :          (self.__tr('Yellow toner cartridge'),
                                             ''),
            
            'agent_unspecified_maint_kit' : (self.__tr('Maintenance kit (fuser)'),
                                             ''),
            
            'agent_unspecified_adf_kit'   : (self.__tr('Document feeder (ADF) kit'),
                                             ''),
            
            'agent_unspecified_drum_kit'   : (self.__tr('Drum maintenance kit'),
                                              ''),
            
            'agent_unspecified_transfer_kit'   : (self.__tr('Image transfer kit'),
                                                  ''),
            
            'agent_health_unknown'     : ('Unknown',
                                          ''),
            
            'agent_health_ok'          : (self.__tr('Good/OK'),
                                           ''),
            
            'agent_health_fair_moderate' : (self.__tr('Fair/Moderate'),
                                            ''),
            
            'agent_health_misinstalled': (self.__tr('Not installed'),
                                          ''),
            
            'agent_health_incorrect'   : (self.__tr('Incorrect'),
                                          ''),
            
            'agent_health_failed'      : (self.__tr('Failed'),
                                          ''),
            
            'agent_health_overtemp'      : (self.__tr('Overheated'),
                                            ''),
            
            'agent_health_discharging'      : (self.__tr('Discharging'),
                                               ''),
            
            'agent_health_charging'      : (self.__tr('Charging'),
                                            ''),
            
            'agent_level_unknown'      : ('%unknown%',
                                          ''),
            
            'agent_level_low'          : (self.__tr('Low'),
                                          ''),
            
            'agent_level_out'          : (self.__tr('Very low'),
                                          ''),
            
            'email_test_subject'      : (self.__tr('HPLIP: Email alert test message'),
                                         ''),
            
            'email_test_message'      : (self.__tr('This email is to test the functionality of HPLIP email alerts.'),
                                         ''),
            
            'email_alert_subject'      : (self.__tr('HPLIP: Error/alert on device: '),
                                          ''),
            
        }
    
    def __tr(self,s,c = None):
        return s
        
        
        
    
