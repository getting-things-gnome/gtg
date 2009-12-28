# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
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
import sys
import os
import xml.dom.minidom
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
from utility import iso8601toTime, timeToIso8601, dateToIso8601,\
                    timezone, text_strip_tags
from GTG.tools.dates import NoDate as GtgNoDate,\
                            FuzzyDate as GtgFuzzyDate,\
                            strtodate as gtgstrtodate


class GenericTask(object):
    """GenericTask is the abstract interface that represents a generic task.
    GtgTask and RtmTask are the implementation of this"""

    title = property(lambda self: self._get_title(),
                     lambda self, arg: self._set_title(arg))

    id = property(lambda self: self._get_id())
    #NOTE: text is the task extended description (or notes
    #      in rtm)
    text = property(lambda self: self._get_text(),
                     lambda self, arg: self._set_text(arg))

    modified = property(lambda self: self._get_modified())

    due_date = property(lambda self: self._get_due_date(),
                     lambda self, arg: self._set_due_date(arg))

    tags = property(lambda self: self._get_tags(),
                     lambda self, arg: self._set_tags(arg))

    def __str__(self):
        return "Task " + self.title + "(" + self.id + ")"

    def copy(self, task):
        #NOTE: do not be fooled. Most of these variables are
        #      properties.
        carbon = self.title 
        master = task.title
        if carbon != master:
            self.title = master
        
        #NOTE: please respect this order of text before tags.
        #      tags have a side effect of cleaning up text,
        #      it will be fixed in 0.3

        #note:text sync disabled in 0.2
        #carbon = self.text
        #master = task.text
        #if carbon != master:
        #    self.text = master

        #carbon = self.tags
        #master = task.tags
        #if carbon != master:
        #    self.tags = master

        carbon = self.due_date
        master = task.due_date
        if carbon != master:
            self.due_date = master

    #Interface specification that will be overwritten
    # by the derived classes
    def delete(self):
        raise Exception()


class RtmTask(GenericTask):

    def __init__(self, task, list_id, taskseries_id, rtm, timeline, logger):
        super(RtmTask, self).__init__()
        self.rtm = rtm
        self.timeline = timeline
        self.task = task
        self.list_id = list_id
        self.taskseries_id = taskseries_id
        self.logger = logger

    def _get_title(self):
        if hasattr(self.task,"name"):
            return self.task.name
        else:
            if self.logger:
                self.logger.debug ("rtm task has no title")
            return ""

    def _set_title(self, title):
        self.rtm.tasks.setName(timeline=self.timeline, \
                        list_id =self.list_id, \
                        taskseries_id=self.taskseries_id, \
                        task_id=self.id, \
                        name = title)

    def _get_id(self):
        if hasattr(self.task, 'task'):
            return self.task.task.id
        else:
            return self.task.id

    def _get_tags(self):
        if hasattr(self.task,"tags") and hasattr(self.task.tags, 'tag'):
            if type(self.task.tags.tag) ==list:
                return self.task.tags.tag
            else:
                return [self.task.tags.tag]
        elif hasattr(self.task,"tags") and hasattr(self.task.tags, 'list'):
            return map(lambda x: x.tag if hasattr(x, 'tag') else None, \
                       self.task.tags.list)
        return []

    def _set_tags(self, tags):
        tagstxt=""
        for tag in tags:
            name = tag.get_name()
            name_fixed = name[name.find('@')+1:]
            if tagstxt == "":
                tagstxt = name_fixed
            else:
                tagstxt = tagstxt+ ",  " + name_fixed
        self.rtm.tasks.setTags(timeline=self.timeline, \
                        list_id =self.list_id, \
                        taskseries_id=self.taskseries_id, \
                        task_id=self.id, \
                        tags=tagstxt)

    def _get_text(self):
        if hasattr(self.task, 'notes') and \
           hasattr(self.task.notes, 'note'):
            #Rtm saves the notes text inside the member "$t". Don't ask me why.
            if type(self.task.notes.note) == list:
                return "".join(map(lambda note: getattr(note, '$t') + "\n", \
                                self.task.notes.note))
            else:
                return getattr(self.task.notes.note, '$t')
        else:
            return ""

    def _set_text(self, text):
        #delete old notes
        #FIXME: the first check *should* not be necessary (but it is?).
        if hasattr(self.task, 'notes') and \
            hasattr(self.task.notes, 'note'):
            if type(self.task.notes.note) == list:
                note_ids =map(lambda note: note.id, self.task.notes.note)
            else:
                note_ids = [self.task.notes.note.id]
            map(lambda id: self.rtm.tasksNotes.delete(timeline=self.timeline, \
                    note_id=id), note_ids)
        #add a new one
        #TODO: investigate what is "Note title",  since there doesn't seem to
        #be a note
        # title in the web access.
        #FIXME: minidom this way is ok, or do we suppose to get multiple
        #      nodes in "content"?
        if text == "":
            return
        document = xml.dom.minidom.parseString(text)
        content =document.getElementsByTagName("content")
        if len(content)>0 and hasattr(content[0], 'firstChild') \
           and hasattr(content[0].firstChild, 'data'):
            content = content[0].firstChild.data
        else:
            return
        self.rtm.tasksNotes.add(timeline=self.timeline, \
                                list_id = self.list_id,\
                                taskseries_id = self.taskseries_id, \
                                task_id = self.id, \
                                note_title="",\
                                note_text = content)

    def _get_due_date(self):
        if hasattr(self.task,'task') and hasattr(self.task.task, 'due') and \
                self.task.task.due != "":
            return iso8601toTime(self.task.task.due) - timezone()
        return None

    def _set_due_date(self, due):
        if type(due) != type(None):
            due_string = timeToIso8601(due + timezone())
            self.rtm.tasks.setDueDate(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.id, \
                                      due=due_string)
        else:
            self.rtm.tasks.setDueDate(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.id)

    def _get_modified(self):
        if not hasattr(self.task, 'modified') or self.task.modified == "":
            return None

        return iso8601toTime(self.task.modified) - timezone()

    def delete(self):
        self.rtm.tasks.delete(timeline = self.timeline, \
                              list_id = self.list_id, \
                              taskseries_id = self.taskseries_id, \
                              task_id = self.id)


class GtgTask(GenericTask):

    def __init__(self, task, plugin_api, logger):
        super(GtgTask, self).__init__()
        self.task = task
        self.plugin_api = plugin_api
        self.logger = logger

    def _get_title(self):
        return self.task.get_title()

    def _set_title(self, title):
        self.task.set_title(title)

    def _get_id(self):
        return self.task.get_uuid()

    def _get_tags(self):
        return self.task.get_tags()

    def _set_tags(self, tags):
        #NOTE: isn't there a better mode than removing all tags?
        #      need to add function in GTG/core/task.py
        old_tags = self.tags
        for tag in old_tags:
            try:
                self.task.remove_tag(tag)
            except:
                if self.logger:
                    self.logger.debug("remove tag from GTG failed!!!")
        #moves the tags at the end of the text
        self.text = "<content>" + text_strip_tags(self.text) + "\n" +\
                reduce(lambda tags, tag: tags + ', @' + tag,[" "] + tags)[3:] +\
                "</content>"
        map(lambda tag: self.task.tag_added('@'+tag), tags)

    def _get_text(self):
        return self.task.get_text()

    def _set_text(self, text):
        self.task.set_text(text)

    def _get_due_date(self):
        due = self.task.get_due_date()
        due_string = str(due)
        if self.logger:
            self.logger.debug("due_string |" + due_string + "|")
        #TODO: Handle fuzzy dates
        if due_string == "" or isinstance( due, GtgFuzzyDate):
            return None
        return iso8601toTime(due_string)

    def _set_due_date(self, due):
        if type(due) != None:
            due_string = dateToIso8601(due)
            self.task.set_due_date(gtgstrtodate(due_string))
        else:
            return GtgNoDate

    def _get_modified(self):
        modified = self.task.get_modified()
        if modified == None or modified == "":
            return None
        return iso8601toTime(modified)

    def delete(self):
        self.plugin_api.get_requester().delete_task(self.task.get_id())
