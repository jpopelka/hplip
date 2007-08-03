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

# Std Lib
import sys
import re

# Local
from g import *
import pexpect
import utils

def enter_yes_no(question, default_value='y'):
    if type(default_value) == type(True):
        if default_value:
            default_value = 'y'
        else:
            default_value = 'n'
            
    assert default_value in ['y', 'n']
    
    if default_value == 'y':
        question += " (y=yes*, n=no, q=quit) ? "
    else:
        question += " (y=yes, n=no*, q=quit) ? "
    
    while True:
        user_input = raw_input(log.bold(question)).lower().strip()
        
        if not user_input and default_value:
            return True, default_value

        if user_input == 'n':
            return True, False

        if user_input == 'y':
            return True, True

        if user_input == 'q':
            return False, default_value

        log.error("Please press <enter> or enter 'y', 'n', or 'q'.")

def enter_range(question, min_value, max_value, default_value=None):
    while True:
        user_input = raw_input(log.bold(question)).lower().strip()

        if not user_input:
            if default_value is not None:
                return True, default_value

        if user_input == 'q':
            return False, default_value

        try:
            value_int = int(user_input)
        except ValueError:
            log.error('Please enter a number between %d and %d, or "q" to quit.' % 
                (min_value, max_value))
            continue

        if value_int < min_value or value_int > max_value:
            log.error('Please enter a number between %d and %d, or "q" to quit.' % 
                (min_value, max_value))
            continue

        return True, value_int

def enter_choice(question, choices, default_value=None):
    if 'q' not in choices:
        choices.append('q')
        
    while True:
        user_input = raw_input(log.bold(question)).lower().strip()

        if (not user_input and default_value) or user_input == default_value:
            return True, default_value

        if user_input == 'q':
            return False, default_value

        if user_input in choices:
            return True, user_input

        log.error("Please enter %s or press <enter> for the default of '%s'." % 
            (', '.join(["'%s'" % x for x in choices]), default_value))


def title(text):
    log.info("")
    log.info("")
    log.info(log.bold(text))
    log.info(log.bold("-"*len(text)))
    
def header(text):
    c = len(text)
    log.info("")
    log.info("-"*(c+4))
    log.info("| "+text+" |")
    log.info("-"*(c+4))
    log.info("")
    
def load_paper_prompt():
    return continue_prompt("A page will be printed.\nPlease load plain paper into the printer.")

def continue_prompt(prompt=''):
    while True:
        x = raw_input(log.bold(prompt + " Press <enter> to continue or 'q' to quit: ")).lower().strip()
        
        if not x:
            return True
            
        elif x == 'q':
            return  False
    
        log.error("Please press <enter> or enter 'q' to quit.")
       

def enter_regex(regex, prompt, pattern, default_value=None):
    re_obj = re.compile(regex)
    while True:
        x = raw_input(log.bold(prompt))
        
        if not x and default_value is not None:
            return default_value, x
            
        elif x == 'q':
            return False, default_value
            
        match = re_obj.search(x)
        
        if not match:
            log.error("Incorrect input. Please enter correct input.")
            continue
            
        return True, x
        
        
def ttysize():
    import commands
    ln1 = commands.getoutput('stty -a').splitlines()[0]
    vals = {'rows':None, 'columns':None}
    for ph in ln1.split(';'):
        x = ph.split()
        if len(x) == 2:
            vals[x[0]] = x[1]
            vals[x[1]] = x[0]
    return int(vals['rows']), int(vals['columns'])
    
    
class ProgressMeter:
    def __init__(self, prompt="Progress:"):
        self.progress = 0
        self.prompt = prompt
        self.prev_length = 0
        self.spinner = "\|/-\|/-"
        self.spinner_pos = 0
        self.update(0)
        
    def update(self, progress, msg=''): # progress in %
        self.progress = progress
        if self.progress > 100:
            self.progress = 100
        elif self.progress < 0:
            self.progress = 0
        
        sys.stdout.write("\b" * self.prev_length)
        
        x = "%s [%s%s%s] %d%%  %s   " % \
            (self.prompt, '*'*(self.progress-1), self.spinner[self.spinner_pos], 
             ' '*(100-self.progress), self.progress, msg)
            
        sys.stdout.write(x)
        sys.stdout.flush()
        self.prev_length = len(x)
        self.spinner_pos = (self.spinner_pos + 1) % 8
        
        
        
