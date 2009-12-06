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
TaskClipboard allows to cut/copy the content of a TaskView accross multiples
taskeditors, preserving subtasks
"""
class TaskClipboard():
    def __init__(self):
        self.description = None
        self.content = []
        
    """"take two gtk.TextIter as parameter and copy the
    """
    def copy(self,start,stop,bullet=None):
        #Now, we take care of the normal, cross application clipboard
        text = start.get_text(stop)
        if text and bullet:
            #we replace the arrow by the original "-"
            newtext = text.replace(bullet, "-")
            self.description = newtext
        elif text:
            self.description = text
        
        end_line = start.copy()
        #we take line after line in the selection
        while end_line.get_line() <= stop.get_line() and end_line.forward_line():
            print "clip 1 offset : %s" %end_line.get_offset()
            end_line.backward_char()
            #we want to detect subtasks in the selection
            tags = end_line.get_tags()+end_line.get_toggled_tags(False)
            is_subtask = False
            print "clip 2 offset : %s" %end_line.get_offset()
            for ta in tags :
                if (ta.get_data('is_subtask')):
                    is_subtask = True
                    self.content.append(['subtask', ta.get_data('child')])
            if not is_subtask:
                if end_line.get_line() < stop.get_line():
                    self.content.append(['text', "%s\n" %start.get_text(end_line)])
                else:
                    self.content.append(['text', start.get_text(stop)])
            print "clip 3 offset : %s" %end_line.get_offset()
            end_line.forward_char()
            start.forward_line()
            print "clip 4 offset : %s" %end_line.get_offset()
        
        
    def paste_text(self):
        return self.description
        
    def paste(self):
        return self.content
    
    def clear(self):
        self.descriptiion = None
        self.content = []
