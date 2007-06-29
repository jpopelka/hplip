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
import pwd
import grp

# Local
import cherrypy
from base.g import *
from Cheetah.Template import Template
from base import utils, pexpect

import core
import distros
import dcheck

ACTION_INIT = 0 # core.init()
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


def sort_vers(x, y):
    #print("####>>>>sort")
    try:
        return cmp(float(x), float(y))
    except ValueError:
        return cmp(x, y)

def run(cmd, callback=None, passwd='', timeout=0.5):
    #print("####>>>>run")
    try:
        child = pexpect.spawn(cmd, timeout=timeout)
    except pexpect.ExceptionPexpect:
        return 1

    try:
        while True:
            update_spinner()
            i = child.expect(["[pP]assword:", pexpect.EOF, pexpect.TIMEOUT])
            #print "####>>>> i: ", i
            
            if child.before:
                log.log_to_file(child.before)
            
                if callback is not None:
                    if callback(child.before): # cancel
                        break

            if i == 0: # Password:
                child.sendline(passwd)

            elif i == 1: # EOF
                break

            elif i == 2: # TIMEOUT
                continue

    except Exception:
        pass

    cleanup_spinner()
    
    try: 
        child.close()
    except OSError:
        pass

    return child.exitstatus

def cat(package_mgr_cmd, packages_to_install):
    #print("####>>>>cat")
    return utils.cat(package_mgr_cmd)


class Installer(object):
    def __init__(self):
        #print("####>>>>__init__")
        self.history = []
        self.auto_mode = False # custom_mode = False, auto_mode = True
        self.passwd = ''
        self.next = None
        self.progress_status_code = -1
        self.action_lock = thread.allocate_lock() # lock to protect self.progress_status_code
        self.queue = Queue.Queue()
        self.pre_has_run = False
        self.post_has_run = False
        self.depends_to_install = []
        self.is_signal_stop = 0

        core.version_description, core.version_public, core.version_internal = \
            core.getHPLIPVersion()

    def popHistory(self):
        #print("####>>>>popHistory")
        #print "####self.history.pop(): >>>>", self.history.pop()
        return self.history.pop()

    def pushHistory(self, pg):
        #print("####>>>>pushHistory")
        #print "####>>>>self.history.append(pg): >>>>", self.history.append(pg)
        #print "####>>>>pg", pg
        self.history.append(pg)

    def createTemplate(self, name):
        #print("####>>>>createTemplate")
        #print "####>>>>createTemplate: >>>>", name
        template = Template(file="installer/pages/%s.tmpl" % name, \
            compilerSettings={'useStackFrames': False})

        template.title = "Title: %s" % name
        template.content = "<em>%s<em>" % name
        template.version = core.version_public
        return template

    def distroKnown(self):
        #print("####>>>>distroKnown")
        return core.distro != distros.DISTRO_UNKNOWN and core.distro_version != '0.0'

    #
    # INDEX (LAUNCHES MAIN INSTALLER PAGE WELCOME IN NEW WINDOW)
    #

    def quit(self): # No pushing or pop required.. for this screen
        #print("####>>>>quit")
        return str(self.createTemplate("quit"))

    quit.exposed = True

    def unsupported(self): # No pushing or pop required.. for this screen
        #print("####>>>>unsupported")
        return str(self.createTemplate("unsupported"))

    unsupported.exposed = True
    
    def unsupported_controller(self): # No pushing or pop required.. for this screen
        #print("####>>>>unsupported")
        return str(self.createTemplate("welcome"))

    unsupported_controller.exposed = True


    def index(self): # No pushing or pop required.. for this screen
        #print("####>>>>index")
        return str(self.createTemplate("index"))

    index.exposed = True

    def signal_stop(self): # Called by Quit to signal a stop
        #print("####>>>>signal_stop")
        self.is_signal_stop = 1

    signal_stop.exposed = True

    def signal_stopped(self): # Checked by index.html to see if we are stopping
        #print("####>>>>signal_stopped")
        return str(self.is_signal_stop)

    signal_stopped.exposed = True

    def stop(self): # Stop the CherryPy browser
        #print("####>>>>stop")
        raise SystemExit

    stop.exposed = True

    #
    # WELCOME
    #

    def welcome(self): 
        #print("####>>>>welcome")
        template = self.createTemplate("welcome")
        self.pushHistory(self.welcome)
        return str(template)

    welcome.exposed = True

    def welcome_controller(self):
        #print("####>>>>welcome_controller")
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if os.geteuid() == 0:
            return self.warning()
        else: 
            self.next = self.password
            return self.progress(ACTION_INIT)
            #<#>return self.password()

    welcome_controller.exposed = True
    

    #
    # PASSWORD
    #
    
    def password_callback(message):
        #print "####>>>>password_callback: ", message
        return False

    def set_password(self, passwd): # Collect root password from user - password?passwd=<passwd>
        #print("####>>>>set_password")
        rvalue = "Empty"

        if passwd:
            self.passwd = base64.decodestring(passwd)
            
            #print "####Password: ", self.passwd

            cmd = core.su_sudo() % "echo test"

            #print "####Cmd: ", cmd

            status = run(cmd, self.password_callback, self.passwd)

            rvalue = "Failed"

            if status == 0:
                rvalue = "True"

            #print "####>>>>self.passwd", self.passwd
            #print "####>>>>rvalue", rvalue
            #print "####>>>>status", status

        return rvalue

    set_password.exposed = True


    def password(self): # Collect root password from user
        #print("####>>>>password")
        self.pushHistory(self.password)
        return str(self.createTemplate("password"))

    password.exposed = True

    def password_controller(self): 
        #print("####>>>>password_controller")
        nxt = self.next
        #print "####password_controller"
        if nxt is not None:
            self.next = None
            return nxt()

        #return self.dependency_controller1()  # CHANGE - this need to reroute to <dependency_controller1>
        return self.mode()
        #return self.progress(ACTION_INIT)

    password_controller.exposed = True
    
    #
    # WARNING
    #

    def warning(self): 
        #print("####>>>>warning")
        template = self.createTemplate("warning")
        self.pushHistory(self.warning)
        return str(template)

    warning.exposed = True

    def warning_controller(self):
        #print("####>>>>warning_controller")
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        self.next = self.password
        return self.progress(ACTION_INIT)  # CHANGE - this need to reroute to <progress_init(0)>

    warning_controller.exposed = True
    

    #
    # MODE SELECTION
    #

    def mode(self): # Install Mode: Custom or Automatic
        #print("####>>>>mode")
        template = self.createTemplate("mode")
        self.pushHistory(self.mode)
        return str(template)

    mode.exposed = True

    def mode_controller(self, auto_mode): # mode_controller?auto_mode=0|1
        #print("####>>>>mode_controller")
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

    #
    # COMPONENT SELECTION
    #

    def component(self): # Install Component: HPLIP or HPIJS (not shown in auto mode)
        #print("####>>>>component")
        template = self.createTemplate("component")
        self.pushHistory(self.component)
        return str(template)

    component.exposed = True

    def component_controller(self, component): # component_controller?component=hplip|hpijs
        #print("####>>>>component_controller")
        core.selected_component = component.strip().lower()

        assert core.selected_component in core.components.keys()

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        return self.distro_controller()

    component_controller.exposed = True

    #
    # DISTRO AND DISTRO VERSION
    #

    def distro_controller(self): # Determine if distro confirm or select is to be shown
        #print("####>>>>distro_controller")
        if self.distroKnown():
            if self.auto_mode:
                return self.notes() # auto mode, skip ahead to notes
            else:
                return self.confirm_distro() # manual mode, confirm distro info
        else:
            # distro and version is not known, get it from user
            return self.select_distro()

    distro_controller.exposed = True

    def confirm_distro(self): # Correct Distro? (NOTE: Only display is distro && distro version is known)
        #print("####>>>>confirm_distro")
        template = self.createTemplate("confirm_distro")
        template.distro_version = core.distro_version
        #template.distro_name = core.distros[core.distro_name]['display_name']
        template.distro_name = core.get_distro_data('display_name')
        self.pushHistory(self.confirm_distro)
        return str(template)

    confirm_distro.exposed = True

    def confirm_distro_controller(self, confirmation): # confirm_distro_controller?confirmation=0|1
        #print("####>>>>confirm_distro_controller")
        confirmation = int(confirmation)
        assert confirmation in (0, 1)

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if confirmation:
            return self.notes()
        else:
            return self.select_distro()

    confirm_distro_controller.exposed = True

    def select_distro(self): # Choose Distro and Distro Version (only shown if distro and/or version not known || correct distro question answered "no")
        #print("####>>>>select_distro")
        template = self.createTemplate("select_distro")
        self.pushHistory(self.select_distro)
        template.distro_version = core.distro_version
        template.distro_name = core.distro_name
        template.distros = {}
        template.distro = core.distro

        for d in core.distros_index:
            dd = core.distros[core.distros_index[d]]

            if dd['display']:
                template.distros[d] = dd['display_name']

        return str(template)

    select_distro.exposed = True

    def select_distro_update_combo(self, index): # AJAX method to update distro version combo box
        #print("####>>>>select_distro_update_combo")
        core.distro = int(index)
        core.distro_name = core.distros_index[core.distro]
        versions = core.distros[core.distro_name]['versions'].keys()
        versions.sort(lambda x, y: sort_vers(x, y))
        return ' '.join(versions)

    select_distro_update_combo.exposed = True

    def select_distro_controller(self, distro, version): # select_distro_controller?distro=0&version=0.0
        #print("####>>>>select_distro_controller")
        core.distro = int(distro)
        core.distro_version = version

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if not  self.distroKnown():
            self.check_required()

            if self.num_req_missing:
                return self.error_unsupported_distro() # still unknown and missing req. deps, bail out
            else:
                return self.notes() # unsupported, but no required missing, so continue
        else:
            return self.notes() # ok, move ahead to notes

    select_distro_controller.exposed = True

    #
    # NOTES
    #

    def notes(self): # Installation Notes (distro specific)
        #print("####>>>>notes")
        self.pushHistory(self.notes)
        template = self.createTemplate("notes")

        distro_notes = core.get_distro_data('notes', '')
        #try:
        #    distro_notes = core.distros[core.distro_name]['notes']
        #except KeyError:
        #    distro_notes = ''

        ver_notes = core.get_ver_data('notes', '')
        #try:
        #    ver_notes = core.distros[core.distro_name]['versions'][core.distro_version]['notes']
        #except KeyError:
        #    ver_notes = ''

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
        #print("####>>>>notes_controller")
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        if self.auto_mode:
            self.required_components_to_install()
            self.optional_components_to_install()
            #return self.password()        # CHANGE - this need to reroute to <password()>
            return self.dependency_controller1()
        else:
            return self.options()

    notes_controller.exposed = True

    #
    # INSTALLATION OPTIONS
    #

    def options(self): # Build Options (not shown in auto mode)
        #print("####>>>>options")
        template = self.createTemplate("options")
        template.options = core.options
        template.components = core.components
        template.selected_component = core.selected_component
        return str(template)

    options.exposed = True

    def options_controller(self, **options): # options_controller?opt=0|1&opt=0|1&...
        #print("####>>>>options_controller")
        for opt in options:
            #print("####>>>>options_controller>>>>options: ", opt)
            assert options[opt] in ('0', '1')
            assert opt in core.selected_options
            core.selected_options[opt] = int(options[opt])

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        #return self.password()    # CHANGE - this need to reroute to <password()>
        return self.dependency_controller1()

    options_controller.exposed = True

    #
    # PACKAGE MANAGER
    #

    def error_package_manager(self, pkg_mgr=''): # A package manager is running, prompt for closure
        #print("####>>>>error_package_manager")
        template = self.createTemplate("error_package_manager")
        template.package_manager_name = pkg_mgr
        return str(template)

    error_package_manager.exposed = True

    def error_package_manager_controller(self):
        #print("####>>>>error_package_manager_controller")
        pkg_mgr = core.check_pkg_mgr()
        if pkg_mgr:
            return self.error_package_manager(pkg_mgr)
        else:
            return self.next()

    error_package_manager_controller.exposed = True

    def package_manager_check(self): # AJAX call
        #print("####>>>>package_manager_check")
        return str(int(core.check_pkg_mgr()())) # returns '' for no running pkg manager, or '<name>' of running package manager

    package_manager_check.exposed = True


    #
    # DEPENDENCIES
    #

    def dependency_controller1(self):
        #print("####>>>>dependency_controller1")
        self.check_required()
        self.check_optional()

        if self.distroKnown():
            if self.num_req_missing:
                if self.auto_mode: # auto, distro known, req. missing
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
        #print("####>>>>dependency_controller2")
        if self.distroKnown():
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
        #print("####>>>>dependency_controller3")
        core.hpoj_present = dcheck.check_hpoj()
        if core.hpoj_present and core.selected_component == 'hplip' and \
            core.distro_version_supported:

            if self.auto_mode:
                return self.hpoj_remove_controller()
            else:
                return self.hpoj_remove()
        else:
            return self.dependency_controller9()

    def dependency_controller4(self):
        #print("####>>>>dependency_controller4")
        self.next = self.dependency_controller7
        return self.progress(ACTION_INSTALL_REQUIRED)

    def dependency_controller5(self):
        #print("####>>>>dependency_controller5")
        self.next = self.dependency_controller3
        return self.progress(ACTION_INSTALL_OPTIONAL)

    def dependency_controller6(self):
        #print("####>>>>dependency_controller6")
        #if self.post_has_run:
        #    return self.dependency_controller3()
        #else:
        self.next = self.dependency_controller3
        return self.progress(ACTION_POST_DEPENDENCY)

    def dependency_controller7(self):
        #print("####>>>>dependency_controller7")
        #self.next = self.dependency_controller2
        return self.dependency_controller2()
        #return self.progress(ACTION_POST_DEPENDENCY)

    def dependency_controller8(self):
        #print("####>>>>dependency_controller8")
        #if self.auto_mode:  ## commented out to bpass installation path screen
        self.next = self.finished
        return self.progress(ACTION_BUILD_AND_INSTALL)
        #else: ## commented out to bpass installation path screen
        #    return self.installation_path()  ## commented out to bpass installation path screen

    def dependency_controller9(self):
        #print("####>>>>dependency_controller10")
        core.hplip_present = dcheck.check_hplip()
        if core.hplip_present and core.selected_component == 'hplip' and \
            core.distro_version_supported:

            if self.auto_mode:
                return self.hplip_remove_controller()
            else:
                return self.hplip_remove()
        else:
            return self.dependency_controller8()
            
    #       
    # Network Ping test to verify if network access is available.
    #
    def network_unavailable(self):
        #print("####>>>>network_unavailable")
        template = self.createTemplate("network_unavailable")
        self.pushHistory(self.network_unavailable)
        return str(template)
    
    network_unavailable.exposed = True
    
    
    def network_unavailable_controller(self):
        pkg_mgr = core.check_pkg_mgr()
        
        if self.network_ping() != 0:
            #print "####>>>>network unavailable"
            return self.network_unavailable()
        else:
            if pkg_mgr:
                self.next = self.install_required_controller()
                return self.error_package_manager(pkg_mgr)
            else:
                self.next = self.dependency_controller4
                return self.progress(ACTION_PRE_DEPENDENCY)
    
    network_unavailable_controller.exposed = True
    
    #
    # CHECK FOR ACTIVE NETWORK CONNECTION
    #
    def network_ping(self):
        status = 0
        ping = utils.which("ping")

        if ping:
           ping = os.path.join(ping, "ping")
           status = run(ping + " -c3 sf.net", self.ping_callback, self.passwd, 2.0)
        #print "####>>>> Status: ", status
        return status 
        
        
        
    #
    # callback for network_ping
    #
    def ping_callback(message):
        #print "####>>>>ping_callback: ", message
        return False

    #
    # Various installer checks
    #
    def check_required(self):
        #print("####>>>>check_required")
        self.num_req_missing = 0
        # required core.options
        for opt in core.components[core.selected_component][1]:
            if core.options[opt][0]: # required core.options
                for d in core.options[opt][2]: # dependencies for option
                    if not core.have_dependencies[d]: # missing
                        self.num_req_missing += 1

    def check_optional(self):
        #print("####>>>>check_optional")
        self.num_opt_missing = 0
        # optional core.options
        for opt in core.components[core.selected_component][1]:
            if not core.options[opt][0]: # optional core.options
                for d in core.options[opt][2]: # dependencies for option
                    if not core.have_dependencies[d]: # missing
                        self.num_opt_missing += 1



    def install_required(self): # Ask user if they want to try to install required dependencies (not shown in auto mode)
        #print("####>>>>install_required")
        template = self.createTemplate("install_required")
        template.missing_required_dependencies = {}
        for opt in core.components[core.selected_component][1]:
            if core.options[opt][0]: # required options
                for d in core.options[opt][2]: # dependencies for option
                    if not core.have_dependencies[d]: # missing
                        log.error("Missing REQUIRED dependency: %s (%s)" % (d, core.dependencies[d][2]))
                        template.missing_required_dependencies[d] = core.dependencies[d][2]
                        self.depends_to_install.append(d)

        return str(template)

    install_required.exposed = True
    
    def required_components_to_install(self):
        for opt in core.components[core.selected_component][1]:
            if core.options[opt][0]: # required options
                for d in core.options[opt][2]: # dependencies for option
                    if not core.have_dependencies[d]: # missing
                        log.error("Missing REQUIRED dependency: %s (%s)" % (d, core.dependencies[d][2]))
                        #template.missing_required_dependencies[d] = core.dependencies[d][2]
                        self.depends_to_install.append(d)
                        
    def optional_components_to_install(self):
        for opt in core.components[core.selected_component][1]:
             if not core.options[opt][0]: # not required
                 if core.selected_options[opt]: # only for options that are ON
                     for d in core.options[opt][2]: # dependencies
                         if not core.have_dependencies[d]: # missing dependency
                             if core.dependencies[d][0]: # dependency is required for this option
                                 log.warning("Missing OPTIONAL dependency: %s (%s) [Required for option '%s']" % (d, core.dependencies[d][2], core.options[opt][1]))
                                 self.depends_to_install.append(d)
                             else:
                                 log.warning("Missing OPTIONAL dependency: %s (%s) [Optional for option '%s']" % (d, core.dependencies[d][2], core.options[opt][1]))
                                 self.depends_to_install.append(d)

    def install_required_controller(self): # install_required_controller
        #print("####>>>>install_required_controller")
        pkg_mgr = core.check_pkg_mgr()
        #print "####>>>>install_required_controller:pkg_mgr: ", pkg_mgr
        if self.network_ping() != 0:
            #print "####>>>>network unavailable"
            return self.network_unavailable()
            
        if pkg_mgr:
            self.next = self.install_required_controller()
            return self.error_package_manager(pkg_mgr)
        else:
            self.next = self.dependency_controller4
            return self.progress(ACTION_PRE_DEPENDENCY)

    install_required_controller.exposed = True

    def install_optional(self): # Ask user if they want to try to install optional dependencies (not shown in auto mode)
        #print("####>>>>install_optional")
        self.depends_to_install = []
        template = self.createTemplate("install_optional")
        template.missing_optional_dependencies = {}
        #self.optional_components_to_install()
        for opt in core.components[core.selected_component][1]:
             if not core.options[opt][0]: # not required
                 if core.selected_options[opt]: # only for options that are ON
                     for d in core.options[opt][2]: # dependencies
                        if not core.have_dependencies[d]: # missing dependency
                             if core.dependencies[d][0]: # dependency is required for this option
                                 log.warning("Missing OPTIONAL dependency: %s (%s) [Required for option '%s']" % (d, core.dependencies[d][2], core.options[opt][1]))
                                 template.missing_optional_dependencies[d] = core.dependencies[d][2]
                                 self.depends_to_install.append(d)
                             else:
                                 log.warning("Missing OPTIONAL dependency: %s (%s) [Optional for option '%s']" % (d, core.dependencies[d][2], core.options[opt][1]))
                                 template.missing_optional_dependencies[d] = core.dependencies[d][2]
                                 self.depends_to_install.append(d)
        return str(template)

    install_optional.exposed = True

    def install_optional_controller(self):
        #print("####>>>>install_optional_controller")
        pkg_mgr = core.check_pkg_mgr()
        #print "####>>>>pkg_mgr", pkg_mgr
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

    def turn_off_options(self): # Inform the user that some options have been turned off because of missing optional dependencies
        #print("####>>>>turn_off_options")
        template = self.createTemplate("turn_off_options")
        template.turned_off_options = {}

        self.depends_to_install = []
        for opt in core.components[core.selected_component][1]:
            if not core.options[opt][0]: # not required
                if core.selected_options[opt]: # only for options that are ON
                    for d in core.options[opt][2]: # dependencies
                        if not core.have_dependencies[d]: # missing dependency
                            if core.dependencies[d][0]: # dependency is required for this option
                                log.warning("Missing OPTIONAL dependency: %s (%s) [Required for option '%s']" % (d, core.dependencies[d][2], core.options[opt][1]))
                                template.turned_off_options[opt] = core.options[opt][1]
                                core.selected_options[opt] = False
                            else:
                                self.depends_to_install.append(d)

        return str(template)

    turn_off_options.exposed = True

    def turn_off_options_controller(self):
        #print("####>>>>turn_off_options_controller")
        return self.dependency_controller3()

    turn_off_options_controller.exposed = True

    def error_required_missing(self): # A required dependency is missing, can't continue
        #print("####>>>>error_required_missing")
        template = self.createTemplate("error_required_missing")
        template.missing_required_dependencies = {}
        for opt in core.components[core.selected_component][1]:
            if core.options[opt][0]: # required options
                for d in core.options[opt][2]: # dependencies for option
                    if not core.have_dependencies[d]: # missing
                        log.error("Missing REQUIRED dependency: %s (%s)" % (d, core.dependencies[d][2]))
                        template.missing_required_dependencies[d] = core.dependencies[d][2]

        return str(template) #self.error("One or more required dependencies are missing and cannot be installed. This installer will exit.")

    error_required_missing.exposed = True

    #def error_required_missing_controller(self):
        # TODO: How to close browser window?
    #    raise SystemExit

    #
    # PROGRESS
    #

    # Reusable progress screen
    
    def progress(self, action): # progress?action=0|1|2|3|4|5|6|7|8
        #print("####>>>>progress")
        self.action = int(action)
        assert action in range(ACTION_MAX)
        template = self.createTemplate("progress")
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

                package_mgr_cmd = core.get_distro_data('package_mgr_cmd', '')
                #try:
                #    package_mgr_cmd = core.distros[core.distro_name]['package_mgr_cmd']
                #except KeyError:
                #    package_mgr_cmd = ''

                for d in self.depends_to_install:
                    log.debug("*** Processing dependency: %s" % d)
                    #package, command = core.distros[core.distro_name]['versions'][core.distro_version]['dependency_cmds'][d]
                    package, command = core.get_ver_data('dependency_cmds', {}).get(d, ('', ''))

                    if package:
                        log.debug("Package '%s' will be installed to satisfy dependency '%s'." % (package, d))
                        packages_to_install.append(package)

                    if command:
                        log.debug("Command '%s' will be run to satisfy dependency '%s'." % (command, d))
                        if type(command) == type(""):
                            commands_to_run.append(command)
                        
                        elif type(command) == type([]):
                            commands_to_run.extend(command)
                            
                        else:
                            pass

                self.cmds.append(cat(package_mgr_cmd, ' '.join(packages_to_install)))
                self.cmds.extend(commands_to_run)

            elif self.action == ACTION_PRE_DEPENDENCY: # 3
                self.pre_has_run = True
                #try:
                    #self.cmds.extend(core.distros[core.distro_name]['versions'][core.distro_version]['pre_depend_cmd'] or core.distros[core.distro_name]['pre_depend_cmd'])
                #except KeyError:
                #    pass
                self.cmds.extend(core.get_distro_ver_data('pre_depend_cmd'))

                self.fail_ok = True

            elif self.action == ACTION_POST_DEPENDENCY: # 4
                self.post_has_run = True
                #print "####>>>>Action here: ", self.action
                #try:
                    #print "####>>>>Action 4: ", core.distros[core.distro_name]['versions'][core.distro_version]['post_depend_cmd']
                    #print "####>>>>Sction 4:2: ", core.distros[core.distro_name]['post_depend_cmd']
                #    self.cmds.extend(core.distros[core.distro_name]['versions'][core.distro_version]['post_depend_cmd'] or core.distros[core.distro_name]['post_depend_cmd'])
                #except KeyError:
                    #print "####>>>>Action 4:", KeyError
                #    pass
                self.cmds.extend(core.get_distro_ver_data('post_depend_cmd'))

                self.fail_ok = True

            elif self.action == ACTION_BUILD_AND_INSTALL: # 5  Do I want to combile pre_build and post_build?
                self.cmds.extend(self.action_pre_build())
                enable_ppds = core.ppd_install_flag()
                log.debug("Enable PPD install: %s" % enable_ppds)
                ppd_dir = core.get_distro_ver_data('ppd_dir')
                log.debug("PPD dir=%s" % ppd_dir)
                self.cmds = core.build_cmds(enable_ppds, core.selected_component == 'hpijs', ppd_dir)
                self.cmds.extend(self.action_post_build())
                #print "####core.build_cmds() ", self.cmds
                #else:
                    #self.cmds = core.hpijs_build_cmds()
                    #print "####>>>>core.hpijs_build_cmds() ", self.cmds

            elif self.action == ACTION_REMOVE_HPOJ: # 6
                #self.cmds.append(core.distros[core.distro_name]['hpoj_remove_cmd'])
                self.cmds.append(core.get_distro_data('hpoj_remove_cmd', ''))
                self.fail_ok = True

            elif self.action == ACTION_REMOVE_HPLIP: # 7
                self.cmds.append(core.stop_hplip())
                #self.cmds.append(core.distros[core.distro_name]['hplip_remove_cmd'])
                self.cmds.append(core.get_distro_data('hplip_remove_cmd', ''))
                self.fail_ok = True
            #else:
                #print "###ACTION_REMOVE_HPLIP: ", self.action
                
            if self.cmds:
                self.cmds = [c for c in self.cmds if c]
                log.debug(self.cmds)
                self.action_thread = thread.start_new_thread(self.run_action_thread, (self.cmds,))
                return str(template)
            else:
                return self.next()

    progress.exposed = True
    
    def action_pre_build(self):
        cmds = []
        # Remove the link /usr/share/foomatic/db/source/PPD if the symlink is corrupt (Dapper only?)
        if core.get_distro_ver_data('fix_ppd_symlink', False):
          log.debug("Fixing PPD symlink...")
          cmd = core.su_sudo() % 'python ./installer/fix_symlink.py'
          log.debug("Running symlink fix utility: %s" % cmd)
          cmds.append(cmd)
        return cmds


    def action_post_build(self):
        cmds = []
        logoff_required = False
        log.debug("Checking for 'lp' group membership...")

        all_groups = grp.getgrall()
        for g in all_groups:
            name, pw, gid, members = g
            log.debug("group=%s gid=%d" % (name, gid))

        users = {}
        for p in pwd.getpwall():
            user, pw, uid, gid, name, home, ci = p
            log.debug("user=%s uid=%d gid=%d" % (user, uid, gid))

            if 1000 <= uid <= 10000:
                log.debug("Checking user %s..." % user)
                grps = []

                for g in all_groups:
                    grp_name, pw, gid, members = g
                    if user in members:
                        grps.append(grp_name)

                log.debug("Member of groups: %s" % ', '.join(grps))
                users[user] = ('lp' in grps)

        user_list = users.keys()
        log.debug("User list: %s" % ','.join(user_list))

        if len(user_list) == 1 and users[user_list[0]]:
            log.debug("1 user (%s) and in 'lp' group. No action needed." % users[user_list[0]])
            log.info("OK")

        elif len(user_list) == 1 and not users[user_list[0]]:
            log.debug("1 user (%s) and NOT in 'lp' group. Adding user to 'lp' group..." % user_list[0])
            log.debug("Adding user '%s' to 'lp' group..." % user_list[0])
            cmd = "usermod -a -Glp %s" % user_list[0]
            cmd = core.su_sudo() % cmd
            log.debug("Running: %s" % cmd)
            #status, output = run(cmd, True, password_func)
            cmds.append(cmd)
            logoff_required = True

        else:
            #log.info("In order for USB I/O to function, each user that will access the device")
            #log.info("must be a member of the 'lp' group:" )
            for u in users:
                if not users[u]:
                    #answer = enter_yes_no("\nWould you like to add user '%s' to the 'lp' group (y=yes*, n=no, q=quit)?", default="y")
                    answer = True
                    if answer:
                        log.debug("Adding user '%s' to 'lp' group..." % u)
                        cmd = "usermod -a -Glp %s" % u
                        cmd = core.su_sudo() % cmd
                        log.debug("Running: %s" % cmd)
                        #status, output = run(cmd, True, password_func)
                        cmds.append(cmd)

                        #if u == prop.username:
            logoff_required = True

        # Fix any udev device nodes that aren't 066x

        udev_mode_fix = core.get_distro_ver_data('udev_mode_fix', False)
        if udev_mode_fix:
            #log.info("")
            log.debug("Fixing USB device permissions...")
            cmd = core.su_sudo() % 'python ./installer/permissions.py'
            log.debug("Running USB permissions utility: %s" % cmd)
            #status, output = run(cmd, True, password_func)
            cmds.append(cmd)

            # Trigger USB devices so that the new mode will take effect 

            log.debug("Triggering USB devices...")
            cmd = core.su_sudo() % 'python ./installer/trigger.py'
            log.debug("Running USB trigger utility: %s" % cmd)
            #status, output = run(cmd, True, password_func)
            cmds.append(cmd)

        if core.cups11:
            #log.info("")
            log.debug("Restarting CUPS...")
            #status, output = run(core.restart_cups(), True, password_func)
            cmds.append(core.restart_cups())

            #if status != 0:
            #    log.warn("CUPS restart failed.")
            #else:
            #    log.info("Command completed successfully.")

        # Kill any running hpssd.py instance from a previous install
        #log.info("")
        log.debug("Checking for running hpssd...")
        if dcheck.check_hpssd():
            pid = dcheck.get_ps_pid('hpssd')
            try:
                log.debug("Killing the running 'hpssd' process...")
                os.kill(pid, 9)
            except OSError:
                pass
            else:
                log.debug("OK")
        else:
            log.debug("Not running (OK).")

        return cmds
    

    def progress_update(self): # AJAX method to update progress screen. Called periodically...
        ##print("####>>>>progress_update")
        output = ""
        while not self.queue.empty():
            output = ''.join([output, self.queue.get()])
        return output.lstrip()

    progress_update.exposed = True

    def progress_status(self): # AJAX method to update progress screen. Returns an ineteger -1, 0, or >0
        ##print("####>>>>progress_status")
        self.action_lock.acquire()
        t = self.progress_status_code
        self.action_lock.release()
        #print "####>>>>progress_status code:", t
        t2 = utils.printable(str(t))
        return str(t2)

    progress_status.exposed = True
    
    
    def operation_number(self):
        #print("####>>>>operation_number")
        self.action_lock.acquire()
        t = self.action
        self.action_lock.release()
        #print "####>>>>operation_number code:", t
        return str(t)

    operation_number.exposed = True
    
    def retry_progress(self):
        #print("####>>>>retry_progress")
        return self.progress(self.action)

    retry_progress.exposed = True
        

    def progress_cancel(self): # AJAX method to cancel current operation.
        #print("####>>>>progress_cancel")
        self.cancel_signaled = True
        return '' # TODO: Hook to install canceled page

    progress_cancel.exposed = True

    def run_action_thread(self, cmds):
        #print("####>>>>run_action_thread")
        # 0 : Done, no error
        # >0 : Done, with error
        for cmd in cmds:
            self.queue.put(cmd)
            status = run(cmd, callback=self.progress_callback, passwd=self.passwd, timeout=0.5)

            if status != 0:
                self.action_lock.acquire()
                self.progress_status_code = status
                self.action_lock.release()
                break

        self.action_lock.acquire()
        self.progress_status_code = 0
        self.action_lock.release()

    def run_core_init_thread(self): # run core.init() in a thread, report sucess at end
        #print("####>>>>run_core_init_thread")
        core.init(self.progress_callback)
        self.action_lock.acquire()
        self.progress_status_code = 0
        self.action_lock.release()

        if self.distroKnown():
            log.debug("Distro is %s %s" % (core.get_distro_data('display_name'), core.distro_version))

    def progress_callback(self, output): # Called by core.init() in a thread to collect output
        #print("####>>>>progress_callback")
        self.queue.put(output)
        return self.cancel_signaled

    def progress_controller(self): # Called at end if progress_status_code == 0
        #print("####>>>>progress_controller")
        nxt = self.next
        #print "####Progress_controller: ", nxt
        if nxt is not None:
            self.next = None
            return nxt()

    progress_controller.exposed = True

    def error_command_failed(self): # Called at end if progress_status > 0
        #print("####>>>>error_command_failed")
        if self.fail_ok:
            return self.next()
        else:
            return self.error("Command '%s' failed with error code %d." % (self.cmds, self.progress_status_code))

    error_command_failed.exposed = True


    #
    # INSTALLATION PATH
    #

    def installation_path(self): # Install path (not shown in auto mode)
        #print("####>>>>installation_path")
        template = self.createTemplate("installation_path")
        template.install_location = core.install_location
        #print "####>>>>installation_path::core.install_location: >>>>> ", template.install_location
        return str(template)

    installation_path.exposed = True

    def installation_path_controller(self, path): # installation_path_controller?path=<path>
        #print("####>>>>installation_path_controller")
        core.install_location = path

        #assert os.path.exists(path)
        #print "####>>>>installation_path_controller::core.install_location: >>>>> ", core.install_location

        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        #self.next = self.finished
        #TODO: this determines where I need to 
        # if sudo is found then self.nxt=self.finished else self.next = self.quit

        #print "####>>>>path: ", path
        #su_sudo = ""
        #if utils.which('kdesu'):
        #    su_sudo = 'kdesu -- "%s"'

        #elif utils.which('gksu'):
        #    su_sudo = 'gksu "%s"'

        #if su_sudo:
        #    self.next = self.finished 
        #else: 
        #    self.next = self.quit

        self.next = self.finished
        return self.progress(ACTION_BUILD_AND_INSTALL)

    installation_path_controller.exposed = True

    #
    # PACKAGE CONFLICTS: HPOJ & HPLIP
    #

    def hpoj_remove(self): # Ask user if they want to uninstall HPOJ (not shown in auto mode)
        #print("####>>>>hpoj_remove")
        template = self.createTemplate("hpoj_remove")
        return str(template)

    hpoj_remove.exposed = True

    def hpoj_remove_controller(self):
        #print("####>>>>hpoj_remove_controller")
        self.next = self.dependency_controller9
        return self.progress(ACTION_REMOVE_HPOJ)

    hpoj_remove_controller.exposed = True

    def hplip_remove(self): # Ask user if they want to uninstall HPLIP (not shown in auto mode)
        #print("####>>>>hplip_remove")
        template = self.createTemplate("hplip_remove")
        return str(template)

    hplip_remove.exposed = True

    def hplip_remove_controller(self):
        #print("####>>>>hplip_remove_controller")
        self.next = self.dependency_controller8
        return self.progress(ACTION_REMOVE_HPLIP)

    hplip_remove_controller.exposed = True

    #
    # BUILD AND INSTALL
    #

    def ready_to_build(self): # Ask user to OK the start of the build (not shown in auto mode)
        #print("####>>>>ready_to_build")
        template = self.createTemplate("ready_to_build")
        return str(template)

    ready_to_build.exposed = True

    def ready_to_build_controller(self):
        #print("####>>>>ready_to_build_controller")
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        return ''

    ready_to_build_controller.exposed = True

    def finished(self): # Display summary and results
        #print("####>>>>finished")
        template = self.createTemplate("finished")
        return str(template)

    finished.exposed = True

    def finished_controller(self, setup):
        #print("####>>>>finished_controller")
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        #TODO: this determines where I need to
        setup = int(setup)
        if setup == 1: 
            su_sudo = ""
            if utils.which('kdesu'):
                su_sudo = 'kdesu -- "%s"'

            elif utils.which('gksu'):
                su_sudo = 'gksu "%s"'

            if not su_sudo:
                # What should I do if this is
                # I think we should go to the return to quit for now...
                return self.quit()
            else:
                if utils.which('hp-setup'):
                    c = 'hp-setup -u --username=%s' % prop.username
                    cmd = su_sudo % c
                else:
                    c = 'python ./setup.py -u --username=%s' % prop.username
                    cmd = su_sudo % c

                log.debug(cmd)
                status, output = utils.run(cmd, log_output=True, password_func=None, timeout=1)

        return self.quit()

    finished_controller.exposed = True


    #
    # VARIOUS ERRORS
    #

    def error(self, error_text): # Generic re-usable error page
        #print("####>>>>error")
        template = self.createTemplate("error")
        template.error_text = error_text
        return str(template)

    error.exposed = True

    def error_controller(self):
        #print("####>>>>error_controller")
        raise SystemExit

    error_controller.exposed = True

    def error_unsupported_distro(self): # Can only continue from here if all required dependencies are installed
        #print("####>>>>error_unsupported_distro")
        template = self.createTemplate("error_unsupported_distro")
        template.distro_version = core.distro_version
        template.distro_name = core.get_distro_data('display_name') #core.distro_name

        template.missing_required_dependencies = {}
        for opt in core.components[core.selected_component][1]:
            if core.options[opt][0]: # required options
                for d in core.options[opt][2]: # dependencies for option
                    if not core.have_dependencies[d]: # missing
                        log.error("Missing REQUIRED dependency: %s (%s)" % (d, core.dependencies[d][2]))
                        template.missing_required_dependencies[d] = core.dependencies[d][2]
                        #self.depends_to_install.append(d)

        return str(template)

    error_unsupported_distro.exposed = True

    def error_unsupported_distro_controller(self, cont): # error_unsupported_distro_controller?cont=0|1
        #print("####>>>>error_unsupported_distro_controller")
        # User can chose to continue even if unsupported, but might get tripped up
        # if any required dependencies are missing.
        if self.next is not None:
            self.next = None
            return self.next()

        return ''

    error_unsupported_distro_controller.exposed = True


    #
    # MISC
    #


    def previous(self):
        #print("####>>>>previous")
        self.popHistory()
        return (self.popHistory())()

    previous.exposed = True

    def test(self):
        #print("####>>>>test")
        # Force reusable screens back to test when done
        self.next = self.test
        template = self.createTemplate("test")
        template.options = core.options
        template.components = core.components
        template.selected_component = core.selected_component
        template.dependencies = core.dependencies
        template.have_dependencies = core.have_dependencies
        template.selected_options = core.selected_options
        template.version_description = core.version_description
        template.version_public = core.version_public
        template.version_internal = core.version_internal
        template.bitness = core.bitness
        template.endian = core.endian
        #template.hpijs_version = core.hpijs_version  # Per Don's new format
        #template.hpijs_version_description = core.hpijs_version_description
        template.distro = core.distro
        template.distro_name = core.distro_name
        template.distro_version = core.distro_version
        template.distro_version_supported = core.distro_version_supported
        template.install_location = core.install_location
        template.hpoj_present = core.hpoj_present
        template.hplip_present = core.hplip_present
        template.distro_known = self.distroKnown()
        template.passwd = self.passwd
        template.auto_mode = self.auto_mode
        return str(template)

    test.exposed = True



    #========================== End of Class =========================

def init():
    #print("####>>>>init")
    log.info("Server ready.")
    utils.openURL("http://localhost:8080")

def start():
    #print("####>>>>start")
    cherrypy.root = Installer()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    log.debug("The current path: %s" % current_dir)

    cherrypy.config.update({
        'server.environment':'production',
        'server.socketHost':'127.0.0.1',
        'autoreload.on': False,
        'server.thread_pool': 1,
        'log_debug_info_filter.on': False,
        'server.log_file_not_found': False,
        'server.show_tracebacks': False,
        'server.log_request_headers': False,
        'server.socket_port': 8080,
        'server.socket_queue_size': 5,
        'server.protocol_version': 'HTTP/1.0',
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

    cherrypy.server.start_with_callback(init)


