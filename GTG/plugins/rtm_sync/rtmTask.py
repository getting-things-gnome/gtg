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
import datetime
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genericTask import GenericTask



class RtmTask(GenericTask):
    
    def __init__(self, task, list_id, taskseries_id, rtm, timeline, logger,
                 proxy):
        super(RtmTask, self).__init__(proxy)
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

    def _get_status(self):
        if hasattr(self.task, 'task'):
            return self.get_proxy()._rtm_to_gtg_status[self.task.task.completed\
                                                      == ""]
        else:
            return self.get_proxy()._rtm_to_gtg_status[self.task.completed == ""]

    def _set_status(self, gtg_status):
        status = self.get_proxy()._gtg_to_rtm_status[gtg_status]
        print "setting status"
        if status == True:
            self.rtm.tasks.uncomplete(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.id)
        else:
            self.rtm.tasks.complete(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.id)

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
            to_return = self.__time_rtm_to_datetime(self.task.task.due) 
                    #   - datetime.timedelta(seconds = time.timezone)
            return to_return.date()
        return None

    def _set_due_date(self, due):
        if due != None:
            due_string = self.__time_date_to_rtm(due + \
                    datetime.timedelta(seconds = time.timezone))
            self.rtm.tasks.setDueDate(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.id, \
                                      parse = 1, \
                                      due=due_string)
        else:
            self.rtm.tasks.setDueDate(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.id)

    def _get_modified(self):
        if not hasattr(self.task, 'modified') or self.task.modified == "":
            return None
        return self.__time_rtm_to_datetime(self.task.modified) #\
                #                + datetime.timedelta(time.timezone)

    def delete(self):
        self.rtm.tasks.delete(timeline = self.timeline, \
                              list_id = self.list_id, \
                              taskseries_id = self.taskseries_id, \
                              task_id = self.id)


    def __time_rtm_to_datetime(self, string):
        #FIXME: need to handle time with TIMEZONES!
        string = string.split('.')[0].split('Z')[0]
        return datetime.datetime.strptime(string.split(".")[0], \
                                          "%Y-%m-%dT%H:%M:%S")

    def __time_rtm_to_date(self, string):
        #FIXME: need to handle time with TIMEZONES!
        string = string.split('.')[0].split('Z')[0]
        return datetime.datetime.strptime(string.split(".")[0], "%Y-%m-%d")

    def __time_datetime_to_rtm(self, timeobject):
        if timeobject == None:
            return ""
        return timeobject.strftime("%Y-%m-%dT%H:%M:%S")

    def __time_date_to_rtm(self, timeobject):
        if timeobject == None:
            return ""
        return timeobject.strftime("%Y-%m-%d")
