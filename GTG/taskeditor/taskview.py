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


#This is a class taken originally from http://trac.atzm.org/index.cgi/wiki/PyGTK
#It was in Japanese and I didn't understood anything but the code.

#This class implement a gtk.TextView but with many other features like hyperlink
#others stuffs special for GTG
#
#For your information, a gtkTextView always contains a gtk.TextBuffer which
#Contains the text. Ours is called self.buff (how original !)
#

import gtk
import gobject
import pango

from GTG.taskeditor import taskviewserial
from GTG.tools import openurl

separators = [' ','.',',','/','\n','\t','!','?',';','\0']
url_separators = [' ',',','\n','\t','\0']

bullet1 = '→'
bullet2 = '↳'

class TaskView(gtk.TextView):
    __gtype_name__ = 'HyperTextView'
    __gsignals__ = {'anchor-clicked': (gobject.SIGNAL_RUN_LAST, None, (str, str, int))}
    __gproperties__ = {
        'link':  (gobject.TYPE_PYOBJECT, 'link color', 'link color of TextView', gobject.PARAM_READWRITE),
        'active':(gobject.TYPE_PYOBJECT, 'active color', 'active color of TextView', gobject.PARAM_READWRITE),
        'hover': (gobject.TYPE_PYOBJECT, 'link:hover color', 'link:hover color of TextView', gobject.PARAM_READWRITE),
        'tag' :(gobject.TYPE_PYOBJECT, 'tag color', 'tag color of TextView', gobject.PARAM_READWRITE),
        'done':  (gobject.TYPE_PYOBJECT, 'link color', 'link color of TextView', gobject.PARAM_READWRITE),
        'indent':  (gobject.TYPE_PYOBJECT, 'indent color', 'indent color of TextView', gobject.PARAM_READWRITE),
        }

    def do_get_property(self, prop):
        try:
            return getattr(self, prop.name)
        except AttributeError:
            raise AttributeError, 'unknown property %s' % prop.name

    def do_set_property(self, prop, val):
        if prop.name in self.__gproperties__.keys():
            setattr(self, prop.name, val)
        else:
            raise AttributeError, 'unknown property %s' % prop.name

    #Yes, we want to redefine the buffer. Disabling pylint on that error.
    def __init__(self, requester, buffer=None): #pylint: disable-msg=W0622
        gtk.TextView.__init__(self, buffer)
        self.buff = self.get_buffer()
        self.req = requester
        #Buffer init
        self.link   = {'background': 'white', 'foreground': '#007bff', 
                                    'underline': pango.UNDERLINE_SINGLE, 'strikethrough':False}
        self.done   = {'background': 'white', 'foreground': 'gray', 
                                    'strikethrough': True}
        self.active = {'background': 'light gray', 'foreground': '#ff1e00', 
                                    'underline': pango.UNDERLINE_SINGLE}
        self.hover  = {'background': 'light gray'}
        self.tag = {'background': "#FFea00", 'foreground' : 'black'}
        self.indent = {'scale': 1.4, 'editable' : False, 'left-margin': 10,
                                     "accumulative-margin" : True}
        
        
        ###### Tag we will use ######
        # We use the tag table (tag are defined here but set in self.modified)
        self.table = self.buff.get_tag_table()
        # Tag for title
        self.title_tag  = self.buff.create_tag("title",foreground="#007bff",scale=1.6,underline=1)
        self.title_tag.set_property("pixels-above-lines",10)
        self.title_tag.set_property("pixels-below-lines",10)
        # Tag for highlight (tags are automatically added to the tag table)
        self.buff.create_tag("fluo",background="#F0F")
        # Tag for bullets
        self.buff.create_tag("bullet", scale=1.6)
        #end = self.buff.get_end_iter()

        #This is the list of all the links in our task
        self.__tags = []
        #This is a simple stack used by the serialization
        self.__tag_stack = {}
        
        #Signals
        self.connect('motion-notify-event'   , self._motion)
        self.connect('focus-out-event'       , lambda w, e: self.table.foreach(self.__tag_reset, e.window))
        self.insert_sigid = self.buff.connect('insert-text', self._insert_at_cursor)
        self.buff.connect("delete-range",self._delete_range)
        
        #All the typical properties of our textview
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(True)
        self.set_cursor_visible(True)
        self.buff.set_modified(False)
        
        #Let's try with serializing
        self.mime_type = 'application/x-gtg-task'
        serializer = taskviewserial.Serializer()
        unserializer = taskviewserial.Unserializer(self)
        self.buff.register_serialize_format(self.mime_type, serializer.serialize, None)
        self.buff.register_deserialize_format(self.mime_type, unserializer.unserialize, None)
        
        #The list of callbacks we have to set
        self.remove_tag_callback = None
        self.add_tag_callback = None
        self.get_tagslist = None
        self.get_subtasks = None
        self.refresh_browser = None
        self.remove_subtask =None
        self.__refresh_cb = None  # refresh the editor window
        self.open_task            = None # open another task
        self.new_subtask_callback = None # create a subtask
        self.get_subtasktitle     = None
        self.save_task = None #This will save the task without refreshing all
        
        #The signal emitted each time the buffer is modified
        #Putting it at the end to avoid doing it too much when starting
        self.modified_sigid = self.buff.connect("changed" , self.modified)
        self.connect("backspace",self.backspace)
        self.tobe_refreshed = False

    
    #This function is called to refresh the editor 
    #Specially when we change the title
    def refresh(self,title) :
        if self.__refresh_cb :
            self.__refresh_cb(title)

    def refresh_callback(self,funct) :
        self.__refresh_cb = funct
    #This callback is called to add a new tag
    def set_add_tag_callback(self,funct) :
        self.add_tag_callback = funct
        
    #This callback is called to add a new tag
    def set_remove_tag_callback(self,funct) :
        self.remove_tag_callback = funct
        
    #This callback is called to have the list of tags of a task
    def set_get_tagslist_callback(self,funct) :
        self.get_tagslist = funct
        
    #This callback is called to create a new subtask
    def set_subtask_callback(self,funct) :
        self.new_subtask_callback = funct
    
    #This callback is called to open another task
    def open_task_callback(self,funct) :
        self.open_task = funct
        
    #This callback is called to know the title of a task
    #Knowing its tid
    def tasktitle_callback(self,funct) :
        self.get_subtasktitle = funct
    
    #This callback is called to get the list of tid of subtasks
    def subtasks_callback(self,funct) :
        self.get_subtasks = funct
        
    #This callback is called to remove a subtask by its pid
    def removesubtask_callback(self,funct) :
        self.remove_subtask = funct
        
    #This callback refresh the task browser
    def refresh_browser_callback(self,funct) :
        self.refresh_browser = funct
    
    def save_task_callback(self,funct) :
        self.save_task = funct
    
    #Buffer related functions
    #Those functions are higly related and should always be symetrical
    #See also the serializing functions
 #### The "Set text" group ########
    #This set the text of the buffer (and replace any existing one)
    #without deserializing (used for the title)
    def set_text(self,stri) :
        self.buff.set_text(stri)
    #This append text at the end of the buffer after deserializing it
    def insert(self, text, _iter=None):
        if _iter is None:
            _iter = self.buff.get_end_iter()
        #Ok, this line require an integer at some place !
        #disable the insert and modified signals
        reconnect_insert = False
        reconnect_modified = False
        if self.insert_sigid :
            self.buff.disconnect(self.insert_sigid)
            self.insert_sigid = False
            reconnect_insert = True
        if self.modified_sigid :
            self.buff.disconnect(self.modified_sigid)
            self.modified_sigid = False
            reconnect_modified = True
            
        #deserialize
        self.buff.deserialize(self.buff, self.mime_type, _iter, text)
        
        #reconnect
        if reconnect_insert :
            self.insert_sigid = self.buff.connect('insert-text', self._insert_at_cursor)
        if reconnect_modified :
            self.modified_sigid = self.buff.connect("changed" , self.modified)
            
    #This insert raw text without deserializing
    def insert_text(self,text, _iter=None) :
        if _iter is None :
            _iter = self.buff.get_end_iter()
        self.buff.insert(_iter,text)
    
    #We cannot get an insert in the title
    def get_insert(self) :
        mark = self.buff.get_insert()
        itera = self.buff.get_iter_at_mark(mark)
        if itera.get_line() == 0 :
            itera.forward_line()
        return itera
    
    def insert_with_anchor(self, text, anchor=None, _iter=None,typ=None):
        b = self.get_buffer()
        if _iter is None:
            _iter = b.get_end_iter()
        if anchor is None:
            anchor = text
        tag = self.create_anchor_tag(b,anchor,text,typ=typ)
        b.insert_with_tags(_iter, text, tag)

    def create_anchor_tag(self,b,anchor,text=None,typ=None):
        #We cannot have two tags with the same name
        #That's why the link tag has no name
        #but it has a "is_anchor" property
        if typ == "http" :
            linktype = 'link'
        #By default, the type is a subtask
        else :
            task = self.req.get_task(anchor)
            if task and task.get_status() == "Active" :
                linktype = 'link'
            else :
                linktype = 'done'
        tag = b.create_tag(None, **self.get_property(linktype)) #pylint: disable-msg=W0142
        tag.set_data('is_anchor', True)
        tag.set_data('link',anchor)
        if typ :
            tag.set_data('type',typ)
        tag.connect('event', self._tag_event, text, anchor,typ)
        self.__tags.append(tag)
        return tag
        
    #Apply the tag tag to a set of TextMarks (not Iter)
    def apply_tag_tag(self,buff,tag,s,e) :
        ss = buff.get_iter_at_mark(s)
        ee = buff.get_iter_at_mark(e)
        #If the tag is already applied, we do nothing
        t_list = ss.get_tags()
        texttag = None
        already = False
        for t in t_list :
            if t.get_data('is_tag') and t.get_data('tagname') == tag :
                texttag = t
                if ss.begins_tag(t) and ee.ends_tag(t) :
                    already = True
        if not texttag :
            texttag = buff.create_tag(None,**self.get_property('tag'))#pylint: disable-msg=W0142
            texttag.set_data('is_tag', True)
            texttag.set_data('tagname',tag)
            #This one is for marks
        if not already :
            self.__apply_tag_to_mark(s,e,tag=texttag)
        
    #Apply the tag tag to a set of TextMarks (not Iter)
    #Also change the subtask title if needed
    def apply_subtask_tag(self,buff,subtask,s,e) :
        i_s = buff.get_iter_at_mark(s)
        i_e = buff.get_iter_at_mark(e)
        tex = buff.get_text(i_s,i_e)
        if len(tex) > 0 :
            self.req.get_task(subtask).set_title(tex)
            texttag = self.create_anchor_tag(buff,subtask,text=tex,typ="subtask")
            texttag.set_data('is_subtask', True)
            texttag.set_data('child',subtask)
            #This one is for marks
            self.__apply_tag_to_mark(s,e,tag=texttag)
        else :
            self.remove_subtask(subtask)
            buff.delete_mark(s)
            buff.delete_mark(e)
        
    def create_indent_tag(self,buff,level) :
        tag = buff.create_tag(None, **self.get_property('indent'))#pylint: disable-msg=W0142
        tag.set_data('is_indent',True)
        tag.set_data('indent_level',level)
        return tag
    
    #Insert a list of subtasks at the end of the buffer
    def insert_subtasks(self,st_list) :
        for tid in st_list :
            line_nbr = self.buff.get_end_iter().get_line()
            #Warning, we have to take the next line !
            self.write_subtask(self.buff,line_nbr+1,tid)
            
    #Insert a list of tag in the first line of the buffer
    def insert_tags(self,tag_list) :
        #We insert them just after the title
        #We use the current first line if it begins with a tag
        firstline = self.buff.get_iter_at_line(1)
        newline = True
        for tt in firstline.get_tags() :
            if tt.get_data('is_tag') :
                newline = False
                firstline.forward_to_line_end()
                #Now we should check if the current char is a separator or not
                #Currently, we insert a space
                self.insert_text(" ",firstline)
        #Now we check if this newline is empty (it contains only " " and ",")
#        if newline :
#            endline = firstline.copy()
#            if not endline.ends_line() :
#                endline.forward_to_line_end()
#            text = self.buff.get_text(firstline,endline)
#            if not text.strip(", ") :
#                newline = False
#                firstline.forward_to_line_end()
        #Now we can process
        if newline :
            firstline = self.buff.get_iter_at_line(0)
            firstline.forward_to_line_end()
            self.insert_text("\n",firstline)
            firstline = self.buff.get_iter_at_line(1)
        line_mark = self.buff.create_mark("firstline",firstline,False)
        #self.tv.insert_at_mark(buf,line_mark,"\n")
        for t in tag_list :
            self.insert_at_mark(self.buff,line_mark,t)
            self.insert_at_mark(self.buff,line_mark,",")
        self.buff.delete_mark(line_mark)
        self.modified(full=True)
        
    #this function select and highligth the title (first line)
    def select_title(self) :
        start = self.buff.get_start_iter()
        stop = start.copy()
        stop.forward_to_line_end()
        self.buff.select_range(start, stop)
        
 ##### The "Get text" group #########
    #Get the complete serialized text
    #But without the title
    def get_text(self) :
        #we get the text
        start = self.buff.get_start_iter()
        conti = True
        while conti and not start.ends_tag(self.table.lookup("title")) :
            conti = start.forward_line()
        end = self.buff.get_end_iter()
        texte = self.buff.serialize(self.buff, self.mime_type, start, end)
        
        return texte
    #Get the title of the task (aka the first line of the buffer)
    def get_title(self) :
        start = self.buff.get_start_iter()
        end = self.buff.get_start_iter()
        #The boolean stays True as long as we are in the buffer
        conti = True
        while conti and not end.ends_tag(self.table.lookup("title")) :
            conti = end.forward_line()
        #We don't want to deserialize the title
        #Let's get the pure text directly
        title = self.buff.get_text(start,end)
        #Let's strip blank lines
        stripped = title.strip(' \n\t')
        return stripped
        
### PRIVATE FUNCTIONS ##########################################################

        
    #This function is called so frequently that we should optimize it more.    
    def modified(self,buff=None,full=False) : #pylint: disable-msg=W0613
        """Called when the buffer has been modified.

        It reflects the changes by:

        1. Applying the title style on the first line
        2. Changing the name of the window if title change
        """
        tags_before = self.get_tagslist()
        if not buff : buff = self.buff   
        cursor_mark = buff.get_insert()
        cursor_iter = buff.get_iter_at_mark(cursor_mark)
        table = buff.get_tag_table()
        
        #This should be called only if we are on the title line
        #As an optimisation
        #But we should still get the title_end iter
        if full or self.is_at_title(buff,cursor_iter) :
            #The apply title is very expensive because
            #It involves refreshing the whole task tree
            title_end = self._apply_title(buff)

        if full :
            local_start = title_end.copy()
            local_end = buff.get_end_iter()
        else :
            #We analyse only the current line
            local_start = cursor_iter.copy()
            local_start.set_line(local_start.get_line())
            local_end = cursor_iter.copy()
            local_end.forward_lines(2)
        #if full=False we detect tag only on the current line
        
        #The following 3 lines are a quick ugly fix for bug #359469
#        temp = buff.get_iter_at_line(1)
#        temp.backward_char()
#        self._detect_tag(buff,temp,buff.get_end_iter())
        #This should be the good line
        self._detect_tag(buff,local_start,local_end)
        self._detect_url(buff,local_start,local_end)
        
        #subt_list = self.get_subtasks()
        #First, we remove the olds tags
        tag_list = []
        def subfunc(texttag,data=None) : #pylint: disable-msg=W0613
            if texttag.get_data('is_subtask') :
                tag_list.append(texttag)
        table.foreach(subfunc)
        start,end = buff.get_bounds()
        for t in tag_list :
            buff.remove_tag(t,start,end)
            table.remove(t)
        
        #We apply the hyperlink tag to subtask
        for s in self.get_subtasks() :
            start_mark = buff.get_mark(s)
            # "applying %s to %s - %s"%(s,start_mark,end_mark)
            if start_mark :
                #In fact, the subtask mark always go to the end of line.
                start_i = buff.get_iter_at_mark(start_mark)
                start_i.forward_to_line_end()
                end_mark = buff.create_mark("/%s"%s,start_i,False)
                self.apply_subtask_tag(buff,s,start_mark,end_mark)
    
                
        #Now we apply the tag tag to the marks
        for t in self.get_tagslist() :
            start_mark = buff.get_mark(t)
            end_mark = buff.get_mark("/%s"%t)
            # "applying %s to %s - %s"%(t,start_mark,end_mark)
            if start_mark and end_mark :
                self.apply_tag_tag(buff,t,start_mark,end_mark)
        
        #Ok, we took care of the modification
        self.buff.set_modified(False)
        #If tags have been modified, we update the browser
        if tags_before != self.get_tagslist() :
            self.refresh_browser()
        #Else we save the task anyway (but without refreshing all)
        elif self.save_task :
            self.save_task()
            
    #Detect URL in the tasks
    #It's ugly...
    def _detect_url(self,buff,start,end) :
        #firtst, we remove the old tags :
        #subt_list = self.get_subtasks()
        #First, we remove the olds tags
        tag_list = []
        table = buff.get_tag_table()
        def subfunc(texttag,data=None) : #pylint: disable-msg=W0613
            if texttag.get_data('is_anchor') :
                tag_list.append(texttag)
        table.foreach(subfunc)
        for t in tag_list :
            buff.remove_tag(t,start,end)
        #Now we add the tag URL
        it = start.copy()
        prev = start.copy()
        while (it.get_offset() < end.get_offset()) and (it.get_char() != '\0') :
            it.forward_word_end()
            prev = it.copy()
            prev.backward_word_start()
            text = buff.get_text(prev,it)
            if text in ["http","https"] :
                while it.get_char() not in url_separators and (it.get_char() != '\0') :
                    it.forward_char()
                url = buff.get_text(prev,it)
                if url.startswith("http://") or url.startswith("https://") :
                    texttag = self.create_anchor_tag(buff,url,text=None,typ="http")
                    buff.apply_tag(texttag, prev , it)
            elif text in ["bug","lp","bgo","fdo"] :
                if it.get_char() == " " :
                    it.forward_char()
                if it.get_char() == "#" :
                    it.forward_char()
                    while it.get_char().isdigit() and (it.get_char() != '\0') :
                        it.forward_char()
                    url = buff.get_text(prev,it)
                    nbr = url.split("#")[1]
                    topoint = None
                    if url.startswith("bug #") or url.startswith("lp #") :
                        topoint = "https://launchpad.net/bugs/%s" %nbr
                    elif url.startswith("bgo #") :
                        topoint = "http://bugzilla.gnome.org/show_bug.cgi?id=%s" %nbr
                    elif url.startswith("fdo #") :
                        topoint = "http://bugs.freedesktop.org/show_bug.cgi?id=%s" %nbr
                    if topoint :
                        texttag = self.create_anchor_tag(buff,\
                                                topoint,text=None,typ="http")
                        buff.apply_tag(texttag, prev , it)
                
        

    #Detect tags in buff in the regio between start iter and end iter
    def _detect_tag(self,buff,start,end) :
        # Removing already existing tag in the current selection
        # out of the tag table
        it = start.copy()
        table = buff.get_tag_table()
        old_tags = []
        new_tags = []
        #We must be strictly < than the end_offset. If not, we might
        #found the beginning of a tag on the nextline
        while (it.get_offset() < end.get_offset()) and (it.get_char() != '\0'):
            if it.begins_tag() :
                tags = it.get_toggled_tags(True)
                for ta in tags :
                    #removing deleted tags
                    if ta.get_data('is_tag') :
                        tagname = ta.get_data('tagname')
                        old_tags.append(tagname)
                        buff.remove_tag(ta,start,end)
                        table.remove(ta)
                        #Removing the marks if they exist
                        mark1 = buff.get_mark(tagname)
                        if mark1 :
                            offset1 = buff.get_iter_at_mark(mark1).get_offset()
                            if start.get_offset() <= offset1 <= end.get_offset() :
                                buff.delete_mark_by_name(tagname)
                        mark2 = buff.get_mark("/%s"%tagname)
                        if mark2 :
                            offset2 = buff.get_iter_at_mark(mark2).get_offset()
                            if start.get_offset() <= offset2 <= end.get_offset():
                                buff.delete_mark_by_name("/%s"%tagname)
            it.forward_char()

        # Set iterators for word
        word_start = start.copy()
        word_end   = start.copy()

        # Set iterators for char
        char_start = start.copy()
        char_end   = start.copy()
        char_end.forward_char()
        
        # Iterate over characters of the line to get words
        while char_end.compare(end) <= 0:
            do_word_check = False
            my_char       = buff.get_text(char_start, char_end)
            if my_char not in separators :
                word_end = char_end.copy()
            else:
                do_word_check = True
                
            if char_end.compare(end) == 0:
                do_word_check = True
            
            # We have a new word
            if do_word_check:
                if (word_end.compare(word_start) > 0):
                    my_word = buff.get_text(word_start, word_end)
                    # We do something about it
                    #We want a tag bigger than the simple "@"
                    if len(my_word) > 1 and my_word[0] == '@':
                        #self.apply_tag_tag(buff,my_word,word_start,word_end)
                        #We will add mark where tag should be applied
                        buff.create_mark(my_word,word_start,True)
                        buff.create_mark("/%s"%my_word,word_end,False)
                        #adding tag to a local list
                        new_tags.append(my_word)
                        #adding tag to the model
                        self.add_tag_callback(my_word)
    
                # We set new word boundaries
                word_start = char_end.copy()
                word_end   = char_end.copy()

            # Stop loop if we are at the end
            if char_end.compare(end) == 0: 
                break
            
            # We search the next word
            char_start = char_end.copy()
            char_end.forward_char()
            
        # Update tags in model : 
        # we remove tags that are not in the description anymore
        for t in old_tags :
            if not t in new_tags :
                self.remove_tag_callback(t)
                
    def is_at_title(self,buff,itera) :
        to_return = False
        if itera.get_line() == 0 :
            to_return = True
        #We are at a line with the title tag applied
        elif self.title_tag in itera.get_tags() :
            to_return = True
        #else, we look if there's something between us and buffer start
        elif not buff.get_text(buff.get_start_iter(),itera).strip('\n\t ') :
            to_return = True
        return to_return
        
    #When the user remove a selection, we remove subtasks and @tags
    #from this selection
    def _delete_range(self,buff,start,end) :
        it = start.copy()
#        #If we are at the beginning of a mark, put this mark at the end
#        marks = start.get_marks()
#        for m in marks :
#            print m.get_name()
#            buff.move_mark(m,end)
        #If the begining of the selection is in the middle of an indent
        #We want to start at the begining
        tags = it.get_tags()+it.get_toggled_tags(False)
        for ta in tags :
            if (ta.get_data('is_indent') and not it.begins_tag(ta) \
                                            and not it.ends_tag(ta)) :
                it.backward_to_tag_toggle(ta)
                start.backward_to_tag_toggle(ta)
                endindent = it.copy()
                endindent.forward_to_tag_toggle(ta)
                buff.remove_tag(ta,start,endindent)
        #Now we delete all, char after char
        while (it.get_offset() <= end.get_offset()) and (it.get_char() != '\0'):
            if it.begins_tag() :
                tags = it.get_tags()
                for ta in tags :
                    #removing deleted subtasks
                    #it looks like it works without that.
                    if ta.get_data('is_subtask') :
#                        target = ta.get_data('child')
#                        #self.remove_subtask(target)
                        self.refresh_browser()
                    #removing deleted tags
                    if ta.get_data('is_tag') :
                        tagname = ta.get_data('tagname')
                        self.remove_tag_callback(tagname)
                        if buff.get_mark(tagname) :
                            buff.delete_mark_by_name(tagname)
                        if buff.get_mark("/%s"%tagname) :
                            buff.delete_mark_by_name("/%s"%tagname)
                        self.refresh_browser()
                    if ta.get_data('is_indent') :
                        #Because the indent tag is read only, we will remove it
                        endtag = it.copy()
                        endtag.forward_to_tag_toggle(ta)
                        buff.remove_tag(ta,it,endtag)
                        #Also, we want to delete the indent completely,
                        #Even if the selection was in the middle of an indent
                        if endtag.compare(end) :
                            end = endtag
                        
            it.forward_char()
        #We return false so the parent still get the signal
        return False
        
    #Apply the title and return an iterator after that title.
    def _apply_title(self,buff) :
        start     = buff.get_start_iter()
        end       = buff.get_end_iter()
        line_nbr  = 1
        linecount = buff.get_line_count()
    
        # Apply the title tag on the first line 
        #---------------------------------------
        
        # Determine the iterators for title
        title_start = start.copy() 
        if linecount > line_nbr :
            # Applying title on the first line
            title_end = buff.get_iter_at_line(line_nbr)
            stripped  = buff.get_text(title_start,title_end).strip('\n\t ')
            # Here we ignore lines that are blank
            # Title is the first written line
            while line_nbr <= linecount and not stripped :
                line_nbr  += 1
                title_end  = buff.get_iter_at_line(line_nbr)
                stripped   = buff.get_text(title_start, title_end).strip('\n\t ')
        # Or to all the buffer if there is only one line
        else :
            title_end = end.copy()            
            
        buff.apply_tag_by_name  ('title', title_start , title_end)
        buff.remove_tag_by_name ('title', title_end   , end)

        # Refresh title of the window
        self.refresh(buff.get_text(title_start,title_end).strip('\n\t'))
        return title_end
    
            
        
    def __newsubtask(self,buff,title,line_nbr, level=1) :
        anchor = self.new_subtask_callback(title)
        end_i = self.write_subtask(buff,line_nbr,anchor,level=level)
        self.refresh_browser()
        return end_i
    
    #Write the subtask then return the iterator at the end of the line
    def write_subtask(self,buff,line_nbr,anchor,level=1) :
        #disable the insert signal to avoid recursion
        reconnect_insert = False
        reconnect_modified = False
        if self.insert_sigid :
            self.buff.disconnect(self.insert_sigid)
            self.insert_sigid = False
            reconnect_insert = True
        if self.modified_sigid :
            self.buff.disconnect(self.modified_sigid)
            self.modified_sigid = False
            reconnect_modified = True
        
        #First, we insert the request \n
        #If we don't do this, the content of next line will automatically
        #be in the subtask title
        start_i = buff.get_iter_at_line(line_nbr)
        start_i.forward_to_line_end()
        buff.insert(start_i,"\n")
        #Ok, now we can start working
        start_i = buff.get_iter_at_line(line_nbr)
        end_i   = start_i.copy()
        #We go back at the end of the previous line
        start_i.backward_char()
        #But only if this is not the title.
        insert_enter = True
        if start_i.has_tag(self.title_tag) :
            start_i.forward_char()
            insert_enter = False
        start   = buff.create_mark("start",start_i,True)
        end_i.forward_line()
        end     = buff.create_mark("end",end_i,False)
        buff.delete(start_i,end_i)
        start_i = buff.get_iter_at_mark(start)
        self.insert_indent(buff,start_i,level, enter=insert_enter)
        newline = self.get_subtasktitle(anchor)
        end_i = buff.get_iter_at_mark(end)
        startm = buff.create_mark(anchor,end_i,True)
        #Putting the subtask marks around the title
        self.insert_at_mark(buff,end,newline)
        end_i = buff.get_iter_at_mark(end)
        endm = buff.create_mark("/%s"%anchor,end_i,False)
        #put the tag on the marks
        self.apply_subtask_tag(buff,anchor,startm,endm)
        #buff.delete_mark(start)
        #buff.delete_mark(end)
        
        
        if reconnect_insert :
            self.insert_sigid = self.buff.connect('insert-text', self._insert_at_cursor)
        if reconnect_modified :
            self.modified_sigid = self.buff.connect("changed" , self.modified)
        return end_i
        
    def insert_newtask(self,fitera=None) :
        if not fitera :
            fitera = self.get_insert()
        #First, find a line without subtask
        line = fitera.get_line()
        #Avoid the title at all cost
        if line <= 0 :
            line = 1
        startl = self.buff.get_iter_at_line(line)
        itera = None
        while not itera :
            found = True
            for t in startl.get_tags() :
                if t.get_data('is_indent') :
                    line += 1
                    startl = self.buff.get_iter_at_line(line)
                    found = False
            if found :
                itera = startl 
                    
        #If we are not on the end of line, go there
        #but if we are at the start of line, then create the subtask
        #before the current line
        enter = True
        if itera.starts_line() :
            mark = self.buff.create_mark("temp",itera,True)
            self.buff.insert(itera,"\n")
            itera = self.buff.get_iter_at_mark(mark)
            self.buff.delete_mark(mark)
            enter = False
        elif not itera.ends_line() :
            itera.forward_to_line_end()
        endm = self.insert_indent(self.buff,itera,1,enter=enter)
        end = self.buff.get_iter_at_mark(endm)
        self.buff.place_cursor(end)
        
    def insert_indent(self,buff,start_i,level,enter=True) :
        #We will close the current subtask tag
        list_stag = start_i.get_toggled_tags(False)
        stag = None
        for t in list_stag :
            if t.get_data('is_subtask') :
                stag = t
        #maybe the tag was not toggled off here but we were in the middle
        if not stag :
            list_stag = start_i.get_tags()
            for t in list_stag :
                if t.get_data('is_subtask') :
                    stag = t
        if stag :
            #We will remove the tag from the whole text
            subtid = stag.get_data('child')
        #We move the end_subtask mark to here
        #We have to create a temporary mark with left gravity
        #It will be later replaced by the good one with right gravity
        temp_mark = self.buff.create_mark("temp",start_i,True)
        
        end     = buff.create_mark("end",start_i,False)
        if enter : 
            buff.insert(start_i,"\n")
        
        #Moving the end of subtask mark to the position of the temp mark
        if stag :
            itera = buff.get_iter_at_mark(temp_mark)
            buff.move_mark_by_name("/%s"%subtid,itera)
        buff.delete_mark(temp_mark)
        #The mark has right gravity but because we putted it on the left
        #of the newly inserted \n, it will not move anymore.
        
        itera = buff.get_iter_at_mark(end)
        #We should never have an indentation at 0.
        #This is normally not needed and purely defensive
        if itera.get_line() <= 0 :
            itera = buff.get_iter_at_line(1)
        start   = buff.create_mark("start",itera,True)
        indentation = ""
        #adding two spaces by level
        spaces = "  "
        indentation = indentation + (level-1)*spaces
        #adding the symbol 
        if level == 1 :
            indentation = "%s%s "%(indentation,bullet1)
        buff.insert(itera,indentation)
        indenttag = self.create_indent_tag(buff,level)
        self.__apply_tag_to_mark(start,end,tag=indenttag)
        return end

        
    def __apply_tag_to_mark(self,start,end,tag=None,name=None) :
        start_i = self.buff.get_iter_at_mark(start)
        end_i = self.buff.get_iter_at_mark(end)
        if tag :
            self.buff.apply_tag(tag,start_i,end_i)
        elif name :
            self.buff.apply_tag_by_name(name,start_i,end_i)
    
    def insert_at_mark(self,buff,mark,text,anchor=None) :
        ite = buff.get_iter_at_mark(mark)
        if anchor :
            self.insert_with_anchor(text,anchor,_iter=ite,typ="subtask")
        else :
            buff.insert(ite,text)
        
    #Function called each time the user input a letter   
    def _insert_at_cursor(self, tv, itera, tex, leng) : #pylint: disable-msg=W0613
        #disable the insert signal to avoid recursion 
        self.buff.disconnect(self.insert_sigid)
        self.insert_sigid = False
        self.buff.disconnect(self.modified_sigid)
        self.modified_sigid = False
        
        #First, we will get the actual indentation value
        #The nbr just before the \n
        line_nbr   = itera.get_line()
        start_line = itera.copy()
        start_line.set_line(line_nbr)
        end_line   = itera.copy()
        tags = start_line.get_tags()
        current_indent = 0
        subtask_nbr = None
        for ta in tags :
            if ta.get_data('is_indent') :
                current_indent = ta.get_data('indent_level')
        tags = itera.get_tags()
        for ta in tags :
            if ta.get_data('is_subtask') :
                subtask_nbr = ta.get_data('child')
        #Maybe we are simply at the end of the tag
        if not subtask_nbr and itera.ends_tag():
            for ta in itera.get_toggled_tags(False) :
                if ta.get_data('is_subtask') :
                    subtask_nbr = ta.get_data('child')

        #New line : the user pressed enter !
        #If the line begins with "-", it's a new subtask !
        if tex == '\n' :
            self.buff.create_mark("insert_point", itera, True)
            #First, we close tag tags.
            #If we are at the end of a tag, we look for closed tags
            closed_tag = None
            cutting_subtask = False
            if itera.ends_tag() :
                list_stag = itera.get_toggled_tags(False)
            #Or maybe we are in the middle of a tag
            else :
                list_stag = itera.get_tags()
            for t in list_stag :
                if t.get_data('is_tag') :
                    closed_tag = t.get_data('tagname')
                elif t.get_data('is_subtask') :
                    cutting_subtask = True
                    closed_tag = t.get_data('child')
            #We add a bullet list but not on the first line
            #Because it's the title
            if line_nbr > 0 :
                line = start_line.get_slice(end_line)
                
                #If indent is 0, We check if we created a new task
                #the "-" might be after a space
                #Python 2.5 should allow both tests in one
                if current_indent == 0 :
                    if line.startswith('-') or line.startswith(' -') :
                        line = line.lstrip(' -')
                        end_i = self.__newsubtask(self.buff,line,line_nbr)
                        #Here, we should increment indent level
                        self.insert_indent(self.buff,end_i,1,enter=True)
                        tv.emit_stop_by_name('insert-text')
                    else :
                        self.buff.insert(itera,"\n")
                        tv.emit_stop_by_name('insert-text')
                        
                #Then, if indent > 0, we increment it
                #First step : we preserve it.
                else :
                    if not line.lstrip("%s "%bullet1) :
                        self.deindent(itera,newlevel=0)
                        tv.emit_stop_by_name('insert-text')
                        
                    elif current_indent == 1 :
                        self.insert_indent(self.buff,itera,current_indent)
                        tv.emit_stop_by_name('insert-text')
                #Then we close the tag tag
                if closed_tag :
                    insert_mark = self.buff.get_mark("insert_point")
                    insert_iter = self.buff.get_iter_at_mark(insert_mark)
                    self.buff.move_mark_by_name("/%s"%closed_tag,insert_iter)
                    self.buff.delete_mark(insert_mark)
                    if cutting_subtask :
                        cursor = self.buff.get_iter_at_mark(self.buff.get_insert())
                        endl = cursor.copy()
                        if not endl.ends_line() :
                            endl.forward_to_line_end()
                        text = self.buff.get_text(cursor,endl)
                        anchor = self.new_subtask_callback(text)
                        self.buff.create_mark(anchor,cursor,True)
                        self.buff.create_mark("/%s"%anchor,endl,False)
                    self.modified(full=True)
        #The user entered something else than \n
        elif tex :
            #We are on an indented line without subtask ? Create it !
            if current_indent > 0 and not subtask_nbr :
                #self.__newsubtask(self.buff,tex,line_nbr, level=current_indent)
                anchor = self.new_subtask_callback(tex)
                self.buff.create_mark(anchor,itera,True)
                self.buff.create_mark("/%s"%anchor,itera,False)
        self.insert_sigid = self.buff.connect('insert-text', self._insert_at_cursor)
        self.connect('key_press_event', self._keypress)
        self.modified_sigid = self.buff.connect("changed" , self.modified)
        
    def _keypress(self, widget, event):
        # Check for Ctrl-Return/Enter
        if event.state & gtk.gdk.CONTROL_MASK and event.keyval in (gtk.keysyms.Return, gtk.keysyms.KP_Enter):
            buff = self.buff
            cursor_mark = buff.get_insert()
            cursor_iter = buff.get_iter_at_mark(cursor_mark)
            local_start = cursor_iter.copy()

            for tag in local_start.get_tags():
                anchor =  tag.get_data('link')
                typ =  tag.get_data('type')
                if(anchor):
                    if typ == "subtask" :
                        self.open_task(anchor)
                    elif typ == "http" :
                        openurl.openurl(anchor)

            return True

    #Deindent the current line of one level
    #If newlevel is set, force to go to that level
    def deindent(self,itera,newlevel=-1) :
        line = itera.get_line()
        startline = self.buff.get_iter_at_line(line)
        if newlevel < 0 :
            for t in itera.get_toggled_tags(False) :
                if t.get_data('is_indent') :
                    newlevel = t.get_data('indent_level')
                    
            if newlevel > 0 :
                newlevel -= 1
        #If it's still < 0
        if newlevel < 0 :
            print "bug : no is_indent tag on that line"
        startline.backward_char()
        #We make a temp mark where we should insert the new indent
        tempm = self.buff.create_mark("temp",startline)
        self.buff.delete(startline,itera)
        newiter = self.buff.get_iter_at_mark(tempm)
        self.buff.delete_mark(tempm)
        self.insert_indent(self.buff,newiter,newlevel)
        
        
    def backspace(self,tv) :
        self.buff.disconnect(self.insert_sigid)
        insert_mark = self.buff.get_insert()
        insert_iter = self.buff.get_iter_at_mark(insert_mark)
        #All that craps to find if we are at the end of an indent tag
        if insert_iter.ends_tag() :
            for t in insert_iter.get_toggled_tags(False) :
                if t.get_data('is_indent') :
                    self.deindent(insert_iter)
                    tv.emit_stop_by_name('backspace')
        self.insert_sigid = self.buff.connect('insert-text', self._insert_at_cursor)

    #The mouse is moving. We must change it to a hand when hovering a link
    def _motion(self, view, ev):
        window = ev.window
        x, y, _ = window.get_pointer()
        x, y = view.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        tags = view.get_iter_at_location(x, y).get_tags()
        for tag in tags:
            if tag.get_data('is_anchor'):
                for t in set(self.__tags) - set([tag]):
                    self.__tag_reset(t, window)
                self.__set_anchor(window, tag, gtk.gdk.Cursor(gtk.gdk.HAND2), self.get_property('hover'))
                break
        else:
            tag_table = self.buff.get_tag_table()
            tag_table.foreach(self.__tag_reset, window)

    #We clicked on a link
    def _tag_event(self, tag, view, ev, _iter, text, anchor,typ): #pylint: disable-msg=W0613
        _type = ev.type
        if _type == gtk.gdk.MOTION_NOTIFY:
            return
        elif _type in [gtk.gdk.BUTTON_PRESS, gtk.gdk.BUTTON_RELEASE]:
            button = ev.button
            cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
            if _type == gtk.gdk.BUTTON_RELEASE:
                if typ == "subtask" :
                    self.open_task(anchor)
                elif typ == "http" :
                    openurl.openurl(anchor)
                else :
                    print "Unknown link type for %s" %anchor
                self.emit('anchor-clicked', text, anchor, button)
                self.__set_anchor(ev.window, tag, cursor, self.get_property('hover'))
            elif button in [1, 2]:
                self.__set_anchor(ev.window, tag, cursor, self.get_property('active'))

    def __tag_reset(self, tag, window):
        if tag.get_data('is_anchor'):
            #We need to get the normal cursor back
            editing_cursor = gtk.gdk.Cursor(gtk.gdk.XTERM)
            if tag.get_property('strikethrough') : 
                linktype = 'done'
            else : 
                linktype = 'link'
            self.__set_anchor(window, tag, editing_cursor, self.get_property(linktype))

    def __set_anchor(self, window, tag, cursor, prop):
        window.set_cursor(cursor)
        for key, val in prop.iteritems():
            tag.set_property(key, val)

gobject.type_register(TaskView)

