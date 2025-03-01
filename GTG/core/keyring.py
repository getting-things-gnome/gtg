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

from typing import Type
import gi # type: ignore[import-untyped]
import logging
try:
    gi.require_version('Secret', '1')
    from gi.repository import Secret # type: ignore[import-untyped]
except (ValueError, ImportError):
    Secret = None

try:
    gi.require_version('GnomeKeyring', '1.0')
    from gi.repository import GnomeKeyring
except (ValueError, ImportError):
    GnomeKeyring = None

from GTG.core.borg import Borg

log = logging.getLogger(__name__)

class SecretKeyring(Borg):
    def __init__(self):
        super().__init__()
        self._SECRET_SCHEMA = Secret.Schema.new("org.gnome.GTG.v1",
            Secret.SchemaFlags.NONE,
            {
                "id": Secret.SchemaAttributeType.STRING,
            }
        )

    def set_password(self, pass_name, password):
        log.debug(f"set_password {pass_name}")
        result = Secret.password_store_sync(
                self._SECRET_SCHEMA, { "id": pass_name },
                Secret.COLLECTION_DEFAULT, str(pass_name), password, None)

        if not result:
            raise Exception(f"Can't create a new password: {result}")

        return pass_name

    def get_password(self, pass_name):
        log.debug(f"get_password {pass_name}")
        passwd= Secret.password_lookup_sync(self._SECRET_SCHEMA, { "id": pass_name }, None)
        return passwd or ""

class GNOMEKeyring(Borg):

    def __init__(self):
        super().__init__()
        if not hasattr(self, "keyring"):
            result, self.keyring = GnomeKeyring.get_default_keyring_sync()
            if result != GnomeKeyring.Result.OK:
                raise Exception(f"Can't get default keyring, error={result}")

    def set_password(self, name, password, userid=""):
        attrs = GnomeKeyring.Attribute.list_new()
        GnomeKeyring.Attribute.list_append_string(attrs, "backend", name)
        result, password_id = GnomeKeyring.item_create_sync(
            self.keyring,
            GnomeKeyring.ItemType.GENERIC_SECRET,
            name,
            attrs,
            password,
            True)

        if result != GnomeKeyring.Result.OK:
            raise Exception(f"Can't create a new password, error={result}")

        return str(password_id)

    def get_password(self, item_id):
        result, item_info = GnomeKeyring.item_get_info_sync(
            self.keyring, int(item_id))
        if result == GnomeKeyring.Result.OK:
            return item_info.get_secret()
        else:
            return ""


class FallbackKeyring(Borg):

    def __init__(self):
        super().__init__()
        if not hasattr(self, "keyring"):
            self.keyring = {}
            self.max_key = 1

    def set_password(self, name, password, userid=""):
        """ This implementation does nto need name and userid.
        It is there because of GNOMEKeyring """

        # Find unused key
        while self.max_key in self.keyring:
            self.max_key += 1

        self.keyring[self.max_key] = password
        return str(self.max_key)

    def get_password(self, key):
        return self.keyring.get(int(key), "")


if Secret is not None:
    Keyring: Type[SecretKeyring|GNOMEKeyring|FallbackKeyring] = SecretKeyring
elif GnomeKeyring is not None:
    Keyring = GNOMEKeyring
else:
    log.error("GNOME keyring not found, passwords will be "
              "not stored after restarting GTG")
    Keyring = FallbackKeyring
