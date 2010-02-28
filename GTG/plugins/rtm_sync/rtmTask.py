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
import datetime
import time
import xml.dom.minidom
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genericTask import GenericTask
from GTG.taskeditor.taskview import bullet1_ltr, bullet1_rtl, bullet2




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
        #Checking if a task is recurring is done inside __get_rtm_task_attribute
        # so we call that to set self.recurring correctly
        self.recurring = False
        self.__get_rtm_task_attribute("id")

    def _get_title(self):
        if hasattr(self.task,"name"):
            return self.task.name
        else:
            self.__log("rtm task has no title: " + str(self.task))
            return ""

    def _set_title(self, title):
        self.rtm.tasks.setName(timeline=self.timeline, \
                        list_id =self.list_id, \
                        taskseries_id=self.taskseries_id, \
                        task_id=self.id, \
                        name = title)

    def _get_id(self):
        self.__log("getting the task id")
        return self.__get_rtm_task_attribute("id")

    def __get_rtm_task_attribute(self, attr):
        if hasattr(self.task, 'task'):
            if hasattr(self.task.task, 'list'):
                return getattr(self.task.task.list, attr)
            elif type(self.task.task) == list:
                self.recurring = True
                return getattr(self.task.task[len(self.task.task) - 1], attr)
            else:
                return getattr(self.task.task, attr)
        else:
            if type(self.task) == list:
                return getattr(self.task[len(self.task) - 1], attr)
            else:
                return getattr(self.task, attr)

    def _get_status(self):
        completed = self.__get_rtm_task_attribute("completed")
        self.__log("getting status:" + str(completed))
        return self.get_proxy()._rtm_to_gtg_status[completed == ""]

    def _set_status(self, gtg_status):
        status = self.get_proxy()._gtg_to_rtm_status[gtg_status]
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
        self.__log("getting tag list(1): " + str(self.task))
        if hasattr(self.task,"tags") and hasattr(self.task.tags, 'tag'):
            self.__log("getting tag list(2): " + str(self.task.tags.tag))
            if type(self.task.tags.tag) ==list:
                return self.task.tags.tag
            else:
                return [self.task.tags.tag]
        elif hasattr(self.task,"tags") and hasattr(self.task.tags, 'list'):
            self.__log("getting tag list(2): " + str(self.task.tags.list))
            return map(lambda x: x.tag if hasattr(x, 'tag') else None, \
                       self.task.tags.list)
        return []

    def _set_tags(self, tags):
        #remove the @ at the beginning
        tags_purified = []
        for tag in tags:
            if tag[0] == '@':
                tag = tag[1:]
            tags_purified.append(tag.lower())

        #check if it's necessary to sync
        rtm_tags_set = set(self.tags)
        tags_purified_set = set(tags_purified)
        if rtm_tags_set.intersection(tags_purified_set) == set() and \
           rtm_tags_set.union(tags_purified_set) == rtm_tags_set:
            return

        #sync
        if len(tags_purified) > 0:
            tagstxt = reduce(lambda x,y: x + ", " + y, tags_purified)
        else:
            tagstxt = ""
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
                text = "".join(map(lambda note: getattr(note, '$t') + "\n", \
                                self.task.notes.note))
            else:
                text = getattr(self.task.notes.note, '$t')
        else:
            text = ""
        #adding back the tags (subtasks are added automatically)
        tags = self.tags
        if len(tags) > 0:
            tagstxt = "@" + reduce(lambda x,y: x + ", " + "@" + y, self.tags) + "\n"
        else:
            tagstxt = ""
        return tagstxt + text.strip()

    def _set_text(self, content):
        element = xml.dom.minidom.parseString(content)
        text = ""
        if element:
            for n in element.getElementsByTagName("content")[0].childNodes:
                if n.nodeType == n.TEXT_NODE:
                    text += n.nodeValue

        p = re.compile(r'^\s* [' + bullet1_ltr + ',' + bullet1_rtl + ',' + \
                       bullet2 + ']\s*$',re.MULTILINE)
        text = p.sub('', text)
        text = text.strip()
        print text
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
        self.rtm.tasksNotes.add(timeline=self.timeline, \
                                list_id = self.list_id,\
                                taskseries_id = self.taskseries_id, \
                                task_id = self.id, \
                                note_title = "",\
                                note_text = text)

    def __strip_content(self, element):
        txt = ""
        if element:
            for n in element.childNodes:
                if n.nodeType == n.ELEMENT_NODE:
                    txt += self.__strip_content(n)
                elif n.nodeType == n.TEXT_NODE:
                    txt += n.nodeValue
        return tx



    def _get_due_date(self):
        if hasattr(self.task,'task'):
            if type(self.task.task) != list:
                task = self.task.task
            else:
                task = self.task.task[len(self.task.task) - 1]
            if hasattr(task, 'due') and task.due != "":
                to_return = self.__time_rtm_to_datetime(task.due) 
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
        modified = self.__time_rtm_to_datetime(self.task.modified)
        if self.recurring == False:
            return modified
        else:
            now = datetime.datetime.now()
            this_morning =datetime.datetime(year = now.year,\
                                        month = now.month,\
                                        day = now.day)
            if modified > this_morning:
                return modified
            else:
                return this_morning

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

    def __log(self, message):
        if self.logger:
            self.logger.debug (message)
