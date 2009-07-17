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

#The tagstore is where the tag objects are handled. See the end of the file for
#the tag object implementation

import os

from GTG.core  import CoreConfig
from GTG.tools import cleanxml

XMLFILE = "tags.xml"
XMLROOT = "tagstore"

#There's only one Tag store by user. It will store all the tag used and their attribute.
class TagStore :
    def __init__(self) :
        self.store = {}
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
        
        #Now we build special tags. Special tags are not
        #in the traditionnal tag list
        #Their name doesn't begin with "@"
        
        #Build the "all tags tag"
        self.alltag_tag = Tag("alltags_tag",save_cllbk=self.save)
        self.alltag_tag.set_attribute("special","all")
        self.alltag_tag.set_attribute("icon","gtg-tags-all")
        #Build the "without tag tag"
        self.notag_tag = Tag("notag_tag",save_cllbk=self.save)
        self.notag_tag.set_attribute("special","notag")
        self.notag_tag.set_attribute("icon","gtg-tags-none")
            
        
    #create a new tag and return it
    #or return the existing one with corresponding name
    def new_tag(self,tagname) :
        #we create a new tag from a name
        tname = tagname.encode("UTF-8")
        if not self.store.has_key(tname) :
            tag = Tag(tname,save_cllbk=self.save)
            self.add_tag(tag)
            return tag
        else :
            return self.store[tname]
        
    def add_tag(self,tag) :
        name = tag.get_name()
        #If tag does not exist in the store, we add it
        if not self.store.has_key(name) :
            self.store[name] = tag
        #else, we just take the attributes of the new tag
        #This allow us to keep attributes of the old tag
        #that might be not set in the new one
        else :
            atts = tag.get_all_attributes()
            for att_name in atts :
                val = tag.get_attribute(att_name)
                if att_name != 'name' and val :
                    self.store[name].set_attribute(att_name,val)
                    
    
    def get_tag(self,tagname) :
        if self.store.has_key(tagname) :
            return self.store[tagname]
        else :
            return None
    
    #Return the special tag "All tags"
    def get_alltag_tag(self) :
        return self.alltag_tag
    def get_notag_tag(self) :
        return self.notag_tag
    
    #Return the name of all tags
    #Optionnaly, if you pass the attname and attvalue argument, it will
    #only add tags that have the given value for the given attribute
    #excluding tags that don't have this attribute (except if attvalue is None)
    def get_all_tags_name(self,attname=None,attvalue=None) :
        l = []
        for t in self.store :
            if not attname :
                l.append(self.store[t].get_name())
            elif self.store[t].get_attribute(attname) == attvalue :
                l.append(self.store[t].get_name())
        return l
        
    def get_all_tags(self,attname=None,attvalue=None) :
        l = []
        keys = self.store.keys()
        for t in keys :
            if not attname :
                l.append(self.store[t])
            elif self.store[t].get_attribute(attname) == attvalue :
                l.append(self.store[t])
        return l
    
        
    def save(self) :
        doc,xmlroot = cleanxml.emptydoc(XMLROOT)
        tags = self.get_all_tags()
        already_saved = [] #We avoid saving the same tag twice
        #we don't save tags with no attributes
        #It saves space and allow the saved list growth to be controlled
        for t in tags :
            attr = t.get_all_attributes(butname=True)
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
                

#########################################################################
######################### Tag ###########################################

class Tag:
    """A short name that can be applied to Tasks.

    I mean, surely you must know what a tag is by now. Think Gmail,
    del.icio.us, Flickr et al.

    A tag is defined by its name, which in most cases is '@something'. A tag
    can also have multiple arbitrary attributes. The only attribute enforced
    for tags is 'name', which always matches `Tag.get_name()`.
    """

    def __init__(self, name, save_cllbk=None):
        """Construct a tag.

        :param name: The name of the tag. Should be a string, generally a
            short one.
        :param save_cllbk: A nullary callable, called whenever an attribute
            is set.
        """
        self.attributes = {}
        self.name = name
        self.set_attribute("name", self.name)
        self.save = save_cllbk

    def get_name(self):
        """Return the name of the tag."""
        return self.get_attribute("name")

    def set_attribute(self, att_name, att_value):
        """Set an arbitrary attribute.

        This will call the 'save_cllbk' callback passed to the constructor.

        :param att_name: The name of the attribute.
        :param att_value: The value of the attribute. Will be converted to a
            string.
        """
        # Warning : only the constructor can set the "name".
        if att_name != "name":
            # Attributes should all be strings.
            val = unicode(str(att_value), "UTF-8")
            self.attributes[att_name] = val
            self.save()
        elif self.name == att_value:
            self.attributes[att_name] = str(att_value)

    def get_attribute(self, att_name):
        """Get the attribute 'att_name'.

        Returns None if there is no attribute matching 'att_name'.
        """
        if att_name in self.attributes:
            return self.attributes[att_name]
        else:
            return None

    def get_all_attributes(self, butname=False):
        """Return a list of all attribute names.

        :param butname: If True, exclude 'name' from the list of attribute
            names.
        """
        l = self.attributes.keys()
        if butname:
            # Normally this condition is not necessary
            # Defensiveness...
            if "name" in l:
                l.remove("name")
        return l

    def __str__(self):
        return "Tag: %s" % self.get_name()
