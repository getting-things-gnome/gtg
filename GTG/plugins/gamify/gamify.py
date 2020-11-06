import os

from gi.repository import Gio
from gi.repository import Gtk

from GTG.core.logger import log
from gettext import gettext as _

class Gamify:
    PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
    PLUGIN_NAMESPACE = 'gamify'
    DEFAULT_PREFERENCES = {
        "target": 3
    }

    def __init__(self):
        self.configureable = True

    def _init_dialog_pref(self):
        self.builder = Gtk.Builder()
        path = f"{self.PLUGIN_PATH}/prefs.ui"
        self.builder.add_from_file(path)
        # Get the dialog widget
        self.pref_dialog = self.builder.get_object('gamify-pref-dialog')
        # Get the buttonSpin
        self.spinner = self.builder.get_object('target-spin-button')

        if self.pref_dialog is None or self.spinner is None:
            raise ValueError('Cannot load preference dialog widget')

        SIGNALS = {
            "on_preferences_changed": self.on_preferences_changed,
            "on_dialog_close": self.on_preferences_closed
        }
        self.builder.connect_signals(SIGNALS) 


    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.browser = plugin_api.get_browser()

        # Add a button to the MainWindow
        self.menu_item = Gtk.ModelButton.new()
        self.menu_item.set_label(_("Gamify"))
        self.menu_item.connect("clicked", self.on_marked_as_done, plugin_api)
        self.plugin_api.add_menu_item(self.menu_item)

        # Init the preference dialog
        try:
            self._init_dialog_pref()
        except ValueError:
            self.configureable = False
            log.debug('Cannot load preference dialog widget')

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

    def preferences_load(self):
        return self.plugin_api.load_configuration_object(
            self.PLUGIN_NAMESPACE, "preferences",
            default_values=self.DEFAULT_PREFERENCES
        )

    def save_preferences(self, preferences):
        self.plugin_api.save_configuration_object(
            self.PLUGIN_NAMESPACE, 
            "preferences", 
            preferences
        )

    def configure_dialog(self, manager_dialog):
        if not self.configureable:
            log.debug('trying to open preference menu, but dialog widget not loaded')
            return

        preferences = self.preferences_load()
        self.pref_dialog.set_transient_for(manager_dialog) 
        
        self.spinner.set_value(preferences['target'])

        self.pref_dialog.show_all()

    def on_preferences_closed(self, widget=None, data=None):
        self.pref_dialog.hide()
        return True

    def on_preferences_changed(self, widget=None, data=None):
        preferences = self.preferences_load()

        # Get the new preferences
        preferences['target'] = self.spinner.get_value()
        
        self.save_preferences(preferences) 
