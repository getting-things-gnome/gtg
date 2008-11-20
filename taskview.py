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
        table = self.buff.get_tag_table()
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
        self.connect('focus-out-event', lambda w, e: self.get_buffer().get_tag_table().foreach(self.__tag_reset, e.window))
        #The signal emitted each time the buffer is modified
        self.buff.connect("modified_changed",self._modified)
        self.buff.connect('insert-text',self._insert_at_cursor)
        
        #All the typical properties of our textview
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(True)
        self.set_cursor_visible(True)
        self.buff.set_modified(False)
    
    #This function is called to refresh the editor 
    #Specially when we change the title
    def refresh_callback(self,funct) :
        self.refresh = funct
    
    #Buffer related functions
    #This set the text of the buffer (and replace any existing one)
    def set_text(self,stri) :
        self.buff.set_text(stri)
    #This append text at the end of the buffer
    def insert(self, text, _iter=None):
        if _iter is None:
            _iter = self.buff.get_end_iter()
        self.buff.insert(_iter, text)

    def insert_with_anchor(self, text, anchor=None, _iter=None):
        b = self.get_buffer()
        if _iter is None:
            _iter = b.get_end_iter()
        if anchor is None:
            anchor = text

        tag = b.create_tag(None, **self.get_property('link'))
        tag.set_data('is_anchor', True)
        tag.connect('event', self._tag_event, text, anchor)
        self.__tags.append(tag)
        b.insert_with_tags(_iter, text, tag)
        
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

