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

'''
'''
#To introspect tomboy: qdbus org.gnome.Tomboy /org/gnome/Tomboy/RemoteControl

import os
import time
import uuid
import threading
import datetime
import subprocess
import exceptions
from dateutil.tz     import tzutc, tzlocal

from GTG.backends.genericbackend        import GenericBackend
from GTG                                import _
from GTG.backends.backendsignals        import BackendSignals
from GTG.backends.syncengine            import SyncEngine, SyncMeme
from GTG.backends.rtm.rtm               import createRTM, RTMError, RTMAPIError
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.tools.dates                    import RealDate, NoDate
from GTG.core.task                      import Task
from GTG.tools.interruptible            import interruptible


GTG_TO_RTM_STATUS = {Task.STA_ACTIVE: True,
                     Task.STA_DONE: False,
                     Task.STA_DISMISSED: False}
RTM_TO_GTG_STATUS = {True: Task.STA_ACTIVE,
                     False: Task.STA_DONE}

class RtmTask(object):
    

    def __init__(self, task, list_id, taskseries_id, rtm, timeline):
        self.rtm = rtm
        self.timeline = timeline
        self.task = task
        self.list_id = list_id
        self.taskseries_id = taskseries_id
        #Checking if a task is recurring is done inside __get_rtm_task_attribute
        # so we call that to set self.recurring correctly
        self.recurring = False
        self.__get_rtm_task_attribute("id")

    def get_title(self):
        if hasattr(self.task,"name"):
            return self.task.name
        else:
            return ""

    def set_title(self, title):
        self.rtm.tasks.setName(timeline=self.timeline, \
                        list_id =self.list_id, \
                        taskseries_id=self.taskseries_id, \
                        task_id=self.get_id(), \
                        name = title)

    def get_id(self):
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

    def get_status(self):
        completed = self.__get_rtm_task_attribute("completed")
        return RTM_TO_GTG_STATUS[completed == ""]

    def set_status(self, gtg_status):
        status = GTG_TO_RTM_STATUS[gtg_status]
        if status == True:
            self.rtm.tasks.uncomplete(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.get_id())
        else:
            self.rtm.tasks.complete(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.get_id())

    def get_tags(self):
        if hasattr(self.task,"tags") and hasattr(self.task.tags, 'tag'):
            if type(self.task.tags.tag) ==list:
                return self.task.tags.tag
            else:
                return [self.task.tags.tag]
        elif hasattr(self.task,"tags") and hasattr(self.task.tags, 'list'):
            return map(lambda x: x.tag if hasattr(x, 'tag') else None, \
                       self.task.tags.list)
        return []

    def set_tags(self, tags):
        #remove the @ at the beginning
        tags_purified = []
        for tag in tags:
            if tag[0] == '@':
                tag = tag[1:]
            tags_purified.append(tag.lower())

        #check if it's necessary to sync
        rtm_tags_set = set(self.get_tags())
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
                        task_id=self.get_id(), \
                        tags=tagstxt)

    def get_text(self):
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
        tags = self.get_tags()
        if len(tags) > 0:
            tagstxt = "@" + reduce(lambda x,y: x + ", " + "@" + y, tags) + "\n"
        else:
            tagstxt = ""
        return tagstxt + text.strip()

    def set_text(self, text):
        #delete old notes
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
        #be a note title in the web access.
        #FIXME: minidom this way is ok, or do we suppose to get multiple
        #      nodes in "content"?
        if text == "":
            return
        self.rtm.tasksNotes.add(timeline=self.timeline, \
                                list_id = self.list_id,\
                                taskseries_id = self.taskseries_id, \
                                task_id = self.get_id(), \
                                note_title = "",\
                                note_text = text)

    def get_due_date(self):
        if hasattr(self.task,'task'):
            if type(self.task.task) != list:
                task = self.task.task
            else:
                task = self.task.task[len(self.task.task) - 1]
            if hasattr(task, 'due') and task.due != "":
                date = self.__time_rtm_to_datetime(task.due).date()
                if date:
                    return RealDate(date)
        return NoDate()

    def set_due_date(self, due):
        if due != None:
            due_string = self.__time_date_to_rtm(due)
            self.rtm.tasks.setDueDate(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.get_id(), \
                                      parse = 1, \
                                      due=due_string)
        else:
            self.rtm.tasks.setDueDate(timeline=self.timeline, \
                                      list_id = self.list_id,\
                                      taskseries_id = self.taskseries_id, \
                                      task_id = self.get_id())

    def get_modified(self):
        if not hasattr(self.task, 'modified') or self.task.modified == "":
            modified = self.__time_rtm_to_datetime(self.task.added)
        else:
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
                              task_id = self.get_id())

    #RTM speaks utc, and accepts utc if the "parse" option is set.
    def __tz_utc_to_local(self, dt):
        dt = dt.replace(tzinfo = tzutc())
        dt = dt.astimezone(tzlocal())
        return dt.replace(tzinfo = None)

    def __tz_local_to_utc(self, dt):
        dt = dt.replace(tzinfo = tzlocal())
        dt = dt.astimezone(tzutc())
        return dt.replace(tzinfo = None)

    def __time_rtm_to_datetime(self, string):
        string = string.split('.')[0].split('Z')[0]
        dt = datetime.datetime.strptime(string.split(".")[0], \
                                          "%Y-%m-%dT%H:%M:%S")
        return self.__tz_utc_to_local(dt)
        

    def __time_rtm_to_date(self, string):
        string = string.split('.')[0].split('Z')[0]
        dt = datetime.datetime.strptime(string.split(".")[0], "%Y-%m-%d")
        return self.__tz_utc_to_local(dt)


    def __time_datetime_to_rtm(self, timeobject):
        if timeobject == None:
            return ""
        timeobject = self.__tz_local_to_utc(timeobject)
        return timeobject.strftime("%Y-%m-%dT%H:%M:%S")

    def __time_date_to_rtm(self, timeobject):
        if timeobject == None:
            return ""
        #WARNING: no timezone? seems to break the symmetry.
        return timeobject.strftime("%Y-%m-%d")

    def __str__(self):
        return "Task %s (%s)" % (self.get_title(), self.get_id())



class Backend(PeriodicImportBackend):
    

    _general_description = { \
        GenericBackend.BACKEND_NAME:       "backend_rtm", \
        GenericBackend.BACKEND_HUMAN_NAME: _("Remember The Milk"), \
        GenericBackend.BACKEND_AUTHORS:    ["Luca Invernizzi"], \
        GenericBackend.BACKEND_TYPE:       GenericBackend.TYPE_READWRITE, \
        GenericBackend.BACKEND_DESCRIPTION: \
            _("Fill me"),\
        }

    _static_parameters = { \
        "period": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT, \
            GenericBackend.PARAM_DEFAULT_VALUE: 10, },
        }

    PUBLIC_KEY = "2a440fdfe9d890c343c25a91afd84c7e"
    PRIVATE_KEY = "ca078fee48d0bbfa"

###############################################################################
### Backend standard methods ##################################################
###############################################################################

    def __init__(self, parameters):
        """
        Instantiates a new backend.

        @param parameters: should match the dictionary returned in
        get_parameters. Anyway, the backend should care if one expected
        value is None or does not exist in the dictionary. 
        """
        super(Backend, self).__init__(parameters)
        #loading the saved state of the synchronization, if any
        self.sync_engine_path = os.path.join('backends/rtm/', \
                                      "sync_engine-" + self.get_id())
        self.token_path = os.path.join('backends/rtm/', \
                                      "auth_token-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.sync_engine_path, \
                                                   SyncEngine())
        self.token = self._load_pickled_file(self.token_path, None)
        self.authenticated = threading.Event()
        self.enqueued_start_get_task = False
        self.login_event = threading.Event()
        
    def initialize(self):
        super(Backend, self).initialize()
        self._rtm_task_dict = {}
        initialize_thread = threading.Thread(target = self._authenticate)
        initialize_thread.setDaemon(True)
        initialize_thread.start()

    def do_periodic_import(self):
        '''
        Once this function is launched, the backend can start pushing
        tasks to gtg parameters.
        
        @return: start_get_tasks() might not return or finish
        '''
        if not self.authenticated.isSet():
            if self.enqueued_start_get_task:
                return
            else:
                self.enqueued_start_get_task = True
                print
                "WAIT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                self.authenticated.wait()
                print "EOWAIT"
                self.enqueued_start_get_task = False
        
        print "GETTING TASKS!!!"
        self.downloadFromWeb()
        #FIXME:push
        stored_rtm_task_ids = self.sync_engine.get_all_remote()
        current_rtm_task_ids = [tid for tid in \
                                    self._get_rtm_task_dict().iterkeys()]
        for rtm_task_id in current_rtm_task_ids:
            self.cancellation_point()
            #Adding and updating
            print "remote " + rtm_task_id
            self._process_rtm_task(rtm_task_id)

        for rtm_task_id in set(stored_rtm_task_ids).difference(\
                                        set(current_rtm_task_ids)):
            self.cancellation_point()
            #Removing the old ones
            print "toremove" + rtm_task_id
            if not self.please_quit:
                tid = self.sync_engine.get_local_id(rtm_task_id)
                self.datastore.request_task_deletion(tid)
                try:
                    self.sync_engine.break_relationship(remote_id = \
                                                        rtm_task_id)
                except KeyError:
                    pass
        




    def save_state(self):
        self._store_pickled_file(self.sync_engine_path, self.sync_engine)

    def get_number_of_tasks(self):
        '''
        Returns the number of tasks stored in the backend. Doesn't need to be a
        fast function, is called just for the UI
        '''
        return 42

###############################################################################
### Something got removed #####################################################
###############################################################################

    @interruptible
    def remove_task(self, tid):
        ''' Completely remove the task with ID = tid '''
        print "REM*******************************************############ "
        if not self.authenticated.isSet():
            #FIXME: isn't wait better?
            return
        self.cancellation_point()
        try:
            print "REMOVING"
            rtm_task_id = self.sync_engine.get_remote_id(tid)
            print "RTM_DICT",  self._get_rtm_task_dict()
            print "TID", rtm_task_id
            if rtm_task_id not in self._get_rtm_task_dict():
                #we might need to refresh our task cache
                self.downloadFromWeb()
            rtm_task = self._get_rtm_task_dict()[rtm_task_id]
            rtm_task.delete()
            print "Removed"
        except KeyError:
            print "KEYERROR"
            return
            try:
                self.sync_engine.break_relationship(local_id = tid)
            except:
                pass


###############################################################################
### Process tasks #############################################################
###############################################################################

    @interruptible
    def set_task(self, task):
        print "Set task rtm"
        if not self.authenticated.isSet():
            #FIXME: to_set queue?
            return
        self.cancellation_point()
        tid = task.get_id()
        is_syncable = self._task_is_syncable(task)
        action, rtm_task_id = self.sync_engine.analyze_local_id(tid, \
                              self.datastore.has_task, self._rtm_has_task, \
                                                         is_syncable)
        print action, rtm_task_id
        if action == SyncEngine.ADD:
            title = task.get_title()
            result = self.rtm.tasks.add(timeline=self.timeline, name=title)
            rtm_task = RtmTask(result.list.taskseries.task, result.list.id,\
                              result.list.taskseries.id, self.rtm, \
                              self.timeline)
            self._rtm_task_dict[rtm_task.get_id()] = rtm_task
            self._populate_rtm_task(task, rtm_task)
            self.sync_engine.record_relationship( \
                local_id = tid, remote_id = rtm_task.get_id(), \
                meme = self._new_meme(task, rtm_task, "GTG"))

        elif action == SyncEngine.UPDATE:
            rtm_task = self._get_rtm_task_dict()[rtm_task_id]
            meme = self.sync_engine.get_meme_from_local_id(task.get_id())
            print rtm_task.get_modified()
            print type(rtm_task.get_modified())
            newest = meme.which_is_newest(task.get_modified(),
                                 rtm_task.get_modified())
            if newest == "local":
                self._populate_rtm_task(task, rtm_task)
                self._update_meme(meme, task, rtm_task)

        elif action == SyncEngine.REMOVE:
            self.datastore.request_task_deletion(tid)
            try:
                self.sync_engine.break_relationship(local_id = tid)
            except KeyError:
                pass

        elif action == SyncEngine.LOST_SYNCABILITY:
            #FIXME: TODO
            self._exec_lost_syncability(tid, rtm_task)

    def _process_rtm_task(self, rtm_task_id):
        print "Set task rtm"
        self.cancellation_point()
        if not self.authenticated.isSet():
            return
        action, tid = self.sync_engine.analyze_remote_id(rtm_task_id, \
                     self.datastore.has_task, \
                     self._rtm_has_task)
        print "processing rtm" + action

        if action == SyncEngine.ADD:
            rtm_task = self._get_rtm_task_dict()[rtm_task_id]
            tid = str(uuid.uuid4())
            task = self.datastore.task_factory(tid)
            self._populate_task(task, rtm_task)
            self.sync_engine.record_relationship(local_id = tid,\
                    remote_id = rtm_task_id, \
                    meme = self._new_meme(task, rtm_task, self.get_id()))
            self.datastore.push_task(task)

        elif action == SyncEngine.UPDATE:
            rtm_task = self._get_rtm_task_dict()[rtm_task_id]
            task = self.datastore.get_task(tid)
            meme = self.sync_engine.get_meme_from_remote_id(rtm_task_id)
            newest = meme.which_is_newest(task.get_modified(),
                                rtm_task.get_modified())
            if newest == "remote":
                print "HAVE TO UPDATE"
                self._populate_task(task, rtm_task)
                self._update_meme(meme, task, rtm_task)

        elif action == SyncEngine.REMOVE:
            try:
                rtm_task = self._get_rtm_task_dict()[rtm_task_id]
                rtm_task.delete()
                self.sync_engine.break_relationship(remote_id = rtm_task_id)
            except KeyError:
                pass
#
#        elif action == SyncEngine.LOST_SYNCABILITY:
#            self._exec_lost_syncability(tid, note)

###############################################################################
### Helper methods ############################################################
###############################################################################

    def _task_is_syncable(self, task):
        attached_tags = self.get_attached_tags()
        if GenericBackend.ALLTASKS_TAG in attached_tags:
            return True
        for tag in task.get_tags_name():
            if tag in attached_tags:
                return  True
        return False

    def _new_meme(self, task, rtm_task, origin):
        meme = self._update_meme(SyncMeme(), task, rtm_task)
        meme.set_origin(origin)
        return meme
        
    def _update_meme(self, meme, task, rtm_task):
        meme.set_local_last_modified(task.get_modified())
        meme.set_remote_last_modified(rtm_task.get_modified())
        meme.set_remote_last_modified(task.get_modified())
        return meme

    def _rtm_has_task(self, wanted_id):
        #this is very bad in terms of performances, but RTM does not have a
        # "has_task" method.
        # caching of this list should be done to reduce the issue.
        return wanted_id in self._get_rtm_task_dict()
    
    def _get_rtm_task_dict(self):
        print "RTMTD"
        try:
            time_difference = datetime.datetime.now() - \
                              self._rtm_task_dict_timestamp
            if time_difference.seconds < 60:
                return self._rtm_task_dict
        except Exception,e :
            print e
            pass
        print "REFRESHING CACHE!"
        new_dict = {}
        self.downloadFromWeb()
        return self._rtm_task_dict

    def quit(self, disable = False):
        super(Backend, self).quit(disable)

    def _authenticate(self):
        print "AUTHENTICATING", self.token
        self.authenticated.clear()
        while not self.authenticated.isSet():
            self.login_event.clear()
            if not self.token:
                print "AAAAAAAAAAAAAAAAA"
                self.rtm= createRTM(self.PUBLIC_KEY, self.PRIVATE_KEY, self.token)
                print "b"
                subprocess.Popen(['xdg-open', self.rtm.getAuthURL()])
                BackendSignals().interaction_requested(self.get_id(),
                    "You need to authenticate to Remember The Milk. A browser"
                    " is opening with the correct page.\n When you have "
                    " finished, press the 'Confirm' button", \
                    BackendSignals().INTERACTION_CONFIRM, \
                    "on_login")
                self.login_event.wait()
                try:
                    self.token = self.rtm.getToken()
                except Exception, e:
                    print "MUHJAHA"
                    print e
                    print self.token
                    self.token = None
                    continue
                print "_LOGIN"
            try:
                if self._login():
                    self._store_pickled_file(self.token_path, self.token)
                    self.authenticated.set()
            except exceptions.IOError, e:
                print "LOGIN FAILED"
                BackendSignals().backend_failed(self.get_id(), \
                            BackendSignals.ERRNO_NETWORK)
                time.sleep(30)

    def on_login(self):
        self.login_event.set()

    def _login(self):
        try:
            self.rtm = createRTM(self.PUBLIC_KEY, self.PRIVATE_KEY, self.token)
            self.timeline = self.rtm.timelines.create().timeline
            return True
        except (RTMError, RTMAPIError), e:
            print "RTM ERROR"
        return False

    def downloadFromWeb(self):
        #NOTE: syncing only incomplete tasks for now
        #(it's easier to debug the things you see)
        lists_id_list = map(lambda x: x.id, \
                             self.rtm.lists.getList().lists.list)

        # Download all non-archived tasks in the list with id x
        def get_list_of_taskseries(x):
            currentlist = self.rtm.tasks.getList(list_id = x, \
                                filter = 'includeArchived:true').tasks
            if hasattr(currentlist, 'list'):
                return currentlist.list
            else:
                return []
        task_list_global= map(get_list_of_taskseries, lists_id_list)
        taskseries_list = filter(lambda x: hasattr(x[0], 'taskseries'), \
                                  zip(task_list_global, lists_id_list))
        tasks_list_wrapped = map(lambda x: (x[0].taskseries, x[1]), \
                                 taskseries_list)
        tasks_list_normalized = map(lambda x: zip(x[0], [x[1]] * len(x[0]), \
                map(lambda x: x.id, x[0])) if type(x[0]) == list \
                else [(x[0], x[1], x[0].id)], tasks_list_wrapped)
        tasks_list_unwrapped = []
        task_objects_list = []
        list_ids_list = []
        taskseries_ids_list = []
        if len(tasks_list_normalized)>0:
            tasks_list_unwrapped = reduce(lambda x, y: x+y, \
                                          tasks_list_normalized)
            task_objects_list, list_ids_list, taskseries_ids_list = \
                    self._unziplist(tasks_list_unwrapped)

        data =  zip(task_objects_list, list_ids_list, taskseries_ids_list)
        new_dict = {}
        for task_id, list_id, taskseries_id in data:
            rtm_task = RtmTask(task_id, list_id, taskseries_id, \
                                          self.rtm, self.timeline)
            new_dict[rtm_task.get_id()] = rtm_task
        self._rtm_task_dict = new_dict
        self._rtm_task_dict_timestamp = datetime.datetime.now()

    def _unziplist(self, a):
        if len(a) == 0:
            return [], []
        return tuple(map(list, zip(*a)))

    def _populate_rtm_task(self, task, rtm_task):
        #Get methods of an rtm_task are fast, set are slow: therefore,
        # we try to use set as rarely as possible

        #first thing: the status. This way, if we are syncing a completed
        # task it doesn't linger for ten seconds in the RTM Inbox
        status = task.get_status()
        if rtm_task.get_status() != status:
            rtm_task.set_status(status)

        title = task.get_title()
        if rtm_task.get_title() != title:
            rtm_task.set_title(title)
        text = task.get_excerpt(strip_tags = True, strip_subtasks = True)
        if rtm_task.get_text() != text:
            rtm_task.set_text(text)
        tags = task.get_tags_name()
        rtm_task_tags = []
        for tag in rtm_task.get_tags():
            if tag[0] != '@':
                tag = '@' + tag
            rtm_task_tags.append(tag)
        print "GTG TAGS", tags
        print "RTM TAGS", rtm_task_tags
        #rtm tags are lowercase only
        if rtm_task_tags != [t.lower() for t in tags]:
            rtm_task.set_tags(tags)
        if isinstance(task.get_due_date(), NoDate):
            due_date = None
        else:
            due_date = task.get_due_date().to_py_date()
        if rtm_task.get_due_date() != due_date:
            rtm_task.set_due_date(due_date)
        
    def _populate_task(self, task, rtm_task):
        task.set_title(rtm_task.get_title())
        task.set_text(rtm_task.get_text())
        task.set_due_date(rtm_task.get_due_date())
        status = rtm_task.get_status()
        if GTG_TO_RTM_STATUS[task.get_status()] != status:
            task.set_status(rtm_task.get_status())
        #tags
        print "TAGS"
        tags = []
        for tag in rtm_task.get_tags():
            if tag[0] != '@':
                tag = '@' + tag
            tags.append(tag)
        print "RTMTags", tags
        gtg_tags_lower = [t.get_name().lower() for t in task.get_tags()]
        print "gtg_tags_lower", gtg_tags_lower
        #tags to remove
        for tag in set(gtg_tags_lower).difference(set(tags)):
            task.remove_tag(tag)
        #tags to add
        for tag in set(tags).difference(set(gtg_tags_lower)):
            gtg_all_tags = [t.get_name() for t in \
                            self.datastore.get_all_tags()]
            matching_tags = filter(lambda t: t.lower() == tag, gtg_all_tags)
            if len(matching_tags) !=  0:
                tag = matching_tags[0]
            task.add_tag(tag)
