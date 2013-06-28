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
This library deals with synchronizing two sets of objects.
It works like this:
 - We have two sets of generic objects (local and remote)
 - We present one object of either one of the sets and ask the library what's
 the state of its synchronization
 - the library will tell us if we need to add a clone object in the other set,
   update it or, if the other one has been removed, remove also this one
'''
from GTG.tools.twokeydict import TwoKeyDict


TYPE_LOCAL = "local"
TYPE_REMOTE = "remote"


class SyncMeme(object):
    '''
    A SyncMeme is the object storing the data needed to keep track of the state
    of two objects synchronization.
    This basic version, that can be expanded as needed by the code using the
    SyncEngine, just stores the modified date and time of the last
    synchronization for both objects (local and remote)
    '''
    # NOTE: Checking objects CRCs would make this check nicer, as we could know
    #      if the object was really changed, or it has just updated its
    #      modified time (invernizzi)
    def __init__(self,
                 local_modified=None,
                 remote_modified=None,
                 origin=None):
        '''
        Creates a new SyncMeme, updating the modified times for both the
        local and remote objects, and sets the given origin.
        If any of the parameters is set to None, it's ignored.

        @param local_modified: the modified time for the local object
        @param remote_modified: the modified time for the remote object
        @param origin: an object that identifies whether the local or the
                       remote is the original object, the other one being a
                       copy.
        '''
        if local_modified is not None:
            self.set_local_last_modified(local_modified)
        if remote_modified is not None:
            self.set_remote_last_modified(remote_modified)
        if origin is not None:
            self.set_origin(origin)

    def set_local_last_modified(self, modified_datetime):
        '''
        Setter function for the local object modified datetime.

        @param modified_datetime: the local object modified datetime
        '''
        self.local_last_modified = modified_datetime

    def get_local_last_modified(self):
        '''
        Getter function for the local object modified datetime.
        '''
        return self.local_last_modified

    def set_remote_last_modified(self, modified_datetime):
        '''
        Setter function for the remote object modified datetime.

        @param modified_datetime: the remote object modified datetime
        '''
        self.remote_last_modified = modified_datetime

    def get_remote_last_modified(self):
        '''
        Getter function for the remote object modified datetime.
        '''
        return self.remote_last_modified

    def which_is_newest(self, local_modified, remote_modified):
        '''
        Given the updated modified time for both the local and the remote
        objects, it checks them against the stored modified times and
        then against each other.

        @returns string: "local"- if the local object has been modified and its
                         the newest
                         "remote" - the same for the remote object
                         None - if no object modified time is newer than the
                         stored one (the objects have not been modified)
        '''
        if local_modified <= self.local_last_modified and \
                remote_modified <= self.remote_last_modified:
            return None
        if local_modified > remote_modified:
            return "local"
        else:
            return "remote"

    def get_origin(self):
        '''
        Returns the name of the source that firstly presented the object
        '''
        return self.origin

    def set_origin(self, origin):
        '''
        Sets the source that presented the object for the first time. This
        source holds the original object, while the other holds the copy.
        This can be useful in the case of "lost syncability" (see the
        SyncEngine for an explaination).

        @param origin: object representing the source
        '''
        self.origin = origin


class SyncMemes(TwoKeyDict):
    '''
    A TwoKeyDict, with just the names changed to be better understandable.
    The meaning of these names is explained in the SyncEngine class
    description. It's used to store a set of SyncMeme objects, each one keeping
    storing all the data needed to keep track of a single relationship.
    '''

    get_remote_id = TwoKeyDict._get_secondary_key
    get_local_id = TwoKeyDict._get_primary_key
    remove_local_id = TwoKeyDict._remove_by_primary
    remove_remote_id = TwoKeyDict._remove_by_secondary
    get_meme_from_local_id = TwoKeyDict._get_by_primary
    get_meme_from_remote_id = TwoKeyDict._get_by_secondary
    get_all_local = TwoKeyDict._get_all_primary_keys
    get_all_remote = TwoKeyDict._get_all_secondary_keys


class SyncEngine(object):
    '''
    The SyncEngine is an object useful in keeping two sets of objects
    synchronized.
    One set is called the Local set, the other is the Remote one.
    It stores the state of the synchronization and the latest state of each
    object.
    When asked, it can tell if a couple of related objects are up to date in
    the sync and, if not, which one must be updated.

    It stores the state of each relationship in a series of SyncMeme.
    '''

    UPDATE = "update"
    REMOVE = "remove"
    ADD = "add"
    LOST_SYNCABILITY = "lost syncability"

    def __init__(self):
        '''
        Initializes the storage of object relationships.
        '''
        self.sync_memes = SyncMemes()

    def _analyze_element(self,
                         element_id,
                         is_local,
                         has_local,
                         has_remote,
                         is_syncable=True):
        '''
        Given an object that should be synced with another one,
        it finds out about the related object, and decides whether:
            - the other object hasn't been created yet (thus must be added)
            - the other object has been deleted (thus this one must be deleted)
            - the other object is present, but either one has been changed

        A particular case happens if the other object is present, but the
        "is_syncable" parameter (which tells that we intend to keep these two
        objects in sync) is set to False. In this case, this function returns
        that the Syncability property has been lost. This case is interesting
        if we want to delete one of the two objects (the one that has been
        cloned from the original).

        @param element_id: the id of the element we're analysing.
        @param is_local: True if the element analysed is the local one (not the
                         remote)
        @param has_local: function that accepts an id of the local set and
                          returns True if the element is present
        @param has_remote: function that accepts an id of the remote set and
                          returns True if the element is present
        @param is_syncable: explained above
        @returns string: one of self.UPDATE, self.ADD, self.REMOVE,
                         self.LOST_SYNCABILITY
        '''
        if is_local:
            get_other_id = self.sync_memes.get_remote_id
            is_task_present = has_remote
        else:
            get_other_id = self.sync_memes.get_local_id
            is_task_present = has_local

        try:
            other_id = get_other_id(element_id)
            if is_task_present(other_id):
                if is_syncable:
                    return self.UPDATE, other_id
                else:
                    return self.LOST_SYNCABILITY, other_id
            else:
                return self.REMOVE, None
        except KeyError:
            if is_syncable:
                return self.ADD, None
            return None, None

    def analyze_local_id(self, element_id, *other_args):
        '''
        Shortcut to call _analyze_element for a local element
        '''
        return self._analyze_element(element_id, True, *other_args)

    def analyze_remote_id(self, element_id, *other_args):
        '''
        Shortcut to call _analyze_element for a remote element
        '''
        return self._analyze_element(element_id, False, *other_args)

    def record_relationship(self, local_id, remote_id, meme):
        '''
        Records that an object from the local set is related with one a remote
        set.

        @param local_id: the id of the local task
        @param remote_id: the id of the remote task
        @param meme: the SyncMeme that keeps track of the relationship
        '''
        triplet = (local_id, remote_id, meme)
        self.sync_memes.add(triplet)

    def break_relationship(self, local_id=None, remote_id=None):
        '''
        breaks a relationship between two objects.
        Only one of the two parameters is necessary to identify the
        relationship.

        @param local_id: the id of the local task
        @param remote_id: the id of the remote task
        '''
        if local_id:
            self.sync_memes.remove_local_id(local_id)
        elif remote_id:
            self.sync_memes.remove_remote_id(remote_id)

    def __getattr__(self, attr):
        '''
        The functions listed here are passed directly to the SyncMeme object

        @param attr: a function name among the ones listed here
        @returns object: the function return object.
        '''
        if attr in ['get_remote_id',
                    'get_local_id',
                    'get_meme_from_local_id',
                    'get_meme_from_remote_id',
                    'get_all_local',
                    'get_all_remote']:
            return getattr(self.sync_memes, attr)
        else:
            raise AttributeError
