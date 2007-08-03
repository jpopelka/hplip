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

# Local
import cherrypy
from base.g import *
from Cheetah.Template import Template
from base import utils
from core_install import *
from base import utils, pexpect
from xml.dom.minidom import parse, parseString

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

XMLFILE = 'data/localization/hplip_zh.ts'

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
        template = Template(file="installer/pages/%s.tmpl" % name, \
            compilerSettings={'useStackFrames': False})

        template.title = "Title: %s" % name
        template.content = "<em>%s<em>" % name
        template.version = self.core.version_public
        return template

    #
    # INDEX (LAUNCHES MAIN INSTALLER PAGE WELCOME IN NEW WINDOW)
    #

    def quit(self): 
        return str(self.createTemplate("quit"))

    quit.exposed = True

    def unsupported(self):
        return str(self.createTemplate("unsupported"))

    unsupported.exposed = True

    def unsupported_controller(self):
        return str(self.createTemplate("welcome"))

    unsupported_controller.exposed = True


    def index(self):
        return str(self.createTemplate("index"))

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

    def stop(self): 
        """
            Stop the CherryPy browser
        """
        raise SystemExit

    stop.exposed = True

    #
    # WELCOME
    #

    def welcome(self): 
        template = self.createTemplate("welcome")
        template.installer_title = "HELLO"
        template.welcome_message_title = "HELLO1"
        template.welcome_message_body = "HELLO2"
        template.quit_button = "HELLO3"
        template.next_button = "HELLO4"
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
            self.next = self.password
            return self.progress(ACTION_INIT)

    welcome_controller.exposed = True


    #
    # PASSWORD
    #

    def password(self): 
        """
            Collect root password from user
        """
        self.pushHistory(self.password)
        return str(self.createTemplate("password"))

    password.exposed = True

    def password_callback(self):
        return self.core.password

    def password_check_callback(self, msg):
        log.debug(msg)

    @trace
    def set_password(self, passwd): 
        """
            Collect root password from user - password?passwd=<passwd>
        """
        if passwd:
            self.core.password = base64.decodestring(passwd)
            return str(self.core.check_password(self.password_callback))
        else:
            return 'Empty'

    set_password.exposed = True


    def password_controller(self): 
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        return self.mode()

    password_controller.exposed = True

    #
    # WARNING
    #

    @trace
    def warning(self): 
        template = self.createTemplate("warning")
        self.pushHistory(self.warning)
        return str(template)

    warning.exposed = True

    def warning_controller(self):
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        self.next = self.password
        return self.progress(ACTION_INIT)

    warning_controller.exposed = True


    #
    # MODE SELECTION
    #

    @trace
    def mode(self):
        """
            Install Mode: Custom or Automatic
        """
        template = self.createTemplate("mode")
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

    #
    # COMPONENT SELECTION
    #

    def component(self): 
        """
            Install Component: HPLIP or HPIJS (not shown in auto mode)
        """
        template = self.createTemplate("component")
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

    def confirm_distro(self):
        """
            Correct Distro? (NOTE: Only display is distro && distro version is known)
        """
        template = self.createTemplate("confirm_distro")
        template.distro_version = self.core.distro_version
        template.distro_name = self.core.get_distro_data('display_name')
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
            return self.notes()
        else:
            return self.select_distro()

    confirm_distro_controller.exposed = True

    def select_distro(self): 
        """
            Choose Distro and Distro Version (only shown if distro and/or version not known 
            || correct distro question answered "no")
        """
        template = self.createTemplate("select_distro")
        self.pushHistory(self.select_distro)
        template.distro_version = self.core.distro_version
        template.distro_name = self.core.distro_name
        template.distros = {}
        template.distro = self.core.distro

        for d in self.core.distros_index:
            dd = self.core.distros[self.core.distros_index[d]]

            if dd['display']:
                template.distros[d] = dd['display_name']

        return str(template)

    select_distro.exposed = True

    def select_distro_update_combo(self, index): 
        """
            AJAX method to update distro version combo box
        """
        self.core.distro = int(index)
        self.core.distro_name = self.core.distros_index[self.core.distro]
        versions = self.core.distros[self.core.distro_name]['versions'].keys()
        versions.sort(lambda x, y: sort_vers(x, y))
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
            return self.notes() # ok, move ahead to notes

    select_distro_controller.exposed = True

    #
    # NOTES
    #

    def notes(self): 
        """
            Installation Notes (distro specific)
        """
        self.pushHistory(self.notes)
        template = self.createTemplate("notes")

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

    #
    # INSTALLATION OPTIONS
    #

    def options(self): 
        """
            Build Options (not shown in auto mode)
        """
        template = self.createTemplate("options")
        template.options = self.core.options
        template.components = self.core.components
        template.selected_component = self.core.selected_component
        return str(template)

    options.exposed = True

    def options_controller(self, **options): 
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
        template = self.createTemplate("error_package_manager")
        template.package_manager_name = pkg_mgr
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
        return str(int(self.core.check_pkg_mgr()())) 
        # returns '' for no running pkg manager, or '<name>' of running package manager

    package_manager_check.exposed = True


    #
    # DEPENDENCIES
    #

    def dependency_controller1(self):
        self.check_required()
        self.check_optional()

        if self.core.distro_known():
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
        self.core.hpoj_present = dcheck.check_hpoj()
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
        self.next = self.finished
        return self.progress(ACTION_BUILD_AND_INSTALL)

    def dependency_controller9(self):
        self.core.hplip_present = dcheck.check_hplip()
        if self.core.hplip_present and self.core.selected_component == 'hplip' and \
            self.core.distro_version_supported:

            if self.auto_mode:
                return self.hplip_remove_controller()
            else:
                return self.hplip_remove()
        else:
            return self.dependency_controller8()

    #
    # CHECK FOR ACTIVE NETWORK CONNECTION
    #

    def network_unavailable(self):
        template = self.createTemplate("network_unavailable")
        self.pushHistory(self.network_unavailable)
        return str(template)

    network_unavailable.exposed = True

    def network_unavailable_controller(self):
        pkg_mgr = self.core.check_pkg_mgr()

        if not self.core.check_network_connection():
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
    # Various installer checks
    #

    def check_required(self):
        self.num_req_missing = self.core.count_num_required_missing_dependencies()

    def check_optional(self):
        self.num_opt_missing = self.core.count_num_optional_missing_dependencies()

    def install_required(self): 
        """
            Ask user if they want to try to install required dependencies (not shown in auto mode)
        """
        template = self.createTemplate("install_required")
        template.missing_required_dependencies = {}

        for depend, desc, option in self.core.missing_required_dependencies():
            log.error("Missing REQUIRED dependency: %s (%s)" % (depend, desc))
            self.depends_to_install.append(depend)

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
        pkg_mgr = self.core.check_pkg_mgr()
        if self.network_ping() != 0:
            return self.network_unavailable()

        if pkg_mgr:
            self.next = self.install_required_controller()
            return self.error_package_manager(pkg_mgr)
        else:
            self.next = self.dependency_controller4
            return self.progress(ACTION_PRE_DEPENDENCY)

    install_required_controller.exposed = True

    def install_optional(self): 
        """
            Ask user if they want to try to install optional dependencies (not shown in auto mode)
        """
        self.depends_to_install = []
        template = self.createTemplate("install_optional")
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

    def turn_off_options(self): 
        """
            Inform the user that some options have been turned off because of missing optional dependencies
        """
        template = self.createTemplate("turn_off_options")
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

    def turn_off_options_controller(self):
        return self.dependency_controller3()

    turn_off_options_controller.exposed = True

    def error_required_missing(self): 
        """
            A required dependency is missing, can't continue
        """
        for depend, desc, option in self.core.missing_required_dependencies():
            log.error("Missing REQUIRED dependency: %s (%s)" % (depend, desc))
            template.missing_required_dependencies[d] = desc

        return str(template) 

    error_required_missing.exposed = True


    #
    # PROGRESS
    #

    # Reusable progress screen

    @trace
    def progress(self, action): 
        """
            progress?action=0|1|2|3|4|5|6|7|8
        """
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

                package_mgr_cmd = self.core.get_distro_data('package_mgr_cmd', '')

                if package_mgr_cmd:
                    for d in self.depends_to_install:
                        log.debug("*** Processing dependency: %s" % d)
                        packages, commands = core.get_dependency_data(d)
                        
                        log.debug("Packages: %s" % ','.join(packages))
                        log.debug("Commands: %s" % ','.join(commands))

                        if packages:
                            log.debug("Packages '%s' will be installed to satisfy dependency '%s'." % 
                                (','.join(packages), d))
                            packages_to_install.extend(package)
    
                        if commands:
                            log.debug("Commands '%s' will be run to satisfy dependency '%s'." % 
                                (','.join(commands), d))
                            commands_to_run.extend(command)
    
    
                self.cmds.append(cat(package_mgr_cmd, ' '.join(packages_to_install)))
                self.cmds.extend(commands_to_run)

            elif self.action == ACTION_PRE_DEPENDENCY: # 3
                self.pre_has_run = True
                self.cmds.extend(self.core.get_distro_ver_data('pre_depend_cmd'))
                self.fail_ok = True

            elif self.action == ACTION_POST_DEPENDENCY: # 4
                self.post_has_run = True
                self.cmds.extend(self.core.get_distro_ver_data('post_depend_cmd'))
                self.fail_ok = True

            elif self.action == ACTION_BUILD_AND_INSTALL: # 5  Do I want to combile pre_build and post_build?
                self.cmds.extend(self.core.run_pre_build)
                self.cmds.extend(self.core.build_cmds())
                self.cmds.extend(self.core.run_post_build)

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
                self.action_thread = thread.start_new_thread(self.run_action_thread, (self.cmds,))
                return str(template)
            else:
                return self.next()

    progress.exposed = True

    #@trace
    def progress_update(self): 
        """
            AJAX method to update progress screen. Called periodically...
        """
        output = ""
        while not self.queue.empty():
            output = ''.join([output, self.queue.get()])
        
        print output.strip()
        
        return output.lstrip()

    progress_update.exposed = True

    #@trace
    def progress_status(self): 
        """
            AJAX method to update progress screen. Returns an ineteger -1, 0, or >0
        """
        self.action_lock.acquire()
        t = self.progress_status_code
        self.action_lock.release()
        t2 = utils.printable(str(t))
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
    def run_action_thread(self, cmds):
        """
            0 : Done, no error
            >0 : Done, with error
        """
        for cmd in cmds:
            self.queue.put(cmd)
            
            try:
                cmd(self.progress_callback)
            except TypeError:
                status, output = run(cmd, self.progress_callback)
    
                if status != 0:
                    self.action_lock.acquire()
                    self.progress_status_code = status
                    self.action_lock.release()
                    break
                    

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
    def progress_callback(self, output): 
        """
            Called by self.core.init() in a thread to collect output
        """
        #print "put: %s" % output
        self.queue.put(output)
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
                (self.cmds, self.progress_status_code))

    error_command_failed.exposed = True


    #
    # INSTALLATION PATH
    #

    def installation_path(self): 
        """
            Install path (not shown in auto mode)
        """
        template = self.createTemplate("installation_path")
        template.install_location = self.core.install_location
        return str(template)

    installation_path.exposed = True

    @trace
    def installation_path_controller(self, path): 
        """
            installation_path_controller?path=<path>
        """
        self.core.install_location = path
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        self.next = self.finished
        return self.progress(ACTION_BUILD_AND_INSTALL)

    installation_path_controller.exposed = True

    #
    # PACKAGE CONFLICTS: HPOJ & HPLIP
    #

    def hpoj_remove(self): 
        """
            Ask user if they want to uninstall HPOJ (not shown in auto mode)
        """
        template = self.createTemplate("hpoj_remove")
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
        template = self.createTemplate("hplip_remove")
        return str(template)

    hplip_remove.exposed = True

    def hplip_remove_controller(self):
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
        template = self.createTemplate("ready_to_build")
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
        template = self.createTemplate("finished")
        return str(template)

    finished.exposed = True

    @trace
    def finished_controller(self, setup):
        nxt = self.next
        if nxt is not None:
            self.next = None
            return nxt()

        self.core.run_hp_setup()
        return self.quit()

    finished_controller.exposed = True


    #
    # VARIOUS ERRORS
    #

    @trace
    def error(self, error_text): 
        """
            Generic re-usable error page
        """
        template = self.createTemplate("error")
        template.error_text = error_text
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
        template = self.createTemplate("error_unsupported_distro")
        template.distro_version = self.core.distro_version
        template.distro_name = self.core.get_distro_data('display_name')

        template.missing_required_dependencies = {}
        for depend, desc, option in core.missing_required_dependencies():
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
        # Force reusable screens back to test when done
        self.next = self.test
        template = self.createTemplate("test")
        template.options = self.core.options
        template.components = self.core.components
        template.selected_component = self.core.selected_component
        template.dependencies = self.core.dependencies
        template.have_dependencies = self.core.have_dependencies
        template.selected_options = self.core.selected_options
        template.version_description = self.core.version_description
        template.version_public = self.core.version_public
        template.version_internal = self.core.version_internal
        template.bitness = self.core.bitness
        template.endian = self.core.endian
        template.distro = self.core.distro
        template.distro_name = self.core.distro_name
        template.distro_version = self.core.distro_version
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
    

    

    def load_localization_file(self, xmlfile):
        try:
            #print "path: ", xmlfile
            dom = parse(xmlfile.encode('utf-8'))
            #print dom.toxml()
        except IOError:
            print "Location: error.html\n"
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
        sources = dom.getElementsByTagName("source")
        translations = dom.getElementsByTagName("translation")
        translation_list = []
        source_list = []
        self.localized_dict = {}

        for translation in translations:
            translation_list.append(self.get_text(translation.childNodes))
            #print 'Translation: ', translation_list

        for source in sources:
            source_list.append(self.get_text(source.childNodes))
            #print 'Translation: ', source_list

        self.localized_dict = dict(zip(source_list, translation_list))
        #for key in self.localized_dict:
            #print "EN:", key, "ES:", self.localized_dict[key]

    parse_elements.exposed = True

    def localized_string(self, string):  #localized_string?string="Some english string"
        
        try:
            #print "utf8 encoded: ", string 
            in_string = unicode(string).decode('utf-8')
        except IOError:
            print "Decoding Error\n"
            sys.exit()
            
        try:
            #wstring = cstring.decode()
            #print "utf8 decoded: ", in_string 
            rstring = unicode(self.localized_dict.get(in_string, 'Localization load error'))
            #print "Localized string: ", rstring
            out_string = rstring.encode('utf-8')
            #print "Out string: ", out_string
        except IOError:
            print "Encoding Error\n"
            sys.exit()
            
        return out_string

    localized_string.exposed = True

    #
    # Code for reading the localized .ts files from the /data/localization
    #
    
    XMLFILE = 'data/localization/hplip_es.ts'

    def load_localization_file(self, xmlfile):
        try:
            #print "path: ", xmlfile
            dom = parse(xmlfile.encode('utf-8'))
            #print dom.toxml()
        except IOError:
            print "Location: error.html\n"
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
        sources = dom.getElementsByTagName("source")
        translations = dom.getElementsByTagName("translation")
        translation_list = []
        source_list = []
        self.localized_dict = {}

        for translation in translations:
            translation_list.append(self.get_text(translation.childNodes))
            #print 'Translation: ', translation_list

        for source in sources:
            source_list.append(self.get_text(source.childNodes))
            #print 'Translation: ', source_list

        self.localized_dict = dict(zip(source_list, translation_list))
        #for key in self.localized_dict:
            #print "EN:", key, "ES:", self.localized_dict[key]

    parse_elements.exposed = True

    def localized_string(self, string):  #localized_string?string="Some english string"
        
        try:
            #print "utf8 encoded: ", string 
            in_string = unicode(string).decode('utf-8')
        except IOError:
            print "Decoding Error\n"
            sys.exit()
            
        try:
            #wstring = cstring.decode()
            #print "utf8 decoded: ", wstring 
            out_string = unicode(self.localized_dict.get(in_string, 'Localization load error')).encode('utf-8')
            #print "Localized string: ", rstring
            #out_string = rstring.encode('utf-8')
            #print "Out string: ", ostring
        except IOError:
            print "Encoding Error\n"
            sys.exit()
            
        return out_string

    localized_string.exposed = True
    

    #========================== End of Class =========================

def init():
    log.info("Server ready.")
    utils.openURL("http://localhost:8888")

def start():
    cherrypy.root = Installer()
    #cherrypy.root.parse_elements(cherrypy.root.load_localization_file(XMLFILE))

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
        'server.socket_port': 8888,
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


