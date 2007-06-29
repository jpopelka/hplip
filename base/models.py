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

from base.g import *
import os.path, re, glob

class ModelData:
    def __init__(self, root_path=None):
        if root_path is None:
            self.root_path = prop.models_dir
        else:
            self.root_path = root_path

        self.__cache = {}
        self.reset_includes()
        self.sec = re.compile(r'^\[(.*)\]')
        self.inc = re.compile(r'^\%include (.*)', re.IGNORECASE)
        self.inc_line = re.compile(r'^\%(.*)\%')
        self.eq = re.compile(r'^([^=]+)=(.*)')

    def read_all_files(self, unreleased=True):
        released_dat = os.path.join(self.root_path, "models.dat")
        log.debug("Reading file: %s" % released_dat)
        self.read_section(released_dat)

        unreleased_dir = os.path.join(self.root_path, 'unreleased')
        if unreleased and os.path.exists(unreleased_dir):
            unreleased_dat = os.path.join(self.root_path, "unreleased", "unreleased.dat")
            log.debug("Reading file: %s" % unreleased_dat)
            self.read_section(unreleased_dat)

        return self.__cache

    def read_section(self, filename, section=None, is_include=False): # section==None, read all sections
        found, in_section = False, False

        if section is not None:
            section = section.lower()

            if is_include:
                log.debug("Searching for include [%s] in file %s" % (section, filename))
            else:
                log.debug("Searching for section [%s] in file %s" % (section, filename))

        if is_include:
            cache = self.__includes
        else:
            cache = self.__cache

        try:
            fd = file(filename)
        except IOError, e:
            log.error("I/O Error: %s (%s)" % (filename, e.strerror))
            return False

        while True:
            line = fd.readline()

            if not line:
                break

            if line[0] in ('#', ';'):
                continue

            if line[0] == '[':
                if in_section and section is not None:
                    break

                match = self.sec.search(line)

                if match is not None:
                    in_section = True

                    read_section = match.group(1).lower()

                    if section is not None:
                        found = in_section = (read_section == section)

                    if in_section:
                        if section is not None:
                            log.debug("Found section [%s] in file %s" % (read_section, filename))

                        cache[read_section] = {}

                continue

            if line[0] == '%':
                match = self.inc.match(line)

                if match is not None:
                    inc_file = match.group(1)
                    log.debug("Found include file directive: %%include %s" % inc_file)
                    self.__include_files.append(os.path.join(os.path.dirname(filename), inc_file))
                    continue

                if in_section:
                    match = self.inc_line.match(line)

                    if match is not None: 
                        inc_sect = match.group(1)
                        log.debug("Found include directive %%%s%%" % inc_sect)

                        try:
                            self.__includes[inc_sect]
                        except KeyError:
                            for inc in self.__include_files:

                                if self.read_section(inc, inc_sect, True):
                                    break
                            else:
                                log.error("Include %%%s%% not found." % inc_sect)


            if in_section:
                match = self.eq.search(line)

                if match is not None:
                    value = match.group(2)

                    try:
                        value = int(value)
                    except ValueError:
                        pass

                    cache[read_section][match.group(1)] = value

        fd.close()
        return found

    def reset_includes(self):
        self.__include_files = []
        self.__includes = {}


    def __getitem__(self, model):
        model = model.lower()

        try:
            return self.__cache[model]
        except:
            log.debug("Cache miss: %s" % model)

            released_dat = os.path.join(self.root_path, "models.dat")
            log.debug("Reading file: %s" % released_dat)

            if self.read_section(released_dat, model):
                return self.__cache[model]

            unreleased_dir = os.path.join(self.root_path, 'unreleased')

            if os.path.exists(unreleased_dir):
                unreleased_dat = os.path.join(self.root_path, "unreleased", "unreleased.dat")
                log.debug("Reading file: %s" % unreleased_dat)

                if self.read_section(unreleased_dat, model):
                    return self.__cache[model]

            return {}


    def all_models(self):
        return self.__cache

