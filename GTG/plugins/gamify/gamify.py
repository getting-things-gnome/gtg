import os

from gi.repository import Gio
from gi.repository import Gtk

from GTG.core.logger import log
from gettext import gettext as _

class Gamify:
    PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))

    def __init__(self):
        self.task_target = 0

        self.builder = Gtk.Builder()
        path = f"{self.PLUGIN_PATH}/prefs.ui"
        self.builder.add_from_file(path)
        self.pref_dialog = self.builder.get_object('gamify-pref-window')

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.browser = plugin_api.get_browser()

        # Add a button to the MainWindow
        self.menu_item = Gtk.ModelButton.new()
        self.menu_item.set_label(_("Gamify"))
        self.menu_item.connect("clicked", self.on_marked_as_done, plugin_api)
        self.plugin_api.add_menu_item(self.menu_item)

        # Connect to the signals
        self.connect_id = self.browser.connect("task-marked-as-done", self.on_marked_as_done)

    def on_marked_as_done(self, sender, task_id):
        log.debug('a task has been marked as done')

    def OnTaskOpened(self, plugin_api):
        pass
    
    def deactivate(self, plugin_api):
        self.plugin_api.remove_menu_item(self.menu_item)

    def is_configurable(self):
        return True

    def configure_dialog(self, manager_dialog):
        pass
