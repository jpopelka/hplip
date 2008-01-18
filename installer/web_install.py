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
# Author: Don Welch, Pete Parks
#

# Std Lib
import time, thread
import Queue
import base64
import re
import locale
import socket


# Local
import cherrypy
from base.g import *
from Cheetah.Template import Template
from base import utils
from core_install import *
from base import utils, pexpect
from xml.dom.minidom import parse, parseString

ACTION_INIT = 0
ACTION_INSTALL_REQUIRED = 1
ACTION_INSTALL_OPTIONAL = 2
ACTION_PRE_DEPENDENCY = 3
ACTION_POST_DEPENDENCY = 4
ACTION_BUILD_AND_INSTALL = 5
ACTION_REMOVE_HPOJ = 6
ACTION_REMOVE_HPLIP = 7
ACTION_RESTART_CUPS = 8
ACTION_PRE_BUILD = 9
ACTION_POST_BUILD = 10
ACTION_MAX = 10

ACTION_TEXT_INSTALL = '33'

XMLPATH = 'installer/localization'


    
try:
    from functools import update_wrapper
except ImportError: # using Python version < 2.5
    def trace(f):
        def newf(*args, **kw):
           log.debug2("TRACE: func=%s(), args=%s, kwargs=%s" % (f.__name__, args, kw))
           return f(*args, **kw)
        newf.__name__ = f.__name__
        newf.__dict__.update(f.__dict__)
        newf.__doc__ = f.__doc__
        newf.__module__ = f.__module__
        return newf
else: # using Python 2.5+
    def trace(f):
        def newf(*args, **kw):
            log.debug2("TRACE: func=%s(), args=%s, kwargs=%s" % (f.__name__, args, kw))
            return f(*args, **kw)
        return update_wrapper(newf, f)

def cat(package_mgr_cmd, packages_to_install):
    return utils.cat(package_mgr_cmd)

opener = re.escape('$')
closer = opener
pattern = re.compile(opener + '([_A-Za-z][_A-Za-z0-9]*)' + closer)

def sub_string_replace(main_string):
    return re.sub(pattern, r'%(\1)s', main_string.replace('%','%%') )


class Installer(object):
    def __init__(self):
        self.history = []
        self.auto_mode = False # custom_mode = False, auto_mode = True
        self.passwd = ''
        self.next = None
        self.progress_status_code = -1
        self.action_lock = thread.allocate_lock() # lock to protect progress_status_code()
        self.queue = Queue.Queue()
        self.pre_has_run = False
        self.post_has_run = False
        self.depends_to_install = []
        self.is_signal_stop = 0
        self.localized_dict = {}
        self.failed_cmd = ''

        self.core = CoreInstall()
        self.core.get_hplip_version()

    @trace
    def popHistory(self):
        return self.history.pop()

    @trace
    def pushHistory(self, pg):
        self.history.append(pg)

    @trace
    def createTemplate(self, name):

        # maybe save as a class member ( self.cur_dir) or save the template path as a member variable (self.template_dir) and then os.join() it to the name.tmpl?
        #cur_dir = os.path.realpath(os.path.normpath(os.getcwd()))
        #compilerSettings = {'useStackFrames': False}
        #template = Template(os.path.join(cur_dir, "installer", "pages", "%s.tmpl" % name))

        template = Template(file="installer/pages/%s.tmpl" % name, compilerSettings={'useStackFrames': False} )

        template.title = "Title: %s" % name
        template.content = "<em>%s<em>" % name
        template.version = self.core.version_public

        template.installer_title = self.localized_dict["installer_title"]
        template.header_string = self.localized_dict["header_string"]
        template.sub_header_string = self.localized_dict["sub_header_string"]
       ##template.quit_message_title = self.localized_dict.get(screen + "_message_title", "")


        return template

    #
    # INDEX (LAUNCHES MAIN INSTALLER PAGE WELCOME IN NEW WINDOW)
    #

    ####################################
    # QUIT
    ####################################
    def quit(self):
        screen = "quit"
        template = self.createTemplate(screen)

        # body and message inserts
        template.quit_message_title = self.localized_dict[screen + "_message_title"]

        return str(template)

    quit.exposed = True
    

    ####################################
    # RESTART
    ####################################
    def restart(self):
        screen = "restart"
        template = self.createTemplate(screen)
        
        template.installer_title = self.localized_dict["installer_title"]
        template.header_string = self.localized_dict["header_string"]
        template.sub_header_string = self.localized_dict["sub_header_string"]

        # body and message inserts
        template.restart_message_body = self.localized_dict[screen + "_message_body"]
        template.restart_command = self.core.su_sudo() % "hp-setup"
        template.restart_message_body_bottom = self.localized_dict[screen + "_message_body_bottom"]
        template.restart_message_footer = self.localized_dict[screen + "_message_footer"]
        
        template.restart_button = self.localized_dict["restart_button"]
        template.quit_button = self.localized_dict["quit_button"]
        template.replug_button = self.localized_dict["replug_button"]

        return str(template)

    restart.exposed = True
    
    
    ####################################
    # REPLUG
    ####################################
    def replug(self):
        screen = "replug"
        template = self.createTemplate(screen)
        
        template.installer_title = self.localized_dict["installer_title"]
        template.header_string = self.localized_dict["header_string"]
        template.sub_header_string = self.localized_dict["sub_header_string"]

        # body and message inserts
        template.replug_message_body = self.localized_dict[screen + "_message_body"]
        template.replug_message_footer = self.localized_dict[screen + "_message_footer"]
        
        template.next_button = self.localized_dict["next_button"]

        return str(template)

    replug.exposed = True
    
    def replug_controller(self):
        return self.finished()

    replug_controller.exposed = True

    ####################################
    # UNSUPPORTED
    ####################################
    def unsupported(self):
        screen = "unsupported"
        template = self.createTemplate(screen)

        # body and message inserts
        template.unsupported_message_title = self.localized_dict[screen + "_message_title"]
        template.unsupported_notes_field = self.localized_dict[screen + "_notes_field"]
        template.unsupported_notes_field1 = self.localized_dict[screen + "_notes_field1"]
        template.unsupported_notes_field2 = self.localized_dict[screen + "_notes_field2"]
        template.unsupported_notes_field3 = self.localized_dict[screen + "_notes_field3"]
        template.unsupported_notes_field4 = self.localized_dict[screen + "_notes_field4"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.next_button = self.localized_dict["next_button"]
        
        return str(template)

    unsupported.exposed = True

    def unsupported_controller(self):
        return self.welcome()

    unsupported_controller.exposed = True

    ####################################
    # INDEX
    ####################################
    def index(self):
        screen = "index"
        template = self.createTemplate(screen)

        # body and message inserts
        template.index_message_title = self.localized_dict[screen + "_message_title"]
        template.quit_message_title = self.localized_dict["quit_message_title"]
        # button text inserts
        template.start_button = self.localized_dict["start_button"]
        template.command_button = self.localized_dict["command_button"]
        template.quit_button = self.localized_dict["quit_button"]
        return str(template)

    index.exposed = True

    def signal_stop(self):
        """
            Called by Quit to signal a stop
        """
        self.is_signal_stop = 1

    signal_stop.exposed = True

    def signal_stopped(self):
        """
            Checked by index.html to see if we are stopping
        """
        return str(self.is_signal_stop)

    signal_stopped.exposed = True

    def text_installer(self):
        #print "web_install.py::text_installer"
        raise SystemExit(ACTION_TEXT_INSTALL)
        
    text_installer.exposed = True

    def stop(self):
        """
            Stop the CherryPy browser
        """
        raise SystemExit

    stop.exposed = True
        
    def set_restart(self):
        #print "set_restart"
        ok = self.core.restart()
        if not ok:
            log.error("Restart failed. Please restart using the system menu.")
        
    set_restart.exposed = True

    ####################################
    # WELCOME
    ####################################

    def welcome(self):
        screen = "welcome"
        template = self.createTemplate(screen)

        # body and message inserts
        template.welcome_message_title = self.localized_dict[screen + "_message_title"]
        template.welcome_message_body = sub_string_replace(self.localized_dict[screen + "_message_body"]) % { "version":self.core.version_public }
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.next_button = self.localized_dict["next_button"]

        #template.version = "XXXX"   #TODO: Ask Don why this was removed????

        self.pushHistory(self.welcome)
        return str(template)

    welcome.exposed = True

    def welcome_controller(self):
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if os.geteuid() == 0:
            return self.warning()
        else:
            #self.next = self.password
            self.next = self.confirm_distro
            return self.progress(ACTION_INIT)

    welcome_controller.exposed = True


    ####################################
    # PASSWORD
    ####################################
    def password(self):
        """
            Collect root password from user
        """
        screen = "password"
        template = self.createTemplate(screen)

        # body and message inserts
        template.password_message_title = self.localized_dict[screen + "_message_title"]
        template.password_message_body = self.localized_dict[screen + "_message_body"]
        template.password_message_footer = self.localized_dict[screen + "_message_footer"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]
        template.password_alert = self.localized_dict["password_alert"]
        

        self.pushHistory(self.password)
        return str(template)

    password.exposed = True

    # Password callback
    def password_callback(self):
        return self.core.password

    def password_check_callback(self, msg):
        log.debug(msg)

    @trace
    # Passwrod set
    def set_password(self, passwd):
        """
            Collect root password from user - password?passwd=<passwd>
        """
        if passwd:
            self.core.password = base64.decodestring(passwd)
            pstr = str(self.core.check_password(self.password_callback))
            return pstr
        else:
            return 'Empty'

    set_password.exposed = True

    # Password callback
    def password_controller(self):
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        return self.mode()

    password_controller.exposed = True

    ####################################
    # WARNING
    ####################################
    @trace
    def warning(self):

        screen = "warning"
        template = self.createTemplate(screen)

        # body and message inserts
        template.warning_message_title = self.localized_dict[screen + "_message_title"]
        template.warning_notes_field = self.localized_dict[screen + "_notes_field"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]


        self.pushHistory(self.warning)
        return str(template)

    warning.exposed = True

    def warning_controller(self):
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        #self.next = self.password
        self.next = self.confirm_distro
        return self.progress(ACTION_INIT)

    warning_controller.exposed = True


    ####################################
    # MODE
    ####################################
    @trace
    def mode(self):
        """
            Install Mode: Custom or Automatic
        """
        screen = "mode"
        template = self.createTemplate(screen)

        # body and message inserts
        template.mode_message_title = self.localized_dict[screen + "_message_title"]
        template.mode_radio1 = self.localized_dict[screen + "_radio1"]
        template.mode_radio2 = self.localized_dict[screen + "_radio2"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.next_button = self.localized_dict["next_button"]

        self.pushHistory(self.mode)
        return str(template)

    mode.exposed = True

    @trace
    def mode_controller(self, auto_mode):
        """
            mode_controller?auto_mode=0|1
        """
        self.auto_mode = int(auto_mode)

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if not self.auto_mode:
            return self.component()
        else:
            return self.distro_controller()

    mode_controller.exposed = True

    ####################################
    # COMPONENT
    ####################################
    def component(self):
        """
            Install Component: HPLIP or HPIJS (not shown in auto mode)
        """
        screen = "component"
        template = self.createTemplate(screen)

        # body and message inserts
        template.component_message_title = self.localized_dict[screen + "_message_title"]
        template.component_radio1 = self.localized_dict[screen + "_radio1"]
        template.component_radio2 = self.localized_dict[screen + "_radio2"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]

        self.pushHistory(self.component)
        return str(template)

    component.exposed = True

    @trace
    def component_controller(self, component):
        """
            component_controller?component=hplip|hpijs
        """
        self.core.selected_component = component.strip().lower()
        assert self.core.selected_component in self.core.components.keys()

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        return self.distro_controller()

    component_controller.exposed = True

    #
    # DISTRO AND DISTRO VERSION
    #

    def distro_controller(self):
        """
            Determine if distro confirm or select is to be shown
        """
        if self.core.distro_known():
            if self.auto_mode:
                return self.notes() # auto mode, skip ahead to notes
            else:
                return self.confirm_distro() # manual mode, confirm distro info
        else:
            # distro and version is not known, get it from user
            return self.select_distro()

    distro_controller.exposed = True


    ####################################
    # CONFIRM_DISTRO
    ####################################
    def confirm_distro(self):
        """
            Correct Distro? (NOTE: Only display is distro && distro version is known)
        """
        screen = "confirm_distro"
        template = self.createTemplate(screen)

        # body and message inserts
        template.confirm_distro_message_title = self.localized_dict[screen + "_message_title"]
        template.confirm_distro_message_footer = sub_string_replace(self.localized_dict[screen + "_message_footer"]) % { "distro_version":self.core.distro_version, "distro_name":self.core.get_distro_data('display_name') }
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.no_button = self.localized_dict["no_button"]
        template.yes_button = self.localized_dict["yes_button"]

        self.pushHistory(self.confirm_distro)
        return str(template)

    confirm_distro.exposed = True

    @trace
    def confirm_distro_controller(self, confirmation):
        """
            confirm_distro_controller?confirmation=0|1
        """
        confirmation = int(confirmation)
        assert confirmation in (0, 1)

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if confirmation:
            #return self.notes()
            return self.password()
        else:
            return self.select_distro()

    confirm_distro_controller.exposed = True

    ####################################
    # SELECT_DISTRO
    ####################################
    def select_distro(self):
        """
            Choose Distro and Distro Version (only shown if distro and/or version not known
            || correct distro question answered "no")
        """

        screen = "select_distro"
        template = self.createTemplate(screen)

        # body and message inserts
        #select_distro_message_title
        template.select_distro_message_title = self.localized_dict[screen + "_message_title"]
        template.select_distro = self.localized_dict[screen]

        self.pushHistory(self.select_distro)
        template.select_distro_version = self.localized_dict["select_distro_version"]
        template.select_distro_any = self.localized_dict["select_distro_any"]

        template.distro_version = self.core.distro_version
        template.distro_name = self.core.distro_name
        template.distros = {}
        template.distro = self.core.distro

        for d in self.core.distros_index:
            dd = self.core.distros[self.core.distros_index[d]]

            if dd['display']:
                template.distros[d] = dd['display_name']
                
        template.turned_off_options = {}

        self.depends_to_install = []
        for depend, desc, required_for_opt, opt in self.core.missing_optional_dependencies():
            log.warn("Missing OPTIONAL dependency: %s (%s)" % (depend, desc))

            if required_for_opt:
                log.warn("(Required for %s option)" % opt)

            self.depends_to_install.append(depend)
            self.core.selected_options[opt] = False
            template.turned_off_options[opt] = self.core.options[opt][1]

        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]

        return str(template)

    select_distro.exposed = True

    def select_distro_update_combo(self, index):
        """
            AJAX method to update distro version combo box
        """
        self.core.distro = int(index)
        self.core.distro_name = self.core.distros_index[self.core.distro]
        versions = self.core.distros[self.core.distro_name]['versions'].keys()
        versions.sort(lambda x, y: self.core.sort_vers(x, y))
        return ' '.join(versions)

    select_distro_update_combo.exposed = True

    def select_distro_controller(self, distro, version):
        """
            select_distro_controller?distro=0&version=0.0
        """
        self.core.distro = int(distro)
        self.core.distro_version = version

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if not self.core.distro_known():
            self.check_required()

            if self.num_req_missing:
                return self.error_unsupported_distro() # still unknown and missing req. deps, bail out
            else:
                return self.notes() # unsupported, but no required missing, so continue
        else:
            #return self.notes() # ok, move ahead to notes
            #return self.password()
            return self.confirm_distro()

    select_distro_controller.exposed = True

    ####################################
    # NOTES
    ####################################
    def notes(self):
        """
            Installation Notes (distro specific)
        """
        self.pushHistory(self.notes)

        screen = "notes"
        template = self.createTemplate(screen)

        # body and message inserts
        template.notes_message_title = self.localized_dict[screen + "_message_title"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]

        distro_notes = self.core.get_distro_data('notes', '')
        ver_notes = self.core.get_ver_data('notes', '')

        if distro_notes and ver_notes:
            template.notes = distro_notes + "<p>" + ver_notes
        elif distro_notes:
            template.notes = distro_notes
        elif ver_notes:
            template.notes = ver_notes
        else:
            template.notes = "No notes are available."

        return str(template)

    notes.exposed = True

    def notes_controller(self):
        #print "notes_controller"
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if self.auto_mode:
            self.required_components_to_install()
            self.optional_components_to_install()
            return self.dependency_controller1()
        else:
            return self.options()

    notes_controller.exposed = True

    ####################################
    # OPTIONS
    ####################################
    def options(self):
        """
            Build Options (not shown in auto mode)
        """
        screen = "options"
        template = self.createTemplate(screen)

        # body and message inserts
        template.options_message_title = self.localized_dict[screen + "_message_title"]
        #template.welcome_message_body = sub_string_replace(self.localized_dict[screen + "_message_body"]) % {"version":self.core.distro_version}

        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]

        template.options = self.core.options
        template.components = self.core.components
        template.selected_component = self.core.selected_component

        return str(template)

    options.exposed = True

    def options_controller(self, **options):
        #print "options_controller"
        """
            options_controller?opt=0|1&opt=0|1&...
        """
        for opt in options:
            assert options[opt] in ('0', '1')
            assert opt in self.core.selected_options
            self.core.selected_options[opt] = int(options[opt])

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        return self.dependency_controller1()

    options_controller.exposed = True

    #
    # PACKAGE MANAGER
    #

    @trace
    def error_package_manager(self, pkg_mgr=''):
        """
            A package manager is running, prompt for closure
        """
        screen = "error_package_manager"
        template = self.createTemplate(screen)

        # body and message inserts
        template.error_package_manager_message_title = self.localized_dict[screen + "_message_title"]
        template.error_package_manager_message_body = sub_string_replace(self.localized_dict[screen + "_message_body"]) % {"package_manager_name":pkg_mgr}
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]

        return str(template)

    error_package_manager.exposed = True

    def error_package_manager_controller(self):
        pkg_mgr = self.core.check_pkg_mgr()
        if pkg_mgr:
            return self.error_package_manager(pkg_mgr)
        else:
            return self.next()

    error_package_manager_controller.exposed = True

    def package_manager_check(self):
        """
            Note: AJAX call
        """
        #print "package_manager_check"
        return str(int(self.core.check_pkg_mgr()()))
        # returns '' for no running pkg manager, or '<name>' of running package manager

    package_manager_check.exposed = True


    #
    # DEPENDENCIES
    #

    def dependency_controller1(self):
        self.check_required()
        self.check_optional()

        #
        # PRE-INSTALL COMMANDS
        #
        if self.core.run_pre_install(self.progress_callback): # some cmds were run...
            self.num_req_missing = self.core.count_num_required_missing_dependencies()
            self.num_opt_missing = self.core.count_num_optional_missing_dependencies()


        if self.core.distro_known():
            if self.num_req_missing:
                if self.auto_mode: # auto, distro known, req. missing
                    #print "dependency_controller1 => install_required_controller"
                    return self.install_required_controller() # ************* Seems Broke this way *********** answer=1)
                else:
                    return self.install_required() # manual, distro known, req. missing
            else:
                return self.dependency_controller2() # distro known, no req. missing (check optional)
        else:
            # distro unknown
            if self.num_req_missing:
                return self.error_required_missing() # distro unknown, req. missing, exit
            else:
                return self.dependency_controller2() # distro unknown, no req. missing (check optional)


    def dependency_controller2(self):
        if self.core.distro_known():
            if self.num_opt_missing:
                if self.auto_mode: # auto, distro known, opt. missing
                    return self.install_optional_controller()
                else:
                    return self.install_optional() # manual, distro known, opt. missing
            else:
                return self.dependency_controller3()
        else:
            # distro unknown
            if self.num_opt_missing:
                return self.turn_off_options() # distro unknown, opt. missing, turn off options, then continue
            else:
                return self.dependency_controller3() # distro unknown, no opt. (continue)

    def dependency_controller3(self):
        self.core.hpoj_present = self.core.check_hpoj()  #dcheck.check_hpoj()
        if self.core.hpoj_present and self.core.selected_component == 'hplip' and \
            self.core.distro_version_supported:

            if self.auto_mode:
                return self.hpoj_remove_controller()
            else:
                return self.hpoj_remove()
        else:
            return self.dependency_controller9()

    def dependency_controller4(self):
        self.next = self.dependency_controller7
        return self.progress(ACTION_INSTALL_REQUIRED)

    def dependency_controller5(self):
        self.next = self.dependency_controller3
        return self.progress(ACTION_INSTALL_OPTIONAL)

    def dependency_controller6(self):
        self.next = self.dependency_controller3
        return self.progress(ACTION_POST_DEPENDENCY)

    def dependency_controller7(self):
        return self.dependency_controller2()

    def dependency_controller8(self):
        #print "dependency_controller8"
        self.next = self.restart  #finished
        return self.progress(ACTION_BUILD_AND_INSTALL)

    def dependency_controller9(self):
        self.core.hplip_present = self.core.check_hplip()  #dcheck.check_hplip()
        #print "self.core.hplip_present:", self.core.hplip_present
        #print "self.core.selected_component", self.core.selected_component
        #print "self.core.distro_version_supported", self.core.distro_version_supported
        if self.core.hplip_present and self.core.selected_component == 'hplip' and \
            self.core.distro_version_supported:

            if self.auto_mode:
                return self.hplip_remove_controller()
            else:
                return self.hplip_remove()
        else:
            #print "dependency_controller9"
            return self.dependency_controller8()

    #
    # CHECK FOR ACTIVE NETWORK CONNECTION
    #

    def network_unavailable(self):
        #print "network_unavailable"
        screen = "network_unavailable"
        template = self.createTemplate(screen)

        # body and message inserts
        template.network_unavailable_message_title = self.localized_dict[screen + "_message_title"]
        template.network_unavailable_notes_field = self.localized_dict[screen + "_notes_field"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.retry_button = self.localized_dict["retry_button"]

        self.pushHistory(self.network_unavailable)
        return str(template)

    network_unavailable.exposed = True

    def network_unavailable_controller(self):
        #print "network_unavailable_controller"
        pkg_mgr = self.core.check_pkg_mgr()
        
        if not self.core.check_network_connection():
            return self.network_unavailable()
        else:
            if pkg_mgr:
                #print "network_unavailable_controller => install_required_controller"
                self.next = self.install_required_controller()
                return self.error_package_manager(pkg_mgr)
            else:
                self.next = self.dependency_controller4
                return self.progress(ACTION_PRE_DEPENDENCY)

    network_unavailable_controller.exposed = True


    #
    # Various installer checks
    #

    def check_required(self):
        self.num_req_missing = self.core.count_num_required_missing_dependencies()

    def check_optional(self):
        self.num_opt_missing = self.core.count_num_optional_missing_dependencies()

    # =====================================================================
    # install_required
    # =====================================================================
    def install_required(self):
        """
            Ask user if they want to try to install required dependencies (not shown in auto mode)
        """
        screen = "install_required"
        template = self.createTemplate(screen)

        # body and message inserts
        template.install_required_message_title = self.localized_dict[screen + "_message_title"]
        template.install_required_message_footer = self.localized_dict[screen + "_message_footer"]
        # button text inserts
        template.previous_button = self.localized_dict["previous_button"]
        template.no_button = self.localized_dict["no_button"]
        template.yes_button = self.localized_dict["yes_button"]

        template.missing_required_dependencies = {}
        for depend, desc, option in self.core.missing_required_dependencies():
            log.error("Missing REQUIRED dependency: %s (%s)" % (depend, desc))
            self.depends_to_install.append(depend)
            template.missing_required_dependencies[depend] = desc

        return str(template)

    install_required.exposed = True

    def required_components_to_install(self):
        for depend, desc, option in self.core.missing_required_dependencies():
            log.error("Missing REQUIRED dependency: %s (%s)" % (depend, desc))
            self.depends_to_install.append(depend)

    def optional_components_to_install(self):
        for depend, desc, required_for_opt, opt in self.core.missing_optional_dependencies():
            log.warn("Missing OPTIONAL dependency: %s (%s)" % (depend, desc))

            if required_for_opt:
                log.warn("(Required for %s option)" % opt)

            self.depends_to_install.append(depend)


    def install_required_controller(self): # install_required_controller
        #print "install_required_controller"
        pkg_mgr = self.core.check_pkg_mgr()
        if not self.core.check_network_connection():
            #print "install_required_controller = > network_unavailable"
            return self.network_unavailable()

        if pkg_mgr:
            self.next = self.install_required_controller
            return self.error_package_manager(pkg_mgr)
        else:
            self.next = self.dependency_controller4
            return self.progress(ACTION_PRE_DEPENDENCY)

    install_required_controller.exposed = True

    # =====================================================================
    # install_optional
    # =====================================================================
    def install_optional(self):
        """
            Ask user if they want to try to install optional dependencies (not shown in auto mode)
        """
        screen = "install_optional"
        template = self.createTemplate(screen)
        # body and message inserts
        template.install_optional_message_title = self.localized_dict[screen + "_message_title"]
        template.install_optional_message_footer = self.localized_dict[screen + "_message_footer"]
        # button text inserts
        template.yes_button = self.localized_dict["yes_button"]
        template.no_button = self.localized_dict["no_button"]
        template.quit_button = self.localized_dict["quit_button"]

        self.depends_to_install = []
        template.missing_optional_dependencies = {}

        for depend, desc, required_for_opt, opt in self.core.missing_optional_dependencies():
            log.warn("Missing OPTIONAL dependency: %s (%s)" % (depend, desc))

            if required_for_opt:
                log.warn("(Required for %s option)" % opt)

            self.depends_to_install.append(depend)
            template.missing_optional_dependencies[depend] = desc

        return str(template)

    install_optional.exposed = True

    def install_optional_controller(self):
        #print "install_optional_controller"
        pkg_mgr = self.core.check_pkg_mgr()
        if pkg_mgr:
            self.next = self.install_optional_controller()
            return self.error_package_manager(pkg_mgr)
        else:
            if self.pre_has_run:
                self.next = self.dependency_controller6
                return self.progress(ACTION_INSTALL_OPTIONAL)
            else:
                self.next = self.dependency_controller5
                return self.progress(ACTION_PRE_DEPENDENCY)


    install_optional_controller.exposed = True

    # =====================================================================
    # turn_off_options
    # =====================================================================
    def turn_off_options(self):
        """
            Inform the user that some options have been turned off because of missing optional dependencies
        """
        screen = "turn_off_options"
        template = self.createTemplate(screen)


        # body and message inserts
        template.turn_off_options_message_title = self.localized_dict[screen + "_message_title"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]

        template.turned_off_options = {}

        self.depends_to_install = []
        for depend, desc, required_for_opt, opt in self.core.missing_optional_dependencies():
            log.warn("Missing OPTIONAL dependency: %s (%s)" % (depend, desc))

            if required_for_opt:
                log.warn("(Required for %s option)" % opt)

            self.depends_to_install.append(depend)
            self.core.selected_options[opt] = False
            template.turned_off_options[opt] = self.core.options[opt][1]

        return str(template)

    turn_off_options.exposed = True

    # =====================================================================
    # turn_off_options_controller
    # =====================================================================
    def turn_off_options_controller(self):
        return self.dependency_controller3()

    turn_off_options_controller.exposed = True

    # =====================================================================
    # error_required_missing
    # =====================================================================
    def error_required_missing(self):
        """
            A required dependency is missing, can't continue
        """
        screen = "error_required_missing"
        template = self.createTemplate(screen)

        for depend, desc, option in self.core.missing_required_dependencies():
            log.error("Missing REQUIRED dependency: %s (%s)" % (depend, desc))
            template.missing_required_dependencies[d] = desc


        # body and message inserts
        template.error_required_missing_message_title = self.localized_dict[screen + "_message_title"]
        template.error_required_missing_message_footer = self.localized_dict[screen + "_notes_footer"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]


        return str(template)

    error_required_missing.exposed = True


    # =====================================================================
    # PROGRESS
    # =====================================================================
    # Reusable progress screen
    #  @trace
    def progress(self, action):
        """
            progress?action=0|1|2|3|4|5|6|7|8
        """
        self.action = int(action)
        assert action in range(ACTION_MAX)

        screen = "progress"

        template = self.createTemplate(screen)

        template.profile_software_requirements = self.localized_dict["profile_software_requirements"]
        template.required_dependencies = self.localized_dict["required_dependencies"]
        template.optional_dependencies = self.localized_dict["optional_dependencies"]
        template.preparing_dependencies = self.localized_dict["preparing_dependencies"]
        template.finishing_dependencies = self.localized_dict["finishing_dependencies"]
        template.building_and_installing = self.localized_dict["building_and_installing"]
        template.remove_hpoj = self.localized_dict["remove_hpoj"]
        template.remove_hplip = self.localized_dict["remove_hplip"]
        template.restarting_cups = self.localized_dict["restarting_cups"]
        template.unimplemented_operation = self.localized_dict["unimplemented_operation"]
        
        template.installation_progress = self.localized_dict["installation_progress"]
        template.installation_progress_error = self.localized_dict["installation_progress_error"]
        template.got_into_bad_state = self.localized_dict["got_into_bad_state"]
  
        # button text inserts
        template.cancel_button = self.localized_dict["cancel_button"]
        template.retry_button = self.localized_dict["retry_button"]
        template.next_button = self.localized_dict["next_button"]
        template.progress_text = self.localized_dict["progress_text"]


        self.action_lock.acquire()
        self.progress_status_code = -1 # running
        self.action_lock.release()
        self.cancel_signaled = False
        self.cmds = []
        self.fail_ok = False


        if self.action == ACTION_INIT: # 0
            self.action_thread = thread.start_new_thread(self.run_core_init_thread, ())
            return str(template)

        else:
            if self.action in (ACTION_INSTALL_REQUIRED, ACTION_INSTALL_OPTIONAL): # 1 & 2
                log.debug(self.depends_to_install)
                packages_to_install = []
                commands_to_run = []

                package_mgr_cmd = self.core.get_distro_data('package_mgr_cmd', '')

                if package_mgr_cmd:
                    for d in self.depends_to_install:
                        log.debug("*** Processing dependency: %s" % d)
                        packages, commands = self.core.get_dependency_data(d)

                        log.debug("Packages: %s" % ','.join(packages))
                        log.debug("Commands: %s" % ','.join(commands))

                        if packages:
                            log.debug("Packages '%s' will be installed to satisfy dependency '%s'." %
                                (','.join(packages), d))
                            packages_to_install.extend(packages)

                        if commands:
                            log.debug("Commands '%s' will be run to satisfy dependency '%s'." %
                                (','.join(commands), d))
                            commands_to_run.extend(commands)


                self.cmds.append(cat(package_mgr_cmd, ' '.join(packages_to_install)))
                self.cmds.extend(commands_to_run)

            elif self.action == ACTION_PRE_DEPENDENCY: # 3
                self.pre_has_run = True
                self.cmds.extend(self.core.get_distro_ver_data('pre_depend_cmd', []))
                self.fail_ok = True

            elif self.action == ACTION_POST_DEPENDENCY: # 4
                self.post_has_run = True
                self.cmds.extend(self.core.get_distro_ver_data('post_depend_cmd', []))
                self.fail_ok = True

            elif self.action == ACTION_BUILD_AND_INSTALL: # 5  Do I want to combile pre_build and post_build?
                #print "ACTION_BUILD_AND_INSTALL"
                self.cmds.extend(self.core.pre_build())
                self.cmds.extend(self.core.build_cmds())
                self.cmds.extend(self.core.post_build())

                # Logoff if necessary
                #(*) Todo - I need to finish this...
            #    if self.core.restart_required:
                    #tui.title("IMPORTANT! RESTART REQUIRED!")
                    #log.note("If you are installing a USB connected printer, you must now restart your PC")
                    #log.note("in order to communicate with the printer. After restarting, run:")
                    #log.note(self.core.su_sudo() % "hp-setup")
                    #log.note("to setup a printer in HPLIP.")
                    #log.note("")
                    #log.note("IMPORTANT! Make sure to save all work in all open applications before restarting!")
                #    ok, ans = tui.enter_yes_no(log.bold("Restart now"), 'n')
                #    if not ok: sys.exit(0)
                #    if ans:
                    #    ok = self.core.restart()
                    #    if not ok:
                            #log.error("Restart failed. Please restart using the system menu.")
                #    sys.exit(0)

            #    elif self.core.logoff_required:
                    #tui.title("IMPORTANT! LOGOFF REQUIRED!")
                    #log.note("If you are installing a USB connected printer, you must now logoff and re-logon")
                    #log.note("in order to communicate with the printer. After logging back on, run:")
                    #log.note(self.core.su_sudo() % "hp-setup")
                    #log.note("to setup a printer in HPLIP.")
                    #log.note("")
                    #log.note("IMPORTANT! Make sure to save all work in all open applications before logging off!")
                #    ok, ans = tui.enter_yes_no(log.bold("Logoff now"), 'n')
                #    if not ok: sys.exit(0)
                #    if ans:
                    #    ok = self.core.logoff()
                    #    if not ok:
                            #log.error("Logoff failed. Please logoff using the system menu.")
                #    sys.exit(0)

            elif self.action == ACTION_REMOVE_HPOJ: # 6
                self.cmds.append(self.core.get_distro_data('hpoj_remove_cmd', ''))
                self.fail_ok = True

            elif self.action == ACTION_REMOVE_HPLIP: # 7
                self.cmds.append(self.core.stop_hplip())
                self.cmds.append(self.core.get_distro_data('hplip_remove_cmd', ''))
                self.fail_ok = True

            if self.cmds:
                self.cmds = [c for c in self.cmds if c]
                log.debug(self.cmds)
                self.action_thread = thread.start_new_thread(self.run_action_thread, (self.cmds, self.fail_ok))
                return str(template)
            else:
                return self.next()
            #print self.cmds

    progress.exposed = True

    #@trace
    def progress_update(self):
        """
            AJAX method to update progress screen. Called periodically...
        """
        #print "progress_update"
        output = ""
        while not self.queue.empty():
            output = ''.join([output, self.queue.get()])
            
        log.debug(output.strip())
        #print "update:", output.lstrip()
        return output.lstrip()

    progress_update.exposed = True

    #@trace
    def progress_status(self):
        """
            AJAX method to update progress screen. Returns an integer -1, 0, or >0
            -1 : Running
             0 : Finished with no error
             > 0 : Finished with error
        """
        #print "progress_status"
        self.action_lock.acquire()
        t = self.progress_status_code
        self.action_lock.release()
        t2 = utils.printable(str(t))
        #print "status: ", str(t2)
        return str(t2)

    progress_status.exposed = True


    def operation_number(self):
        self.action_lock.acquire()
        t = self.action
        self.action_lock.release()
        return str(t)

    operation_number.exposed = True

    def retry_progress(self):
        return self.progress(self.action)

    retry_progress.exposed = True


    def progress_cancel(self):
        """
            AJAX method to cancel current operation.
        """
        self.cancel_signaled = True
        return '' # TODO: Hook to install canceled page

    progress_cancel.exposed = True

    @trace
    def run_action_thread(self, cmds, fail_ok=False):
        """
            0 : Done, no error
            >0 : Done, with error
        """
        for cmd in cmds:
            self.queue.put(cmd)

            try:
                cmd(self.progress_callback)
            except TypeError:
                status, output = self.core.run(cmd, self.progress_callback)

                if status != 0:
                    self.action_lock.acquire()
                    
                    if fail_ok:
                        log.warn("Command '%s' failed. This is OK." % cmd)
                        self.progress_status_code = 0
                    else:
                        log.error("Command '%s' failed." % cmd)
                        self.progress_status_code = status
                        self.failed_cmd  = cmd
                    
                    self.action_lock.release()
                    return


        self.action_lock.acquire()
        self.progress_status_code = 0
        self.action_lock.release()

    @trace
    def run_core_init_thread(self):
        """
            run self.core.init() in a thread, report sucess at end
        """
        #self.queue.put("Init...\n")
        self.core.init(self.progress_callback)

        self.action_lock.acquire()
        self.progress_status_code = 0
        self.action_lock.release()

        if self.core.distro_known():
            log.debug("Distro is %s %s" % (self.core.get_distro_data('display_name'),
                self.core.distro_version))

    @trace
    def progress_callback(self, cmd='', desc=''):
        """
            Called by self.core.init() in a thread to collect output
        """
        log.debug("Progress callback: %s" % cmd)
        
        if desc:
            self.queue.put("%s (%s)" % (cmd, desc))
        else:
            self.queue.put(cmd)
            
        return self.cancel_signaled

    @trace
    def progress_controller(self):
        """
            Called at end if progress_status_code == 0
        """
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

    progress_controller.exposed = True

    @trace
    def error_command_failed(self):
        """
            Called at end if progress_status > 0
        """
        if self.fail_ok:
            return self.next()
        else:
            return self.error("Command '%s' failed with error code %d." %
                (self.failed_cmd, self.progress_status_code))

    error_command_failed.exposed = True


    #
    # INSTALLATION PATH
    #

    def installation_path(self):
        """
            Install path (not shown in auto mode)
        """
        screen = "installation_path"
        template = self.createTemplate(screen)


        # body and message inserts
        template.installation_path_message_title = self.localized_dict[screen + "_message_title"]

        template.installation_path_radio1 = self.localized_dict[screen + "_radio1"]
        template.installation_path_radio2 = self.localized_dict[screen + "_radio2"]

        template.installation_path_a = self.localized_dict[screen + "_a"]
        template.installation_path_b = self.localized_dict[screen + "_b"]
        template.installation_path_c = self.localized_dict[screen + "_c"]
        template.installation_path_d = self.localized_dict[screen + "_d"]
        template.installation_path_e = self.localized_dict[screen + "_e"]

        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]

        template.install_location = self.core.install_location
        return str(template)

    installation_path.exposed = True

    @trace
    def installation_path_controller(self, path):
        """
            installation_path_controller?path=<path>
        """
        #print "installation_path_controller"
        self.core.install_location = path
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        self.next = self.restart #finished
        return self.progress(ACTION_BUILD_AND_INSTALL)

    installation_path_controller.exposed = True

    #
    # PACKAGE CONFLICTS: HPOJ & HPLIP
    #

    def hpoj_remove(self):
        """
            Ask user if they want to uninstall HPOJ (not shown in auto mode)
        """
        screen = "hpoj_remove"
        template = self.createTemplate(screen)


        # body and message inserts
        template.hpoj_remove_message_body = self.localized_dict[screen + "_message_body"]

        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.no_button = self.localized_dict["no_button"]
        template.yes_button = self.localized_dict["yes_button"]

        return str(template)

    hpoj_remove.exposed = True

    def hpoj_remove_controller(self):
        self.next = self.dependency_controller9
        return self.progress(ACTION_REMOVE_HPOJ)

    hpoj_remove_controller.exposed = True

    def hplip_remove(self):
        """
            Ask user if they want to uninstall HPLIP (not shown in auto mode)
        """
        screen = "hplip_remove"
        template = self.createTemplate(screen)


        # body and message inserts
        template.hplip_remove_message_body = self.localized_dict[screen + "_message_body"]

        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.no_button = self.localized_dict["no_button"]
        template.yes_button = self.localized_dict["yes_button"]
        return str(template)

    hplip_remove.exposed = True

    def hplip_remove_controller(self):
        #print "hplip_remove_controller"
        self.next = self.dependency_controller8
        return self.progress(ACTION_REMOVE_HPLIP)

    hplip_remove_controller.exposed = True

    #
    # BUILD AND INSTALL
    #

    def ready_to_build(self):
        """
            Ask user to OK the start of the build (not shown in auto mode)
        """
        screen = "ready_to_build"
        template = self.createTemplate(screen)


        # body and message inserts
        template.ready_to_build_message_title = self.localized_dict[screen + "_message_title"]
        template.ready_to_build_radio1 = self.localized_dict[screen + "_radio1"]
        template.ready_to_build_radio2 = self.localized_dict[screen + "_radio2"]
        template.ready_to_build_message_footer = sub_string_replace(self.localized_dict[screen + "_message_footer"]) % {"version":self.core.distro_version}

        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        template.previous_button = self.localized_dict["previous_button"]
        template.next_button = self.localized_dict["next_button"]
        return str(template)

    ready_to_build.exposed = True

    def ready_to_build_controller(self):
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        return ''

    ready_to_build_controller.exposed = True

    def finished(self):
        """
            Display summary and results
        """
        screen = "finished"
        template = self.createTemplate(screen)


        # body and message inserts
        template.finished_message_title = self.localized_dict[screen + "_message_title"]
        template.finished_checkbox = self.localized_dict[screen + "_checkbox"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]
        return str(template)

    finished.exposed = True

    @trace
    def finished_controller(self, setup):
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()
        #print "finished_controller"
        self.core.run_hp_setup()
        return self.quit()
        
        #cherrypy::engine.stop
        #self.bus.stop()
        #self.bus.exit()

    finished_controller.exposed = True


    #
    # VARIOUS ERRORS
    #

    @trace
    def error(self, error_text):
        """
            Generic re-usable error page
        """
        screen = "error"
        template = self.createTemplate(screen)

        # body and message inserts
        template.error_message_title = self.localized_dict[screen + "_message_title"]
        template.error_message_body = error_text
        # button text inserts
        template.next_button = self.localized_dict["next_button"]

        return str(template)

    error.exposed = True

    def error_controller(self):
        raise SystemExit

    error_controller.exposed = True

    @trace
    def error_unsupported_distro(self):
        """
            Can only continue from here if all required dependencies are installed
        """

        screen = "error_unsupported_distro"
        template = self.createTemplate(screen)

        # body and message inserts
        template.error_unsupported_distro_message_title = self.localized_dict[screen + "_message_title"]
        template.error_unsupported_distro_message_footer = self.localized_dict[screen + "_message_footer"]
        # button text inserts
        template.quit_button = self.localized_dict["quit_button"]

        template.distro_version = self.core.distro_version
        template.distro_name = self.core.get_distro_data('display_name')

        template.missing_required_dependencies = {}
        for depend, desc, option in self.core.missing_required_dependencies():
            template.missing_required_dependencies[depend] = desc
            log.error("Missing REQUIRED dependency: %s (%s)" % (depend, desc))

        return str(template)

    error_unsupported_distro.exposed = True

    @trace
    def error_unsupported_distro_controller(self, cont):
        """
            error_unsupported_distro_controller?cont=0|1
            User can chose to continue even if unsupported, but might get tripped up
            if any required dependencies are missing.
        """
        if self.next is not None:
            self.next = None
            return self.next()

        return ''

    error_unsupported_distro_controller.exposed = True


    #
    # MISC
    #

    @trace
    def previous(self):
        self.popHistory()
        return (self.popHistory())()

    previous.exposed = True

    def test(self):

        screen = "test"
        template = self.createTemplate(screen)


        # Force reusable screens back to test when done
        self.next = self.test
        template.options = self.core.options
        template.components = self.core.components
        template.selected_component = self.core.selected_component
        template.dependencies = self.core.dependencies
        template.have_dependencies = self.core.have_dependencies
        template.selected_options = self.core.selected_options
        template.version_description = self.core.version_description
        template.version_public = self.core.version_public
        template.version_internal = self.core.version_internal
        #template.hpijs_version = self.core.hpijs_version
        template.bitness = self.core.bitness
        template.endian = self.core.endian
        template.distro = self.core.distro
        template.distro_name = self.core.distro_name
        template.distro_version = self.core.distro_version
        #template.hpijs_version = self.hpijs_version
        template.distro_version_supported = self.core.distro_version_supported
        template.install_location = self.core.install_location
        template.hpoj_present = self.core.hpoj_present
        template.hplip_present = self.core.hplip_present
        template.distro_known = self.core.distro_known()
        template.passwd = self.passwd
        template.auto_mode = self.auto_mode
        return str(template)

    test.exposed = True
    
    #
    # Code for reading the localized .ts files from the /data/localization
    #
    
    def user_specified_country(self):
        lang = None
        data = parse("installer/localization/gui_info.ts")
        
        countrys_code = data.getElementsByTagName("country")
        for country_code in countrys_code:
            lang = self.get_text(country_code.childNodes)
        
        #print self.core.language
        return lang
        
    user_specified_country.exposed = False


    def load_localization_file(self, path, lang):
        xmlfile = os.path.join(path, "gui_strings_%s.ts" % utils.validate_language(lang))
 
        try:
            #log.debug("XML Path: %s" % xmlfile)
            dom = parse(xmlfile) #.decode('utf-8')
            #strings = unicode(dom).decode('utf-8')
            
            #log.debug("DOM info: %s" % dom.toxml())
            
        except IOError:
            #log.debug("Location: error.html\n")
            sys.exit()
        return dom

    load_localization_file.exposed = True

    def get_text(self, nodelist):
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

    get_text.exposed = False

    def parse_elements(self, dom):
        messages = dom.getElementsByTagName("message")
        sources = dom.getElementsByTagName("tag")
        translations = dom.getElementsByTagName("translation")
        translation_list = []
        source_list = []

        for translation in translations:
            translation_list.append(self.get_text(translation.childNodes))
            #log.debug("Translation: %s" % translation_list.encode('ascii', 'replace'))

        for source in sources:
            source_list.append(self.get_text(source.childNodes))
            #log.debug("Translation Source: %s" % source_list.encode('ascii', 'replace'))

        self.localized_dict = dict(zip(source_list, translation_list))
        for key in self.localized_dict:
            log.debug( "Translation String Key: %s  Value: %s" % (key, unicode(self.localized_dict[key]).encode('ascii', 'replace') ) )

    parse_elements.exposed = True

    def localized_string(self, string):  #localized_string?string="Some english string"

        try:
            #log.debug("Utf8 encoded: %s" % string.encode('ascii', 'replace'))
            in_string = unicode(string).decode('utf-8')
        except IOError:
            #log.error("Decoding Error\n")
            sys.exit()
        try:
            #log.debug("Utf8 decoded:  %s" % in_string.encode('ascii', 'replace'))
            rstring = unicode(self.localized_dict.get(in_string, 'Localization load error'))
            #log.debug("Localized string:  %s" % rstring.encode('ascii', 'replace'))
            out_string = rstring.encode('utf-8')
            #log.debug("Out string::  %s" % out_string.encode('ascii', 'replace'))
        except IOError:
            #log.error("Encoding Error\n")
            sys.exit()

        return out_string

    localized_string.exposed = True

    #
    # Code for reading the localized .ts files from the /data/localization
    #



    #========================== End of Class =========================
socket_port = 8888
socket_host = '127.0.0.1'
socket_file = ''
socket_queue_size = 5
socket_timeout = 10
protocol_version = 'HTTP/1.0'
reverse_dns = False
thread_pool = 1
max_request_header_size = 500 * 1024
max_request_body_size = 100 * 1024 * 1024
instance = None
ssl_certificate = None
ssl_private_key = None

    
    

def init():
    log.info("Server ready.")
    utils.openURL("http://localhost:8888")

def start(language):
    cherrypy.root = Installer()
    
    check_port(socket_host, socket_port)
    
    cherrypy.root.parse_elements(cherrypy.root.load_localization_file(XMLPATH, language))

    current_dir = os.path.dirname(os.path.abspath(__file__))
    log.debug("The current path: %s" % current_dir)
    
    #cherrypy.response.headers['Content-Type']="text/html; charset=utf-8"

    cherrypy.config.update({
        'server.environment':'production',
        'server.socketHost': socket_host,
        'autoreload.on': False,
        'server.thread_pool': thread_pool,
        'log_debug_info_filter.on': False,
        'server.log_file_not_found': False,
        'server.show_tracebacks': False,
        'server.log_request_headers': False,
        'server.socket_port': socket_port,
        'server.socket_queue_size': socket_queue_size,
        'server.protocol_version': protocol_version,
        'server.log_to_screen': False,
        'server.log_file': 'hplip_log',
        'server.reverse_dns': False,

        '/': {
            'static_filter.on': True,
            'static_filter.dir': current_dir,},
        '/styles': {
            'static_filter.on': True,
            'static_filter.dir': os.path.join(current_dir, "styles")},
        '/scripts': {
            'static_filter.on': True,
            'static_filter.dir': os.path.join(current_dir, "scripts")},
        '/pages': {
            'static_filter.on': True,
            'static_filter.dir': os.path.join(current_dir, "pages")},
        '/images': {
            'static_filter.on': True,
            'static_filter.dir': os.path.join(current_dir, "images")},
        '/favicon.ico': {
            'static_filter.on': True,
            'static_filter.file': os.path.join(current_dir, "images", "favicon.ico")}
        })

    try:
        cherrypy.server.start_with_callback(init)
    except KeyboardInterrupt, exc:
        #print "<Ctrl-C> hit: shutting down HTTP servers"
        self.interrupt = exc
        self.stop()
        cherrypy.engine.stop()
    except SystemExit, exc:
        #print "SystemExit raised: shutting down HTTP servers"
        val = exc.args[0]
        if cmp(val, ACTION_TEXT_INSTALL) == 0:
            # need to handle the text installer request.
            import text_install
            log.debug("Starting terminal text installer...")
            text_install.start(language)
            return
        self.interrupt = exc
        self.stop()
        cherrypy.engine.stop()
        cherrypy.engine.exit()
        raise
    
    

def check_port(host, port):
    """Raise an error if the given port is not free on the given host."""
    if not host:
        host = 'localhost'
    port = int(port)

    # AF_INET or AF_INET6 socket
    # Get the correct address family for our host (allows IPv6 addresses)
    for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                  socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        s = None
        try:
            s = socket.socket(af, socktype, proto)
            # See http://groups.google.com/group/cherrypy-users/
            #        browse_frm/thread/bbfe5eb39c904fe0
            s.settimeout(1.0)
            s.connect((host, port))
            s.close()
            raise IOError("Port %s is in use on %s; perhaps the previous "
                          "httpserver did not shut down properly." %
                          (repr(port), repr(host)))
        except socket.error:
            if s:
                s.close()
