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

#The tagstore is where the tag objects are handled. See the end of the file for
#the tag object implementation

import os

from GTG.core      import CoreConfig
from GTG.core.tree import Tree, TreeNode
from GTG.tools     import cleanxml

XMLFILE = "tags.xml"
XMLROOT = "tagstore"

# There's only one Tag store by user. It will store all the tag used
# and their attribute.
class TagStore :
    
    def __init__(self,requester):
        self.req = requester
        self.tree = Tree()
        self.tags={}
        self.root = self.tree.get_root()
        self.filename = os.path.join(CoreConfig.DATA_DIR,XMLFILE)
        doc,self.xmlstore = cleanxml.openxmlfile(self.filename,XMLROOT) #pylint: disable-msg=W0612
        for t in self.xmlstore.childNodes:
            #We should only care about tag with a name beginning with "@"
            #Other are special tags
            tagname = t.getAttribute("name")
            tag = self.new_tag(tagname)
            attr = t.attributes
            i = 0
            while i < attr.length :
                at_name = attr.item(i).name
                at_val = t.getAttribute(at_name)
                tag.set_attribute(at_name,at_val)
                i += 1
            parent = tag.get_attribute('parent')
            if parent:
                pnode=self.new_tag(parent)
                tag.reparent(pnode, update_attr=False)
        
        #Now we build special tags. Special tags are not
        #in the traditional tag list
        #Their name doesn't begin with "@"
        
#        #Build the "all tags tag"
#        self.alltag_tag = Tag("alltags_tag",save_cllbk=self.save)
#        self.alltag_tag.set_attribute("special","all")
#        self.alltag_tag.set_attribute("icon","gtg-tags-all")
#        #Build the "without tag tag"
#        self.notag_tag = Tag("notag_tag",save_cllbk=self.save)
#        self.notag_tag.set_attribute("special","notag")
#        self.notag_tag.set_attribute("icon","gtg-tags-none")

    def get_tree(self):
        return self.tree

    def new_tag(self, tagname):
        """Create a new tag and return it or return the existing one
        with corresponding name"""
        #we create a new tag from a name
        tname = tagname.encode("UTF-8")
        if tname not in self.tags:
            tag = Tag(tname, save_cllbk=self.save, req=self.req)
            tag.reparent(self.root)
            self.tags[tname]=tag
            return tag
        else:
            return self.tags[tname]
        
    def add_tag(self, tag):
        name = tag.get_name()
        #If tag does not exist in the store, we add it
        if name not in self.tags:
            tag.reparent(self.root)
            self.tags[name]=tag
        #else, we just take the attributes of the new tag
        #This allow us to keep attributes of the old tag
        #that might be not set in the new one
        else :
            atts = tag.get_all_attributes()
            for att_name in atts:
                val = tag.get_attribute(att_name)
                if att_name != 'name' and val:
                    self.tags[name].set_attribute(att_name,val)

    def get_tag(self, tagname):
        return self.tags.get(tagname, None)

#    def get_alltag_tag(self):
#        """Return the special tag 'All tags'"""
#        return self.alltag_tag
#    
#    def get_notag_tag(self):
#        """Return the special tag 'No tags'"""
#        return self.notag_tag
    
    def get_all_tags_name(self, attname=None, attvalue=None):
        """Return the name of all tags
        Optionally, if you pass the attname and attvalue argument, it will
        only add tags that have the given value for the given attribute
        excluding tags that don't have this attribute
        (except if attvalue is None)"""
        l = []
        for t in self.tags.values():
            if not attname :
                l.append(t.get_name())
            elif t.get_attribute(attname) == attvalue:
                l.append(t.get_name())
        return l
        
    def get_all_tags(self, attname=None, attvalue=None):
        l = []
        for t in self.tags.values():
            if not attname:
                l.append(t)
            elif t.get_attribute(attname) == attvalue:
                l.append(t)
        return l

    def save(self):
        doc,xmlroot = cleanxml.emptydoc(XMLROOT)
        tags = self.get_all_tags()
        already_saved = [] #We avoid saving the same tag twice
        #we don't save tags with no attributes
        #It saves space and allow the saved list growth to be controlled
        for t in tags:
            attr = t.get_all_attributes(butname=True)
            if "special" in attr:
                continue
            if len(attr) > 0 :
                tagname = t.get_name()
                if not tagname in already_saved :
                    t_xml = doc.createElement("tag")
                    t_xml.setAttribute("name",tagname)
                    already_saved.append(tagname)
                    for a in attr :
                        value = t.get_attribute(a)
                        t_xml.setAttribute(a,value)
                    xmlroot.appendChild(t_xml)          
                    cleanxml.savexml(self.filename,doc)
                
### Tag Objects ##############################################################
#
class Tag(TreeNode):
    """A short name that can be applied to L{Task}s.

    I mean, surely you must know what a tag is by now. Think Gmail,
    del.icio.us, Flickr et al.

    A tag is defined by its name, which in most cases is C{@something}. A tag
    can also have multiple arbitrary attributes. The only attribute enforced
    for tags is C{name}, which always matches L{Tag.get_name()}.
    """

    def __init__(self, name, save_cllbk=None,req=None):
        """Construct a tag.

        @param name: The name of the tag. Should be a string, generally a
            short one.
        @param save_cllbk: A nullary callable, called whenever an attribute
            is set.
        """
        TreeNode.__init__(self, name)
        self._name = str(name)
        self.req = req
        self._attributes = {'name': self._name}
        self._save = save_cllbk
        #list of tasks associated with this tag
        self.tasks = []

    def get_name(self):
        """Return the name of the tag."""
        return self.get_attribute("name")

    def set_attribute(self, att_name, att_value):
        """Set an arbitrary attribute.

        This will call the C{save_cllbk} callback passed to the constructor.

        @param att_name: The name of the attribute.
        @param att_value: The value of the attribute. Will be converted to a
            string.
        """
        if att_name == "name":
            # Warning : only the constructor can set the "name".
            #
            # XXX: This should actually raise an exception, or warn, or
            # something. The Zen of Python says "Errors should never pass
            # silently." -- jml, 2009-07-17
            return
        # Attributes should all be strings.
        val = unicode(str(att_value), "UTF-8")
        self._attributes[att_name] = val
        if self._save:
            self._save()

    def get_attribute(self, att_name):
        """Get the attribute C{att_name}.

        Returns C{None} if there is no attribute matching C{att_name}.
        """
        return self._attributes.get(att_name, None)

    def get_all_attributes(self, butname=False):
        """Return a list of all attribute names.

        @param butname: If True, exclude C{name} from the list of attribute
            names.
        """
        attributes = self._attributes.keys()
        if butname:
            attributes.remove('name')
        return attributes

    def reparent(self, parent, update_attr=True):
        if update_attr:
            if isinstance(parent, Tag):
                self.set_attribute('parent', parent.get_name())
            elif 'parent' in self._attributes:
                del self._attributes['parent']
        TreeNode.reparent(self, parent)
        
    def all_children(self):
        l = [self]
        for i in self.get_children_objs():
            l += i.all_children()
        return l

    ### TASK relation ####      
    def add_task(self, tid):
        if tid not in self.tasks:
            self.tasks.append(tid)      
    def remove_task(self,tid):
        if tid in self.tasks:
            self.tasks.remove(tid)          
    def get_tasks(self):
        #return a copy of the list
        toreturn = self.tasks[:]
        return toreturn 
    def get_tasks_nbr(self,workview=False,children=True):
        if workview:
            temp_list = []
            for t in self.tasks:
                ta = self.req.get_task(t)
                if ta.get_status() == "Active" and ta.is_workable() and\
                                                   ta.is_started():
                    temp_list.append(t)
            toreturn = len(temp_list)
        else:
            temp_list = []
            for t in self.tasks:
                ta = self.req.get_task(t)
                if ta.get_status() == "Active" :
                    temp_list.append(t)
            toreturn = len(temp_list)
        if children:
            for i in self.get_children_objs():
                toreturn += i.get_tasks_nbr(workview=workview, children=True)
        return toreturn
    def is_used(self):
        return len(self.tasks) > 0
    def is_actively_used(self):
        toreturn = False
        for task in self.tasks :
            if self.req.get_task(task).get_status() == "Active":
                toreturn = True
        return toreturn

    def __str__(self):
        return "Tag: %s" % self.get_name()
