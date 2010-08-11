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

TAG_XMLFILE = "tags.xml"
TAG_XMLROOT = "tagstore"

"""
The DaataStore contains a list of TagSource objects, which are proxies
between a backend and the datastore itself
"""

import threading
import gobject
import uuid
import os.path
from collections import deque
import xml.sax.saxutils as saxutils

from GTG.core                    import requester
from GTG.core.task               import Task
from GTG.core.tagstore           import Tag
from GTG.core                    import CoreConfig
from GTG.core.treefactory        import TreeFactory
from GTG.tools.logger            import Log
from GTG.backends.genericbackend import GenericBackend
from GTG.tools                   import cleanxml
from GTG.tools.keyring           import Keyring
from GTG.backends.backendsignals import BackendSignals
from GTG.tools.synchronized      import synchronized
from GTG.tools.borg              import Borg


class DataStore(object):
    '''
    A wrapper around all backends that is responsible for keeping the backend
    instances. It can enable, disable, register and destroy backends, and acts
    as interface between the backends and GTG core.
    You should not interface yourself directly with the DataStore: use the
    Requester instead (which also sends signals as you issue commands).
    '''


    def __init__(self):
        '''
        Initializes a DataStore object
        '''
        self.backends = {} #dictionary {backend_name_string: Backend instance}
        self.treefactory = TreeFactory()
        self.__tasks = self.treefactory.get_tasks_tree()
        self.requester = requester.Requester(self)
        self.tagfile = None
        self.__tagstore = self.treefactory.get_tags_tree(self.requester)
        self.load_tag_tree()
        self._backend_signals = BackendSignals()
        self.mutex = threading.RLock()
        self.is_default_backend_loaded = False
        self._backend_signals.connect('default-backend-loaded', \
                                      self._activate_non_default_backends)
        self.filtered_datastore = FilteredDataStore(self)

    ##########################################################################
    ### Helper functions (get_ methods for Datastore embedded objects)
    ##########################################################################

    def get_tagstore(self):
        '''
        Helper function to obtain the Tagstore associated with this DataStore
        @return GTG.core.tagstore.TagStore: the tagstore object
        '''
        return self.__tagstore

    def get_requester(self):
        '''
        Helper function to get the Requester associate with this DataStore
        @returns GTG.core.requester.Requester: the requester associated with
        this datastore
        '''
        return self.requester
        
    def get_tasks_tree(self):
        '''
        Helper function to get a Tree with all the tasks contained in this
        Datastore
        @returns GTG.core.tree.Tree: a task tree (the main one)
        '''
        return self.__tasks
        
    ##########################################################################
    ### Tags functions
    ##########################################################################
    
    def new_tag(self,tagname):
        """Create a new tag and return it or return the existing one
        with corresponding name"""
        #we create a new tag from a name
        tname = tagname.encode("UTF-8")
        #if tname not in self.tags:
        if not self.__tagstore.has_node(tname):
            tag = Tag(tname, req=self.requester)
            self.__tagstore.add_node(tag)
            p = {'tag':tname,'transparent':True}
            self.__tasks.add_filter(tname,self.treefactory.tag_filter,parameters=p)
            tag.set_save_callback(self.save)
            Log.debug("********* tag added %s *******" % tagname)
        else:
            raise IndexError('tag %s was already in the datastore' %tagname)
        return tag
        
    def rename_tag(self,oldname,newname):
        print "Tag renaming not implemented yet"
    
    def get_tag(self,tagname):
        if tagname[0] != "@":
            tagname = "@" + tagname
        if self.__tagstore.has_node(tagname):
            return self.__tagstore.get_node(tagname)
        else:
            return None
            
    def load_tag_tree(self):
        # Loading tags
        tagfile = os.path.join(CoreConfig().get_data_dir(), TAG_XMLFILE)
        doc, xmlstore = cleanxml.openxmlfile(tagfile,TAG_XMLROOT)
        for t in xmlstore.childNodes:
            #We should only care about tag with a name beginning with "@"
            #Other are special tags
            tagname = t.getAttribute("name")
            tag = self.new_tag(tagname)
            attr = t.attributes
            i = 0
            while i < attr.length:
                at_name = attr.item(i).name
                at_val = t.getAttribute(at_name)
                tag.set_attribute(at_name, at_val)
                i += 1
            parent = tag.get_attribute('parent')
            if parent:
                if self.__tagstore.has_node(parent):
                    pnode = self.__tagstore.get_node(parent)
                else:
                    pnode=self.new_tag(parent)
                tag.set_parent(pnode.get_id())
        self.tagfile = tagfile
                
    def save_tagtree(self):
        if self.tagfile:
            doc, xmlroot = cleanxml.emptydoc(TAG_XMLROOT)
            tags = self.__tagstore.get_main_view().get_all_nodes()
            already_saved = [] #We avoid saving the same tag twice
            #we don't save tags with no attributes
            #It saves space and allow the saved list growth to be controlled
            for tname in tags:
                t = self.__tagstore.get_node(tname)
                attr = t.get_all_attributes(butname = True, withparent = True)
                if "special" not in attr and len(attr) > 0:
                    tagname = t.get_name()
                    if not tagname in already_saved:
                        t_xml = doc.createElement("tag")
                        t_xml.setAttribute("name", tagname)
                        already_saved.append(tagname)
                        for a in attr:
                            value = t.get_attribute(a)
                            if value:
                                t_xml.setAttribute(a, value)
                        xmlroot.appendChild(t_xml)
            cleanxml.savexml(self.tagfile, doc)
    

    ##########################################################################
    ### Tasks functions
    ##########################################################################

    def has_task(self, tid):
        '''
        Returns true if the tid is among the open or closed tasks for
        this DataStore, False otherwise.
        @param tid: Task ID to search for
        @return bool: True if the task is present
        '''
        return self.__tasks.has_node(tid)

    def get_task(self, tid):
        '''
        Returns the internal task object for the given tid, or None if the
        tid is not present in this DataStore.
        @param tid: Task ID to retrieve
        @returns GTG.core.task.Task or None:  whether the Task is present
        or not
        '''
        if self.has_task(tid):
            return self.__tasks.get_node(tid)
        else:
            Log.debug("requested non-existent task")
            return None
        
    def task_factory(self, tid, newtask = False):
        '''
        Instantiates the given task id as a Task object.
        @param tid: a task id. Must be unique
        @param newtask: True if the task has never been seen before
        @return Task: a Task instance
        '''
        return Task(tid, self.requester, newtask)

    def new_task(self):
        """
        Creates a blank new task in this DataStore.
        New task is created in all the backends that collect all tasks (among
        them, the default backend). The default backend uses the same task id
        in its own internal representation.
        @return: The task object that was created.
        """
        task = self.task_factory(str(uuid.uuid4()), True)
        self.__tasks.add_node(task)
        return task
        
    @synchronized
    def push_task(self, task, backend_capabilities = 'bypass for now'):
        '''
        Adds the given task object to the task tree. In other words, registers
        the given task in the GTG task set.
        @param task: A valid task object  (a GTG.core.task.Task)
        @return bool: True if the task has been accepted
        '''

        if self.has_task(task.get_id()):
            return False
        else:
#            self.__tasks.add_node(task)
            gobject.idle_add(self.__tasks.add_node,task)
            task.set_loaded()
            if self.is_default_backend_loaded:
                task.sync()
            return True

    ##########################################################################
    ### Backends functions
    ##########################################################################

    def get_all_backends(self, disabled = False):
        """ 
        returns list of all registered backends for this DataStore.
        @param disabled: If disabled is True, attaches also the list of disabled backends
        @return list: a list of TaskSource objects
        """
        #NOTE: consider cashing this result for speed.
        result = []
        for backend in self.backends.itervalues():
            if backend.is_enabled() or disabled:
                result.append(backend)
        return result

    def get_backend(self, backend_id):
        '''
        Returns a backend given its id
        @param backend_id: a backend id
        @returns GTG.core.datastore.TaskSource or None: the requested backend,
        or none
        '''
        if backend_id in self.backends:
            return self.backends[backend_id]
        else:
            return None

    def register_backend(self, backend_dic):
        """
        Registers a TaskSource as a backend for this DataStore
        @param backend_dic: Dictionary object containing all the
        parameters to initialize the backend (filename...). It should
        also contain the backend class (under "backend"), and its unique
        id (under "pid")
        """
        if "backend" in backend_dic:
            if "pid" not in backend_dic:
                Log.debug("registering a backend without pid.")
                return None
            backend = backend_dic["backend"]
            #Checking that is a new backend
            if backend.get_id() in self.backends:
                Log.debug("registering already registered backend")
                return None
            source = TaskSource(requester = self.requester,
                                backend = backend,
                                datastore = self.filtered_datastore)
            self.backends[backend.get_id()] = source
            #we notify that a new backend is present
            self._backend_signals.backend_added(backend.get_id())
            #saving the backend in the correct dictionary (backends for enabled
            # backends, disabled_backends for the disabled ones)
            #this is useful for retro-compatibility 
            if not GenericBackend.KEY_ENABLED in backend_dic:
                source.set_parameter(GenericBackend.KEY_ENABLED, True)
            if not GenericBackend.KEY_DEFAULT_BACKEND in backend_dic:
                source.set_parameter(GenericBackend.KEY_DEFAULT_BACKEND, True)
            #if it's enabled, we initialize it
            if source.is_enabled() and \
               (self.is_default_backend_loaded or source.is_default()):
                source.initialize(connect_signals = False)
                #Filling the backend
                #Doing this at start is more efficient than
                #after the GUI is launched
                source.start_get_tasks()
            return source
        else:
            Log.debug("Tried to register a backend without a  pid")

    def _activate_non_default_backends(self, sender = None):
        '''
        Non-default backends have to wait until the default loads before
        being  activated. This function is called after the first default
        backend has loaded all its tasks.
        '''
        if self.is_default_backend_loaded:
            Log.debug("spurious call")
            return
        self.is_default_backend_loaded = True
        for backend in self.backends.itervalues():
            if backend.is_enabled() and not backend.is_default():
                backend.initialize()
                backend.start_get_tasks()
                self.flush_all_tasks(backend.get_id())

    def set_backend_enabled(self, backend_id, state):
        """
        The backend corresponding to backend_id is enabled or disabled
        according to "state".
        Disable:
        Quits a backend and disables it (which means it won't be
        automatically loaded next time GTG is started)
        Enable:
        Reloads a disabled backend. Backend must be already known by the
        Datastore
        @parma backend_id: a backend id
        @param state: True to enable, False to disable
        """
        if backend_id in self.backends:
            backend = self.backends[backend_id]
            current_state = backend.is_enabled()
            if current_state == True and state == False:
                #we disable the backend
                backend.quit(disable = True)
            elif current_state == False and state == True:
                if self.is_default_backend_loaded == True:
                    backend.initialize()
                    self.flush_all_tasks(backend_id)
                else:
                    #will be activated afterwards
                    backend.set_parameter(GenericBackend.KEY_ENABLED,
                                       True)

    def remove_backend(self, backend_id):
        '''
        Removes a backend, and forgets it ever existed.
        @param backend_id: a backend id
        '''
        if backend_id in self.backends:
            backend = self.backends[backend_id]
            if backend.is_enabled():
                self.set_backend_enabled(backend_id, False)
            backend.purge()
            #we notify that the backend has been deleted
            self._backend_signals.backend_removed(backend.get_id())
            del self.backends[backend_id]

    def backend_change_attached_tags(self, backend_id, tag_names):
        '''
        Changes the tags for which a backend should store a task
        @param backend_id: a backend_id
        @param tag_names: the new set of tags. This should not be a tag object,
                          just the tag name.
        '''
        backend = self.backends[backend_id]
        backend.set_attached_tags(tag_names)

    def flush_all_tasks(self, backend_id):
        '''
        This function will cause all tasks to be checked against the backend
        identified with backend_id. If tasks need to be added or removed, it
        will be done here.
        It has to be run after the creation of a new backend (or an alteration
        of its "attached tags"), so that the tasks which are already loaded in 
        the Tree will be saved in the proper backends
        @param backend_id: a backend id
        '''
        def _internal_flush_all_tasks():
            backend = self.backends[backend_id]
            for task_id in self.requester.get_all_tasks_list():
                backend.queue_set_task(None, task_id)
        t = threading.Thread(target = _internal_flush_all_tasks).start()
        self.backends[backend_id].start_get_tasks()

    def save(self, quit = False):
        '''
        Saves the backends parameters. 
        @param quit: If quit is true, backends are shut down
        '''
        doc,xmlconfig = cleanxml.emptydoc("config")
        #we ask all the backends to quit first.
        if quit:
            for b in self.get_all_backends():
                #NOTE:we could do this in parallel. Maybe a quit and
                #has_quit would be faster (invernizzi)
                b.quit()
        #we save the parameters
        for b in self.get_all_backends(disabled = True):
            t_xml = doc.createElement("backend")
            for key, value in b.get_parameters().iteritems():
                if key in ["backend", "xmlobject"]:
                    #We don't want parameters,backend,xmlobject
                    continue
                param_type = b.get_parameter_type(key)
                value = b.cast_param_type_to_string(param_type, value)
                t_xml.setAttribute(str(key), value)
            #Saving all the projects at close
            xmlconfig.appendChild(t_xml)
            
        datafile = os.path.join(CoreConfig().get_data_dir(), CoreConfig.DATA_FILE)
        cleanxml.savexml(datafile,doc,backup=True)

        #Saving the tagstore
        self.save_tagtree()
        
    def request_task_deletion(self, tid):
        ''' 
        This is a proxy function to request a task deletion from a backend
        @param tid: the tid of the task to remove
        '''
        self.requester.delete_task(tid)


class TaskSource():
    '''
    Transparent interface between the real backend and the DataStore.
    Is in charge of connecting and disconnecting to signals
    '''
    def __init__(self, requester, backend, datastore):
        """
        Instantiates a TaskSource object.
        @param requester: a Requester
        @param backend:  the backend being wrapped
        @param datastore: a FilteredDatastore
        """
        self.backend = backend
        self.req = requester
        self.backend.register_datastore(datastore)
        self.tasktree = datastore.get_tasks_tree().get_main_view()
        self.to_set = deque()
        self.to_remove = deque()
#        self.task_filter = self.get_task_filter_for_backend()
        if Log.is_debugging_mode():
            self.timer_timestep = 5
        else:
            self.timer_timestep = 1 
        self.set_task_handle = None
        self.remove_task_handle = None
        self.to_set_timer = None
        
    def start_get_tasks(self):
        ''''
        Maps the TaskSource to the backend and starts threading.
        '''
        threading.Thread(target = self.__start_get_tasks).start()

    def __start_get_tasks(self):
        '''
        Loads all task from the backend and connects its signals afterwards.
        Launched as a thread by start_get_tasks
        '''
        self.backend.start_get_tasks()
        self._connect_signals()
        if self.backend.is_default():
            BackendSignals().default_backend_loaded()

    def get_task_filter_for_backend(self):
        '''
        Fiter that checks if the task should be stored in this backend.

        @returns function: a function that accepts a task and returns True/False
                 whether the task should be stored or not
        '''
        raw_filter = self.req.get_filter("backend_filter").get_function()
        return lambda task: raw_filter(task, \
                        {"tags": set(self.backend.get_attached_tags())})

    def should_task_id_be_stored(self, task_id):
        '''
        Helper function:  Checks if a task should be stored in this backend
        @param task_id: a task id
        @returns bool: True if the task should be stored
        '''
        task = self.req.get_task(task_id)
        #FIXME: it will be a lot easier to add, instead,
        # a filter to a tree and check that this task is well in the tree
#        return self.task_filter(task)
        return True

    def queue_set_task(self, sender, tid):
        """
        Updates the task in the DataStore.  Actually, it adds the task to a
        queue to be updated asynchronously.
        @param sender: not used, any value will do.
        @param task: The Task object to be updated.
        """
        if self.should_task_id_be_stored(tid):
            if tid not in self.to_set and tid not in self.to_remove:
                self.to_set.appendleft(tid)
                self.__try_launch_setting_thread()
        else:
            self.queue_remove_task(None, tid)
            
    def launch_setting_thread(self):
        '''
        Operates the threads to set and remove tasks.
        Releases the lock when it is done.
        '''
        #FIXME: the lock should be general for all backends. Therefore, it
        #should be handled in the datastore
        while True:
            try:
                tid = self.to_set.pop()
            except IndexError:
                break
            #we check that the task is not already marked for deletion
            #and that it's still to be stored in this backend
            #NOTE: no need to lock, we're reading
            if tid not in self.to_remove and \
                    self.should_task_id_be_stored(tid) and \
                   self.req.has_task(tid):
                task = self.req.get_task(tid)
                self.backend.queue_set_task(task)
        while True:
            try:
                tid = self.to_remove.pop()
            except IndexError:
                break
            self.backend.queue_remove_task(tid)
        #we release the weak lock
        self.to_set_timer = None
    
    def queue_remove_task(self, sender, tid):
        '''
        Queues task to be removed.
        @param sender: not used, any value will do
        @param tid: The Task ID of the task to be removed
        '''
        if tid not in self.to_remove:
            self.to_remove.appendleft(tid)
            self.__try_launch_setting_thread()

    def __try_launch_setting_thread(self):
        '''
        Helper function to launch the setting thread, if it's not running
        '''
        if self.to_set_timer == None:
            self.to_set_timer = threading.Timer(self.timer_timestep, \
                                        self.launch_setting_thread)
            self.to_set_timer.start()

    def initialize(self, connect_signals = True):
        '''
        Initializes the backend and starts looking for signals.
        @param connect_signals: if True, it starts listening for signals
        '''
        self.backend.initialize()
        if connect_signals:
            self._connect_signals()

    def _connect_signals(self):
        '''
        Helper function to connect signals
        '''
        if not self.set_task_handle:
            self.set_task_handle = self.tasktree.connect('node-modified', \
                                                    self.queue_set_task)
        if not self.remove_task_handle:
            self.remove_task_handle = self.tasktree.connect('node-deleted',\
                                                   self.queue_remove_task)

    def _disconnect_signals(self):
        '''
        Helper function to disconnect signals
        '''
        if self.set_task_handle:
            self.tasktree.disconnect(self.set_task_handle)
            self.set_task_handle = None
        if  self.remove_task_handle:
            self.tasktree.disconnect(self.remove_task_handle)
            self.remove_task_handle = None

    def sync(self):
        '''
        Forces the TaskSource to sync all the pending tasks
        '''
        if self.to_set_timer != None:
            try:
                self.to_set_timer.cancel()
            except:
                pass
            try:
                self.to_set_timer.join(5)
            except:
                pass
        self.launch_setting_thread()

    def quit(self, disable = False):
        '''
        Quits the backend and disconnect the signals
        @param disable: if True, the backend is disabled.
        '''
        self._disconnect_signals()
        self.sync()
        self.backend.quit(disable)
    
    def __getattr__(self, attr):
        '''
        Delegates all the functions not defined here to the real backend
        (standard python function)
        @param attr: attribute to get
        '''
        if attr in self.__dict__: 
            return self.__dict__[attr]
        else:
            return getattr(self.backend, attr)



class FilteredDataStore(Borg):
    ''' 
    This class acts as an interface to the Datastore.
    It is used to hide most of the methods of the Datastore.
    The backends can safely use the remaining methods.
    '''


    def __init__(self, datastore):
        super(FilteredDataStore, self).__init__()
        self.datastore = datastore

    def __getattr__(self, attr):
        if attr in ['task_factory', \
                    'push_task',
                    'get_task',
                    'has_task',
                    'request_task_deletion',
                    'get_tasks_tree',]:
            return getattr(self.datastore, attr)
        else:
            raise AttributeError("No attribute %s" %attr)

