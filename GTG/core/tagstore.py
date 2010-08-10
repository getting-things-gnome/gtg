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


# The TagStore is deprecated (we are now using liblarch
# Keeping the code until it is feature complete.


#class TagStore(Tree):

#    
#    def __init__(self,requester):
#        Tree.__init__(self)
#        self.req = requester
#        self.req.connect('tag-modified',self.update_tag)
#        
#        self.loaded = False
#        
#        ### building the initial tags
#        # Build the "all tasks tag"
#        self.alltag_tag = self.new_tag(CoreConfig.ALLTASKS_TAG)
#        self.alltag_tag.set_attribute("special","all")
#        self.alltag_tag.set_attribute("label","<span weight='bold'>%s</span>"\
#                                             % _("All tasks"))
#        self.alltag_tag.set_attribute("icon","gtg-tags-all")
#        self.alltag_tag.set_attribute("order",0)
#        # Build the "without tag tag"
#        self.notag_tag = self.new_tag("gtg-tags-none")
#        self.notag_tag.set_attribute("special","notag")
#        self.notag_tag.set_attribute("label","<span weight='bold'>%s</span>"\
#                                             % _("Tasks with no tags"))
#        self.notag_tag.set_attribute("icon","gtg-tags-none")
#        self.notag_tag.set_attribute("order",1)
#        # Build the separator
#        self.sep_tag = self.new_tag("gtg-tags-sep")
#        self.sep_tag.set_attribute("special","sep")
#        self.sep_tag.set_attribute("order",2)

#        self.filename = os.path.join(CoreConfig().get_data_dir(), XMLFILE)
#        doc, self.xmlstore = cleanxml.openxmlfile(self.filename,
#            XMLROOT) #pylint: disable-msg=W0612
#        for t in self.xmlstore.childNodes:
#            #We should only care about tag with a name beginning with "@"
#            #Other are special tags
#            tagname = t.getAttribute("name")
#            tag = self.new_tag(tagname)
#            attr = t.attributes
#            i = 0
#            while i < attr.length:
#                at_name = attr.item(i).name
#                at_val = t.getAttribute(at_name)
#                tag.set_attribute(at_name, at_val)
#                i += 1
#            parent = tag.get_attribute('parent')
#            if parent:
#                pnode=self.new_tag(parent)
#                tag.set_parent(pnode.get_id())
#        self.loaded = True

#    def update_tag(self,sender,tagname):
#        tag = self.get_tag(tagname)
#        if tag and tag.is_removable():
#            self.remove_tag(tagname)
#            
#    def remove_tag(self,tagname):
#        self.req._tag_deleted(tagname)
#        self.remove_node(tagname)

#    def new_tag(self, tagname):
#        """Create a new tag and return it or return the existing one
#        with corresponding name"""
#        #we create a new tag from a name
#        tname = tagname.encode("UTF-8")
#        #if tname not in self.tags:
#        if not self.has_node(tname):
#            tag = Tag(tname, req=self.req)
#            self.add_node(tag)
#            self.req._tag_added(tname)
#            self.open_tasks.add_filter(tname,None)
#            for c in tag.get_children():
#                self.req._tag_modified(c)
#            #self.tags[tname] = tag
#            tag.set_save_callback(self.save)
#        Log.debug("********* tag added %s *******" % tagname)
##        self.print_tree()
#        return self.get_node(tname)

#    def get_tag(self, tagname):
#        if tagname[0] != "@":
#            tagname = "@" + tagname
#        return self.get_node(tagname)

#    #FIXME : also add a new filter
#    def rename_tag(self, oldname, newname):
#        if len(newname) > 0 and \
#                            oldname not in ['gtg-tags-none','gtg-tags-all']:
#            if newname[0] != "@":
#                newname = "@" + newname
#            if newname != oldname and newname != None :
#                otag = self.get_node(oldname)
#                if not self.has_node(newname):
#                    ntag = self.new_tag(newname)
#                else:
#                    ntag = self.get_tag(newname)
#                    #copy attributes
#                for att in otag.get_all_attributes(butname=True):
#                    if not ntag.get_attribute(att):
#                        ntag.set_attribute(att,otag.get_attribute(att))
#                #restore position in tree
#                if otag.has_parent():
#                    opar = otag.get_parent()
#                    ntag.set_parent(opar)
#                for ch in otag.get_children():
#                    tagchild = self.get_tag(ch)
#                    tagchild.set_parent(ntag)
#                #copy tasks
#                for tid in otag.get_tasks():
#                    tas = self.req.get_task(tid)
#                    tas.rename_tag(oldname,newname)
#                #remove the old one
#                self.remove_tag(oldname)
#                self.req._tag_modified(oldname)
##        print "tag %s has %s tasks" %(newname,self.get_node(newname).get_tasks_nbr())
#                
#    def get_all_tags_name(self, attname=None, attvalue=None):
#        """Return the name of all tags
#        Optionally, if you pass the attname and attvalue argument, it will
#        only add tags that have the given value for the given attribute
#        excluding tags that don't have this attribute
#        (except if attvalue is None)"""
#        l = []
#        for t in self.get_all_nodes():
#            if not attname:
#                l.append(t.get_name())
#            elif t.get_attribute(attname) == attvalue:
#                l.append(t.get_name())
#        return l

#    def get_all_tags(self, attname=None, attvalue=None):
#        l = []
#        for t in self.get_all_nodes():
#            if not attname:
#                l.append(t)
#            elif t.get_attribute(attname) == attvalue:
#                l.append(t)
#        return l

#    def save(self):
#        if self.loaded:
#            doc, xmlroot = cleanxml.emptydoc(XMLROOT)
#            tags = self.get_all_tags()
#            already_saved = [] #We avoid saving the same tag twice
#            #we don't save tags with no attributes
#            #It saves space and allow the saved list growth to be controlled
#            for t in tags:
#                attr = t.get_all_attributes(butname = True, withparent = True)
#                if "special" not in attr and len(attr) > 0:
#                    tagname = t.get_name()
#                    if not tagname in already_saved:
#                        t_xml = doc.createElement("tag")
#                        t_xml.setAttribute("name", tagname)
#                        already_saved.append(tagname)
#                        for a in attr:
#                            value = t.get_attribute(a)
#                            if value:
#                                t_xml.setAttribute(a, value)
#                        xmlroot.appendChild(t_xml)
#            cleanxml.savexml(self.filename, doc)

#    def get_alltag_tag(self):
#        ''' Returns the "All Tasks" tag'''
#        return self.alltag_tag

#    def get_notag_tag(self):
#        ''' Returns the "No tags" tag'''
#        return self.notag_tag

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
        #list of tasks associated with this tag

    def get_name(self):
        """Return the name of the tag."""
        return self.get_attribute("name")

    def set_save_callback(self,save):
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
                    to_return = reduce(lambda a,b: "%s,%s" % (a, b), parents_id)
        elif att_name == 'label':
            to_return = self._attributes.get(att_name,self.get_id())
        else:
            to_return = self._attributes.get(att_name, None)
        return to_return
        
    def del_attribute(self, att_name):
        """Deletes the attribute C{att_name}.
        """
        if not att_name in self._attributes:
            return
        elif att_name in ['name','parent']:
            return
        else:
            del self._attributes[att_name]
        if self._save:
            self._save()

    def get_all_attributes(self, butname=False, withparent = False):
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

    def get_tasks(self,filters=[]):
        tasktree = self.req.get_tasks_tree(name=self.get_name(),refresh=False)
        for f in filters:
            tasktree.apply_filter(f,refresh=False)
        tasktree.apply_filter(self.get_name())
        return tasktree.get_all_nodes()
       
    def get_active_tasks_count(self):
        count = self.__get_count(filters=['active'])
        #PLOUM_DEBUG : this can be optimized by using
        #the existing active tree. FIXME (currently broken)
#        tree = self.req.get_tasks_tree(name='active')
#        count = self.__get_count(tasktree=tree)
#        print "%s has %s tasks" %(self.get_name(),count)
        return count
        
    def get_total_tasks_count(self):
        return self.__get_count()
        
    def __get_count(self,filters=[],tasktree=None):
        if not tasktree:
            tasktree = self.req.get_tasks_tree()
        for f in filters:
            tasktree.apply_filter(f)
        sp_id = self.get_attribute("special")
        if sp_id == "all":
            toreturn = tasktree.get_n_nodes(\
                    withfilters=['no_disabled_tag'],include_transparent=False)
        elif sp_id == "notag":
            toreturn = tasktree.get_n_nodes(\
                            withfilters=['notag'],include_transparent=False)
        elif sp_id == "sep" :
            toreturn = 0
        else:
            tname = self.get_name()
            toreturn = tasktree.get_n_nodes(\
                                withfilters=[tname],include_transparent=False)
        return toreturn
        
    #is it useful to keep the tag in the tagstore.
    #if no attributes and no tasks, it is not useful.
    def is_removable(self):
        attr = self.get_all_attributes(butname = True, withparent = True)
        return (len(attr) <= 0 and not self.is_used())
    def is_used(self):
        return self.get_total_tasks_count() > 0
    def is_actively_used(self):
        if self.get_attribute('special'):
            return True
        else:
#            print "tag %s has %s active tasks" %(self.get_name(),self.get_active_tasks_count())
            return self.get_active_tasks_count() > 0

    def __str__(self):
        return "Tag: %s" % self.get_name()
