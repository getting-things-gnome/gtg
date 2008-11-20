#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This is a class take originally from http://trac.atzm.org/index.cgi/wiki/PyGTK

#This class implement a gtk.TextView but with many other features like hyperlink

import gtk
import gobject
import pango

class HyperTextView(gtk.TextView):
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
        self.link   = {'background': 'white', 'foreground': 'blue', 'underline': pango.UNDERLINE_SINGLE}
        self.active = {'background': 'light gray', 'foreground': 'red', 'underline': pango.UNDERLINE_SINGLE}
        self.hover  = {'background': 'light gray', 'foreground': 'blue', 'underline': pango.UNDERLINE_SINGLE}

        self.set_editable(False)
        self.set_cursor_visible(False)

        self.__tags = []

        self.connect('motion-notify-event', self._motion)
        self.connect('focus-out-event', lambda w, e: self.get_buffer().get_tag_table().foreach(self.__tag_reset, e.window))
        
        #All the typical properties
        self.set_wrap_mode(gtk.WRAP_WORD)
        self.set_editable(True)
        self.set_cursor_visible(True)

    def insert(self, text, _iter=None):
        b = self.get_buffer()
        if _iter is None:
            _iter = b.get_end_iter()
        b.insert(_iter, text)

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

gobject.type_register(HyperTextView)

