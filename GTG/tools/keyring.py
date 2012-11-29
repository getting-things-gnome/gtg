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


try:
    from gi.repository import GnomeKeyring
except ImportError:
    GnomeKeyring = None

from GTG.tools.borg import Borg
from GTG.tools.logger import Log


class GNOMEKeyring(Borg):
    def __init__(self):
        super(Keyring, self).__init__()
        if not hasattr(self, "keyring"):
            result, self.keyring = GnomeKeyring.get_default_keyring_sync()
            if result != GnomeKeyring.Result.OK:
                raise Exception("Can't get default keyring, error=%s" % result)

    def set_password(self, name, password, userid = ""):
        attrs = GnomeKeyring.Attribute.list_new()
        GnomeKeyring.Attribute.list_append_string(attrs, "backend", name)
        result, password_id = GnomeKeyring.item_create_sync(self.keyring,
                GnomeKeyring.ItemType.GENERIC_SECRET, name, attrs,
                password, True)

        if result != GnomeKeyring.Result.OK:
            raise Exception("Can't create a new password, error=%s" % result)

        return password_id

    def get_password(self, item_id):
        result, item_info = GnomeKeyring.item_get_info_sync(self.keyring, item_id)
        if result == GnomeKeyring.Result.OK:
            return item_info.get_secret()
        else:
            return ""

class FallbackKeyring(Borg):
    def __init__(self):
        super(Keyring, self).__init__()
        if not hasattr(self, "keyring"):
            self.keyring = {}
            self.max_key = 1

    def set_password(self, name, password, userid = ""):
        """ This implementation does nto need name and userid.
        It is there because of GNOMEKeyring """

        # Find unused key
        while self.max_key in self.keyring:
            self.max_key += 1

        self.keyring[self.max_key] = password
        return self.max_key

    def get_password(self, key):
        return self.keyring.get(key, "")

if GnomeKeyring is not None:
    Keyring = GNOMEKeyring 
else:
    Log.info("GNOME keyring was not found, passwords will be not stored after restart of GTG")
    Keyring = FallbackKeyring
