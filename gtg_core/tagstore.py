import os

from gtg_core   import CoreConfig
from tools import cleanxml

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
        self.alltag_tag.set_attribute("icon","data/16x16/icons/tags_alltasks.png")
        #Build the "without tag tag"
        self.notag_tag = Tag("notag_tag",save_cllbk=self.save)
        self.notag_tag.set_attribute("special","notag")
        self.notag_tag.set_attribute("icon","data/16x16/icons/tags_notag.png")
            
        
    #create a new tag and return it
    #or return the existing one with corresponding name
    def new_tag(self,tagname) :
        #we create a new tag from a name
        if not self.store.has_key(tagname) :
            tag = Tag(tagname,save_cllbk=self.save)
            self.add_tag(tag)
            return tag
        else :
            return self.store[tagname]
        
    def add_tag(self,tag) :
        name = tag.get_name()
        #If tag does not exist in the store, we add it
        if not self.store.has_key(name) :
            self.store[name] = tag
        #else, we just take the attributes of the new tag
        #This allow us to keep attributes of the old tag
        #that might be not set in the new one
        else :
            att = tag.get_all_attributes()
            for a in att :
                att_name = a.get_name()
                val = tag.get_attribute(att_name)
                if val :
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
    
    def get_all_tags_name(self) :
        l = []
        for t in self.store :
            l.append(self.store[t].get_name())
        return l
        
    def get_all_tags(self) :
        l = []
        for t in self.store :
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

#A tag is defined by its name (in most cases, it will be "@something") and it can have multiple attributes
class Tag :

    def __init__(self,name,save_cllbk=None) :
        self.attributes = {}
        self.name = name
        self.set_attribute("name",name)
        self.save = save_cllbk
        
    def get_name(self) :
        return self.get_attribute("name")
        
    def set_attribute(self,att_name,att_value) :
        #warning : only the constructor can set the "name"  
        if att_name != "name" :
            self.attributes[att_name] = att_value
            self.save()
        elif self.name == att_value :
            self.attributes[att_name] = att_value
        
    def get_attribute(self,att_name) :
        if self.attributes.has_key(att_name) :
            return self.attributes[att_name]
        else :
            return None
            
    #if butname argument is set, the "name" attributes is removed
    #from the list
    def get_all_attributes(self,butname=False) :
        l = self.attributes.keys()
        if butname :
            #Normally this condition is not necessary
            #Defensiveness...
            if "name" in l :
                l.remove("name")
        return l
        
    def __str__(self):
        return "Tag: %s" %self.get_name()

