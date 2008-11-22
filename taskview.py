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
        ##########Tag we will use #######
        #We use the tag table (tag are defined here but set in self.modified)
        self.table = self.buff.get_tag_table()
        #tag test for title
        title_tag = self.buff.create_tag("title",foreground="#12F",scale=1.6,underline=1)
        title_tag.set_property("pixels-above-lines",10)
        title_tag.set_property("pixels-below-lines",10)
        #Tag higligt
        fluo_tag = self.buff.create_tag("fluo",background="#F0F")
        #Bullet tag
        bullet_tag = self.buff.create_tag("bullet",scale=1.6)
        #start = self.buff.get_start_iter()
        end = self.buff.get_end_iter()
        #We have to find a way to keep this tag for the first line
        #Even when the task is edited

        self.__tags = []
        
        #Callback to refresh the editor window
        self.refresh = None
        
        #Signals
        self.connect('motion-notify-event', self._motion)
        self.connect('focus-out-event', lambda w, e: self.table.foreach(self.__tag_reset, e.window))
        #The signal emitted each time the buffer is modified
        self.buff.connect("modified_changed",self._modified)
        self.buff.connect('insert-text',self._insert_at_cursor)
        
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
    def insert_with_anchor(self, text, anchor=None, _iter=None):
        b = self.get_buffer()
        if _iter is None:
            _iter = b.get_end_iter()
        if anchor is None:
            anchor = text

        tag = b.create_tag("link", **self.get_property('link'))
        tag.set_data('is_anchor', True)
        tag.connect('event', self._tag_event, text, anchor)
        self.__tags.append(tag)
        b.insert_with_tags(_iter, text, tag)

        
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
    #Get the content of the task without the title
    def get_tasktext(self) :
        texte = self.get_text()
        return texte
#    #Strip the title (first line with text) from the rest  
#    #We don't use serializing here !
#    def get_fulltext(self) :
#        texte = self.buff.get_text(self.buff.get_start_iter(),self.buff.get_end_iter())

#        stripped = texte.strip(' \n\t')
#        content = texte.partition('\n')
#        #We don't have an empty task
#        #We will find for the first line as the title
#        if stripped :
#            while not content[0] :
#                content = content[2].partition('\n')
#        return content[0],content[2]
        
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

    #parse the buffer and output an XML representation
    #Buf is the buffer to parse from start to end
    #name is the name of the XML element and doc is the XML dom
    def __parsebuf(self,buf, start, end,name,doc) :
        txt = ""
        it = start.copy()
        parent = doc.createElement(name)
        while it.get_offset() != end.get_offset() :
            #if a tag begin, we will parse until the end
            if it.begins_tag() :
                #We take the tag with the highest priority
                ta = it.get_tags()[0]
                for t in it.get_tags() :
                    if t.get_priority() > ta.get_priority() :
                        ta = t
                #So now, we are in tag "ta"
                startit = it.copy()
                it.forward_to_tag_toggle(ta)
                endit = it.copy()
                #remove the tag (to avoid infinite loop)
                buf.remove_tag(ta,startit,endit)
                #recursive call around the tag "ta"
                parent.appendChild(self.__parsebuf(buf,startit,endit,ta.props.name,doc))
            #else, we just add the text
            else :
                parent.appendChild(doc.createTextNode(it.get_char()))
                it.forward_char()
        parent.normalize()
        return parent
        
    #parse the XML and put the content in the buffer
    def __parsexml(self,buf,ite,element) :
        for n in element.childNodes :
            if n.nodeType == n.ELEMENT_NODE :
                #print "<%s>" %n.nodeName
                start = ite.get_offset()
                end = self.__parsexml(buf,ite,n)
                s = buf.get_iter_at_offset(start)
                e = buf.get_iter_at_offset(end)
                buf.apply_tag_by_name(n.nodeName,s,e)
                #print "</%s>" %n.nodeName
            elif n.nodeType == n.TEXT_NODE :
                buf.insert(ite,n.toxml())
        #return buf.get_end_iter()
        return ite.get_offset()
                
    #We should have a look at Tomboy Serialize function 
    #NoteBuffer.cs : line 1163
    ### Serialize the task : transform it's content in something
    #we can store
    def __taskserial(self,register_buf, content_buf, start, end, udata) :
        #Currently we serialize in XML
        its = start.copy()
        ite = end.copy()
        doc = xml.dom.minidom.Document()
        doc.appendChild(self.__parsebuf(content_buf,its, ite,"content",doc))
        #We don't want the whole doc with the XML declaration
        #we only take the first node (the "content" one)
        node = doc.firstChild
        return node.toxml().encode("utf-8")
        #return content_buf.get_text(start,end)
        
    ### Deserialize : put all in the TextBuffer
    def __taskdeserial(self,register_buf, content_buf, ite, data, cr_tags, udata) :
        #Currently the serializing is still trivial
        #content_buf.insert(ite, data)
        #fluo = self.table.lookup("fluo")
        #content_buf.insert_with_tags(ite,data,fluo)
        
        #backward compatibility
        if not data.startswith("<content>") :
            data = "<content>%s</content>" %data
        #print data
        element = xml.dom.minidom.parseString(data)
        val = self.__parsexml(content_buf,ite,element)
        #content_buf.insert(ite, "\n- aze\n -qsd")
        #self.insert_with_anchor("http://aze","http://eaz")
        return True
        
########### Private function ####################
        
    #The buffer was modified, let reflect this
    # 1. Apply the title style on the first line
    # 2. Change the name of the window if title change
    def _modified(self,a=None) :
        start = self.buff.get_start_iter()
        end = self.buff.get_end_iter()
        #Here we apply the title tag on the first line
        line_nbr = 1
        linecount = self.buff.get_line_count()
        if linecount > line_nbr :
            #Applying title on the first line
            end_title = self.buff.get_iter_at_line(line_nbr)
            stripped = self.buff.get_text(start,end_title).strip('\n\t ')
            #Here we ignore lines that are blank
            #Title is the first written line
            while line_nbr <= linecount and not stripped :
                line_nbr += 1
                end_title = self.buff.get_iter_at_line(line_nbr)
                stripped = self.buff.get_text(start,end_title).strip('\n\t ')
            self.buff.apply_tag_by_name('title', start, end_title)
            self.buff.remove_tag_by_name('title',end_title,end)
            #title of the window  (we obviously remove \t and \n)
            self.refresh(self.buff.get_text(start,end_title).strip('\n\t'))
        #Or to all the buffer if there is only one line
        else :
            self.buff.apply_tag_by_name('title', start, end)
            #title of the window 
            #self.window.set_title(self.buff.get_text(start,end))
            self.refresh(self.buff.get_text(start,end))
                        
        #Do we want to save the text at each modification ?
        
        #Ok, we took care of the modification
        self.buff.set_modified(False)
    
    #Function called each time the user input a letter   
    def _insert_at_cursor(self,tv,itera,tex,leng) :
        #New line : the user pressed enter !
        #If the line begins with "-", it's a new subtask !
        if tex == '\n' :
            #The nbr just before the \n
            line_nbr = itera.get_line()
            start_line = itera.copy()
            start_line.set_line(line_nbr)
            end_line = itera.copy()
            #We add a bullet list but not on the first line
            #Because it's the title
            if line_nbr > 0 :
                line = start_line.get_slice(end_line)
                #the "-" might be after a space
                #Python 2.5 should allow both tests in one
                if line.startswith('-') or line.startswith(' -') :
                    line = line.lstrip(' -')
                    #From Tomboy : ('\u2022\u2218\u2023')
                    #bullet = '%s%s%s' %(unichr(2022),unichr(2218),unichr(2023))
                    #FIXME : we should insert the correct UTF-8 code
                    bullet =' ↪ '
                    newline = '%s\n' %(line)
                    newline.encode('utf-8')
                    starts = self.buff.get_iter_at_line(line_nbr)
                    ends = starts.copy()
                    ends.forward_line()
                    #self.buff.apply_tag_by_name('fluo',starts,ends)
                    self.buff.delete(starts,ends)
                    starts = self.buff.get_iter_at_line(line_nbr)
                    ends = starts.copy()
                    ends.forward_line()
                    #Inserting the bullet
                    self.buff.insert(starts,bullet)
                    starts = self.buff.get_iter_at_line(line_nbr)
                    ends = starts.copy()
                    ends.forward_line()
                    self.buff.apply_tag_by_name("bullet",starts,ends)
                    #Inserting the name of the subtask as a link
                    #TODO : anchor = get_task_by_title(newline)
                    anchor = "1@1"
                    starts = self.buff.get_iter_at_line(line_nbr)
                    ends = starts.copy()
                    ends.forward_line()
                    self.insert_with_anchor(newline,anchor,_iter=ends)
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
            tag_table = self.get_buffer().get_tag_table()
            tag_table.foreach(self.__tag_reset, window)

    #We clicked on a link
    def _tag_event(self, tag, view, ev, _iter, text, anchor):
        _type = ev.type
        if _type == gtk.gdk.MOTION_NOTIFY:
            return
        elif _type in [gtk.gdk.BUTTON_PRESS, gtk.gdk.BUTTON_RELEASE]:
            button = ev.button
            cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
            if _type == gtk.gdk.BUTTON_RELEASE:
                print "anchor clicked : %s" %anchor
                self.emit('anchor-clicked', text, anchor, button)
                self.__set_anchor(ev.window, tag, cursor, self.get_property('hover'))
            elif button in [1, 2]:
                self.__set_anchor(ev.window, tag, cursor, self.get_property('active'))

    def __tag_reset(self, tag, window):
        if tag.get_data('is_anchor'):
            self.__set_anchor(window, tag, None, self.get_property('link'))

    def __set_anchor(self, window, tag, cursor, prop):
        window.set_cursor(cursor)
        for key, val in prop.iteritems():
            tag.set_property(key, val)

gobject.type_register(TaskView)

