# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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
This file contains the most generic representation of a backend,
the GenericBackend class
"""

import os
import errno
import pickle
import threading
from collections import deque

from GTG.backends.backendsignals import BackendSignals
from GTG.tools.keyring import Keyring
from GTG.core import CoreConfig
from GTG.tools.logger import Log
from GTG.tools.interruptible import _cancellation_point

PICKLE_BACKUP_NBR = 2


class GenericBackend(object):
    '''
    Base class for every backend.
    It defines the interface a backend must have and takes care of all the
    operations common to all backends.
    A particular backend should redefine all the methods marked as such.
    '''

   ###########################################################################
   ### BACKEND INTERFACE #####################################################
   ###########################################################################
    # General description of the backend: these parameters are used
    # to show a description of the backend to the user when s/he is
    # considering adding it.
    # For an example, see the GTG/backends/backend_localfile.py file
    # _general_description has this format:
    # _general_description = {
    #    GenericBackend.BACKEND_NAME:       "backend_unique_identifier", \
    #    GenericBackend.BACKEND_HUMAN_NAME: _("Human friendly name"), \
    #    GenericBackend.BACKEND_AUTHORS:    ["First author", \
    #                                        "Chuck Norris"], \
    #    GenericBackend.BACKEND_TYPE:       GenericBackend.TYPE_READWRITE, \
    #    GenericBackend.BACKEND_DESCRIPTION: \
    #        _("Short description of the backend"),\
    #    }
    # The complete list of constants and their meaning is given below.
    _general_description = {}

    # These are the parameters to configure a new backend of this type. A
    # parameter has a name, a type and a default value.
    # For an example, see the GTG/backends/backend_localfile.py file
    # _static_parameters has this format:
    # _static_parameters = { \
    #    "param1_name": { \
    #        GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
    #        GenericBackend.PARAM_DEFAULT_VALUE: "my default value",
    #    },
    #    "param2_name": {
    #        GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
    #        GenericBackend.PARAM_DEFAULT_VALUE: 42,
    #        }}
    # The complete list of constants and their meaning is given below.
    _static_parameters = {}

    def initialize(self):
        '''
        Called each time it is enabled (including on backend creation).
        Please note that a class instance for each disabled backend *is*
        created, but it's not initialized.
        Optional.
        NOTE: make sure to call super().initialize()
        '''
        self._parameters[self.KEY_ENABLED] = True
        self._is_initialized = True
        # we signal that the backend has been enabled
        self._signal_manager.backend_state_changed(self.get_id())

    def start_get_tasks(self):
        '''
        This function starts submitting the tasks from the backend into GTG
        core.
        It's run as a separate thread.

        @return: start_get_tasks() might not return or finish
        '''
        return

    def set_task(self, task):
        '''
        This function is called from GTG core whenever a task should be
        saved, either because it's a new one or it has been modified.
        If the task id is new for the backend, then a new task must be
        created. No special notification that the task is a new one is given.

        @param task: the task object to save
        '''
        pass

    def remove_task(self, tid):
        ''' This function is called from GTG core whenever a task must be
        removed from the backend. Note that the task could be not present here.

        @param tid: the id of the task to delete
        '''
        pass

    def this_is_the_first_run(self, xml):
        '''
        Optional, and almost surely not needed.
        Called upon the very first GTG startup.
        This function is needed only in the default backend (XML localfile,
        currently).
        The xml parameter is an object containing GTG default tasks.

        @param xml: an xml object containing the default tasks.
        '''
        pass

    def quit(self, disable=False):
        '''
        Called when GTG quits or the user wants to disable the backend.

        @param disable: If disable is True, the backend won't
                        be automatically loaded when GTG starts
        '''
        if self._parameters[self.KEY_ENABLED]:
            self._is_initialized = False
            if disable:
                self._parameters[self.KEY_ENABLED] = False
                # we signal that we have been disabled
                self._signal_manager.backend_state_changed(self.get_id())
                self._signal_manager.backend_sync_ended(self.get_id())
            threading.Thread(target=self.sync).run()

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

   ###########################################################################
   ### CONSTANTS #############################################################
   ###########################################################################
    # BACKEND TYPE DESCRIPTION
    # Each backend must have a "_general_description" attribute, which
    # is a dictionary that holds the values for the following keys.
    BACKEND_NAME = "name"  # the backend gtg internal name (doesn't change in
                          # translations, *must be unique*)
    BACKEND_HUMAN_NAME = "human-friendly-name"  # The name shown to the user
    BACKEND_DESCRIPTION = "description"  # A short description of the backend
    BACKEND_AUTHORS = "authors"  # a list of strings
    BACKEND_TYPE = "type"
    # BACKEND_TYPE is one of:
    TYPE_READWRITE = "readwrite"
    TYPE_READONLY = "readonly"
    TYPE_IMPORT = "import"
    TYPE_EXPORT = "export"

    #"static_parameters" is a dictionary of dictionaries, each of which
    # are a description of a parameter needed to configure the backend and
    # is identified in the outer dictionary by a key which is the name of the
    # parameter.
    # For an example, see the GTG/backends/backend_localfile.py file
    # Each dictionary contains the keys:
    PARAM_DEFAULT_VALUE = "default_value"  # its default value
    PARAM_TYPE = "type"
    # PARAM_TYPE is one of the following (changing this changes the way
    # the user can configure the parameter)
    TYPE_PASSWORD = "password"  # the real password is stored in the GNOME
                               # keyring
                               # This is just a key to find it there
    TYPE_STRING = "string"  # generic string, nothing fancy is done
    TYPE_INT = "int"  # edit box can contain only integers
    TYPE_BOOL = "bool"  # checkbox is shown
    TYPE_LIST_OF_STRINGS = "liststring"  # list of strings. the "," character
                                         # is prohibited in strings

    # These parameters are common to all backends and necessary.
    # They will be added automatically to your _static_parameters list
    # NOTE: for now I'm disabling changing the default backend. Once it's all
    #      set up, we will see about that (invernizzi)
    KEY_DEFAULT_BACKEND = "Default"
    KEY_ENABLED = "Enabled"
    KEY_HUMAN_NAME = BACKEND_HUMAN_NAME
    KEY_ATTACHED_TAGS = "attached-tags"
    KEY_USER = "user"
    KEY_PID = "pid"
    ALLTASKS_TAG = "gtg-tags-all"  # NOTE: this has been moved here to avoid
                                  #    circular imports. It's the same as in
                                  #    the CoreConfig class, because it's the
                                  #    same thing conceptually. It doesn't
                                  #    matter it the naming diverges.

    _static_parameters_obligatory = {
        KEY_DEFAULT_BACKEND: {
            PARAM_TYPE: TYPE_BOOL,
            PARAM_DEFAULT_VALUE: False,
        },
        KEY_HUMAN_NAME: {
            PARAM_TYPE: TYPE_STRING,
            PARAM_DEFAULT_VALUE: "",
        },
        KEY_USER: {
            PARAM_TYPE: TYPE_STRING,
            PARAM_DEFAULT_VALUE: "",
        },
        KEY_PID: {
            PARAM_TYPE: TYPE_STRING,
            PARAM_DEFAULT_VALUE: "",
        },
        KEY_ENABLED: {
            PARAM_TYPE: TYPE_BOOL,
            PARAM_DEFAULT_VALUE: False,
        }}

    _static_parameters_obligatory_for_rw = {
        KEY_ATTACHED_TAGS: {
            PARAM_TYPE: TYPE_LIST_OF_STRINGS,
            PARAM_DEFAULT_VALUE: [ALLTASKS_TAG],
        }}

    # Handy dictionary used in type conversion (from string to type)
    _type_converter = {TYPE_STRING: str,
                       TYPE_INT: int,
                       }

    @classmethod
    def _get_static_parameters(cls):
        '''
        Helper method, used to obtain the full list of the static_parameters
        (user configured and default ones)

        @returns dict: the dict containing all the static parameters
        '''
        temp_dic = cls._static_parameters_obligatory.copy()
        if cls._general_description[cls.BACKEND_TYPE] == \
                cls.TYPE_READWRITE:
            for key, value in \
                    cls._static_parameters_obligatory_for_rw.iteritems():
                temp_dic[key] = value
        for key, value in cls._static_parameters.iteritems():
            temp_dic[key] = value
        return temp_dic

    def __init__(self, parameters):
        """
        Instantiates a new backend. Please note that this is called also
        for disabled backends. Those are not initialized, so you might
        want to check out the initialize() function.
        """
        if self.KEY_DEFAULT_BACKEND not in parameters:
            # if it's not specified, then this is the default backend
            #(for retro-compatibility with the GTG 0.2 series)
            parameters[self.KEY_DEFAULT_BACKEND] = True
        # default backends should get all the tasks
        if parameters[self.KEY_DEFAULT_BACKEND] or \
                (not self.KEY_ATTACHED_TAGS in parameters and
                 self._general_description[self.BACKEND_TYPE]
                 == self.TYPE_READWRITE):
            parameters[self.KEY_ATTACHED_TAGS] = [self.ALLTASKS_TAG]
        self._parameters = parameters
        self._signal_manager = BackendSignals()
        self._is_initialized = False
        # if debugging mode is enabled, tasks should be saved as soon as
        # they're marked as modified. If in normal mode, we prefer speed over
        # easier debugging.
        if Log.is_debugging_mode():
            self.timer_timestep = 5
        else:
            self.timer_timestep = 1
        self.to_set_timer = None
        self.please_quit = False
        self.cancellation_point = lambda: _cancellation_point(
            lambda: self.please_quit)
        self.to_set = deque()
        self.to_remove = deque()

    def get_attached_tags(self):
        '''
        Returns the list of tags which are handled by this backend
        '''
        if hasattr(self._parameters, self.KEY_DEFAULT_BACKEND) and \
                self._parameters[self.KEY_DEFAULT_BACKEND]:
            # default backends should get all the tasks
            # NOTE: this shouldn't be needed, but it doesn't cost anything and
            #      it could avoid potential tasks losses.
            return [self.ALLTASKS_TAG]
        try:
            return self._parameters[self.KEY_ATTACHED_TAGS]
        except:
            return []

    def set_attached_tags(self, tags):
        '''
        Changes the set of attached tags

        @param tags: the new attached_tags set
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
        '''
        Change a parameter for this backend

        @param parameter: the parameter name
        @param value: the new value
        '''
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

        @param key: the key to extract
        '''
        return cls._general_description[key]

    @classmethod
    def cast_param_type_from_string(cls, param_value, param_type):
        '''
        Parameters are saved in a text format, so we have to cast them to the
        appropriate type on loading. This function does exactly that.

        @param param_value: the actual value of the parameter, in a string
                            format
        @param param_type: the wanted type
        @returns something: the casted param_value
        '''
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

        @param param_value: the actual value of the parameter
        @param param_type: the type of the parameter (password...)
        @returns something: param_value casted to string
        '''
        if param_type == GenericBackend.TYPE_PASSWORD:
            if param_value is None:
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

        @returns string: the backend id
        '''
        return self.get_name() + "@" + self._parameters["pid"]

    @classmethod
    def get_human_default_name(cls):
        '''
        returns the user friendly default backend name, without eventual user
        modifications.

        @returns string: the default "human name"
        '''
        return cls._general_description[cls.BACKEND_HUMAN_NAME]

    def get_human_name(self):
        '''
        returns the user customized backend name. If the user hasn't
        customized it, returns the default one.

        @returns string: the "human name" of this backend
        '''
        if self.KEY_HUMAN_NAME in self._parameters and \
                self._parameters[self.KEY_HUMAN_NAME] != "":
            return self._parameters[self.KEY_HUMAN_NAME]
        else:
            return self.get_human_default_name()

    def set_human_name(self, name):
        '''
        sets a custom name for the backend

        @param name: the new name
        '''
        self._parameters[self.KEY_HUMAN_NAME] = name
        # we signal the change
        self._signal_manager.backend_renamed(self.get_id())

    def is_enabled(self):
        '''
        Returns if the backend is enabled

        @returns: bool
        '''
        return self.get_parameters()[GenericBackend.KEY_ENABLED] or \
            self.is_default()

    def is_default(self):
        '''
        Returns if the backend is enabled

        @returns: bool
        '''
        return self.get_parameters()[GenericBackend.KEY_DEFAULT_BACKEND]

    def is_initialized(self):
        '''
        Returns if the backend is up and running

        @returns: is_initialized
        '''
        return self._is_initialized

    def get_parameter_type(self, param_name):
        '''
        Given the name of a parameter, returns its type. If the parameter is
         one of the default ones, it does not have a type: in that case, it
        returns None

        @param param_name: the name of the parameter
        @returns string: the type, or None
        '''
        try:
            return self.get_static_parameters()[param_name][self.PARAM_TYPE]
        except:
            return None

    def register_datastore(self, datastore):
        '''
        Setter function to inform the backend about the datastore that's
        loading it.

        @param datastore: a Datastore
        '''
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
        # mkdir -p
        try:
            os.makedirs(os.path.dirname(path))
        except OSError, exception:
            if exception.errno != errno.EEXIST:
                raise

        # Shift backups
        for i in range(PICKLE_BACKUP_NBR, 1, -1):
            destination = "%s.bak.%d" % (path, i)
            source = "%s.bak.%d" % (path, i - 1)

            if os.path.exists(destination):
                os.unlink(destination)

            if os.path.exists(source):
                os.rename(source, destination)

        # Backup main file
        if PICKLE_BACKUP_NBR > 0:
            destination = "%s.bak.1" % path
            if os.path.exists(path):
                os.rename(path, destination)

        # saving
        with open(path, 'wb') as file:
                pickle.dump(data, file)

    def _load_pickled_file(self, path, default_value=None):
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

        with open(path, 'r') as file:
            try:
                return pickle.load(file)
            except Exception:
                Log.error("Pickle file for backend '%s' is damaged" %
                          self.get_name())

        # Loading file failed, trying backups
        for i in range(1, PICKLE_BACKUP_NBR + 1):
            backup_file = "%s.bak.%d" % (path, i)
            if os.path.exists(backup_file):
                with open(backup_file, 'r') as file:
                    try:
                        data = pickle.load(file)
                        Log.info("Succesfully restored backup #%d for '%s'" %
                                (i, self.get_name()))
                        return data
                    except Exception:
                        Log.error("Backup #%d for '%s' is damaged as well" %
                                 (i, self.get_name()))

        # Data could not be loaded, degrade to default data
        Log.error("There is no suitable backup for '%s', "
                  "loading default data" % self.get_name())
        return default_value

    def _gtg_task_is_syncable_per_attached_tags(self, task):
        '''
        Helper function which checks if the given task satisfies the filtering
        imposed by the tags attached to the backend.
        That means, if a user wants a backend to sync only tasks tagged @works,
        this function should be used to check if that is verified.

        @returns bool: True if the task should be synced
        '''
        attached_tags = self.get_attached_tags()
        if GenericBackend.ALLTASKS_TAG in attached_tags:
            return True
        for tag in task.get_tags_name():
            if tag in attached_tags:
                return True
        return False

###############################################################################
### THREADING #################################################################
###############################################################################
    def __try_launch_setting_thread(self):
        '''
        Helper function to launch the setting thread, if it's not running.
        '''
        if self.to_set_timer is None and self.is_enabled():
            self.to_set_timer = threading.Timer(self.timer_timestep,
                                                self.launch_setting_thread)
            self.to_set_timer.start()

    def launch_setting_thread(self, bypass_quit_request=False):
        '''
        This function is launched as a separate thread. Its job is to perform
        the changes that have been issued from GTG core.
        In particular, for each task in the self.to_set queue, a task
        has to be modified or to be created (if the tid is new), and for
        each task in the self.to_remove queue, a task has to be deleted

        @param bypass_quit_request: if True, the thread should not be stopped
                                    even if asked by self.please_quit = True.
                                    It's used when the backend quits, to finish
                                    syncing all pending tasks
        '''
        while not self.please_quit or bypass_quit_request:
            try:
                task = self.to_set.pop()
            except IndexError:
                break
            tid = task.get_id()
            if tid not in self.to_remove:
                self.set_task(task)

        while not self.please_quit or bypass_quit_request:
            try:
                tid = self.to_remove.pop()
            except IndexError:
                break
            self.remove_task(tid)
        # we release the weak lock
        self.to_set_timer = None

    def queue_set_task(self, task):
        ''' Save the task in the backend. In particular, it just enqueues the
        task in the self.to_set queue. A thread will shortly run to apply the
        requested changes.

        @param task: the task that should be saved
        '''
        tid = task.get_id()
        if task not in self.to_set and tid not in self.to_remove:
            self.to_set.appendleft(task)
            self.__try_launch_setting_thread()

    def queue_remove_task(self, tid):
        '''
        Queues task to be removed. In particular, it just enqueues the
        task in the self.to_remove queue. A thread will shortly run to apply
        the requested changes.

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
        if self.to_set_timer is not None:
            self.please_quit = True
            try:
                self.to_set_timer.cancel()
            except:
                pass
            try:
                self.to_set_timer.join()
            except:
                pass
        self.launch_setting_thread(bypass_quit_request=True)
        self.save_state()
