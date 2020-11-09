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
    LEVELS = {
        100: 'Beginner',
        1000: 'Novice',
        2000: 'prefessional',
        4000: 'Expert',
        9000: 'Master',
        13000: 'Master II',
        19000: 'Grand Master',
        25000: 'Productivity Lord'
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
        self.preferences = None

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
        self.headerbar_button = self.builder.get_object('gamify-headerbar')

        self.stack.add_named(self.submenu, 'gamify')
        self.headerbar = self.plugin_api.get_header()
        self.headerbar.add(self.headerbar_button)

    def remove_submenu(self):
        self.stack.remove(self.submenu)
        self.headerbar.remove(self.headerbar_button)

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

        self.analitics_load()
        self.preferences_load()
        self.update_date()
        self.update_streak()
        self.analitics_save()
        self.update_widget()
        print(self.data)

    def on_marked_as_done(self, sender, task_id):
        log.debug('a task has been marked as done')
        self.analitics_load()
        self.preferences_load()

        # Update the date, if it is different from today
        self.update_date()

        # Increase the number of tasks done and update the streak
        # if the target number of tasks was achieved
        self.data['last_task_number'] += 1
        self.update_streak()
        self.data['score'] += self.get_points_for_task(task_id)
        self.analitics_save()
        self.update_widget()
        print(self.data)

    def get_points_for_task(self, task_id):
        """Returns the number of point for doing a perticular task

        If a task is taged as @hard: the user receives 3 points
        If a task is taged as @meduim: the use receives 2 points
        If a task is taged as @easy: the user receives 1 point
        """
        easy = False
        meduim = False
        hard = False
        task = self.plugin_api.get_requester().get_task(task_id)
        tags = task.get_tags_name()
        for tag in tags:
            if tag == '@easy':
                easy = True
            elif tag == '@meduim':
                meduim = True
            elif tag == '@hard':
                hard = True
        
        if easy:
            return 1
        if meduim:
            return 2
        if hard:
            return 3
        return 1

    def OnTaskOpened(self, plugin_api):
        pass
    
    def deactivate(self, plugin_api):
        self.remove_submenu()
        self.remove_menu_entry()

    def is_configurable(self):
        return True

    def preferences_load(self):
        self.preferences = self.plugin_api.load_configuration_object(
            self.PLUGIN_NAMESPACE, "preferences",
            default_values=self.DEFAULT_PREFERENCES
        )

    def save_preferences(self):
        self.plugin_api.save_configuration_object(
            self.PLUGIN_NAMESPACE, 
            "preferences", 
            self.preferences
        )

    def analitics_load(self):
        self.data = self.plugin_api.load_configuration_object(
            self.PLUGIN_NAMESPACE, "analitics",
            default_values=self.DEFAULT_ANALITICS
        )

    def analitics_save(self):
        self.plugin_api.save_configuration_object(
            self.PLUGIN_NAMESPACE,
            "analitics",
            self.data
        )

    def update_streak(self):
        if self.data['last_task_number'] >= self.preferences['target']:
            if not self.data['goal_achieved']:
                self.data['goal_achieved'] = True
                self.data['streak'] += 1

    def update_date(self):
        today = date.today()
        if self.data['last_task_date'] != today:
            if self.data['last_task_number'] < self.preferences['target']:
                self.data['streak'] = 0
            self.data['goal_achieved'] = False
            self.data['last_task_number'] = 0
            self.data['last_task_date'] = today

    def get_current_level(self):
        return min([(score, level) for score,level in self.LEVELS.items() if score >= self.get_score()])[1]

    def get_score(self):
        return self.data['score']

    def get_number_of_tasks(self):
        return self.data['last_task_number']

    def update_score(self):
        score_label = self.builder.get_object('score_label')
        score_label.set_markup(_("<b>{current_level}</b>").format(current_level=self.get_current_level()))
        score_value = self.builder.get_object('score_value')
        score_value.set_markup(_('You have: <b>{score}</b> points').format(score=self.get_score()))

    def update_goal(self):
        goal_label = self.builder.get_object('goal_label')
        headerbar_label_button = self.builder.get_object('headerbar-label-button')
        levelbar = self.builder.get_object('gamify-level-bar')

        goal_label.set_markup(_("<b>{tasks_done} tasks out of {goal}</b>").format(tasks_done=self.get_number_of_tasks(), goal=self.preferences['target']))
        headerbar_label_button.set_markup("{tasks_done}/{goal}".format(tasks_done=self.get_number_of_tasks(), goal=self.preferences['target']))

        levelbar.set_max_value(self.preferences['target'])
        levelbar.set_value(self.get_number_of_tasks())

    def update_widget(self):
        self.update_score()
        self.update_goal()

    def configure_dialog(self, manager_dialog):
        if not self.configureable:
            log.debug('trying to open preference menu, but dialog widget not loaded')
            return

        self.preferences_load()
        self.pref_dialog.set_transient_for(manager_dialog) 
        
        self.spinner.set_value(self.preferences['target'])

        self.pref_dialog.show_all()

    def on_preferences_closed(self, widget=None, data=None):
        self.pref_dialog.hide()
        return True

    def on_preferences_changed(self, widget=None, data=None):
        self.preferences_load()

        # Get the new preferences
        self.preferences['target'] = self.spinner.get_value_as_int()
        
        self.save_preferences() 
        self.update_goal()
