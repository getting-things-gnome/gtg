# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
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

from GTG.taskbrowser.browser import TaskBrowser
from GTG.core.dbuswrapper import DBusTaskWrapper

class Manager():

    def __init__(self,req,config,logger=None):
        self.config = config
        self.req = req
        self.logger = logger

    def show_browser(self):
        tb = TaskBrowser(self.req, self.config, logger=self.logger)
        DBusTaskWrapper(self.req, tb)
        tb.main()



