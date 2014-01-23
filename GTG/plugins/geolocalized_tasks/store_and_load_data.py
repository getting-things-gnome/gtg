# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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


import os
import errno
import pickle

from GTG.core import CoreConfig
from GTG.tools.logger import Log

PICKLE_BACKUP_NBR = 2

def store_pickled_file(path, data):
    '''
    A helper function to save some object in a file.

    @param path: a relative path. A good choice is
    "backend_name/object_name"
    @param data: the object
    '''
    path = os.path.join(CoreConfig().get_data_dir(), path)
    print (path)
    # mkdir -p
    try:
        os.makedirs(os.path.dirname(path))
    except OSError as exception:
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

def load_pickled_file(path, default_value=None):
    '''
    A helper function to load some object from a file.

    @param path: the relative path of the file
    @param default_value: the value to return if the file is missing or
    corrupt
    @returns object: the needed object, or default_value
    '''
    path = os.path.join(CoreConfig().get_data_dir(), path)
    print (path)
    if not os.path.exists(path):
        return default_value

    with open(path, 'rb') as file:
        print (file)
        try:
            return pickle.load(file)
        except Exception:
            Log.error("Pickle file '%s' is damaged" % path)

    # Loading file failed, trying backups
    for i in range(1, PICKLE_BACKUP_NBR + 1):
        backup_file = "%s.bak.%d" % (path, i)
        if os.path.exists(backup_file):
            with open(backup_file, 'r') as file:
                try:
                    data = pickle.load(file)
                    Log.info("Succesfully restored backup #%d for '%s'" %
                            (i, path))
                    return data
                except Exception:
                    Log.error("Backup #%d for '%s' is damaged as well" %
                             (i, path))

    # Data could not be loaded, degrade to default data
    Log.error("There is no suitable backup for '%s', "
              "loading default data" % path)
    return default_value
