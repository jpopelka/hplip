# -*- coding: utf-8 -*-
#
# (c) Copyright @ 2013 Hewlett-Packard Development Company, L.P.
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
# Author: Amarnath Chitumalla
#
import os
import getpass
import cStringIO
import time
import string

from base import utils, tui
from base.g import *
import pexpect

PASSWORD_RETRY_COUNT = 3

AUTH_TYPES ={'mepis':'su',
             'debian':'su',
             'suse':'su',
             'mandriva':'su',
             'fedora':'su',
             'redhat':'su',
             'rhel':'su',
             'slackware':'su',
             'gentoo':'su',
             'redflag':'su',
             'ubuntu':'sudo',
             'xandros':'su',
             'freebsd':'su',
             'linspire':'su',
             'ark':'su',
             'pclinuxos':'su',
             'centos':'su',
             'igos':'su',
             'linuxmint':'sudo',
             'linpus':'sudo',
             'gos':'sudo',
             'boss':'su',
             'lfs':'su',
             }


#TBD this function shoud be removed once distro class implemented
def get_distro_name():
    os_name = None;
    if utils.which('lsb_release'):
       name = os.popen('lsb_release -i | cut -f 2')
       os_name = name.read().strip()
       name.close()
    else:
       name = os.popen("cat /etc/issue | awk '{print $1}' | head -n 1")
       os_name = name.read().strip()
       name.close()

    if "redhatenterprise" in os_name.lower():
        os_name = 'rhel'
    elif "suse" in os_name.lower():
        os_name = 'suse'

    return os_name




class Password(object):
    def __init__(self, Mode = INTERACTIVE_MODE):
        self.__password =""
        self.__passwordValidated = False
        self.__mode = Mode
        self.__readAuthType()  #self.__authType   
        self.__expectList =[]
        for s in utils.EXPECT_WORD_LIST:
            try:
                p = re.compile(s, re.I)
            except TypeError:
                self.__expectList.append(s)
            else:
                self.__expectList.append(p)

    ##################### Private functions ######################


    def __readAuthType(self):
        #TBD: Getting distro name should get distro class
        distro_name =  get_distro_name().lower()

        try:
            self.__authType = AUTH_TYPES[distro_name]
        except KeyError:
            log.warn("%s distro is not found in AUTH_TYPES"%distro_name)
            self.__authType = 'su'

    def __getPasswordDisplayString(self):
        if self.__authType == "su":
            return "Please enter the root/superuser password: "
        else:
            return "Please enter the sudoer (%s)'s password: " % os.getenv('USER')


    def __changeAuthType(self):
        if self.__authType == "sudo":
            self.__authType = "su"
        else:
            self.__authType = "sudo"


    def __get_password(self,pswd_msg=''):
        if pswd_msg == '':
            if self.__authType == "su":
                pswd_msg = "Please enter the root/superuser password: "
            else:
                pswd_msg = "Please enter the sudoer (%s)'s password: " % os.getenv('USER')

        return getpass.getpass(log.bold(pswd_msg))



    def __get_password_ui(self,pswd_msg='', qt="qt4"):
        if pswd_msg == '':
            pswd_msg = "Your HP Device requires to install HP proprietary plugin\nPlease enter root/superuser password to continue"

        #TBD: currently takes only username as root, need to handle for other users also.
        if qt == "qt4":
            from ui4.setupdialog import showPasswordUI
            username, password = showPasswordUI(pswd_msg, "root", False)

        if qt == "qt3":
            from ui.setupform import showPasswordUI
            username, password = showPasswordUI(pswd_msg, "root", False)

        return  password


    def __password_check(self, cmd, timeout=1):
        output = cStringIO.StringIO()
        ok, ret = False, ''

        try:
            child = pexpect.spawn(cmd, timeout=1)
        except pexpect.ExceptionPexpect:
            return 1, ''

        try:
            try:
                start = time.time()

                while True:
                    update_spinner()

                    i = child.expect_list(self.__expectList)
                    cb = child.before
                    if cb:
                        # output
                        start = time.time()
                        log.log_to_file(cb)
                        log.debug(cb)
                        output.write(cb)

                    if i == 0: # EOF
                        ok, ret = True, output.getvalue()
                        break

                    elif i == 1: # TIMEOUT
                        continue

                    else: # password
                        child.sendline(self.__password)

            except (Exception, pexpect.ExceptionPexpect):
                log.exception()

        finally:
            cleanup_spinner()

            try:
                child.close()
            except OSError:
                pass

        if ok:
            return child.exitstatus, ret
        else:
            return 1, ''


    def __validatePassword(self ,pswd_msg):
        x = 1
        qt = ""
        while True:
            if self.__mode == INTERACTIVE_MODE:
                self.__password = self.__get_password(pswd_msg)
            else:
                if self.getAuthType() == 'su':
                    if not utils.to_bool(sys_conf.get('configure', 'qt4', '0')) and utils.to_bool(sys_conf.get('configure', 'qt3', '0')) :
                        qt = "qt3"      #ifqt4 is enabled, gives more preferrence to qt4.
                    else:
                        qt = "qt4"

                    self.__password = self.__get_password_ui(pswd_msg, qt)
                else:
                    # Other password utils (i.e. kdesu, gnomesu, gksu) just validates the password but won't return password.
                    break

            cmd = self.getAuthCmd() % "true"
            log.debug(cmd)

            status, output = self.__password_check(cmd)
            log.debug("status = %s  output=%s "%(status,output))

            if status == 0:
                self.__passwordValidated = True
                break
            elif "not in the sudoers file" in output:
                log.error("User is not in the sudoers file.")
                break
                #TBD.. IF user dosn't have sudo permissions, needs to change to "su" type and query for password
#                self.__changeAuthType()
            else:
                self.__password = ""
                x += 1
                if self.__mode == GUI_MODE:
                    if qt == "qt4":
                        from ui4.setupdialog import FailureMessageUI
                    if qt == "qt3":
                        from ui.setupform import FailureMessageUI

                    if x > PASSWORD_RETRY_COUNT:
                        FailureMessageUI("Password incorrect. ")
                        return
                    else:
                        FailureMessageUI("Password incorrect. %d attempt(s) left." % (PASSWORD_RETRY_COUNT +1 -x ))
                else:
                    if x > PASSWORD_RETRY_COUNT:
                        log.error("Password incorrect. ")
                        return
                    else:
                        log.error("Password incorrect. %d attempt(s) left." % (PASSWORD_RETRY_COUNT +1 -x ))


    def __get_password_utils(self):
        if self.__authType == "su":
            AuthType, AuthCmd = 'su', 'su -c "%s"'
        else:
            AuthType, AuthCmd = 'sudo', 'sudo %s'

        return AuthType, AuthCmd


    def __get_password_utils_ui(self):
        distro_name =  get_distro_name().lower()
        if distro_name == 'rhel':
            AuthType, AuthCmd  = 'su', 'su -c "%s"'
        else:
            AuthType, AuthCmd  = 'su', 'su - -c "%s"'

        if utils.which('kdesu'):
            AuthType, AuthCmd = 'kdesu', 'kdesu -- %s'
        elif utils.which('gnomesu'):
            AuthType, AuthCmd = 'gnomesu', 'gnomesu -c "%s"'
        elif utils.which('gksu'):
            AuthType, AuthCmd = 'gksu' , 'gksu "%s"'
            
#Uncomment :::   For testing 
#        AuthType, AuthCmd = 'su' ,'su - -c "%s"'
        return AuthType, AuthCmd


    ##################### Public functions ######################

    def clearPassword(self):
        log.debug("Clearing password...")
        self.__password =""
        self.__passwordValidated = False
        if self.__authType == 'sudo':
            utils.run("sudo -K")


    def getAuthType(self):
        if self.__mode == INTERACTIVE_MODE:
            retValue = self.__authType
        else:
            retValue, AuthCmd = self.__get_password_utils_ui()

        return retValue


    def getAuthCmd(self):
        if self.__mode == INTERACTIVE_MODE:
            AuthType, AuthCmd = self.__get_password_utils()
        else:
            AuthType, AuthCmd = self.__get_password_utils_ui()

        return AuthCmd


    def getPassword(self, pswd_msg='', psswd_queried_cnt = 0):
        if self.__passwordValidated:
            return self.__password

        if psswd_queried_cnt:
            return self.__password

        self.__validatePassword( pswd_msg)
        return self.__password

