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

#=== IMPORT ====================================================================

#system imports
import pygtk
pygtk.require('2.0')
import gobject
import gtk

from GTG.core.gtg_tags import Tag, TagStore

### MODEL ######################################################################
# Typically for usage in UI, as it presents an abstract model of the data store

class TagTreeModel(gtk.TreeStore):

    TAGS_MODEL_OBJ   = 0
    TAGS_MODEL_COLOR = 1
    TAGS_MODEL_NAME  = 2
    TAGS_MODEL_COUNT = 3
    TAGS_MODEL_SEP   = 4

    column_types     = ( gobject.TYPE_PYOBJECT, \
                         str,                   \
                         str,                   \
                         str,                   \
                         bool)

    def __init__(self):

        gtk.TreeStore.__init__(self, *self.column_types)

        #Build the "all tags tag"
        self.alltags_tag = Tag("alltags_tag")
        self.alltags_tag.set_attribute("special","all")
        self.alltags_tag.set_attribute("icon","gtg-tags-all")
        #Build the "without tag tag"
        self.notag_tag = Tag("notag_tag")
        self.notag_tag.set_attribute("special","notag")
        self.notag_tag.set_attribute("icon","gtg-tags-none")

        # Fill with default data
        self.append(None, [self.alltags_tag,None,_("<span weight=\"bold\">All tags</span>"),0,False])
        self.append(None, [self.notag_tag,None,_("<span weight=\"bold\">Tasks without tags</span>"),1,False])
        self.append(None, [None,None,"","",True])


