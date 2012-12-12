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

'''
Identi.ca backend: imports direct messages, replies and/or the user timeline.
'''

import os
import re
import sys
import uuid
import urllib2

from GTG                                import _
from GTG.backends.genericbackend        import GenericBackend
from GTG.core                           import CoreConfig
from GTG.backends.backendsignals        import BackendSignals
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.backends.syncengine            import SyncEngine
from GTG.tools.logger                   import Log

#The Ubuntu version of python twitter is not updated: 
# it does not have identi.ca support. Meanwhile, we ship the right version
# with our code.
import GTG.backends.twitter as twitter



class Backend(PeriodicImportBackend):
    '''
    Identi.ca backend: imports direct messages, replies and/or the user
    timeline.
    '''


    _general_description = { \
        GenericBackend.BACKEND_NAME: "backend_identica", \
        GenericBackend.BACKEND_HUMAN_NAME: _("Identi.ca"), \
        GenericBackend.BACKEND_AUTHORS:    ["Luca Invernizzi"], \
        GenericBackend.BACKEND_TYPE:       GenericBackend.TYPE_IMPORT, \
        GenericBackend.BACKEND_DESCRIPTION: \
            _("Imports your identi.ca  messages into your GTG " + \
              "tasks. You can choose to either import all your " + \
              "messages or just those with a set of hash tags. \n" + \
              "The message will be interpreted following this" + \
              " format: \n" + \
              "<b>my task title, task description #tag @anothertag</b>\n" + \
              " Tags can be  anywhere in the message"),\
        }

    base_url = "http://identi.ca/api/"

    _static_parameters = { \
        "username": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING, \
            GenericBackend.PARAM_DEFAULT_VALUE: "", },
        "password": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_PASSWORD, \
            GenericBackend.PARAM_DEFAULT_VALUE: "", },
        "period": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT, \
            GenericBackend.PARAM_DEFAULT_VALUE: 2, },
        "import-tags": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_LIST_OF_STRINGS, \
            GenericBackend.PARAM_DEFAULT_VALUE: ["#todo"], },
        "import-from-replies": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL, \
            GenericBackend.PARAM_DEFAULT_VALUE: False, },
        "import-from-my-tweets": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL, \
            GenericBackend.PARAM_DEFAULT_VALUE: False, },
        "import-from-direct-messages": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL, \
            GenericBackend.PARAM_DEFAULT_VALUE: True, },
        }

    def __init__(self, parameters):
        '''
        See GenericBackend for an explanation of this function.
        Re-loads the saved state of the synchronization
        '''
        super(Backend, self).__init__(parameters)
        #loading the list of already imported tasks
        self.data_path = os.path.join('backends/identica/', "tasks_dict-%s" %\
                                     self.get_id())
        self.sync_engine = self._load_pickled_file(self.data_path, \
                                                        SyncEngine())
        
    def save_state(self):
        '''
        See GenericBackend for an explanation of this function.
        Saves the state of the synchronization.
        '''
        self._store_pickled_file(self.data_path, self.sync_engine)

    def do_periodic_import(self):
        '''
        See GenericBackend for an explanation of this function.
        '''
        #we need to authenticate only to see the direct messages or the replies
        # (why the replies? Don't know. But python-twitter requires that)
        # (invernizzi)
        with self.controlled_execution(self._parameters['username'],\
                                       self._parameters['password'], \
                                       self.base_url, \
                                       self) as api:
            #select what to import
            tweets_to_import = []
            if self._parameters["import-from-direct-messages"]:
                tweets_to_import += api.GetDirectMessages()
            if self._parameters["import-from-my-tweets"]:
                tweets_to_import += \
                        api.GetUserTimeline(self._parameters["username"])
            if self._parameters["import-from-replies"]:
                tweets_to_import += \
                    api.GetReplies(self._parameters["username"])
            #do the import
            for tweet in tweets_to_import:
                self._process_tweet(tweet)

    def _process_tweet(self, tweet):
        '''
        Given a tweet, checks if a task representing it must be
        created in GTG and, if so, it creates it.

        @param tweet: a tweet.
        '''
        self.cancellation_point()
        tweet_id = str(tweet.GetId())
        is_syncable = self._is_tweet_syncable(tweet)
        #the "lambda" is because we don't consider tweets deletion (to be
        # faster)
        action, tid = self.sync_engine.analyze_remote_id(\
                                        tweet_id, \
                                        self.datastore.has_task, \
                                        lambda tweet_id: True, \
                                        is_syncable)
        Log.debug("processing tweet (%s, %s)" % (action, is_syncable))
        
        self.cancellation_point()
        if action == None or action == SyncEngine.UPDATE:
            return

        elif action == SyncEngine.ADD:
            tid = str(uuid.uuid4())
            task = self.datastore.task_factory(tid)
            self._populate_task(task, tweet)
            #we care only to add tweets and if the list of tags which must be
            #imported changes (lost-syncability can happen). Thus, we don't
            # care about SyncMeme(s)
            self.sync_engine.record_relationship(local_id = tid,\
                                     remote_id = tweet_id, \
                                     meme = None)
            self.datastore.push_task(task)

        elif action == SyncEngine.LOST_SYNCABILITY:
            self.sync_engine.break_relationship(remote_id = tweet_id)
            self.datastore.request_task_deletion(tid)

        self.save_state()

    def _populate_task(self, task, message):
        '''
        Given a twitter message and a GTG task, fills the task with the content
        of the message
        '''
        try:
            #this works only for some messages
            task.add_tag("@" + message.GetSenderScreenName())
        except:
            pass
        text = message.GetText()    
        
        #convert #hastags to @tags
        matches = re.finditer("(?<![^|\s])(#\w+)", text)
        for g in matches:
            text = text[:g.start()] + '@' + text[g.start() + 1:]
        #add tags objects (it's not enough to have @tag in the text to add a
        # tag
        for tag in self._extract_tags_from_text(text):
            task.add_tag(tag)

        split_text = text.split(",", 1)
        task.set_title(split_text[0])
        if len(split_text) > 1:
            task.set_text(split_text[1])

        task.add_remote_id(self.get_id(), str(message.GetId()))

    def _is_tweet_syncable(self, tweet):
        '''
        Returns True if the given tweet matches the user-specified tags to be
        synced

        @param tweet: a tweet
        '''
        if CoreConfig.ALLTASKS_TAG in self._parameters["import-tags"]:
            return True
        else:
            tags = set(Backend._extract_tags_from_text(tweet.GetText()))
            return tags.intersection(set(self._parameters["import-tags"])) \
                    != set()

    @staticmethod
    def _extract_tags_from_text(text):
        '''
        Given a string, returns a list of @tags and #hashtags
        '''
        return list(re.findall(r'(?:^|[\s])((?:#|@)\w+)', text))

###############################################################################
### AUTHENTICATION ############################################################
###############################################################################

    class controlled_execution(object):
        '''
        This class performs the login to identica and execute the appropriate
        response if something goes wrong during authentication or at network
        level
        '''

        def __init__(self, username, password, base_url, backend):
            '''
            Sets the login parameters
            '''
            self.username = username
            self.password = password
            self.backend = backend
            self.base_url = base_url

        def __enter__(self):
            '''
            Logins to identica and returns the Api object
            '''
            return twitter.Api(self.username, self.password, \
                            base_url = self.base_url)

        def __exit__(self, type, value, traceback):
            '''
            Analyzes the eventual exception risen during the connection to
            identica
            '''
            if isinstance(value, urllib2.HTTPError):
                if value.getcode() == 401:
                    self.signal_authentication_wrong()
                if value.getcode() in [502, 404]:
                    self.signal_network_down()
            elif isinstance(value, twitter.TwitterError):
                self.signal_authentication_wrong()
            elif isinstance(value, urllib2.URLError):
                self.signal_network_down()
            else:
                return False
            return True

        def signal_authentication_wrong(self):
            self.backend.quit(disable = True)
            BackendSignals().backend_failed(self.backend.get_id(), \
                            BackendSignals.ERRNO_AUTHENTICATION)

        def signal_network_down(self):
            BackendSignals().backend_failed(self.backend.get_id(), \
                            BackendSignals.ERRNO_NETWORK)

