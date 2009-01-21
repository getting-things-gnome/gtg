#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This is a class taken originally from http://trac.atzm.org/index.cgi/wiki/PyGTK
#It was in Japanese and I didn't understood anything but the code.

#This class implement a gtk.TextView but with many other features like hyperlink
#others stuffs special for GTG
#
#For your information, a gtkTextView always contains a gtk.TextBuffer which
#Contains the text. Ours is called self.buff (how original !)
#
#The Taskview should not be called anywhere else than in the taskeditor !
#As a rule of thumb, the taskview should not have any logic (so no link 
#to Tasks/Projects or whatever)

import gtk
import gobject
import pango

from gnome_frontend import taskviewserial

separators = [' ','.',',','/','\n','\t','!','?',';']

class TaskView(gtk.TextView):
    __gtype_name__ = 'HyperTextView'
    __gsignals__ = {'anchor-clicked': (gobject.SIGNAL_RUN_LAST, None, (str, str, int))}
    __gproperties__ = {
        'link':  (gobject.TYPE_PYOBJECT, 'link color', 'link color of TextView', gobject.PARAM_READWRITE),
        'active':(gobject.TYPE_PYOBJECT, 'active color', 'active color of TextView', gobject.PARAM_READWRITE),
        'hover': (gobject.TYPE_PYOBJECT, 'link:hover color', 'link:hover color of TextView', gobject.PARAM_READWRITE),
        'tag' :(gobject.TYPE_PYOBJECT, 'tag color', 'tag color of TextView', gobject.PARAM_READWRITE),
        'done':  (gobject.TYPE_PYOBJECT, 'link color', 'link color of TextView', gobject.PARAM_READWRITE),
        
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
        #self.buff.set_text("%s\n"%title)
        
        self.link   = {'background': 'white', 'foreground': 'blue', 
                                    'underline': pango.UNDERLINE_SINGLE, 'strikethrough':False}
        self.done   = {'background': 'white', 'foreground': 'gray', 
                                    'strikethrough': True}
        self.active = {'background': 'light gray', 'foreground': 'red', 
                                    'underline': pango.UNDERLINE_SINGLE}
        self.hover  = {'background': 'light gray'}
        self.tag = {'background': "#FFFF66", 'foreground' : "#FF0000"}
        
        
        ###### Tag we will use ######
        # We use the tag table (tag are defined here but set in self.modified)
        self.table = self.buff.get_tag_table()
        # Tag for title
        self.title_tag  = self.buff.create_tag("title",foreground="#12F",scale=1.6,underline=1)
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
        
        # Callbacks 
        self.__refresh_cb = None  # refresh the editor window
        self.open_task            = None # open another task
        self.new_subtask_callback = None # create a subtask
        self.get_subtasktitle     = None
        
        #Signals
        self.connect('motion-notify-event'   , self._motion)
        self.connect('focus-out-event'       , lambda w, e: self.table.foreach(self.__tag_reset, e.window))
        self.buff.connect('insert-text'      , self._insert_at_cursor)
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
        
        #The signal emitted each time the buffer is modified
        #Putting it at the end to avoid doing it too much when starting
        self.buff.connect("changed" , self.modified)
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
        self.buff.deserialize(self.buff, self.mime_type, _iter, text)
    #This insert raw text without deserializing
    def insert_text(self,text, _iter=None) :
        if _iter is None :
            _iter = self.buff.get_end_iter()
        self.buff.insert(_iter,text)
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
        texttag = buff.create_tag(None,**self.get_property('tag'))#pylint: disable-msg=W0142
        texttag.set_data('is_tag', True)
        texttag.set_data('tagname',tag)
        #This line if for iter
        #buff.apply_tag(texttag,s,e)
        #This one is for marks
        self.__apply_tag_to_mark(s,e,tag=texttag)

        
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
        """
        This function is called when the buffer has been modified,
        it reflects the changes by:
          1. Applying the title style on the first line
          2. Changing the name of the window if title change
        """
        tags_before = self.get_tagslist()
        if not buff : buff = self.buff   
        cursor_mark = buff.get_insert()
        cursor_iter = buff.get_iter_at_mark(cursor_mark)
        
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
            local_start.backward_line()
            local_end = cursor_iter.copy()
            local_end.forward_lines(2)
        #if full=False we detect tag only on the current line
        self._detect_tag(buff,local_start,local_end)
        
        #Now we apply the tag tag to the marks
        for t in self.get_tagslist() :
            if t and t[0] != '@' :
                t = "@%s"%t
            start_mark = buff.get_mark(t)
            end_mark = buff.get_mark("/%s"%t)
            #print "applying %s to %s - %s"%(t,start_mark,end_mark)
            if start_mark and end_mark :
                self.apply_tag_tag(buff,t,start_mark,end_mark)
        
        #Ok, we took care of the modification
        self.buff.set_modified(False)
        #If tags have been modified, we update the browser
        if tags_before != self.get_tagslist() :
            self.refresh_browser()

    #Detect tags in buff in the regio between start iter and end iter
    def _detect_tag(self,buff,start,end) :
        # Removing already existing tag in the current selection
        # out of the tag table
        it = start.copy()
        table = buff.get_tag_table()
        old_tags = []
        new_tags = []
        while (it.get_offset() <= end.get_offset()) and (it.get_char() != '\0'):
            if it.begins_tag() :
                tags = it.get_tags()
                for ta in tags :
                    #removing deleted tags
                    if ta.get_data('is_tag') :
                        #We whould remove the "@" from the tag
                        tagname = ta.get_data('tagname')
                        old_tags.append(tagname[1:])
                        table.remove(ta)
                        #Removing the marks if they exist
                        if buff.get_mark(tagname) :
                            buff.delete_mark_by_name(tagname)
                        if buff.get_mark("%s"%tagname) :
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
                        new_tags.append(my_word[1:])
                        #TODO : Keeping the @ is better 
                        #adding tag to the model
                        self.add_tag_callback(my_word[1:])
    
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
    def _delete_range(self,buff,start,end) : #pylint: disable-msg=W0613
        it = start.copy()
        while (it.get_offset() <= end.get_offset()) and (it.get_char() != '\0'):
            if it.begins_tag() :
                tags = it.get_tags()
                for ta in tags :
                    #removing deleted subtasks
                    if ta.get_data('is_subtask') :
                        target = ta.get_data('child')
                        self.remove_subtask(target)
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
    
            
        
    def __newsubtask(self,buff,title,line_nbr) :
        anchor = self.new_subtask_callback(title)
        self.write_subtask(buff,line_nbr,anchor)
        self.refresh_browser()
        
    def write_subtask(self,buff,line_nbr,anchor) :
        start_i = buff.get_iter_at_line(line_nbr)
        start   = buff.create_mark("start",start_i,True)
        end_i   = start_i.copy()
        end_i.forward_line()
        end     = buff.create_mark("end",end_i,False)
        buff.delete(start_i,end_i)
        bullet ='  ↪ '
        self.insert_at_mark(buff,start,bullet)
        self.__apply_tag_to_mark(start,end,name="bullet")
        newline = self.get_subtasktitle(anchor)
        self.insert_at_mark(buff,end,newline,anchor=anchor)
        #The invisible "subtask" tag
        #It must be the last tag set as it's around everything else
        tag = buff.create_tag(None)
        tag.set_data('is_subtask', True)
        tag.set_data('child',anchor)
        self.__apply_tag_to_mark(start,end,tag=tag)
        self.insert_at_mark(buff,end,"\n")
        buff.delete_mark(start)
        buff.delete_mark(end)
        
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
        #New line : the user pressed enter !
        #If the line begins with "-", it's a new subtask !
        if tex == '\n' :
            #The nbr just before the \n
            line_nbr   = itera.get_line()
            start_line = itera.copy()
            start_line.set_line(line_nbr)
            end_line   = itera.copy()
            #We add a bullet list but not on the first line
            #Because it's the title
            if line_nbr > 0 :
                line = start_line.get_slice(end_line)
                #the "-" might be after a space
                #Python 2.5 should allow both tests in one
                if line.startswith('-') or line.startswith(' -') :
                    line = line.lstrip(' -')
                    self.__newsubtask(self.buff,line,line_nbr)
                    
                    #We must stop the signal because if not,
                    #\n will be inserted twice !
                    tv.emit_stop_by_name('insert-text')
                    return True

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

