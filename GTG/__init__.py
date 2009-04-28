# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
import os
import locale
#Fallback to LANG C if unsupported locale
try :
    locale.setlocale(locale.LC_ALL, '')
except :
    locale.setlocale(locale.LC_ALL,'C')

import gettext
from gtk import glade
from os.path import pardir, abspath, dirname, join

URL             = "http://gtg.fritalk.com"
EMAIL           = "gtg@lists.launchpad.net"
VERSION         = '0.1.1'
LOCAL_ROOTDIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
DIST_ROOTDIR    = "/usr/share/gtg"

# CREDITS
AUTHORS     = ["Main developers:", \
               "\tLionel Dricot <ploum@ploum.net>", \
               "\tBertrand Rousseau <bertrand.rousseau@gmail.com>", \
               "Contributors:", \
               "\tGérôme Fournier <>", \
               "\tAntons Rebguns <arebgun@gmail.com>", \
               "\tCarl Chenet <chaica@ohmytux.com>", \
               "\tJérôme Guelfucci <jerome.guelfucci@gmail.com>",      \
               "\tLuca Falavigna <dktrkranz@ubuntu.com>", \
               "\tKalle Persson <kalle@kallepersson.se>", \
               "\tJonathan Barnoud <jonathan@barnoud.net>"]
ARTISTS     = ["Kalle Persson <kalle@kallepersson.se>", \
                "Bertrand Rousseau <bertrand.rousseau@gmail.com>"]
ARTISTS.sort()
TRANSLATORS = \
"""Belarusian: Sontan, puccha
French: Lionel Dricot, Rafik Ouerchefani, Bertrand Rousseau, Pititjo
Russian: Alexey Kostyuk, Alexey Nedilko, wiz
Spanish: DiegoJ, Pititjo
Swedish: Kalle Persson"""

#Translation setup (from pyroom)
GETTEXT_DOMAIN = 'gtg'
LOCALE_PATH = abspath(join(dirname(__file__), pardir, 'locales'))
if not os.path.isdir(LOCALE_PATH):
    LOCALE_PATH = '/usr/share/locale'
languages_used = []
lc, encoding = locale.getdefaultlocale()
if lc:
    languages_used = [lc]
lang_in_env = os.environ.get('LANGUAGE', None)
if lang_in_env:
    languages_used.extend(lang_in_env.split(':'))

for module in gettext, glade:
    module.bindtextdomain(GETTEXT_DOMAIN, LOCALE_PATH)
    module.textdomain(GETTEXT_DOMAIN)

translation = gettext.translation(GETTEXT_DOMAIN, LOCALE_PATH,
                                  languages=languages_used,
                                  fallback=True)
import __builtin__
__builtin__._ = translation.gettext

#GTG directories setup
if not os.path.isdir( os.path.join(LOCAL_ROOTDIR,'data') ) :
    DATA_DIR = DIST_ROOTDIR
else:
    DATA_DIR = os.path.join(LOCAL_ROOTDIR,'data')
