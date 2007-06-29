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

from base.g import *
from base import utils
import core
import dcheck
import distros
import re
import getpass
import cStringIO
from base import pexpect
import pwd
import grp

password = ''

def get_password():
    return getpass.getpass("Enter password: ")

def run(cmd, log_output=True, password_func=get_password, timeout=1):
    output = cStringIO.StringIO()

    try:
        child = pexpect.spawn(cmd, timeout=timeout)
    except pexpect.ExceptionPexpect:
        return -1, ''

    try:
        while True:
            update_spinner()
            i = child.expect(["[pP]assword:", pexpect.EOF, pexpect.TIMEOUT])

            if child.before:
                log.debug(child.before)
                log.log_to_file(child.before)
                output.write(child.before)

            if i == 0: # Password:
                if password_func is not None:
                    child.sendline(password_func())
                else:
                    child.sendline(get_password())

            elif i == 1: # EOF
                break

            elif i == 2: # TIMEOUT
                continue


    except Exception, e:
        log.error("Exception %s" % e)

    cleanup_spinner()
    child.close()

    return child.exitstatus, output.getvalue()
    

def password_func():
    return password

def enter_yes_no(question, default="y"):
    default_bool = utils.to_bool(default)
    while True:
        user_input = raw_input(utils.bold(question)).lower().strip()
        if not user_input or user_input == default:
            return default_bool

        if user_input == 'n':
            return False

        if user_input == 'y':
            return True

        if user_input == 'q':
            sys.exit(0)

        log.error("Please enter 'y', 'n', or 'q'.")

def enter_range(question, min_value, max_value, default_value=None):
    while True:
        user_input = raw_input(utils.bold(question)).lower().strip()

        if default_value is not None:
            if not user_input or user_input == str(default_value):
                return default_value

        if user_input == 'q':
            sys.exit(0)

        try:
            value_int = int(user_input)
        except:
            log.error('Please enter a number between %d and %d, or "q" to quit.' % (min_value, max_value))
            continue

        if value_int < min_value or value_int > max_value:
            log.error('Please enter a number between %d and %d, or "q" to quit.' % (min_value, max_value))
            continue

        return value_int

def enter_choice(question, choices, default_value):
    choices.append('q')
    while True:
        user_input = raw_input(utils.bold(question)).lower().strip()

        if not user_input or user_input == str(default_value):
            return default_value

        if user_input == 'q':
            sys.exit(0)

        if user_input in choices:
            return user_input

        log.error("Please enter %s or press <enter> for the default of '%s'." % (', '.join(["'%s'" % x for x in choices]), default_value))


def sort_vers(x, y):
    try:
        return cmp(float(x), float(y))
    except ValueError:
        return cmp(x, y)


def title(text):
    log.info("")
    log.info("")
    log.info(utils.bold(text))
    log.info(utils.bold("-"*len(text)))

def start(auto=True):
    log.info("Initializing. Please wait...")
    os.umask(0022)
    core.init()
    
    if os.geteuid() == 0:
        log.error("You are running the installer as root. It is highly recommended that you run the installer as")
        log.error("a regular (non-root) user. Do you still wish to continue?")
        answer = enter_yes_no(utils.bold("Continue with installation (y=yes, n=no*)? "), 'n')
        
        if not answer:
            sys.exit(1)

    if auto:
        log.note("Running in automatic mode. The most common options will be selected.")

    try:
        log.info("")
        log.note("Defaults for each question are maked with a '*'. Press <enter> to accept the default.")

        if not auto:
            title("INSTALLATION MODE")

            user_input = enter_choice("Please choose the installation mode (a=automatic*, c=custom, q=quit) : ", ['a', 'c'], 'a')

            if user_input == 'a':
                auto = True
        
        #
        # HPLIP vs. HPIJS INSTALLATION
        #

        if auto:
            selected_component = 'hplip'
        else:
            user_input = enter_choice("\nWould you like to install HPLIP (desktop/recommended) or HPIJS only (server/printing only) (d='HPLIP'* (recommended), s='HPIJS only', q=quit) ? ", ['d', 's'], 'd')

            if user_input == 'd':
                selected_component = 'hplip'
            else:
                selected_component = 'hpijs'

        #
        # INTRODUCTION/RELEASE NOTES
        #
        
        title("INTRODUCTION")
        
        if selected_component == 'hplip':
            log.info("This installer will install HPLIP version %s on your computer." % core.version_public)
            hpijs_build = False
        else:
            log.info("This installer will install HPIJS version %s on your computer." % core.version_public)
            hpijs_build = True

        if not auto: # and selected_component == 'hplip':
            if os.getenv('DISPLAY'):
                title("VIEW RELEASE NOTES")

                if enter_yes_no("Would you like to view the release notes for this version of HPLIP (y=yes, n=no*, q=quit) ? ", default="n"):
                    log.info("Displaying release notes in a browser window...")
                    url = "file://%s" % os.path.join(os.getcwd(), 'doc', 'release_notes.html')
                    log.debug(url)
                    status, output = run("xhost +", True, password_func)
                    utils.openURL(url)




        num_req_missing = 0
        # required options
        for opt in core.components[selected_component][1]:
            if core.options[opt][0]: # required options
                for d in core.options[opt][2]: # dependencies for option
                    if not core.have_dependencies[d]: # missing
                        num_req_missing += 1



        x = False
        num_opt_missing = 0
        # not-required options
        for opt in core.components[selected_component][1]:
            if not core.options[opt][0]: # not required
                if not auto:
                    if not x:
                        title("BUILD/INSTALL OPTIONS")
                        x = True

                    core.selected_options[opt] = \
                        enter_yes_no("Do you wish to enable '%s' (y=yes*, n=no, q=quit) ? " % \
                        core.options[opt][1], default="y")
                        
                    log.info("")

                if core.selected_options[opt]: # only for options that are ON
                    for d in core.options[opt][2]: # dependencies
                        if not core.have_dependencies[d]: # missing dependency
                            num_opt_missing += 1



        log.debug("Req missing=%d Opt missing=%d HPOJ=%s HPLIP=%s Component=%s" % \
            (num_req_missing, num_opt_missing, core.hpoj_present, core.hplip_present, selected_component))

        if core.distro != distros.DISTRO_UNKNOWN and core.distro_version != '0.0':
            log.info("Distro is %s %s" % (core.get_distro_data('display_name', '(unknown)'), core.distro_version))

        #if num_req_missing or num_opt_missing or (core.hpoj_present and selected_component == 'hplip'):
        if 1:
            title("DISTRO/OS SELECTION")
            distro_ok = False

            if core.distro != distros.DISTRO_UNKNOWN and core.distro_version != '0.0':
                distro_ok = enter_yes_no('\nIs "%s %s" your correct distro/OS and version (y=yes*, n=no, q=quit) ? ' % (core.get_distro_data('display_name', '(unknown)'), core.distro_version), 'y')

            if not distro_ok:
                core.distro, core.distro_version = distros.DISTRO_UNKNOWN, '0.0'
                core.distro_name = core.distros_index[core.distro]

                log.info(utils.bold("\nChoose the name of the distro/OS that most closely matches your system:\n"))

                max_name = 0
                for d in core.distros_index:
                    dd = core.distros[core.distros_index[d]]
                    if dd['display']:
                        max_name = max(max_name, len(dd['display_name']))

                formatter = utils.TextFormatter(
                        (
                            {'width': 4},
                            {'width': max_name, 'margin': 2},
                        )
                    )

                log.info(formatter.compose(("Num.", "Distro/OS Name")))
                log.info(formatter.compose(('-'*4, '-'*(max_name))))

                d_temp = {}
                x = 0
                for d in core.distros_index:
                    dd = core.distros[core.distros_index[d]]

                    if dd['display']:
                        d_temp[x] = d
                        log.info(formatter.compose((str(x), dd['display_name'])))
                        x += 1

                y = enter_range("\nEnter number 0...%d (q=quit) ?" % (x-1), 0, x-1)

                core.distro = d_temp[y]
                core.distro_name = core.distros_index[core.distro]
                distro_display_name = core.distros[core.distro_name]['display_name']
                log.debug("Distro = %s Distro Name = %s Display Name= %s" % 
                    (core.distro, core.distro_name, distro_display_name))

                if core.distro != distros.DISTRO_UNKNOWN:
                    versions = core.distros[core.distro_name]['versions'].keys()
                    versions.sort(lambda x, y: sort_vers(x, y))

                    log.info(utils.bold('\nChoose the version of "%s" that most closely matches your system:\n' % distro_display_name))

                    formatter = utils.TextFormatter(
                            (
                                {'width': 4},
                                {'width': 40, 'margin': 2},
                            )
                        )

                    log.info(formatter.compose(("Num.", "Distro/OS Version")))
                    log.info(formatter.compose(('-'*4, '-'*40)))

                    log.info(formatter.compose(("0", "Unknown or not listed"))) 

                    x = 1
                    for ver in versions:
                        ver_info = core.distros[core.distro_name]['versions'][ver]

                        if ver_info['code_name'] and ver_info['release_date']:
                            text = ver + ' ("' + ver_info['code_name'] + '", Released ' + ver_info['release_date'] + ')'

                        elif ver_info['code_name']:
                            text = ver + ' ("' + ver_info['code_name'] + '")'

                        elif ver_info['release_date']:
                            text = ver + ' (Released ' + ver_info['release_date'] + ')'

                        else:
                            text = ver

                        if not ver_info['supported']:
                            text += " [Unsupported]"

                        log.info(formatter.compose((str(x), text))) 
                        x += 1

                    core.distro_version_int = enter_range("\nEnter number 0...%d (q=quit) ?" % (x-1), 0, x-1)

                    if core.distro_version_int == 0:
                        core.distro_version = '0.0'
                        core.distro_version_supported = False

                    else:
                        core.distro_version = versions[core.distro_version_int - 1]

                        core.distro_version_supported = core.get_ver_data('supported', False)
                    
                    log.debug("Distro = %s Distro Name = %s Display Name= %s Version = %s Supported = %s" % \
                        (core.distro, core.distro_name, core.distros[core.distro_name]['display_name'], \
                        core.distro_version, core.distro_version_supported))

                if core.distro == distros.DISTRO_UNKNOWN or not core.distro_version_supported:
                    if num_req_missing:
                        log.error("The distro/OS that you are running is unsupported and there are required dependencies missing. Please manually install the missing dependencies and then re-run this installer.")

                        log.error("The following REQUIRED dependencies are missing and need to be installed before the installer can be run:")

                        for opt in core.components[selected_component][1]:
                            if core.options[opt][0]: # required options
                                for d in core.options[opt][2]: # dependencies for option
                                    if not core.have_dependencies[d]: # missing
                                        log.error("Missing REQUIRED dependency: %s (%s)" % (d, core.dependencies[d][2]))

                        sys.exit(1)

                    log.error("The distro and/or distro version you are using is unsupported.\nYou may still try to use this installer, but some dependency problems may exist after install.")
                    log.error("The following OPTIONAL dependencies are missing and may need to be installed:")

                    for opt in core.components[selected_component][1]:
                        if not core.options[opt][0]: # not required
                            if core.selected_options[opt]: # only for options that are ON
                                for d in core.options[opt][2]: # dependencies
                                    if not core.have_dependencies[d]: # missing dependency

                                        if core.dependencies[d][0]: # dependency is required for this option
                                            log.warning("Missing OPTIONAL dependency: %s (%s) [Required for option '%s']" % (d, core.dependencies[d][2], core.options[opt][1]))
                                        else:
                                            log.warning("Missing OPTIONAL dependency: %s (%s) [Optional for option '%s']" % (d, core.dependencies[d][2], core.options[opt][1]))


                    if not enter_yes_no("\n\nDo you still wish to continue (y=yes*, n=no, q=quit) ?", default="y"):
                        sys.exit(0)
        
        #
        # COLLECT SUPERUSER PASSWORD
        #
        
        if not os.geteuid() == 0:
            title("ENTER ROOT/SUPERUSER PASSWORD")
                
            # Clear sudo password if set
            su_sudo_str = core.get_distro_data('su_sudo', 'su')
            if su_sudo_str == 'sudo':
                status, output = run("sudo -K")
            
            global password
            x = 1
            
            while True:
                password = getpass.getpass(utils.bold("Please enter the root/superuser password: "))
                status, output = run(core.su_sudo() % "true", True, password_func)
                
                if status == 0:
                    log.note("Password accepted.")
                    break
                    
                log.error("Incorrect password (attempt %d). Please re-enter." % x)
                x += 1
                
                if x > 3:
                    log.error("3 incorrect attempts. Exiting.")
                    sys.exit(1)

        #
        # INSTALLATION NOTES
        #

        if core.distro_version_supported:
            distro_notes = core.get_distro_data('notes', '').strip()
            ver_notes = core.get_ver_data('notes', '').strip()
            if distro_notes or ver_notes:
                title("INSTALLATION NOTES")

                if distro_notes:
                    log.info(distro_notes)

                if ver_notes:
                    log.info(ver_notes)

                user_input = raw_input(utils.bold("\nPlease read the installation notes and hit <enter> to continue (<enter>=continue*, q=quit) : ")).lower().strip()

                if user_input == 'q':
                    sys.exit(0)

        
        #
        # REQUIRED dependencies
        #


        depends_to_install = []
        if num_req_missing:
            title("INSTALL MISSING REQUIRED DEPENDENCIES")

            log.warn("There are %d missing REQUIRED dependencies." % num_req_missing)
            log.notice("Installation of dependencies requires an active internet connection.")

            # required core.options
            for opt in core.components[selected_component][1]:
                if core.options[opt][0]: # required core.options
                    for d in core.options[opt][2]: # dependencies for option

                        if not core.have_dependencies[d]: # missing
                            log.warning("Missing REQUIRED dependency: %s (%s)" % (d, core.dependencies[d][2]))

                            ok = False
                            package, command = core.get_ver_data('dependency_cmds', {}).get(d, ('', ''))
                            if core.distro_version_supported and (package or command):
                                if auto:
                                    answer = True
                                else:
                                    answer = enter_yes_no("\nWould you like to have this installer install the missing dependency (y=yes*, n=no, q=quit)?", default="y")

                                if answer:
                                    ok = True
                                    log.debug("Adding '%s' to list of dependencies to install." % d)
                                    depends_to_install.append(d)

                            else:
                                log.error("This installer cannot install this dependency for your distro/OS and/or version.")

                            if not ok:
                                log.error("Installation cannot continue without this dependency. Please manually install this dependency and re-run this installer.")                    
                                sys.exit(0)

                            log.info("-"*10)
                            log.info("")

        #
        # OPTIONAL dependencies
        #

        if num_opt_missing:
            title("INSTALL MISSING OPTIONAL DEPENDENCIES")

            log.notice("Installation of dependencies requires an active internet connection.")

            for opt in core.components[selected_component][1]:
                if not core.options[opt][0]: # not required
                    if core.selected_options[opt]: # only for core.options that are ON
                        for d in core.options[opt][2]: # dependencies
                            if not core.have_dependencies[d]: # missing dependency

                                if core.dependencies[d][0]: # dependency is required for this option
                                    log.warning("Missing REQUIRED dependency for option '%s': %s (%s)" % (core.options[opt][1], d, core.dependencies[d][2]))

                                else:
                                    log.warning("Missing OPTIONAL dependency for option '%s': %s (%s)" % (core.options[opt][1], d, core.dependencies[d][2]))

                                installed = False
                                package, command = core.get_ver_data('dependency_cmds', {}).get(d, ('', ''))
                                if core.distro_version_supported and (package or command):
                                    if auto:
                                        answer = True
                                    else:
                                        answer = enter_yes_no("\nWould you like to have this installer install the missing dependency (y=yes*, n=no, q=quit)?", default="y")

                                    if answer:
                                        log.debug("Adding '%s' to list of dependencies to install." % d)
                                        depends_to_install.append(d)

                                    else:
                                        log.warning("Missing dependencies may effect the proper functioning of HPLIP. Please manually install this dependency after you exit this installer.")
                                        log.warning("Note: Options that have REQUIRED dependencies that are missing will be turned off.")

                                        if core.dependencies[d][0]:
                                            log.warn("Option '%s' has been turned off." % opt)
                                            core.selected_options[opt] = False
                                else:
                                    log.error("This installer cannot install this dependency for your distro/OS and/or version.")

                                    if core.dependencies[d][0]:
                                        log.warn("Option '%s' has been turned off." % opt)
                                        core.selected_options[opt] = False


                                log.info("-"*10)
                                log.info("")


        log.debug("Dependencies to install: %s" % depends_to_install)

        if core.distro_version_supported and \
            (depends_to_install or ((core.hplip_present or core.hpoj_present) and \
            selected_component == 'hplip')):

            #
            # CHECK FOR RUNNING PACKAGE MANAGER
            #

            p = core.check_pkg_mgr()
            while p:
                user_input = raw_input(utils.bold("\nA running package manager '%s' has been detected. Please quit the package manager and press <enter> to continue (q=quit, i=ignore, <enter>=re-check) :" % p))
                
                user_input = user_input.lower().strip()

                if user_input == 'q':
                    sys.exit(0)
                    
                elif user_input == 'i':
                    log.warn("Ignoring running package manager. Some package operations may fail.")
                    break

                p = core.check_pkg_mgr()


            #
            # CHECK FOR ACTIVE NETWORK CONNECTION
            #
            
            title("CHECKING FOR NETWORK CONNECTION")
            
            ping = utils.which("ping") # TODO: Use something else here...
            
            if ping:
                ping = os.path.join(ping, "ping")
                status, output = run(ping + " -c3 www.google.com", True, None)
                
                if status != 0:
                    log.error("\nThe network appears to be unreachable. Installation cannot complete without access to")
                    log.error("distribution repositories. Please check the network and try again.")
                    sys.exit(1)
                else:
                    log.info("Network connection present.")
                
            #
            # PRE-DEPEND
            #

            pre_cmd = core.get_distro_ver_data('pre_depend_cmd')
            if pre_cmd:
                title("RUNNING PRE-PACKAGE COMMANDS")
                
                if type(pre_cmd) == type(''):
                    pre_cmd = [pre_cmd]
                    
                for cmd in pre_cmd:
                    if type(cmd) == type(''):
                        log.info("Running '%s'\nPlease wait, this may take several minutes..." % cmd)
                        status, output = run(cmd, True, password_func)
                        
                    else: # func
                        log.info("Running command...")
                        status = cmd(core.distro, core.distro_version)
                    
                    if status != 0:
                        log.warn("Command failed.")

            #
            # INSTALL PACKAGES AND RUN COMMANDS
            #
            title("DEPENDENCY AND CONFLICT RESOLUTION")

            packages_to_install = []
            commands_to_run = []
            package_mgr_cmd = core.get_distro_data('package_mgr_cmd')
            if package_mgr_cmd:
                log.debug("Preparing to install packages and run commands...")
    
                for d in depends_to_install:
                    log.debug("*** Processing dependency: %s" % d)
                    package, command = core.distros[core.distro_name]['versions'][core.distro_version]['dependency_cmds'][d]
    
                    if package:
                        log.debug("Package '%s' will be installed to satisfy dependency '%s'." % (package, d))
                        packages_to_install.append(package)
    
                    if command:
                        log.debug("Command '%s' will be run to satisfy dependency '%s'." % (command, d))
                        
                        if type(command) == type(""):
                            commands_to_run.append(command)
                        
                        elif type(command) == type([]):
                            commands_to_run.extend(command)
                            
                packages_to_install = ' '.join(packages_to_install)
            
            else:
                log.error("Invalid package manager")

            if package_mgr_cmd and packages_to_install:
                while True:
                    cmd = utils.cat(package_mgr_cmd)
                    log.debug("Package manager command: %s" % cmd)

                    log.info("Running '%s'\nPlease wait, this may take several minutes..." % cmd)
                    status, output = run(cmd, True, password_func)

                    if status != 0:
                        log.error("Package install command failed with error code %d" % status)
                        user_input = enter_choice("Would you like to retry installing the missing package(s)? (y=yes*, n=no, q=quit) : ", ['y', 'n'], 'y')

                        if user_input == 'y':
                            continue
                        
                        elif user_input == 'n':
                            log.warn("Some HPLIP functionality might not function due to missing package(s).")
                            break

                    else:
                        break

            if commands_to_run:
                for cmd in commands_to_run:
                    log.debug(cmd)
                    log.info("Running '%s'\nPlease wait, this may take several minutes..." % cmd)
                    status, output = run(cmd, True, password_func)

                    if status != 0:
                        log.error("Install command failed with error code %d" % status)
                        sys.exit(1)
                    

            #
            # HPOJ REMOVAL
            #

            core.hpoj_present = dcheck.check_hpoj() # a dependency may have installed it as a sub-dependency

            if core.hpoj_present and selected_component == 'hplip' and core.distro_version_supported:
                log.error("HPOJ is installed and/or running. HPLIP is not compatible with HPOJ.")

                hpoj_remove_cmd = core.get_distro_data('hpoj_remove_cmd')

                if hpoj_remove_cmd:
                    if auto:
                        answer = True
                    else:
                        answer = enter_yes_no("\nWould you like to have this installer attempt to uninstall HPOJ (y=yes*, n=no, q=quit) ? ")

                    if answer:
                        log.info("\nRunning '%s'\nPlease wait, this may take several minutes..." % hpoj_remove_cmd)
                        status, output = run(hpoj_remove_cmd, True, password_func)

                        if status != 0:
                            log.error("HPOJ removal failed. Please manually stop/remove/uninstall HPOJ and then re-run this installer.")
                            sys.exit(1)
                        else:
                            core.hpoj_present = dcheck.check_hpoj()

                            if core.hpoj_present:
                                log.error("HPOJ removal failed. Please manually stop/remove/uninstall HPOJ and then re-run this installer.")
                                sys.exit(1)
                            else:
                                log.info("Removal successful.")
                    else:
                        log.error("Please stop/remove/uninstall HPOJ and then re-run this installer.")
                        sys.exit(0)

                else:
                    log.error("Please stop/remove/uninstall HPOJ and then re-run this installer.")
                    sys.exit(0)


            #
            # HPLIP REMOVE
            #

            core.hplip_present = dcheck.check_hplip() # a dependency may have installed it as a sub-dependency

            if core.hplip_present and selected_component == 'hplip' and core.distro_version_supported:
                failed = True
                log.warn("A previous install of HPLIP is installed and/or running.")

                hplip_remove_cmd = core.get_distro_data('hplip_remove_cmd')
                if hplip_remove_cmd:
                    if auto:
                        answer = True
                    else:
                        answer = enter_yes_no("\nWould you like to have this installer attempt to uninstall the previously installed HPLIP (y=yes*, n=no, q=quit) ? ")

                    if answer:
                        cmd = core.su_sudo() % '/etc/init.d/hplip stop'
                        log.info("Running '%s'\nPlease wait, this may take several minutes..." % cmd)
                        status, output = run(cmd, True, password_func)

                        log.info("\nRunning '%s'\nPlease wait, this may take several minutes..." % hplip_remove_cmd)
                        status, output = run(hplip_remove_cmd, True, password_func)

                        if status == 0:
                            core.hplip_present = dcheck.check_hplip()
                            
                            if not core.hplip_present:
                                log.info("Removal successful.")
                                failed = False

                else:
                    log.error("The previously installed version of HPLIP may conflict with the new one being installed.")
                    log.error("It is recommended that you quit this installer, and manually remove HPLIP before continuing.")
                    sys.exit(0)

                if failed:
                    log.error("HPLIP removal failed. The previous install may have been installed using a tarball or this installer.")
                    log.error("Continuing to run installer - this installation should overwrite the previous one.")


            # 
            # DEPENDENCIES RE-CHECK
            #

            dcheck.update_ld_output()

            # re-check dependencies
            for d in core.dependencies:
                log.debug("***")

                update_spinner()

                log.debug("Checking for dependency '%s'..." % d)
                core.have_dependencies[d] = core.dependencies[d][3]()
                log.debug("have %s = %d" % (d, core.have_dependencies[d]))

            cleanup_spinner()

            # re-check missing required core.options
            for opt in core.components[selected_component][1]:
                if core.options[opt][0]: # required core.options
                    for d in core.options[opt][2]: # dependencies
                        if not core.have_dependencies[d]: # missing
                            log.error("A required dependency '%s' is still missing." % d)
                            log.error("Installation cannot continue without this dependency. Please manually install this dependency and re-run this installer.")                    
                            sys.exit(1)


            # re-check missing optional core.options
            for opt in core.components[selected_component][1]:
                if not core.options[opt][0]: # not required
                    if core.selected_options[opt]: # only for core.options that are ON
                        for d in core.options[opt][2]: # dependencies
                            if not core.have_dependencies[d]: # missing dependency
                                if core.dependencies[d][0]: # required for option
                                    log.warn("An optional dependency '%s' is still missing." % d)
                                    log.warn("Option '%s' has been turned off." % opt)
                                    core.selected_options[opt] = False
                                else:
                                    log.warn("An optional dependency '%s' is still missing." % d)
                                    log.warn("Some features may not function as expected.")


            #
            # POST-DEPEND
            #
            title("RUNNING POST-PACKAGE COMMANDS")

            post_cmd = core.get_distro_data('post_depend_cmd')
            
            if type(post_cmd) == type(''):
                post_cmd = [post_cmd]
                
            if post_cmd:
                for cmd in post_cmd:
                    if type(cmd) == type(''):
                        log.info("Running '%s'\nPlease wait, this may take several minutes..." % cmd)
                        status, output = run(cmd, True, password_func)
                    
                    else: # func
                        log.info("Running command...")
                        status = cmd(core.distro, core.distro_version)
                    
                    if status != 0:
                        log.warn("Command failed.")

        #
        # INSTALL LOCATION
        #
    
        core.install_location = '/usr'
        log.debug("Install location = %s" % core.install_location)


        #
        # BUILD AND INSTALL
        #
        
        if not auto:
            title("READY TO BUILD AND INSTALL")

            user_input = raw_input(utils.bold("Ready to perform build and install. Press <enter> to continue (<enter>=continue*, q=quit) : ")).lower().strip()

            if user_input == 'q':
                sys.exit(0)
                
        title("PRE-BUILD SETUP")
        
        # Remove the link /usr/share/foomatic/db/source/PPD if the symlink is corrupt (Dapper only?)
        if core.get_distro_ver_data('fix_ppd_symlink', False):
            log.info("Fixing PPD symlink...")
            cmd = core.su_sudo() % 'python ./installer/fix_symlink.py'
            log.debug("Running symlink fix utility: %s" % cmd)
            status, output = run(cmd, True, password_func)
        else:
            log.info("OK")

        title("BUILD AND INSTALL")

        enable_ppds = core.ppd_install_flag()
        log.debug("Enable PPD install: %s" % enable_ppds)
        ppd_dir = core.get_distro_ver_data('ppd_dir')
        
        os.umask(0022)
        for cmd in core.build_cmds(enable_ppds, hpijs_build, ppd_dir):
            log.info("Running '%s'\nPlease wait, this may take several minutes..." % cmd)
            status, output = run(cmd, True, password_func)

            if status != 0:
                log.error("'%s' command failed with status code %d" % (cmd, status))
                sys.exit(0)
            else:
                log.info("Command completed successfully.")
            
            log.info("")

        log.info("\nBuild complete.")
        
        title("POST-BUILD SETUP")  
        
        # Make sure all users are in the 'lp' group
        
        logoff_required = False
        trigger_required = False
        
        log.info("Checking for 'lp' group membership...")
        
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
            log.info("Adding user '%s' to 'lp' group..." % user_list[0])
            cmd = "usermod -a -Glp %s" % user_list[0]
            cmd = core.su_sudo() % cmd
            log.debug("Running: %s" % cmd)
            status, output = run(cmd, True, password_func)
            logoff_required = True
        
        else:
            log.info("In order for USB I/O to function, each user that will access the device")
            log.info("must be a member of the 'lp' group:" )
            for u in users:
                if not users[u]:
                    answer = enter_yes_no("\nWould you like to add user '%s' to the 'lp' group (y=yes*, n=no, q=quit)?", default="y")
                    if answer:
                        log.info("Adding user '%s' to 'lp' group..." % u)
                        cmd = "usermod -a -Glp %s" % u
                        cmd = core.su_sudo() % cmd
                        log.debug("Running: %s" % cmd)
                        status, output = run(cmd, True, password_func)
                        
                        if u == prop.username:
                            logoff_required = True

        # Fix any udev device nodes that aren't 066x
        udev_mode_fix = core.get_distro_ver_data('udev_mode_fix', False)
        if udev_mode_fix:
            log.info("")
            log.info("Fixing USB device permissions...")
            cmd = core.su_sudo() % 'python ./installer/permissions.py'
            log.debug("Running USB permissions utility: %s" % cmd)
            status, output = run(cmd, True, password_func)
            trigger_required = True
        
        # Fix some USB issues on Mandriva and PCLinuxOS
        mdk_usb_fix = core.get_distro_ver_data('mdk_usb_fix', False)
        if mdk_usb_fix:
            log.info("")
            log.info("Fixing CUPS group and USB console security permissions...")
            cmd = core.su_sudo() % "python ./installer/mdk_usb_fix.py"
            log.debug("Running mdk usb fix utility: %s" % cmd)
            status, output = run(cmd, True, password_func)
            trigger_required = True
        
        # Trigger USB devices so that the new mode will take effect 
        if trigger_required:
            log.info("Triggering USB devices...")
            cmd = core.su_sudo() % 'python ./installer/trigger.py'
            log.debug("Running USB trigger utility: %s" % cmd)
            status, output = run(cmd, True, password_func)
        
        # Restart CUPS if necessary
        if core.cups11 or mdk_usb_fix:
            log.info("")
            log.info("Restarting CUPS...")
            status, output = run(core.restart_cups(), True, password_func)
            
            if status != 0:
                log.warn("CUPS restart failed.")
            else:
                log.info("Command completed successfully.")
            
        # Kill any running hpssd.py instance from a previous install
        log.info("")
        log.info("Checking for running hpssd...")
        if dcheck.check_hpssd():
            pid = dcheck.get_ps_pid('hpssd')
            try:
                log.info("Killing the running 'hpssd' process...")
                os.kill(pid, 9)
            except OSError:
                pass
            else:
                log.info("OK")
        else:
            log.info("Not running (OK).")
        
        # Logoff if necessary
        if logoff_required:
            title("IMPORTANT! LOGOFF REQUIRED!")
            log.note("If you are installing a USB connected printer, you must now logoff and re-logon")
            log.note("in order to communicate with the printer. After logging back on, run:")
            log.note(core.su_sudo() % "hp-setup")
            log.note("to setup a printer in HPLIP.")
            
            log.note("")
            log.note("IMPORTANT! Make sure to save all work in all open applications before logging off.")
            
            answer = enter_yes_no(utils.bold("Logoff now (y=yes, n=no*)? "), 'n')
            
            if answer:
                ok = False
                pkill = utils.which('pkill')
                if pkill:
                    cmd = "%s -KILL -u %s" % (os.path.join(pkill, "pkill"), prop.username)
                    cmd = core.su_sudo() % cmd
                    status, output = run(cmd, True, password_func)
                    
                    ok = (status == 0)
                        
                if not ok:
                    log.error("Logoff failed. Please logoff using the system menu.")
            
            sys.exit(0)
        #
        # SETUP PRINTER
        #
        title("PRINTER SETUP")

        if auto:
            install_printer = True
        else:
            install_printer = enter_yes_no("Would you like to setup a printer now (y=yes*, n=no, q=quit) ? ", default="y")

        if install_printer:
            log.info("Please make sure your printer is connected and powered on at this time.")

            if os.getenv('DISPLAY') and core.selected_options['gui'] and utils.checkPyQtImport():
                x = "python ./setup.py -u"
                cmd = core.su_sudo() % x
                status, output = run(cmd, True, password_func)

            else:
                io_choice = 'u'
                io_choices = ['u']
                io_list = '(u=USB*'

                if core.selected_options['network']:
                    io_list += ', n=network'
                    io_choices.append('n')

                if core.selected_options['parallel']:
                    io_list += ', p=parallel'
                    io_choices.append('p')

                io_list += ', q=quit)'

                if len(io_choices) > 1:
                    log.info("")
                    io_choice = enter_choice("What I/O type will the newly installed printer use %s ? " % io_list, io_choices, 'u')

                log.debug("IO choice = %s" % io_choice)


                auto_str = ''
                if auto:
                    auto_str = '--auto'

                if io_choice == 'n':
                    ip = ''
                    ip_pat = re.compile(r"""\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b""", re.IGNORECASE)

                    while True:
                        user_input = raw_input(utils.bold("\nEnter the IP address or hostname for the printer (q=quit) : ")).lower().strip()

                        if user_input == 'q':
                            sys.exit(0)

                        if ip_pat.search(user_input) is not None:
                            log.debug("IP match")
                            ip = user_input
                            break

                        try:
                            param = socket.gethostbyname(user_input)
                        except socket.gaierror:
                            log.debug("Gethostbyname() failed.")
                        else:
                            log.debug("gethostbyname() match")
                            ip = user_input
                            break

                        log.error("Invalid or unknown IP address/hostname")

                    if ip:
                        x = "python ./setup.py -i %s %s" % (ip, auto_str)
                        cmd = core.su_sudo() % x
                        status, output = run(cmd, True, password_func)
                        

                elif io_choice == 'p':
                    x = "python ./setup.py -i -b par %s" % auto_str
                    cmd = core.su_sudo() % x
                    status, output = run(cmd, True, password_func)
                    

                elif io_choice == 'u':
                    x = "python ./setup.py -i -b usb %s" % auto_str
                    cmd = core.su_sudo() % x
                    status, output = run(cmd, True, password_func)
                    


    except KeyboardInterrupt:
        log.info("")
        log.error("Aborted.")

    sys.exit(0)


