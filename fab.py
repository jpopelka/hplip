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

__version__ = '3.0'
__title__ = "Fax Address Book"
__doc__ = "A simple fax address book for HPLIP."

import cmd
from base.g import *
from base import utils
import getopt

log.set_module("hp-fab")


USAGE = [(__doc__, "", "name", True),
         ("Usage: hp-fab [MODE] [OPTIONS]", "", "summary", True),
         ("[MODE]", "", "header", False),
         ("Enter interactive mode:", "-i or --interactive (see Note 1)", "option", False),
         ("Enter graphical UI mode:", "-u or --gui (Default)", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_HELP,
         utils.USAGE_NOTES,
         ("1. Use 'help' command at the fab > prompt for command help (interactive mode (-i) only).", "", "note", False),
         utils.USAGE_SPACE,
         utils.USAGE_SEEALSO,
         ("hp-sendfax", "", "seealso", False),
         ]

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, 'hp-fab', __version__)
    sys.exit(0)


# Console class (from ASPN Python Cookbook)
# Author:   James Thiele
# Date:     27 April 2004
# Version:  1.0
# Location: http://www.eskimo.com/~jet/python/examples/cmd/
# Copyright (c) 2004, James Thiele
class Console(cmd.Cmd):

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.intro  = "Type 'help' for a list of commands. Type 'exit' or 'quit' to quit."
        self.db =  fax.FaxAddressBook() # kirbybase instance
        self.prompt = log.bold("hp-fab > ")

    # Command definitions
    def do_hist(self, args):
        """Print a list of commands that have been entered"""
        print self._hist

    def do_exit(self, args):
        """Exits from the console"""
        return -1

    def do_quit(self, args):
        """Exits from the console"""
        return -1

    # Command definitions to support Cmd object functionality
    def do_EOF(self, args):
        """Exit on system end of file character"""
        return self.do_exit(args)

    def do_help(self, args):
        """Get help on commands
           'help' or '?' with no arguments prints a list of commands for which help is available
           'help <command>' or '? <command>' gives help on <command>
        """
        # The only reason to define this method is for the help text in the doc string
        cmd.Cmd.do_help(self, args)

    # Override methods in Cmd object
    def preloop(self):
        """Initialization before prompting user for commands.
           Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
        """
        cmd.Cmd.preloop(self)   # sets up command completion
        self._hist    = []      # No history yet
        self._locals  = {}      # Initialize execution namespace for user
        self._globals = {}

        self.do_list('')

    def postloop(self):
        """Take care of any unfinished business.
           Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
        """
        cmd.Cmd.postloop(self)   # Clean up command completion
        print "Exiting..."

    def precmd(self, line):
        """ This method is called after the line has been input but before
            it has been interpreted. If you want to modifdy the input line
            before execution (for example, variable substitution) do it here.
        """
        self._hist += [line.strip()]
        return line

    def postcmd(self, stop, line):
        """If you want to stop the console, return something that evaluates to true.
           If you want to do some post command processing, do it here.
        """
        return stop

    def emptyline(self):
        """Do nothing on empty input line"""
        pass

    def default(self, line):
        print log.red("error: Unrecognized command. Use 'help' to list commands.")

    def get_nickname(self, args, fail_if_match=True, alt_text=False):
        if not args:
            while True:
                if alt_text:
                    nickname = raw_input(log.bold("Enter the entry name (nickname) to add (<enter>=done*, c=cancel) ? ")).strip()
                else:
                    nickname = raw_input(log.bold("Enter the entry name (nickname) (c=cancel) ? ")).strip()

                if nickname.lower() == 'c':
                    print log.red("Canceled")
                    return ''

                if not nickname:
                    if alt_text:
                        return ''
                    else:
                        print log.red("error: Nickname must not be blank.")
                        continue


                if fail_if_match:
                    if self.db.select(['name'], [nickname]):
                        print log.red("error: Entry already exists. Please choose a different name.")
                        continue

                else:
                    if not self.db.select(['name'], [nickname]):
                        print log.red("error: Entry not found. Please enter a different name.")
                        continue

                break

        else:
            nickname = args.strip()

            if fail_if_match:
                if self.db.select(['name'], [nickname]):
                    print log.red("error: Entry already exists. Please choose a different name.")
                    return ''

            else:
                if not self.db.select(['name'], [nickname]):
                    print log.red("error: Entry not found. Please enter a different name.")
                    return ''

        return nickname


    def get_groupname(self, args, fail_if_match=True, alt_text=False):
        all_groups = self.db.AllGroups()

        if not args:
            while True:
                if alt_text:
                    groupname = raw_input(log.bold("Enter the group name to join (<enter>=done*, c=cancel) ? ")).strip()
                else:
                    groupname = raw_input(log.bold("Enter the group name (c=cancel) ? ")).strip()


                if groupname.lower() == 'c':
                    print log.red("Canceled")
                    return ''

                if not groupname:
                    if alt_text:
                        return ''
                    else:
                        print log.red("error: The group name must not be blank.")
                        continue

                if fail_if_match: 
                    if groupname in all_groups:
                        print log.red("error: Entry already exists. Please choose a different name.")
                        continue

                else:
                    if groupname not in all_groups:
                        print log.red("error: Entry not found. Please enter a different name.")
                        continue

                break

        else:
            groupname = args.strip()

            if fail_if_match: 
                if groupname in all_groups:
                    print log.red("error: Entry already exists. Please choose a different name.")
                    return ''

            else:
                if groupname not in all_groups:
                    print log.red("error: Entry not found. Please enter a different name.")
                    return ''

        return groupname

    def do_list(self, args):
        """ 
        List entries and/or groups.
        list [groups|entries|all|]
        dir [groups|entries|all|]
        """

        if args:
            scope = args.strip().split()[0]

            if args.startswith('ent'):
                self.do_entries('')
                return
            elif args.startswith('gro'):
                self.do_groups('')
                return

        self.do_entries('')
        self.do_groups('')

    do_dir = do_list

    def do_entries(self, args):
        """
        List entries.
        entries
        """
        all_entries = self.db.AllRecordEntries()
        log.debug(all_entries)

        print log.bold("\nEntries:\n")
        if len(all_entries) > 0:

            formatter = utils.TextFormatter(
                            (
                                {'width': 28, 'margin' : 2},
                                {'width': 28, 'margin' : 2},
                                {'width': 58, 'margin' : 2},
                            )
                        )

            print formatter.compose(("Name", "Fax Number", "Member of Group(s)"))
            print formatter.compose(('-'*28, '-'*28, '-'*58))

            # TODO: Sort the list by (nick)name
            for abe in all_entries:
                print formatter.compose((abe.name, abe.fax, abe.groups))
        else:
            print "(None)"

        print

    def do_groups(self, args):
        """ 
        List groups.
        groups
        """
        all_groups = self.db.AllGroups()
        log.debug(all_groups)

        print log.bold("\nGroups:\n")
        if len(all_groups):

            formatter = utils.TextFormatter(
                            (
                                {'width': 28, 'margin' : 2},
                                {'width': 58, 'margin' : 2},
                            )
                        )
            print formatter.compose(("Group", "Members"))
            print formatter.compose(('-'*28, '-'*58))

            # TODO: Sort the list by group name
            for group in all_groups:
                print formatter.compose((group, ', '.join(self.db.GroupEntries(group))))
        else:
            print "(None)"

        print


    def do_edit(self, args):
        """
        Edit an entry.
        edit [entry]
        modify [entry]
        """
        nickname = self.get_nickname(args, fail_if_match=False)
        if not nickname: return

        abe = fax.AddressBookEntry(self.db.select(['name'], [nickname])[0])
        log.debug(abe)

        print log.bold("\nEdit/modify entry information for %s:\n" % abe.name)

        save_title = abe.title
        title = raw_input(log.bold("Title (<enter>='%s', c=cancel)? " % save_title)).strip()

        if title.lower() == 'c':
            print log.red("Canceled")
            return

        if not title:
            title = save_title

        save_firstname = abe.firstname
        firstname = raw_input(log.bold("First name (<enter>='%s', c=cancel)? " % save_firstname)).strip()

        if firstname.lower() == 'c':
            print log.red("Canceled")
            return

        if not firstname:
            firstname = save_firstname

        save_lastname = abe.lastname
        lastname = raw_input(log.bold("Last name (<enter>='%s', c=cancel)? " % save_lastname)).strip()

        if lastname.lower() == 'c':
            print log.red("Canceled")
            return

        if not lastname:
            lastname = save_lastname

        save_faxnum = abe.fax
        while True:
            faxnum = raw_input(log.bold("Fax Number (<enter>='%s', c=cancel)? " % save_faxnum)).strip()

            if faxnum.lower() == 'c':
                print log.red("Canceled")
                return

            if not faxnum and not save_faxnum:
                print log.red("error: Fax number must not be empty.")
                continue

            if not faxnum:
                faxnum = save_faxnum

            ok = True
            for c in faxnum:
                if c not in '0123456789-(+) *#':
                    print log.red("error: Invalid characters in fax number. Fax number may only contain '0123456789-(+) '")
                    ok = False
                    break


            if ok: break

        save_notes = abe.notes
        notes = raw_input(log.bold("Notes (<enter>='%s', c=cancel)? " % save_notes)).strip()

        if notes.lower() == 'c':
            print log.red("Canceled")
            return

        if not notes:
            notes = save_notes

        if abe.group_list:
            print "\nLeave or Stay in a Group:\n"

        new_groups = []
        for g in abe.group_list:
            user_input = raw_input(log.bold("Stay in group '%s' (y=yes*, n=no (leave), c=cancel) ? " % g)).strip().lower()

            if not user_input or user_input == 'y':
                new_groups.append(g)

            if user_input == 'c':
                print log.red("Canceled")
                return


        print "\nJoin New Group(s):\n"

        while True:
            add_group = self.get_groupname('', fail_if_match=False, alt_text=True) 

            if add_group.lower() == 'c':
                print log.red("Canceled")
                return

            if not add_group.lower():
                break

            all_groups = self.db.AllGroups()

            if add_group not in all_groups:
                log.warn("Group not found.")
                user_input = raw_input(log.bold("Is this a new group (y=yes*, n=no) ?")).strip().lower()

                if user_input == 'n':
                    continue

            if add_group in abe.groups:
                log.error("error: Group already specified. Choose a different group name or press <enter> to continue.")
                continue

            new_groups.append(add_group)


        self.db.update(['name'], [nickname], fax.AddressBookEntry((-1, nickname, title, firstname, lastname, faxnum, ','.join(new_groups), notes)))
        self.do_show(nickname)

        print

    do_modify = do_edit


    def do_editgrp(self, args):
        """
        Edit a group.
        editgrp [group]
        modifygrp [group]
        """
        group = self.get_groupname(args, fail_if_match=False)
        if not group: return

        old_entries = self.db.GroupEntries(group)

        new_entries = []

        print "\nLeave or Remove Existing Entries in Group:\n"

        for e in old_entries:
            user_input = raw_input(log.bold("Leave entry '%s' in this group (y=yes*, n=no (remove), c=cancel) ? " % e)).lower().strip()

            if not user_input or user_input == 'y':
                new_entries.append(e)

            if user_input == 'c':
                print log.red("Canceled")
                return

        print "\nAdd New Entries in Group:\n"

        while True:
            nickname = self.get_nickname('', fail_if_match=False, alt_text=True)

            if nickname.lower() == 'c':
                print log.red("Canceled")
                return

            if not nickname.lower():
                break

            new_entries.append(nickname)

        self.db.UpdateGroupEntries(group, new_entries)

        print

    do_modifygrp = do_editgrp


    def do_add(self, args):
        """
        Add an entry.
        add [entry]
        new [entry]
        """
        nickname = self.get_nickname(args, fail_if_match=True)
        if not nickname: return

        print log.bold("\nEnter entry information for %s:\n" % nickname)

        title = raw_input(log.bold("Title (c=cancel)? ")).strip()

        if title.lower() == 'c':
            print log.red("Canceled")
            return

        firstname = raw_input(log.bold("First name (c=cancel)? ")).strip()

        if firstname.lower() == 'c':
            print log.red("Canceled")
            return

        lastname = raw_input(log.bold("Last name (c=cancel)? ")).strip()

        if lastname.lower() == 'c':
            print log.red("Canceled")
            return

        while True:
            faxnum = raw_input(log.bold("Fax Number (c=cancel)? ")).strip()

            if faxnum.lower() == 'c':
                print log.red("Canceled")
                return

            if not faxnum:
                print log.red("error: Fax number must not be empty.")
                continue

            ok = True
            for c in faxnum:
                if c not in '0123456789-(+) *#':
                    print log.red("error: Invalid characters in fax number. Fax number may only contain '0123456789-(+) *#'")
                    ok = False
                    break


            if ok: break

        notes = raw_input(log.bold("Notes (c=cancel)? ")).strip()

        if notes.strip().lower() == 'c':
            print log.red("Canceled")
            return

        groups = []
        all_groups = self.db.AllGroups()
        while True:
            add_group = raw_input(log.bold("Member of group (<enter>=done*, c=cancel) ?" )).strip()

            if add_group.lower() == 'c':
                print log.red("Canceled")
                return

            if not add_group:
                break

            if add_group not in all_groups:
                log.warn("Group not found.")

                while True:
                    user_input = raw_input(log.bold("Is this a new group (y=yes*, n=no) ?")).lower().strip()

                    if user_input not in ['', 'n', 'y']:
                        log.error("Please enter 'y', 'n' or press <enter> for 'yes'.")
                        continue

                    break

                if user_input == 'n':
                    continue

            if add_group in groups:
                log.error("Group already specified. Choose a different group name or press <enter> to continue.")
                continue

            groups.append(add_group)

        self.db.insert(fax.AddressBookEntry((-1, nickname, title, firstname, lastname, faxnum, ','.join(groups), notes)))
        self.do_show(nickname)


    do_new = do_add


    def do_addgrp(self, args):
        """
        Add a group.
        addgrp [group]
        newgrp [group]
        """
        group = self.get_groupname(args, fail_if_match=True)
        if not group: return

        entries = []
        while True:
            nickname = self.get_nickname('', fail_if_match=False, alt_text=True)

            if nickname.lower() == 'c':
                print log.red("Canceled")
                return

            if not nickname.lower():
                break

            entries.append(nickname)

        self.db.UpdateGroupEntries(group, entries)

        print

    do_newgrp = do_addgrp


    def do_view(self, args):
        """
        View all entry data.
        view
        """
        all_entries = self.db.AllRecordEntries()
        log.debug(all_entries)

        print log.bold("\nView all Data:\n")
        if len(all_entries) > 0:

            formatter = utils.TextFormatter(
                            (
                                {'width': 20, 'margin' : 2}, # name
                                {'width': 20, 'margin' : 2}, # title
                                {'width': 20, 'margin' : 2}, # first
                                {'width': 20, 'margin' : 2}, # last
                                {'width': 20, 'margin' : 2}, # fax
                                {'width': 20, 'margin' : 2}, # notes
                                {'width': 20, 'margin' : 2}, # groups
                                {'width': 8, 'margin' : 2}, # recno
                            )
                        )

            print formatter.compose(("Name", "Title", "First Name", "Last Name", "Fax", "Notes", "Member of Group(s)", "(recno)"))
            print formatter.compose(('-'*20, '-'*20, '-'*20, '-'*20, '-'*20, '-'*20, '-'*20, '-'*8))

            # TODO: Sort the list by (nick)name
            for abe in all_entries:
                print formatter.compose((abe.name, abe.title, abe.firstname, abe.lastname, abe.fax, abe.notes, abe.groups, str(abe.recno)))
        else:
            print "(None)"

        print



    def do_show(self, args):
        """
        Show an entry (all details).
        show [entry]
        details [entry]
        """
        name = self.get_nickname(args, fail_if_match=False)
        if not name: return

        rec = self.db.select(['name'], [name])
        if rec:
            abe = fax.AddressBookEntry(rec[0])

            formatter = utils.TextFormatter(
                            (
                                {'width': 28, 'margin' : 2},
                                {'width': 58, 'margin' : 2},
                            )
                        )

            print log.bold("\n%s\n" % name)

            print formatter.compose(("Name:", abe.name))
            print formatter.compose(("Title:", abe.title))
            print formatter.compose(("First Name:", abe.firstname))
            print formatter.compose(("Last Name:", abe.lastname))
            print formatter.compose(("Fax Number:", abe.fax))
            print formatter.compose(("Member of Group(s):", abe.groups))
            print formatter.compose(("Notes:", abe.notes))
            print formatter.compose(("(recno):", str(abe.recno)))

        else:
            print log.red("error: Entry name not found. Use 'list entries' to view all entry names.")

        print

    do_details = do_show

    def do_rm(self, args):
        """
        Remove an entry.
        rm [entry]
        del [entry]
        """
        nickname = self.get_nickname(args, fail_if_match=False)
        if not nickname: return

        self.db.delete(['name'], [nickname])

        print

    do_del = do_rm

    def do_rmgrp(self, args):
        """
        Remove a group.
        rmgrp [group]
        delgrp [group]
        """
        group = self.get_groupname(args, fail_if_match=False)
        if not group: return

        self.db.DeleteGroup(group)

        print

    do_delgrp = do_rmgrp


    def do_about(self, args):
        """About fab."""
        utils.log_title(__title__, __version__)


mode = GUI_MODE
mode_specified = False

try:
    opts, args = getopt.getopt(sys.argv[1:], 'l:hgiu', 
        ['level=', 'help', 'help-rest', 'help-man',
         'help-desc', 'gui', 'interactive'])

except getopt.GetoptError:
    usage()

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    if o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o == '-g':
        log.set_level('debug')

    elif o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')

    elif o == '--help-desc':
        print __doc__,
        sys.exit(0)

    elif o in ('-i', '--interactive'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-i or -u).")
            sys.exit(1)

        mode = INTERACTIVE_MODE
        mode_specified = True

    elif o in ('-u', '--gui'):
        if mode_specified:
            log.error("You may only specify a single mode as a parameter (-i or -u).")
            sys.exit(1)

        mode = GUI_MODE
        mode_specified = True

utils.log_title(__title__, __version__)

# Security: Do *not* create files that other users can muck around with
os.umask(0037)

if mode == GUI_MODE:
    if not os.getenv('DISPLAY'):
        mode = NON_INTERACTIVE_MODE
    elif not utils.checkPyQtImport():
        mode = NON_INTERACTIVE_MODE

if mode == GUI_MODE:
    from qt import *
    from ui.faxaddrbookform import FaxAddrBookForm

    app = None
    addrbook = None
    # create the main application object
    app = QApplication(sys.argv)
    
    loc = user_cfg.ui.get("loc", "system")
    if loc.lower() == 'system':
        loc = str(QTextCodec.locale())
        log.debug("Using system locale: %s" % loc)

    if loc.lower() != 'c':
        log.debug("Trying to load .qm file for %s locale." % loc)
        trans = QTranslator(None)
        qm_file = 'hplip_%s.qm' % loc
        log.debug("Name of .qm file: %s" % qm_file)
        loaded = trans.load(qm_file, prop.localization_dir)

        if loaded:
            app.installTranslator(trans)
        else:
            loc = 'c'
    else:
        loc = 'c'

    if loc == 'c':
        log.debug("Using default 'C' locale")
    else:
        log.debug("Using locale: %s" % loc)

    addrbook = FaxAddrBookForm()
    addrbook.show()
    app.setMainWidget(addrbook)

    try:
        log.debug("Starting GUI loop...")
        app.exec_loop()
    except KeyboardInterrupt:
        pass
    except:
        log.exception()

    sys.exit(0)

else: # INTERACTIVE_MODE
    try:
        from fax import fax
    except ImportError:
        # This can fail on Python < 2.3 due to the datetime module
        log.error("Fax address book disabled - Python 2.3+ required.")
        sys.exit(1)    

    console = Console()
    try:
        try:
            console.cmdloop()
        except KeyboardInterrupt:
            log.error("Aborted.")
        except Exception, e:
            #log.error("An error occured: %s" % e)
            log.exception()
    finally:
        pass
