import os
from datetime import date

from gi.repository import Gio
from gi.repository import Gtk

from GTG.core.logger import log
from gettext import gettext as _

class Gamify:
    PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
    PLUGIN_NAMESPACE = 'gamify'
    DEFAULT_ANALITICS = {
        "last_task_date": date.today(), # The date of the last task marked as done
        "last_task_number": 0, # The number of tasks done today
        "streak": 0, # The number of days in which the goal was achieved
        "goal_achieved": False, # achieved today's goal
        "score": 0
    }
    DEFAULT_PREFERENCES = {
        "target": 3
    }

    def __init__(self):
        self.configureable = True

        self.builder = Gtk.Builder()
        path = f"{self.PLUGIN_PATH}/prefs.ui"
        self.builder.add_from_file(path)

        self.menu = None
        self.stack = None
        self.submenu = None

        self.data = None

    def _init_dialog_pref(self):
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

    def add_submenu(self):
        self.menu = self.plugin_api.get_menu()
        self.stack = self.menu.get_child()
        self.submenu = self.builder.get_object('submenu-popover')
        self.stack.add_named(self.submenu, 'gamify')

    def remove_submenu(self):
        self.stack.remove(self.submenu)

    def add_menu_enty(self):
        self.menu_item = self.builder.get_object('gamify-entry')
        self.plugin_api.add_menu_item(self.menu_item)

    def remove_menu_entry(self):
        self.plugin_api.remove_menu_item(self.menu_item)

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.browser = plugin_api.get_browser()

        # Settings up the menu 
        self.add_submenu()
        self.add_menu_enty()

        # Init the preference dialog
        try:
            self._init_dialog_pref()
        except ValueError:
            self.configureable = False
            log.debug('Cannot load preference dialog widget')

        # Connect to the signals
        self.connect_id = self.browser.connect("task-marked-as-done", self.on_marked_as_done)

        self.data = self.analitics_load()
        preferences = self.preferences_load()
        self.update_date(preferences)
        self.update_streak(preferences)
        self.analitics_save(self.data)
        print(self.data)

    def on_marked_as_done(self, sender, task_id):
        log.debug('a task has been marked as done')
        self.data = self.analitics_load()
        preferences = self.preferences_load()

        # Update the date, if it is different from today
        self.update_date(preferences)

        # Increase the number of tasks done and update the streak
        # if the target number of tasks was achieved
        self.data['last_task_number'] += 1
        self.update_streak(preferences)
        self.analitics_save(self.data)
        print(self.data)

    def OnTaskOpened(self, plugin_api):
        pass
    
    def deactivate(self, plugin_api):
        self.remove_submenu()
        self.remove_menu_entry()

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

    def analitics_load(self):
        return self.plugin_api.load_configuration_object(
            self.PLUGIN_NAMESPACE, "analitics",
            default_values=self.DEFAULT_ANALITICS
        )

    def analitics_save(self, analitics):
        self.plugin_api.save_configuration_object(
            self.PLUGIN_NAMESPACE,
            "analitics",
            analitics
        )

    def update_streak(self, preferences):
        if self.data['last_task_number'] >= preferences['target']:
            if not self.data['goal_achieved']:
                self.data['goal_achieved'] = True
                self.data['streak'] += 1

    def update_date(self, preferences):
        today = date.today()
        if self.data['last_task_date'] != today:
            if self.data['last_task_number'] < preferences['target']:
                self.data['streak'] = 0
            self.data['goal_achieved'] = False
            self.data['last_task_number'] = 0
            self.data['last_task_date'] = today

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
