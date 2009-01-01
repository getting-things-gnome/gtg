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
import xml.dom.minidom

class TaskView(gtk.TextView):
    __gtype_name__ = 'HyperTextView'
    __gsignals__ = {'anchor-clicked': (gobject.SIGNAL_RUN_LAST, None, (str, str, int))}
    __gproperties__ = {
        'link':  (gobject.TYPE_PYOBJECT, 'link color', 'link color of TextView', gobject.PARAM_READWRITE),
        'active':(gobject.TYPE_PYOBJECT, 'active color', 'active color of TextView', gobject.PARAM_READWRITE),
        'hover': (gobject.TYPE_PYOBJECT, 'link:hover color', 'link:hover color of TextView', gobject.PARAM_READWRITE),
        'tag' :(gobject.TYPE_PYOBJECT, 'tag color', 'tag color of TextView', gobject.PARAM_READWRITE)
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

    def __init__(self, buffer=None):
        gtk.TextView.__init__(self, buffer)
        self.buff = self.get_buffer()
        #Buffer init
        #self.buff.set_text("%s\n"%title)
        
        self.link   = {'background': 'white', 'foreground': 'blue', 
                                    'underline': pango.UNDERLINE_SINGLE}
        self.active = {'background': 'light gray', 'foreground': 'red', 
                                    'underline': pango.UNDERLINE_SINGLE}
        self.hover  = {'background': 'light gray', 'foreground': 'blue', 
                                    'underline': pango.UNDERLINE_SINGLE}
        self.tag = {'background': "#FFFF66", 'foreground' : "#FF0000"}
        
        ###### Tag we will use ######
        # We use the tag table (tag are defined here but set in self.modified)
        self.table = self.buff.get_tag_table()
        # Tag for title
        title_tag  = self.buff.create_tag("title",foreground="#12F",scale=1.6,underline=1)
        title_tag.set_property("pixels-above-lines",10)
        title_tag.set_property("pixels-below-lines",10)
        # Tag for highlight
        fluo_tag   = self.buff.create_tag("fluo",background="#F0F")
        # Tag for bullets
        bullet_tag = self.buff.create_tag("bullet", scale=1.6)
        # Tag for tags
        tags_tag = self.buff.create_tag("tag", background="#FFFF66", foreground="#FF0000")
        tags_tag.set_data('is_tag', True)
        #subtask_tag = self.buff.create_tag("subtask",background="#FF0")
        #start = self.buff.get_start_iter()
        end = self.buff.get_end_iter()
        #We have to find a way to keep this tag for the first line
        #Even when the task is edited

        #This is the list of all the links in our task
        self.__tags = []
        #This is a simple stack used by the serialization
        self.__tag_stack = {}
        
        # Callbacks 
        self.refresh              = None # refresh the editor window
        self.open_task            = None # open another task
        self.new_subtask_callback = None # create a subtask
        self.get_subtasktitle     = None
        
        #Signals
        self.connect('motion-notify-event'   , self._motion)
        self.connect('focus-out-event'       , lambda w, e: self.table.foreach(self.__tag_reset, e.window))
        #The signal emitted each time the buffer is modified
        self.buff.connect("modified_changed" , self._modified)
        self.buff.connect('insert-text'      , self._insert_at_cursor)
        self.buff.connect("delete-range",self._delete_range)
        
        #All the typical properties of our textview
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(True)
        self.set_cursor_visible(True)
        self.buff.set_modified(False)
        
        #Let's try with serializing
        self.mime_type = 'application/x-gtg-task'
        self.buff.register_serialize_format(self.mime_type, self.__taskserial, None)
        self.buff.register_deserialize_format(self.mime_type, self.__taskdeserial, None)

    
    #This function is called to refresh the editor 
    #Specially when we change the title
    def refresh_callback(self,funct) :
        self.refresh = funct
    #This callback is called to add a new tag
    def set_add_tag_callback(self,funct) :
        self.add_tag_callback = funct
        
    #This callback is called to add a new tag
    def set_remove_tag_callback(self,funct) :
        self.remove_tag_callback = funct
    
    #This callback is called to add a new tag
#    def set_set_tag_callback(self,funct) :
#        self.set_tag_callback = funct
        
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
        #self.buff.insert(_iter, text)
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
        tag = b.create_tag(None, **self.get_property('link'))
        tag.set_data('is_anchor', True)
        tag.set_data('link',anchor)
        if typ :
            tag.set_data('type',typ)
        tag.connect('event', self._tag_event, text, anchor,typ)
        self.__tags.append(tag)
        return tag
    
    #Insert a list of subtasks at the end of the buffer
    def insert_subtasks(self,st_list) :
        for tid in st_list :
            line_nbr = self.buff.get_end_iter().get_line()
            self.__subtask(line_nbr,tid)
            
    #insert a GTG tag with its TextView tag.
    #Yes, we know : the word tag is used for two different concepts here.
    def insert_tag(self,tag,itera) :
        if tag :
            sm = self.buff.create_mark(None,itera,True)
            em = self.buff.create_mark(None,itera,False)
            self.buff.insert(itera,tag)
            s = self.buff.get_iter_at_mark(sm)
            e = self.buff.get_iter_at_mark(em)
            self.apply_tag_tag(tag,s,e)
        
        
    def apply_tag_tag(self,tag,s,e) :
        texttag = self.buff.create_tag(None,**self.get_property('tag'))
        texttag.set_data('is_tag', True)
        texttag.set_data('tagname',tag)
        self.buff.apply_tag(texttag,s,e)

        
 ##### The "Get text" group #########
    #Get the complete serialized text
    #But without the title
    def get_text(self) :
        #the tag table
        #Currently, we are not saving the tag table
        table = self.buff.get_tag_table()
        
        #we get the text
        #texte = self.buff.get_text(self.buff.get_start_iter(),self.buff.get_end_iter())
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
        
########### Serializing functions ###############

    # TextIter.ends_tag doesn't work (see bug #561916)
    #Let's reimplement it manually
    def __istagend(self,it, tag=None) :
        #FIXME : we should handle the None case
        #if we currently have a tag
        has = it.has_tag(tag)
        it.forward_char()
        #But the tag is not there anymore on next char
        if has and not it.has_tag(tag) :
            #it means we were at the end of a tag
            val = True
            it.backward_char()
        else :
            val = False
            it.backward_char()
        return val

    def __parsebuf(self, buf, start, end, name, doc) :
        """
        Parse the buffer and output an XML representation.
        
          @var buf  : the buffer to parse from start to end
          @var name : the name of the XML element and doc is the XML dom
          
        """
        
        txt    = ""
        it     = start.copy()
        parent = doc.createElement(name)
        
        while (it.get_offset() < end.get_offset()) and (it.get_char() != '\0'):
            
            # If a tag begin, we will parse until the end
            if it.begins_tag() :
                
                # We take the tag with the highest priority
                # The last of the list is the highest priority
                ta_list = it.get_tags()
                ta      = ta_list.pop()
                
                #remove the tag (to avoid infinite loop)
                #buf.remove_tag(ta,startit,endit)
                #But we are modifying the buffer. So instead,
                #We put the tag in the stack so we remember it was
                #already processed.
                startit = it.copy()
                offset  = startit.get_offset()
                
                #a boolean to know if we have processed all tags here
                all_processed = False
                
                #Have we already processed a tag a this point ?
                if self.__tag_stack.has_key(offset) :
                    #Have we already processed this particular tag ?
                    while (not all_processed) and ta.props.name in self.__tag_stack[offset]:
                        #Yes, so we take another tag (if there's one)
                        if len(ta_list) <= 0 :
                            all_processed = True
                        else :
                            ta = ta_list.pop()
                else :
                    #if we process the first tag of this offset, we add an entry
                    self.__tag_stack[offset] = []
                    
                #No tag to process, we are in the text mode
                if all_processed :
                    #same code below. Should we make a separate function ?
                    parent.appendChild(doc.createTextNode(it.get_char()))
                    it.forward_char()
                else :
                    #So now, we are in tag "ta"
                    #Let's get the end of the tag
                    it.forward_to_tag_toggle(ta)
                    endit   = it.copy()
                    tagname = ta.props.name
                    #Let's add this tag to the stack so we remember
                    #it's already processed
                    self.__tag_stack[offset].append(tagname)
                    if ta.get_data('is_subtask') :
                        tagname = "subtask"
                        subt    = doc.createElement(tagname)
                        target  = ta.get_data('child')
                        subt.appendChild(doc.createTextNode(target))
                        parent.appendChild(subt)
                        it.forward_line()
                    elif ta.get_data('is_tag') :
                        #Recursive call !!!!! (we handle tag in tags)
                        child = self.__parsebuf(buf,startit,endit,"tag",doc)
                        parent.appendChild(child)
                    else :
                        #The link tag has noname but has "is_anchor" properties
                        if ta.get_data('is_anchor'): tagname = "link"
                        #Recursive call !!!!! (we handle tag in tags)
                        child = self.__parsebuf(buf,startit,endit,tagname,doc)
                        #handling special tags
                        if ta.get_data('is_anchor') :
                            child.setAttribute("target",ta.get_data('link'))
                        parent.appendChild(child)
            #else, we just add the text
            else :
                parent.appendChild(doc.createTextNode(it.get_char()))
                it.forward_char()
                
        #This function concatenate all the adjacent text node of the XML
        parent.normalize()
        return parent
        
    #parse the XML and put the content in the buffer
    def __parsexml(self,buf,ite,element) :
        start = buf.create_mark(None,ite,True)
        end   = buf.create_mark(None,ite,False)
        subtasks = self.get_subtasks()
        taglist = self.get_tagslist()
        print taglist
        for n in element.childNodes :
            itera = buf.get_iter_at_mark(end)
            if n.nodeType == n.ELEMENT_NODE :
                #print "<%s>" %n.nodeName
                if n.nodeName == "subtask" :
                    tid = n.firstChild.nodeValue
                    #We remove the added subtask from the list
                    #Of known subtasks
                    #If the subtask is not in the list, we don't write it
                    if tid in subtasks :
                        subtasks.remove(tid)
                        line_nbr = itera.get_line()
                        self.__subtask(line_nbr,tid)
                elif n.nodeName == "tag" :
                    text = n.firstChild.nodeValue
                    self.insert_tag(text,itera)
                    #We remove the added tag from the tag list
                    #of known tag for this task
                    if text[1:] in taglist :
                        taglist.remove(text[1:])
                else :
                    self.__parsexml(buf,itera,n)
                    s = buf.get_iter_at_mark(start)
                    e = buf.get_iter_at_mark(end)
                    if n.nodeName == "link" :
                        anchor = n.getAttribute("target")
                        tag = self.create_anchor_tag(buf,anchor,None)
                        buf.apply_tag(tag,s,e)
                    else :
                        buf.apply_tag_by_name(n.nodeName,s,e)
            elif n.nodeType == n.TEXT_NODE :
                buf.insert(itera,n.nodeValue)
        #Now, we insert the remaining subtasks
        self.insert_subtasks(subtasks)
        #We also insert the remaining tags
        for t in taglist :
            print "inserting tag %s" %t
            self.insert_tag(t[1:],end)
        buf.delete_mark(start)
        buf.delete_mark(end)
        return True
        
                
    ### Serialize the task : transform it's content in something
    #we can store
    def __taskserial(self,register_buf, content_buf, start, end, udata) :
        #Currently we serialize in XML
        its = start.copy()
        ite = end.copy()
        #Warning : the serialization process cannot be allowed to modify 
        #the content of the buffer.
        doc = xml.dom.minidom.Document()
        self.__tag_stack = {}
        doc.appendChild(self.__parsebuf(content_buf,its, ite,"content",doc))
        #We don't want the whole doc with the XML declaration
        #we only take the first node (the "content" one)
        node = doc.firstChild
        return node.toxml().encode("utf-8")
        
    ### Deserialize : put all in the TextBuffer
    def __taskdeserial(self,register_buf, content_buf, ite, data, cr_tags, udata) :
        if data :
            element = xml.dom.minidom.parseString(data)
            success = self.__parsexml(content_buf,ite,element.firstChild)
        return True
        
### PRIVATE FUNCTIONS ##########################################################
        
    def _modified(self,a=None) :
        """
        This function is called when the buffer has been modified,
        it reflects the changes by:
          1. Applying the title style on the first line
          2. Changing the name of the window if title change
        """
        
        start     = self.buff.get_start_iter()
        end       = self.buff.get_end_iter()
        line_nbr  = 1
        linecount = self.buff.get_line_count()
        
        # Apply the title tag on the first line 
        #---------------------------------------
        
        # Determine the iterators for title
        title_start = start.copy() 
        if linecount > line_nbr :
            # Applying title on the first line
            title_end = self.buff.get_iter_at_line(line_nbr)
            stripped  = self.buff.get_text(title_start,title_end).strip('\n\t ')
            # Here we ignore lines that are blank
            # Title is the first written line
            while line_nbr <= linecount and not stripped :
                line_nbr  += 1
                title_end  = self.buff.get_iter_at_line(line_nbr)
                stripped   = self.buff.get_text(title_start, title_end).strip('\n\t ')
        # Or to all the buffer if there is only one line
        else :
            title_end = end.copy()            
            
        self.buff.apply_tag_by_name  ('title', title_start , title_end)
        self.buff.remove_tag_by_name ('title', title_end   , end)

        # Refresh title of the window
        
        self.refresh(self.buff.get_text(title_start,title_end).strip('\n\t'))
        
        # Set iterators for body
        body_start = title_end.copy()
        body_end   = end.copy()
        
        # Detect tags
        #-------------
        
#        tag_list = []
        #Removing all texttag related to GTG tags
        #self.buff.remove_tag_by_name ('tag', body_start, body_end)
        table = self.buff.get_tag_table()
        def remove_tag_tag(texttag,data) :
            if texttag.get_data("is_tag") :
                table.remove(texttag)
        table.foreach(remove_tag_tag)

        # Set iterators for word
        word_start = body_start.copy()
        word_end   = body_start.copy()

        # Set iterators for char
        char_start = body_start.copy()
        char_end   = body_start.copy()
        char_end.forward_char()
        
        # Iterate over characters of the line to get words
        while char_end.compare(body_end) <= 0:
            do_word_check = False
            my_char       = self.buff.get_text(char_start, char_end)
#            if my_char in [' ','.',',','/','\n','\t','!','?',';']:
#                if char_start.compare(word_end) > 0:
#                    word_end   = char_start.copy()
#                else:
#                    word_start = char_end.copy()
#                    word_end   = char_end.copy()

            if my_char not in [' ','.',',','/','\n','\t','!','?',';']:
                word_end = char_end.copy()
            else:
                do_word_check = True
                
            if char_end.compare(body_end) == 0:
                do_word_check = True
                
            # We have a new word
            if do_word_check:
                if (word_end.compare(word_start) > 0):
                    my_word = self.buff.get_text(word_start, word_end)
                
                    # We do something about it
                    if len(my_word) > 0 and my_word[0] == '@':
                        self.apply_tag_tag(my_word,word_start,word_end)
                        #self.buff.apply_tag_by_name("tag", word_start, word_end)
                        #adding tag to a local list
#                        tag_list.append(my_word[1:])
                        #adding tag to the model
                        self.add_tag_callback(my_word[1:])
    
                # We set new word boundaries
                word_start = char_end.copy()
                word_end   = char_end.copy()

            # Stop loop if we are at the end
            if char_end.compare(body_end) == 0: break
            
            # We search the next word
            char_start = char_end.copy()
            char_end.forward_char()
        
        # Update tags in model : 
        # we remove tags that are not in the description anymore
#        for t in self.get_tagslist() :
#            if not t in tag_list :
#                self.remove_tag_callback(t)
        
        # Remove all tags from the task
        # Loop over each line
        
        
        # Loop over each word of the line
        # Check if the word starts by '@'
            # Apply tag on the word
            # Add tag to list
        
        #Ok, we took care of the modification
        self.buff.set_modified(False)
        
    def _delete_range(self,buff,start,end) :
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
                        self.remove_tag_callback(ta.get_data('tagname'))
            it.forward_char()
        return False
            
        
    def __newsubtask(self,title,line_nbr) :
        anchor = self.new_subtask_callback(title)
        self.__subtask(line_nbr,anchor)
        self.refresh_browser()
        
    def __subtask(self,line_nbr,anchor) :
        start_i = self.buff.get_iter_at_line(line_nbr)
        start   = self.buff.create_mark("start",start_i,True)
        end_i   = start_i.copy()
        end_i.forward_line()
        end     = self.buff.create_mark("end",end_i,False)
        self.buff.delete(start_i,end_i)
        bullet ='  ↪ '
        self.__insert_at_mark(start,bullet)
        self.__apply_tag_to_mark(start,end,name="bullet")
        newline = self.get_subtasktitle(anchor)
        self.__insert_at_mark(end,newline,anchor=anchor)
        #The invisible "subtask" tag
        #It must be the last tag set as it's around everything else
        tag = self.buff.create_tag(None)
        tag.set_data('is_subtask', True)
        tag.set_data('child',anchor)
        self.__apply_tag_to_mark(start,end,tag=tag)
        self.__insert_at_mark(end,"\n")
        self.buff.delete_mark(start)
        self.buff.delete_mark(end)
        
    def __apply_tag_to_mark(self,start,end,tag=None,name=None) :
        start_i = self.buff.get_iter_at_mark(start)
        end_i = self.buff.get_iter_at_mark(end)
        if tag :
            self.buff.apply_tag(tag,start_i,end_i)
        elif name :
            self.buff.apply_tag_by_name(name,start_i,end_i)
    
    def __insert_at_mark(self,mark,text,anchor=None) :
        ite = self.buff.get_iter_at_mark(mark)
        if anchor :
            self.insert_with_anchor(text,anchor,_iter=ite,typ="subtask")
        else :
            self.buff.insert(ite,text)
        
    #Function called each time the user input a letter   
    def _insert_at_cursor(self, tv, itera, tex, leng) :
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
                    self.__newsubtask(line,line_nbr)
                    
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
    def _tag_event(self, tag, view, ev, _iter, text, anchor,typ):
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
            editing_cursor = gtk.gdk.Cursor(gtk.gdk.XTERM)
            self.__set_anchor(window, tag, editing_cursor, self.get_property('link'))

    def __set_anchor(self, window, tag, cursor, prop):
        window.set_cursor(cursor)
        for key, val in prop.iteritems():
            tag.set_property(key, val)

gobject.type_register(TaskView)

