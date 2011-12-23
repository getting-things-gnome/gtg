# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

"""
tagstore is where the tag objects are handled.  Also defines the Tag object.

Tagstore is to tag as datastore is to task. Of course, the tagstore is
easier.  See the end of this file for the Tag object implementation.
"""

import os
import xml.sax.saxutils as saxutils

from GTG              import _
from GTG.core         import CoreConfig
from GTG.tools.liblarch.tree    import TreeNode
from GTG.tools        import cleanxml
from GTG.tools.logger import Log

XMLFILE = "tags.xml"
XMLROOT = "tagstore"

#TODO: rename this file to tag.py


class Tag(TreeNode):
    """A short name that can be applied to L{Task}s.

    I mean, surely you must know what a tag is by now. Think Gmail,
    del.icio.us, Flickr et al.

    A tag is defined by its name, which in most cases is C{@something}. A tag
    can also have multiple arbitrary attributes. The only attribute enforced
    for tags is C{name}, which always matches L{Tag.get_name()}.
    """

    def __init__(self, name, req):
        """Construct a tag.

        @param name: The name of the tag. Should be a string, generally a
            short one.
        """
        TreeNode.__init__(self, name)
        self._name = saxutils.unescape(str(name))
        self.req = req
        self._attributes = {'name': self._name}
        self._save = None
        self._tasks_count = 0
        #list of tasks associated with this tag

    #overiding some functions to not allow dnd of special tags
    def add_parent(self, parent_id):
        p = self.req.get_tag(parent_id)
        if p and not self.is_special() and not p.is_special():
            TreeNode.add_parent(self, parent_id)

    def add_child(self, child_id):
        if not self.is_special() and not self.req.get_tag(child_id).is_special():
            TreeNode.add_child(self, child_id)

    def get_name(self):
        """Return the name of the tag."""
        return self.get_attribute("name")

    def set_save_callback(self, save):
        self._save = save

    def set_attribute(self, att_name, att_value):
        """Set an arbitrary attribute.

        This will call the C{save_cllbk} callback passed to the constructor.

        @param att_name: The name of the attribute.
        @param att_value: The value of the attribute. Will be converted to a
            string.
        """
        if att_name == "name":
            # Warning : only the constructor can set the "name".
            #or the internalrename
            #This should raise an exception : FIXME
            #print "Error : The name of a tag cannot be manually set"
            pass
        elif att_name == "parent":
            #self.add_parent(att_value)
            self.new_relationship(att_value, self._name)
            self._attributes['parent'] = "We don't care about that value"
        else:
            # Attributes should all be strings.
            val = unicode(str(att_value), "UTF-8")
            self._attributes[att_name] = val
            if self._save:
#                print "saving tag : attribute %s set to %s" %(att_name,att_value)
                self._save()

    def get_attribute(self, att_name):
        """Get the attribute C{att_name}.

        Returns C{None} if there is no attribute matching C{att_name}.
        """
        to_return = None
        if att_name == 'parent':
            if self.has_parent():
                parents_id = self.get_parents()
                if len(parents_id) > 0:
                    to_return = reduce(lambda a, b: "%s,%s" % (a, b), parents_id)
        elif att_name == 'label':
            to_return = self._attributes.get(att_name, self.get_id())
        else:
            to_return = self._attributes.get(att_name, None)
        return to_return

    def del_attribute(self, att_name):
        """Deletes the attribute C{att_name}.
        """
        if not att_name in self._attributes:
            return
        elif att_name in ['name', 'parent']:
            return
        else:
            del self._attributes[att_name]
        if self._save:
            self._save()

    def get_all_attributes(self, butname=False, withparent=False):
        """Return a list of all attribute names.

        @param butname: If True, exclude C{name} from the list of attribute
            names.
        #param withparent: If True, the "parent" attribute is attached
        """
        attributes = self._attributes.keys()
        if butname:
            attributes.remove('name')
        if withparent:
            parent_id = self.get_attribute("parent")
            if parent_id:
                attributes.append("parent")
        return attributes

    ### TASK relation ####

    def get_active_tasks_count(self):
        count = self.__get_count()
        return count

    def get_total_tasks_count(self):
        return self.__get_count()

    def __get_count(self, tasktree=None):
        if not tasktree:
            tasktree = self.req.get_tasks_tree()
        sp_id = self.get_attribute("special")
        if sp_id == "all":
            toreturn = tasktree.get_n_nodes(\
                    withfilters=['active'], include_transparent=False)
        elif sp_id == "notag":
            toreturn = tasktree.get_n_nodes(\
                            withfilters=['notag'], include_transparent=False)
        elif sp_id == "search" :
            if self.req.search_is_active():
                toreturn = (self.req.get_search_tree()).get_n_nodes(include_transparent=False)
            else:
                toreturn = 0
        elif sp_id == "sep" :
            toreturn = 0
        else:
            tname = self.get_name()
            toreturn = tasktree.get_n_nodes(\
                                withfilters=[tname], include_transparent=False)
        return toreturn

    #is it useful to keep the tag in the tagstore.
    #if no attributes and no tasks, it is not useful.
    def is_removable(self):
        attr = self.get_all_attributes(butname=True, withparent=True)
        return (len(attr) <= 0 and not self.is_used())

    def is_special(self):
        return bool(self.get_attribute('special'))

    def is_used(self):
        return self.get_total_tasks_count() > 0

    def is_actively_used(self):
        # FIXME quick hack to alway show views => do we want that?
        # Use constant for that
        search = self.has_parent('search')
        return search or self.is_special() or self.get_active_tasks_count() > 0

    def __str__(self):
        return "Tag: %s" % self.get_name()
