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
FIXME: document!
'''

import os
import sys
import errno
import pickle
import threading
from collections import deque

from GTG.backends.backendsignals import BackendSignals
from GTG.tools.keyring import Keyring
from GTG.core import CoreConfig
from GTG.tools.logger import Log




class GenericBackend(object):
    '''
    Base class for every backend. It's a little more than an interface which
    methods have to be redefined in order for the backend to run.
    '''


    #BACKEND TYPE DESCRIPTION
    #"_general_description" is a dictionary that holds the values for the
    # following keys:
    BACKEND_NAME = "name" #the backend gtg internal name (doesn't change in
                          # translations, *must be unique*)
    BACKEND_HUMAN_NAME = "human-friendly-name" #The name shown to the user
    BACKEND_DESCRIPTION = "description" #A short description of the backend
    BACKEND_AUTHORS = "authors" #a list of strings
    BACKEND_TYPE = "type"
    #BACKEND_TYPE is one of:
    TYPE_READWRITE = "readwrite"
    TYPE_READONLY = "readonly"
    TYPE_IMPORT = "import"
    TYPE_EXPORT = "export"
    _general_description = {}


    #"static_parameters" is a dictionary of dictionaries, each of which
    #representing a parameter needed to configure the backend.
    #each "sub-dictionary" is identified by this a key representing its name.
    #"static_parameters" will be part of the definition of each
    #particular backend.
    # Each dictionary contains the keys:
    #PARAM_DESCRIPTION = "description" #short description (shown to the user
                                      # during configuration)
    PARAM_DEFAULT_VALUE = "default_value" # its default value
    PARAM_TYPE = "type"  
    #PARAM_TYPE is one of the following (changing this changes the way
    # the user can configure the parameter)
    TYPE_PASSWORD = "password" #the real password is stored in the GNOME
                               # keyring
                               # This is just a key to find it there
    TYPE_STRING = "string"  #generic string, nothing fancy is done
    TYPE_INT = "int"  #edit box can contain only integers
    TYPE_BOOL = "bool" #checkbox is shown
    TYPE_LIST_OF_STRINGS = "liststring" #list of strings. the "," character is
                                        # prohibited in strings
    _static_parameters = {}

    def initialize(self):
        '''
        Called each time it is enabled again (including on backend creation).
        Please note that a class instance for each disabled backend *is*
        created, but it's not initialized. 
        Optional. 
        NOTE: make sure to call super().initialize()
        '''
        for module_name in self.get_required_modules():
            sys.modules[module_name]= __import__(module_name)
        self._parameters[self.KEY_ENABLED] = True
        self._is_initialized = True
        #we signal that the backend has been enabled
        self._signal_manager.backend_state_changed(self.get_id())

    def start_get_tasks(self):
        '''
        Once this function is launched, the backend can start pushing
        tasks to gtg parameters.

        @return: start_get_tasks() might not return or finish
        '''
        raise NotImplemented()

    def set_task(self, task):
        '''
        Save the task in the backend. If the task id is new for the 
        backend, then a new task must be created.
        '''
        pass

    def remove_task(self, tid):
        ''' Completely remove the task with ID = tid '''
        pass

    def has_task(self, tid):
        '''Returns true if the backend has an internal idea 
           of the task corresponding to the tid. False otherwise'''
        raise NotImplemented()

    def new_task_id(self):
        '''
        Returns an available ID for a new task so that a task with this ID
        can be saved with set_task later.
        '''
        raise NotImplemented()

    def this_is_the_first_run(self, xml):
        '''
        Steps to execute if it's the first time the backend is run. Optional.
        '''
        pass

    def purge(self):
        '''
        Called when a backend will be removed from GTG. Useful for removing
        configuration files. Optional.
        '''
        pass

    def get_number_of_tasks(self):
        '''
        Returns the number of tasks stored in the backend. Doesn't need to be a
        fast function, is called just for the UI
        '''
        raise NotImplemented()

    @staticmethod
    def get_required_modules():
        return []

    def quit(self, disable = False):
        '''
        Called when GTG quits or disconnects the backend. Remember to execute
        also this function when quitting. If disable is True, the backend won't
        be automatically loaded at next GTG start
        '''
        self._is_initialized = False
        if disable:
            self._parameters[self.KEY_ENABLED] = False
            #we signal that we have been disabled
            self._signal_manager.backend_state_changed(self.get_id())
            self._signal_manager.backend_sync_ended(self.get_id())
        syncing_thread = threading.Thread(target = self.sync).run()

    def save_state(self):
        '''
        It's the last function executed on a quitting backend, after the
        pending actions have been done.
        Useful to ensure that the state is saved in a consistent manner
        '''
        pass

###############################################################################
###### You don't need to reimplement the functions below this line ############
###############################################################################

    #These parameters are common to all backends and necessary.
    # They will be added automatically to your _static_parameters list
    #NOTE: for now I'm disabling changing the default backend. Once it's all
    #      set up, we will see about that (invernizzi)
    KEY_DEFAULT_BACKEND = "Default"
    KEY_ENABLED = "Enabled"
    KEY_HUMAN_NAME = BACKEND_HUMAN_NAME
    KEY_ATTACHED_TAGS = "attached-tags"
    KEY_USER = "user"
    KEY_PID = "pid"
    ALLTASKS_TAG = "gtg-tags-all"  #IXME: moved here to avoid circular imports

    _static_parameters_obligatory = { \
                                    KEY_DEFAULT_BACKEND: { \
                                         PARAM_TYPE: TYPE_BOOL, \
                                         PARAM_DEFAULT_VALUE: False, \
                                    }, \
                                    KEY_HUMAN_NAME: { \
                                         PARAM_TYPE: TYPE_STRING, \
                                         PARAM_DEFAULT_VALUE: "", \
                                    }, \
                                    KEY_USER: { \
                                         PARAM_TYPE: TYPE_STRING, \
                                         PARAM_DEFAULT_VALUE: "", \
                                    }, \
                                    KEY_PID: { \
                                         PARAM_TYPE: TYPE_STRING, \
                                         PARAM_DEFAULT_VALUE: "", \
                                    }, \
                                    KEY_ENABLED: { \
                                         PARAM_TYPE: TYPE_BOOL, \
                                         PARAM_DEFAULT_VALUE: False, \
                                    }}

    _static_parameters_obligatory_for_rw = { \
                                    KEY_ATTACHED_TAGS: {\
                                         PARAM_TYPE: TYPE_LIST_OF_STRINGS, \
                                         PARAM_DEFAULT_VALUE: [ALLTASKS_TAG], \
                                    }}
    
    #Handy dictionary used in type conversion (from string to type)
    _type_converter = {TYPE_STRING: str,
                       TYPE_INT: int,
                      }

    @classmethod
    def _get_static_parameters(cls):
        '''
        Helper method, used to obtain the full list of the static_parameters
        (user configured and default ones)
        '''
        if hasattr(cls, "_static_parameters"):
            temp_dic = cls._static_parameters_obligatory.copy()
            if cls._general_description[cls.BACKEND_TYPE] == cls.TYPE_READWRITE:
                for key, value in \
                          cls._static_parameters_obligatory_for_rw.iteritems():
                    temp_dic[key] = value
            for key, value in cls._static_parameters.iteritems():
                temp_dic[key] = value
            return temp_dic 
        else:
            raise NotImplemented("_static_parameters not implemented for " + \
                                 "backend %s" % type(cls))

    def __init__(self, parameters):
        """
        Instantiates a new backend. Please note that this is called also for
        disabled backends. Those are not initialized, so you might want to check
        out the initialize() function.
        """
        if self.KEY_DEFAULT_BACKEND not in parameters:
            parameters[self.KEY_DEFAULT_BACKEND] = True
        if parameters[self.KEY_DEFAULT_BACKEND] or \
                (not self.KEY_ATTACHED_TAGS in parameters and \
                self._general_description[self.BACKEND_TYPE] \
                                        == self.TYPE_READWRITE):
            parameters[self.KEY_ATTACHED_TAGS] = [self.ALLTASKS_TAG]
        self._parameters = parameters
        self._signal_manager = BackendSignals()
        self._is_initialized = False
        if Log.is_debugging_mode():
            self.timer_timestep = 5
        else:
            self.timer_timestep = 1 
        self.to_set_timer = None
        self.please_quit = False
        self.to_set = deque()
        self.to_remove = deque()

    def get_attached_tags(self):
        '''
        Returns the list of tags which are handled by this backend
        '''
        if hasattr(self._parameters, self.KEY_DEFAULT_BACKEND) and \
                   self._parameters[self.KEY_DEFAULT_BACKEND]:
            return [self.ALLTASKS_TAG]
        try:
            return self._parameters[self.KEY_ATTACHED_TAGS]
        except:
            return []

    def set_attached_tags(self, tags):
        '''
        Changes the set of attached tags
        '''
        self._parameters[self.KEY_ATTACHED_TAGS] = tags

    @classmethod
    def get_static_parameters(cls):
        """
        Returns a dictionary of parameters necessary to create a backend.
        """
        return cls._get_static_parameters()

    def get_parameters(self):
        """
        Returns a dictionary of the current parameters.
        """
        return self._parameters

    def set_parameter(self, parameter, value):
        self._parameters[parameter] = value

    @classmethod
    def get_name(cls):
        """
        Returns the name of the backend as it should be displayed in the UI
        """
        return cls._get_from_general_description(cls.BACKEND_NAME)

    @classmethod
    def get_description(cls):
        """Returns a description of the backend"""
        return cls._get_from_general_description(cls.BACKEND_DESCRIPTION)

    @classmethod
    def get_type(cls):
        """Returns the backend type(readonly, r/w, import, export) """
        return cls._get_from_general_description(cls.BACKEND_TYPE)

    @classmethod
    def get_authors(cls):
        '''
        returns the backend author(s)
        '''
        return cls._get_from_general_description(cls.BACKEND_AUTHORS)

    @classmethod
    def _get_from_general_description(cls, key):
        '''
        Helper method to extract values from cls._general_description.
        Raises an exception if the key is missing (helpful for developers
        adding new backends).
        '''
        if key in cls._general_description:
            return cls._general_description[key]
        else:
            raise NotImplemented("Key %s is missing from " +\
                    "'self._general_description' of a backend (%s). " +
                    "Please add the corresponding value" % (key, type(cls)))

    @classmethod
    def cast_param_type_from_string(cls, param_value, param_type):
        '''
        Parameters are saved in a text format, so we have to cast them to the
        appropriate type on loading. This function does exactly that.
        '''
        #FIXME: we could use pickle (dumps and loads), at least in some cases
        #       (invernizzi)
        if param_type in cls._type_converter:
            return cls._type_converter[param_type](param_value)
        elif param_type == cls.TYPE_BOOL:
            if param_value == "True":
                return True
            elif param_value == "False":
                return False
            else:
                raise Exception("Unrecognized bool value '%s'" %
                                 param_type)
        elif param_type == cls.TYPE_PASSWORD:
            if param_value == -1:
                return None
            return Keyring().get_password(int(param_value))
        elif param_type == cls.TYPE_LIST_OF_STRINGS:
            the_list = param_value.split(",")
            if not isinstance(the_list, list):
                the_list = [the_list]
            return the_list
        else:
            raise NotImplemented("I don't know what type is '%s'" %
                                 param_type)

    def cast_param_type_to_string(self, param_type, param_value):
        '''
        Inverse of cast_param_type_from_string
        '''
        if param_type == GenericBackend.TYPE_PASSWORD:
            if param_value == None:
                return str(-1)
            else:
                return str(Keyring().set_password(
                    "GTG stored password -" + self.get_id(), param_value))
        elif param_type == GenericBackend.TYPE_LIST_OF_STRINGS:
            if param_value == []:
                return ""
            return reduce(lambda a, b: a + "," + b, param_value)
        else:
            return str(param_value)

    def get_id(self):
        '''
        returns the backends id, used in the datastore for indexing backends
        '''
        return self.get_name() + "@" + self._parameters["pid"]

    @classmethod
    def get_human_default_name(cls):
        '''
        returns the user friendly default backend name. 
        '''
        return cls._general_description[cls.BACKEND_HUMAN_NAME]

    def get_human_name(self):
        '''
        returns the user customized backend name. If the user hasn't
        customized it, returns the default one
        '''
        if self.KEY_HUMAN_NAME in self._parameters and \
                    self._parameters[self.KEY_HUMAN_NAME] != "":
            return self._parameters[self.KEY_HUMAN_NAME]
        else:
            return self.get_human_default_name()

    def set_human_name(self, name):
        '''
        sets a custom name for the backend
        '''
        self._parameters[self.KEY_HUMAN_NAME] = name
        #we signal the change
        self._signal_manager.backend_renamed(self.get_id())

    def is_enabled(self):
        '''
        Returns if the backend is enabled
        '''
        return self.get_parameters()[GenericBackend.KEY_ENABLED] or \
               self.is_default()

    def is_default(self):
        '''
        Returns if the backend is enabled
        '''
        return self.get_parameters()[GenericBackend.KEY_DEFAULT_BACKEND]

    def is_initialized(self):
        '''
        Returns if the backend is up and running
        '''
        return self._is_initialized

    def get_parameter_type(self, param_name):
        try:
            return self.get_static_parameters()[param_name][self.PARAM_TYPE]
        except KeyError:
            return None

    def register_datastore(self, datastore):
        self.datastore = datastore

###############################################################################
### HELPER FUNCTIONS ##########################################################
###############################################################################

    def _store_pickled_file(self, path, data):
        '''
        A helper function to save some object in a file.
        @param path: a relative path. A good choice is
        "backend_name/object_name"
        @param data: the object
        '''
        path = os.path.join(CoreConfig().get_data_dir(), path)
        #mkdir -p
        try:
            os.makedirs(os.path.dirname(path))
        except OSError, exception:
            if exception.errno != errno.EEXIST: 
                raise
        #saving
        #try:
        with open(path, 'wb') as file:
                pickle.dump(data, file)
                #except pickle.PickleError:
                    #pass

    def _load_pickled_file(self, path, default_value = None):
        '''
        A helper function to load some object from a file.
        @param path: the relative path of the file
        @param default_value: the value to return if the file is missing or
        corrupt
        @returns object: the needed object, or default_value
        '''
        path = os.path.join(CoreConfig().get_data_dir(), path)
        if not os.path.exists(path):
            return default_value
        else:
            try:
                with open(path, 'r') as file:
                    return pickle.load(file)
            except pickle.PickleError:
                print "PICKLE ERROR"
                return default_value

###############################################################################
### THREADING #################################################################
###############################################################################

    def __try_launch_setting_thread(self):
        '''
        Helper function to launch the setting thread, if it's not running.
        '''
        if self.to_set_timer == None and self.is_enabled():
            self.to_set_timer = threading.Timer(self.timer_timestep, \
                                        self.launch_setting_thread)
            self.to_set_timer.start()

    def launch_setting_thread(self):
        '''
        This function is launched as a separate thread. Its job is to perform
        the changes that have been issued from GTG core. In particular, for
        each task in the self.to_set queue, a task has to be modified or to be
        created (if the tid is new), and for each task in the self.to_remove
        queue, a task has to be deleted
        '''
        while not self.please_quit:
            try:
                task = self.to_set.pop()
            except IndexError:
                break
            #time.sleep(4)
            tid = task.get_id()
            if tid  not in self.to_remove:
                self.set_task(task)

        while not self.please_quit:
            try:
                tid = self.to_remove.pop()
            except IndexError:
                break
            self.remove_task(tid)
        #we release the weak lock
        self.to_set_timer = None

    def queue_set_task(self, task):
        ''' Save the task in the backend. '''
        tid = task.get_id()
        print "SETTING", task.get_title()
        if task not in self.to_set and tid not in self.to_remove:
            self.to_set.appendleft(task)
            self.__try_launch_setting_thread()

    def queue_remove_task(self, tid):
        '''
        Queues task to be removed.
        @param tid: The Task ID of the task to be removed
        '''
        if tid not in self.to_remove:
            self.to_remove.appendleft(tid)
            self.__try_launch_setting_thread()
            return None

    def sync(self):
        '''
        Helper method. Forces the backend to perform all the pending changes.
        It is usually called upon quitting the backend.
        '''
        #FIXME: this function should become part of the r/w r/o generic class
        #  for backends
        if self.to_set_timer != None:
            self.please_quit = True
            try:
                self.to_set_timer.cancel()
                self.to_set_timer.join()
            except:
                pass
        self.please_quit = False
        self.launch_setting_thread()
        self.save_state()

