# -----------------------------------------------------------------------------
# GTG Developer Console
# Based on Pitivi Developer Console
# Copyright (c) 2017-2018, Fabian Orccon <cfoch.fabian@gmail.com>
# Copyright (c) The GTG Team
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""Developer console plugin."""

import sys
from gi.repository import Gtk, Gdk, Gio
from GTG.core.plugins.api import PluginAPI

from gettext import gettext as _

from GTG.plugins.dev_console.utils import Namespace
from GTG.plugins.dev_console.window import ConsoleWidget


class GTGNamespace(Namespace):
    """Easy to shape Python namespace."""

    def __init__(self, app):
        Namespace.__init__(self)
        self._app = app

    @property
    @Namespace.shortcut
    def app(self):
        """The Pitivi instance."""
        return self._app

    @property
    @Namespace.shortcut
    def browser(self):
        """The Plugin Manager instance."""
        return self._app.browser

    @property
    @Namespace.shortcut
    def req(self):
        """The current project."""
        return self._app.req


class DevConsolePlugin():
    """Open a window with a Python interpreter."""

    DEFAULT_PREFERENCES = {}

    def __init__(self):

        self.api = None
        self.window = None
        self.terminal = None

        self.menu_item = Gio.MenuItem.new('Developer Console', 'app.plugin.open_console')

        # Set prompt.
        sys.ps1 = ">>> "
        sys.ps2 = "... "


    def activate(self, api: PluginAPI) -> None:
        """Plugin is activated."""

        self.api = api
        self.api.add_menu_item(self.menu_item)

        namespace = GTGNamespace(self.api.get_view_manager())
        self.window = Gtk.Window()
        self.terminal = ConsoleWidget(namespace,
                                     self.welcome_message(namespace))

        self.terminal.connect("eof", self.eof_cb)

        # Font and colors
        self.terminal.set_font('Source Code Pro 10')
        self.terminal.set_color(Gdk.RGBA(1.0, 1.0, 1.0, 1.0))
        self.terminal.set_stderr_color(Gdk.RGBA(0.96, 0.5, 0.5, 1.0))
        self.terminal.set_stdout_color(Gdk.RGBA(1.0, 1.0, 1.0, 1.0))

        # Build window
        self.window.set_default_size(600, 400)
        self.window.set_title(_('Developer Console'))
        self.window.connect('delete-event', self.on_delete_event)
        self.window.add(self.terminal)

        # Add F12 shortcut
        open_action = Gio.SimpleAction.new('plugin.open_console', None)
        open_action.connect('activate', self.open_window)
        open_action.set_enabled(True)

        app = self.api.get_view_manager()
        app.add_action(open_action)
        app.set_accels_for_action('app.plugin.open_console', ['F12'])


    def welcome_message(self, namespace):
        """Print a message when opening the console window."""

        return _('Welcome to GTG\'s Developer Console'
                 '\n\n'
                 'You can use the following shortcuts:'
                 '\n'
                 '- app (The application class)\n'
                 '- req (The requester class)\n'
                 '- browser (The main window)\n'
                 '\n'
                 'Type "help (<command>)" for more information.'
                 '\n\n')


    def deactivate(self, api: PluginAPI) -> None:
        """Deactivates the plugin."""

        api.remove_menu_item(self.menu_item)


    def open_window(self, widget=None, unsued=None) -> None:
        """Open developer console."""

        self.window.show_all()
        self.window.set_keep_above(True)


    def eof_cb(self, unused_widget):
        self.window.hide()
        return True


    def on_delete_event(self, widget, data):
        """Callback when window is closed."""

        return self.window.hide_on_delete()
