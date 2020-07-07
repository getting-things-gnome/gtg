#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
# Copyright (c) 2020 Jean-François Fortin Tam
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

"""
Contains the info shown in GTG's About/Credits dialog.

Should be updated for every release.
"""

from datetime import date
from gettext import gettext as _

# These variables get used by main_window.py to set the About dialog's metadata.
# Translator credits are set dynamically in main_window.py, not hardcoded.
NAME = "Getting Things GNOME!"
SHORT_DESCRIPTION = _("""A personal productivity tool for GNOME,
inspired by the GTD methodology.""") # A manual line break looks better in the About dialog.
URL = "https://wiki.gnome.org/Apps/GTG"
TRANSLATE_URL = "https://github.com/getting-things-gnome/gtg/"
REPORT_BUG_URL = "https://github.com/getting-things-gnome/gtg/issues/new"
EMAIL = "gtg-contributors@lists.launchpad.net"
VERSION = '0.4.0'

AUTHORS_MAINTAINERS = """
• Diego Garcia Gangl
• Jean-François Fortin Tam
• Lionel Dricot
"""
# Per-release stats generated as per the "release process and checklist.md" file.
# Including contributors with 2 or more commits.
# No need to add extra line breaks between commas, Python/GTK handles them.
# Don't indend lines inside a multi-line string, or it'll show in the About dialog.
AUTHORS_RELEASE_CONTRIBUTORS = """
• Diego Garcia Gangl
• Izidor Matušov
• Jean-François Fortin Tam
• Mart Raudsepp
• Xuan Hu
• Nimit Shah
• Parin Porecha
• Lionel Dricot
• Sagar Ghuge
• Àlex Magaz Graça
• Sara Ribeiro
• Jakub Brindza
• Parth Panchal
• Luca Falavigna
• Atit Anand
• Chenxiong Qi
• "Neui"
• Pawan Hegde
• Amy Chan
• Olivier Mehani
• Sushant Raikar
• J. Diez
• A. MacHattie
• Bertrand Rousseau
• François Boulogne
• Joe R. Nassimian
• Josh Crompton
• Thomas Spura
"""

ARTISTS = ["Kalle Persson (logo)", "Bertrand Rousseau (UX)", "Jean-François Fortin Tam (UX)"]
ARTISTS.sort()
DOCUMENTERS = [ "Danielle Vansia", "Radina Matic", "Jean-François Fortin Tam"]
