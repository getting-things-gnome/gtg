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
Twitter backend: imports direct messages, replies and/or the user timeline.
Authenticates through OAuth.
'''
import os
import re
import sys
import uuid
import subprocess
from webbrowser import open as openurl

#the tweepy library is not packaged for Debian/Ubuntu. Thus, a copy of it is
# kept in the GTG/backends directory
sys.path.append("GTG/backends")
import tweepy as tweepy

from GTG                                import _
from GTG.backends.genericbackend        import GenericBackend
from GTG.core                           import CoreConfig
from GTG.backends.backendsignals        import BackendSignals
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.backends.syncengine            import SyncEngine
from GTG.tools.logger                   import Log


class Backend(PeriodicImportBackend):
    '''
    Twitter backend: imports direct messages, replies and/or the user timeline.
    Authenticates through OAuth.
    '''


    _general_description = { \
        GenericBackend.BACKEND_NAME: "backend_twitter", \
        GenericBackend.BACKEND_HUMAN_NAME: _("Twitter"), \
        GenericBackend.BACKEND_AUTHORS:    ["Luca Invernizzi"], \
        GenericBackend.BACKEND_TYPE:       GenericBackend.TYPE_IMPORT, \
        GenericBackend.BACKEND_DESCRIPTION: \
            _("Imports your twitter  messages into your GTG " + \
              "tasks. You can choose to either import all your " + \
              "messages or just those with a set of hash tags. \n" + \
              "The message will be interpreted following this" + \
              " format: \n" + \
              "<b>my task title, task description #tag @anothertag</b>\n" + \
              " Tags can be  anywhere in the message"),\
        }

    _static_parameters = { \
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
    
    CONSUMER_KEY = "UDRov5YF3ZUinftvVBoeyA"
    #This is supposed to be secret (because of OAuth), but that's not possible.
    #A xAuth alternative is possible, but it's enabled on mail request if the 
    # twitter staff considers your application worthy of such honour.
    CONSUMER_SECRET = "BApykCPskoZ0g4QpVS7yC7TrZntm87KruSeJwvqTg"

    def __init__(self, parameters):
        '''
        See GenericBackend for an explanation of this function.
        Re-loads the saved state of the synchronization
        '''
        super(Backend, self).__init__(parameters)
        #loading the list of already imported tasks
        self.data_path = os.path.join('backends/twitter/', "tasks_dict-%s" %\
                                     self.get_id())
        self.sync_engine = self._load_pickled_file(self.data_path, \
                                                   SyncEngine())
        #loading the parameters for oauth
        self.auth_path = os.path.join('backends/twitter/', "auth-%s" %\
                                     self.get_id())
        self.auth_params = self._load_pickled_file(self.auth_path, None)
        self.authenticated  = False
        self.authenticating = False

    def save_state(self):
        '''
        See GenericBackend for an explanation of this function.
        Saves the state of the synchronization.
        '''
        self._store_pickled_file(self.data_path, self.sync_engine)

###############################################################################
### IMPORTING TWEETS ##########################################################
###############################################################################

    def do_periodic_import(self):
        '''
        See GenericBackend for an explanation of this function.
        '''
        #abort if authentication is in progress or hasn't been done (in which
        # case, start it)
        self.cancellation_point()
        if not self.authenticated:
            if not self.authenticating:
                self._start_authentication()
            return
        #select what to import
        tweets_to_import = []
        if self._parameters["import-from-direct-messages"]:
            tweets_to_import += self.api.direct_messages()
        if self._parameters["import-from-my-tweets"]:
            tweets_to_import += self.api.user_timeline()
        if self._parameters["import-from-replies"]:
            tweets_to_import += self.api.mentions()
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
        tweet_id = str(tweet.id)
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
        #adding the sender as a tag
        #this works only for some messages types (not for the user timeline)
        user = None
        try:
            user = message.user.screen_name
        except:
            pass
        if user:
            task.add_tag("@" + user)

        #setting title, text and tags
        text = message.text    
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

        task.add_remote_id(self.get_id(), str(message.id))

    def _is_tweet_syncable(self, tweet):
        '''
        Returns True if the given tweet matches the user-specified tags to be
        synced

        @param tweet: a tweet
        '''
        if CoreConfig.ALLTASKS_TAG in self._parameters["import-tags"]:
            return True
        else:
            tags = set(Backend._extract_tags_from_text(tweet.text))
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

    def _start_authentication(self):
        '''
        Fist step of authentication: opening the browser with the oauth page
        '''

        #NOTE: just found out that tweepy works with identi.ca (update:
        #      currently broken!).
        #      However, twitter is moving to oauth only authentication, while
        #      identica uses standard login. For now, I'll keep the backends
        #      separate, using two different libraries (Invernizzi)
                #auth = tweepy.BasicAuthHandler(username, password, 
                #host ='identi.ca', api_root = '/api', 
                #secure=True)
        self.auth = tweepy.OAuthHandler(self.CONSUMER_KEY, \
                                        self.CONSUMER_SECRET)
        self.cancellation_point()
        if self.auth_params == None:
            #no previous contact with the server has been made: no stored
            # oauth token found
            self.authenticating = True
            Log.info("Openning browser for twitter authentification")
            openurl(self.auth.get_authorization_url())
            BackendSignals().interaction_requested(self.get_id(),
                "You need to authenticate to <b>Twitter</b>. A browser"
                " is opening with the correct page. When you have "
                " received a PIN code, press 'Continue'.", \
                BackendSignals().INTERACTION_TEXT,
                "on_authentication_step")
        else:
            #we have gone through authentication successfully before.
            self.cancellation_point()
            try:
                self.auth.set_access_token(self.auth_params[0],\
                                       self.auth_params[1])
            except tweepy.TweepError, e:
                self._on_auth_error(e)
                return
            self.cancellation_point()
            self._end_authentication()

    def on_authentication_step(self, step_type = "", pin = ""):
        '''
        Handles the various steps of authentication. It's the only callback
        function the UI knows about this backend.

        @param step_type: if "get_ui_dialog_text", returns the text to be put
                          in the dialog requesting the pin.
                          if "set_text", the UI is feeding the backend with
                          the pin the user provided
        @param pin: contains the pin if step_type == "set_text"
        '''
        if step_type == "get_ui_dialog_text":
            return "PIN request", "Insert the PIN you should have received "\
                                  "through your web browser here:"
        elif step_type == "set_text":
            try:
                token = self.auth.get_access_token(verifier = pin)
            except tweepy.TweepError, e:
                self._on_auth_error(e)
                return
            self.auth_params = (token.key, token.secret)
            self._store_pickled_file(self.auth_path, self.auth_params)
            self._end_authentication()
    
    def _end_authentication(self):
        '''
        Last step of authentication. Creates the API objects and starts
        importing tweets
        '''
        self.authenticated = True
        self.authenticating = False
        self.api = tweepy.API(auth_handler = self.auth, \
                              secure = True, \
                              retry_count = 3)
        self.cancellation_point()
        self.start_get_tasks()

    def _on_auth_error(self, exception):
        '''
        On authentication error, informs the user.

        @param exception: the Exception object that was raised during
                          authentication
        '''
        if isinstance(exception, tweepy.TweepError):
            if exception.reason == "HTTP Error 401: Unauthorized":
                self.auth_params = None
                self._store_pickled_file(self.auth_path, self.auth_params)
                self.quit(disable = True)
                BackendSignals().backend_failed(self.get_id(), \
                                BackendSignals.ERRNO_AUTHENTICATION)

    def signal_network_down(self):
        '''
        If the network is unresponsive, inform the user
        '''
        BackendSignals().backend_failed(self.get_id(), \
                        BackendSignals.ERRNO_NETWORK)
