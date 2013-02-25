# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

import xml.sax.saxutils as saxutils

from GTG.core import CoreConfig
from liblarch import TreeNode


class Tag(TreeNode):
    """A short name that can be applied to L{Task}s.

    I mean, surely you must know what a tag is by now. Think Gmail,
    del.icio.us, Flickr et al.

    A tag is defined by its name, which in most cases is C{@something}. A tag
    can also have multiple arbitrary attributes. The only attribute enforced
    for tags is C{name}, which always matches L{Tag.get_name()}.
    """

    def __init__(self, name, req, attributes={}):
        """Construct a tag.

        @param name: The name of the tag. Should be a string, generally
            a short one.
        @param attributes: Allow having initial set of attributes without
            calling _save callback
        """
        TreeNode.__init__(self, name)
        self._name = saxutils.unescape(str(name))
        self.req = req
        self._save = None
        self._attributes = {'name': self._name}
        for key, value in attributes.iteritems():
            self.set_attribute(key, value)

        self.viewcount = None

    def __get_viewcount(self):
        if not self.viewcount and self.get_name() != "gtg-tags-sep":
            basetree = self.req.get_basetree()
            self.viewcount = basetree.get_viewcount(self.get_name(), False)

            sp_id = self.get_attribute("special")
            if sp_id == "all":
                pass
            if sp_id == "notag":
                self.viewcount.apply_filter('notag', refresh=False)
            # No special means a normal tag
            else:
                self.viewcount.apply_filter(self.get_name(), refresh=False)
            self.viewcount.apply_filter('active')
            self.viewcount.register_cllbck(self.modified)
        return self.viewcount

    def apply_filter(self, filtername):
        if self.viewcount:
            self.viewcount.apply_filter(filtername)

    def unapply_filter(self, filtername):
        if self.viewcount:
            self.viewcount.unapply_filter(filtername)

    # When a task change a tag, we may want to manually update
    # To ensure that the task is well counted/uncounted for that tag
    def update_task(self, task_id):
        vc = self.__get_viewcount()
        vc.modify(task_id)

    # overiding some functions to not allow dnd of special tags
    def add_parent(self, parent_id):
        p = self.req.get_tag(parent_id)
        if p and not self.is_special() and not p.is_special():
            TreeNode.add_parent(self, parent_id)

    def add_child(self, child_id):
        special_child = self.req.get_tag(child_id).is_special()
        if not self.is_special() and not special_child:
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
        modified = False
        if att_name == "name":
            raise Set_Name_Attribute_Error(
                "The name of tag cannot be set manually")
        elif att_name == "parent":
            self.add_parent(att_value)
            modified = True
        else:
            # Attributes should all be strings.
            val = unicode(str(att_value), "UTF-8")
            self._attributes[att_name] = val
            if self._save:
                self._save()
            modified = True
        if modified:
            self.modified()
            self.notify_related_tasks()

    def get_attribute(self, att_name):
        """Get the attribute C{att_name}.

        Returns C{None} if there is no attribute matching C{att_name}.
        """
        to_return = None
        if att_name == 'parent':
            if self.has_parent():
                parents_id = self.get_parents()
                if len(parents_id) > 0:
                    to_return = reduce(lambda a, b: "%s,%s" % (a, b),
                                       parents_id)
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
        self.modified()
        self.notify_related_tasks()

    def get_all_attributes(self, butname=False, withparent=False):
        """Return a list of all attribute names.

        @param butname: If True, exclude C{name} from the list of attribute
            names.
        @param withparent: If True, the "parent" attribute is attached
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
        """Returns the number of all related tasks"""
        # this method purposefully doesn't rely on get_related_tasks()
        # which does a similar job, in order to benefit from liblarch
        # optimizations
        vc = self.__get_viewcount()
        if vc:
            return vc.get_n_nodes()
        else:
            return 0

    def get_related_tasks(self, tasktree=None):
        """Returns all related tasks node ids"""
        if not tasktree:
            tasktree = self.req.get_tasks_tree()
        sp_id = self.get_attribute("special")
        if sp_id == "all":
            toreturn = tasktree.get_nodes(withfilters=['active'])
        elif sp_id == "notag":
            toreturn = tasktree.get_nodes(withfilters=['notag'])
        elif sp_id == "sep":
            toreturn = []
        else:
            tname = self.get_name()
            toreturn = tasktree.get_nodes(withfilters=[tname])
        return toreturn

    def notify_related_tasks(self):
        """Notify changes to all related tasks"""
        for task_id in self.get_related_tasks():
            my_task = self.req.get_task(task_id)
            my_task.modified()

    # is it useful to keep the tag in the tagstore.
    # if no attributes and no tasks, it is not useful.
    def is_removable(self):
        attr = self.get_all_attributes(butname=True, withparent=True)
        return (len(attr) <= 0 and not self.is_used())

    def is_special(self):
        return bool(self.get_attribute('special'))

    def is_search_tag(self):
        return CoreConfig.SEARCH_TAG in self.get_parents()

    def is_used(self):
        return self.get_total_tasks_count() > 0

    def is_actively_used(self):
        return self.is_search_tag() or self.is_special() or\
            self.get_active_tasks_count() > 0

    def __str__(self):
        return "Tag: %s" % self.get_name()


class Set_Name_Attribute_Error(Exception):
    """Exception raised when try to set attribute to name"""
    pass
