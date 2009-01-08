#There's only one Tag store by user. It will store all the tag used and their attribute.
class TagStore :
    def __init__(self) :
        self.store = {}
        #TODO : init store from file
        
    #create a new tag and return it
    #or return the existing one with corresponding name
    def new_tag(self,tagname) :
        #we create a new tag from a name
        if not self.store.has_key(tagname) :
            tag = Tag(tagname)
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
    
    def get_all_tags_name(self) :
        l = []
        for t in self.store :
            l.append(self.store[t].get_name())
        return l
    
        
    def save(self) :
        print "TODO : save tag store"

#########################################################################
######################### Tag ###########################################

#A tag is defined by its name (in most cases, it will be "@something") and it can have multiple attributes
class Tag :

    def __init__(self,name) :
        self.attributes = {}
        self.set_attribute("name",name)
        
    def get_name(self) :
        return self.get_attribute("name")
        
    def set_attribute(self,att_name,att_value) :
        #FIXME : we have to be careful when changing the name
        #if att_name == "name" :   
        self.attributes[att_name] = att_value
        
    def get_attribute(self,att_name) :
        if self.attributes.has_key(att_name) :
            return self.attributes[att_name]
        else :
            return None
            
    def get_all_attributes(self) :
        return self.attributes.keys()

