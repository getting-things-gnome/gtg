import os
import random
from datetime import date
from collections import defaultdict
import logging

from gi.repository import Gio
from gi.repository import Gtk

from gettext import gettext as _
from gettext import ngettext

from GTG.core.task import Task

log = logging.getLogger(__name__)


class Gamify:
    PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
    PLUGIN_NAMESPACE = 'gamify'
    DEFAULT_ANALYTICS = {
        "last_task_date": date.today(),  # The date of the last task marked as done
        "last_task_number": 0,           # The number of tasks done today
        "streak": 0,                     # The number of days in which the goal was achieved
        "goal_achieved": False,          # achieved today's goal
        "score": 0
    }
    DEFAULT_PREFERENCES = {
        "goal": 3,
        "ui_type": "FULL",
        "tag_mapping": {
            _('easy'): 1,
            _('medium'): 2,
            _('hard'): 3,
        }
    }
    LEVELS = {
        100: _('Beginner'),
        1000: _('Novice'),
        2000: _('prefessional'),
        4000: _('Expert'),
        9000: _('Master'),
        13000: _('Master II'),
        19000: _('Grand Master'),
        25000: _('Productivity Lord')
    }

    # INIT #####################################################################

    def __init__(self):
        self.configureable = True

        self.builder = Gtk.Builder()
        path = f"{self.PLUGIN_PATH}/prefs.ui"
        self.builder.add_from_file(path)

        self.data = None
        self.preferences = None

    def _init_dialog_pref(self):
        # Get the dialog widget
        self.pref_dialog = self.builder.get_object('Preferences')

        # Get the listboxs
        self.general_label = self.builder.get_object('general-label')
        self.general_listbox = self.builder.get_object('general-listbox')
        self.mappings_label = self.builder.get_object('mappings-label')
        self.mappings_listbox = self.builder.get_object('mappings-listbox')

        # target tasks
        self.target_tasks = self.builder.get_object('target-tasks')
        self.target_spinbutton = self.builder.get_object('target-spinbutton')
        self.target_label = self.builder.get_object('target-label')

        # UI mode Box
        self.ui_mode = self.builder.get_object('ui-mode')
        self.ui_combobox = self.builder.get_object('ui-combobox')
        self.ui_label = self.builder.get_object('ui-label')

        # Mappings objects
        self.new_mapping_dialog = self.builder.get_object('new-mapping-dialog')
        self.new_mapping_entry = self.builder.get_object('new-mapping-entry')
        self.new_mapping_spinner = self.builder.get_object('new-mapping-spinner')

        if self.pref_dialog is None:
            raise ValueError('Cannot load preference dialog widget')

        self.load_general_listbox()

        SIGNALS = {
            "on-preferences-changed": self.on_preferences_changed,
            "on-preferences-closed": self.on_preferences_closed,
            "dismiss-new-mapping": self.on_dismiss_new_mapping,
            "submit-new-mapping": self.on_add_new_mapping
        }
        self.builder.connect_signals(SIGNALS)

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.browser = plugin_api.get_browser()

        # Load preferences and data
        self.analytics_load()
        self.preferences_load()

        # Settings up the menu
        self.add_ui()

        # Init the preference dialog
        try:
            self._init_dialog_pref()
        except ValueError:
            self.configureable = False
            log.debug('Cannot load preference dialog widget')

        # Connect to the signals
        self.signal_connect_id = self.plugin_api.get_requester().connect("status-changed",
                self.on_status_changed)

        self.update_date()
        self.update_streak()
        self.analytics_save()
        self.update_widget()

    def deactivate(self, plugin_api):
        self.browser.disconnect(self.signal_connect_id)
        self.remove_ui()


    def is_configurable(self):
        return True

    # SAVE/LOAD DATA ##########################################################

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

    def analytics_load(self):
        self.data = self.plugin_api.load_configuration_object(
            self.PLUGIN_NAMESPACE, "analytics",
            default_values=self.DEFAULT_ANALYTICS
        )

    def analytics_save(self):
        self.plugin_api.save_configuration_object(
            self.PLUGIN_NAMESPACE,
            "analytics",
            self.data
        )

    # GAMIFY LOGIC #############################################################

    def update_streak(self):
        if self.data['last_task_number'] >= self.preferences['goal']:
            if not self.data['goal_achieved']:
                self.data['goal_achieved'] = True
                self.data['streak'] += 1
        else:
            if self.data['goal_achieved']:
                self.data['streak'] -= 1
                self.data['goal_achieved'] = False

    def update_date(self):
        today = date.today()
        if self.data['last_task_date'] != today:
            if self.data['last_task_number'] < self.preferences['goal'] or \
                    (today - self.data['last_task_date']).days > 1:
                self.data['streak'] = 0

            self.data['goal_achieved'] = False
            self.data['last_task_number'] = 0
            self.data['last_task_date'] = today

    def get_current_level(self):
        score_levels = [(score, level) for score, level in self.LEVELS.items()
                if score >= self.get_score()]
        return min(score_levels)[1]

    def get_score(self):
        return self.data['score']

    def get_number_of_tasks(self):
        return self.data['last_task_number']

    def get_streak(self):
        return self.data['streak']

    def on_status_changed(self, sender, task_id, status):
        if status == Task.STA_DONE:
            self.on_marked_as_done(task_id)
        else:
            self.on_marked_as_not_done(task_id)

    def on_marked_as_done(self, task_id):
        log.debug('a task has been marked as done')
        self.analytics_load()
        self.preferences_load()

        # Update the date, if it is different from today
        self.update_date()

        # Increase the number of tasks done and update the streak
        # if the goal number of tasks was achieved
        self.data['last_task_number'] += 1
        self.update_streak()
        self.data['score'] += self.get_points_for_task(task_id)
        self.analytics_save()
        self.update_widget()

    def on_marked_as_not_done(self, task_id):
        log.debug('a task has been marked as not done')
        self.analytics_load()
        self.preferences_load()

        self.update_date()

        if self.data['last_task_number'] > 0:
            self.data['last_task_number'] -= 1
        else:
            self.data['last_task_number'] = 0

        self.update_streak()
        if self.data['score'] - (score := self.get_points_for_task(task_id)) >= 0:
            self.data['score'] -= score
        else:
            self.data['score'] = 0
        self.analytics_save()
        self.update_widget()

    def get_points(self, tag):
        return defaultdict(int, self.preferences['tag_mapping'])[tag]

    def get_points_for_task(self, task_id):
        """Returns the number of point for doing a perticular task
        By default the tag mappings are:
        1 point for @easy
        2 points for @medium
        3 points for @hard
        """
        task = self.plugin_api.get_requester().get_task(task_id)
        return max(list(map(self.get_points, task.get_tags_name())), default=1)

    # FRONTEND/UI #############################################################

    def is_full(self):
        """Return True if ui type is FULL"""
        return self.preferences['ui_type'] == 'FULL'

    def has_button(self):
        """Return True if UI contains a BUTTON"""
        return self.preferences['ui_type'] in ('BUTTON', 'FULL')

    def has_levelbar(self):
        """Return True if UI contains a LEVELBAR"""
        return self.preferences['ui_type'] in ('LEVELBAR', 'FULL')

    def add_headerbar_button(self):
        self.headerbar_button = self.builder.get_object('gamify-headerbar')

        self.headerbar = self.plugin_api.get_header()
        self.headerbar.add(self.headerbar_button)

    def remove_headerbar_button(self):
        self.headerbar.remove(self.headerbar_button)

    def add_levelbar(self):
        self.quickadd_pane = self.plugin_api.get_quickadd_pane()
        self.levelbar = self.builder.get_object('goal-levelbar')
        self.quickadd_pane.set_orientation(Gtk.Orientation.VERTICAL)
        self.quickadd_pane.add(self.levelbar)

    def remove_levelbar(self):
        self.quickadd_pane.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.quickadd_pane.remove(self.levelbar)

    def add_ui(self):
        """Add the appropriate UI elements"""
        if self.preferences['ui_type'] == 'FULL':
            self.add_headerbar_button()
            self.add_levelbar()
        elif self.preferences['ui_type'] == 'BUTTON':
            self.add_headerbar_button()
        else:
            self.add_levelbar()


    def remove_ui(self):
        """Remove all the UI elements of the plugin"""
        try:
            self.remove_headerbar_button()
        except AttributeError:
            pass
        try:
            self.remove_levelbar()
        except AttributeError:
            pass

    # UPDATE UI ###############################################################

    def button_update_score(self):
        """Update the score in the BUTTON widget"""
        score_label = self.builder.get_object('score_label')
        score_label.set_markup(_("Level: <b>{current_level}</b>").format(
            current_level=self.get_current_level()))
        score_value = self.builder.get_object('score_value')
        text = ngettext("%d Point", "%d Points", self.get_score())
        score_value.set_markup(text % self.get_score())

    def button_update_goal(self):
        """Update the numbers of tasks done in the BUTTON widget"""
        headerbar_label_button = self.builder.get_object('headerbar-label-button')
        headerbar_label = self.builder.get_object('headerbar-label')
        headerbar_msg = self.builder.get_object('headerbar-msg')

        tasks_done = self.get_number_of_tasks()
        goal = self.preferences['goal']
        headerbar_label_button.set_markup("{tasks_done}/{goal}".format(
            tasks_done=tasks_done, goal=goal))

        # Select a msg and emojo depending on the number of tasks done.
        if tasks_done >= goal:
            emoji = ["\U0001F60E", "\U0001F920", "\U0001F640", "\U0001F31F"]
            headerbar_label.set_markup(random.choice(emoji))
            headerbar_msg.set_markup(_("Good Job!\nYou have achieved your goal."))
        elif tasks_done >= 1:
            emoji = ["\U0001F600", "\U0001F60C", "\U0000270A"]
            headerbar_label.set_markup(random.choice(emoji))
            headerbar_msg.set_markup(_("Only a few tasks to go!"))
        else:
            emoji = ["\U0001F643", "\U0001F648", "\U0001F995", "\U0001F9A5"]
            headerbar_label.set_markup(random.choice(emoji))
            headerbar_msg.set_markup(
                _("Get Down to Business\nYou haven't achieved any tasks today."))

    def button_update_streak(self):
        """Update the streak numbers in the BUTTON widget"""
        streak_number = self.builder.get_object('streak_number')
        if self.get_streak() > 0:
            streak_emoji = "\U0001F525"
        else:
            streak_emoji = "\U0001F9CA"

        streak_number.set_markup(_("{emoji} <b>{streak} day</b> streak").format(
            streak=self.get_streak(), emoji=streak_emoji))

    def update_levelbar(self):
        self.levelbar.set_min_value(0.0)
        self.levelbar.set_max_value(self.preferences['goal'])
        self.levelbar.set_value(self.get_number_of_tasks())

    def update_widget(self):
        """Update the information depending on the UI type"""
        if self.has_button():
            self.button_update_score()
            self.button_update_goal()
            self.button_update_streak()

        if self.has_levelbar():
            self.update_levelbar()


    def update_goal(self):
        if self.has_button():
            self.button_update_goal()
        if self.has_levelbar():
            self.update_levelbar()

    def update_ui(self):
        """Updates the type of ui (FULL, BUTTON, or LEVELBAR)"""
        self.remove_ui()
        self.add_ui()

    # PREFERENCES ############################################################

    def configure_dialog(self, manager_dialog):
        if not self.configureable:
            log.debug('trying to open preference menu, but dialog widget not loaded')
            return

        self.preferences_load()
        self.pref_dialog.set_transient_for(manager_dialog)

        # Tag Mapping
        self.load_mappings_listbox()

        self.load_ui_mode()
        self.load_target_task()

        self.pref_dialog.show_all()

    def on_preferences_closed(self, widget=None, data=None):
        self.pref_dialog.hide()
        return True

    def on_preferences_changed(self, widget=None, data=None):
        self.preferences_load()

        # Get the new preferences
        self.preferences['goal'] = self.target_spinbutton.get_value_as_int()

        ui_mode = int(self.get_ui_mode_combo_value())
        if ui_mode == 0:
            self.preferences['ui_type'] = "FULL"
        elif ui_mode == 1:
            self.preferences['ui_type'] = "BUTTON"
        elif ui_mode == 2:
            self.preferences['ui_type'] = "LEVELBAR"

        # Save the new mappings
        new_tag_mapping = {}
        for row in self.mappings_listbox.get_children()[:-1]:
            label, value = self.get_tag_value_from_mapping_row(row)
            new_tag_mapping[label.get_label()] = value.get_value_as_int()

        self.preferences['tag_mapping'] = new_tag_mapping

        self.save_preferences()
        # Update the type of UI
        self.update_ui()
        # Update the goal in the widget(s)
        self.update_goal()

    def get_ui_mode_combo_value(self):
        return self.ui_combobox.get_active_id()

    def make_mapping_row(self, label_text: str, spin_value):
        row = Gtk.ListBoxRow()
        upper_box = Gtk.Box(spacing=3)
        box = Gtk.HBox(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_homogeneous(True)
        label = Gtk.Label(label_text)
        label.set_alignment(0.05, 0)
        label.set_valign(Gtk.Align.CENTER)

        spin = Gtk.SpinButton()
        spin.set_adjustment(Gtk.Adjustment(upper=100, step_increment=1, page_increment=10))
        spin.set_numeric(True)
        spin.set_value(int(spin_value))

        remove_icon = Gio.ThemedIcon(name="user-trash-symbolic")
        remove = Gtk.Image.new_from_gicon(remove_icon, Gtk.IconSize.BUTTON)
        button = Gtk.Button()
        button.connect("clicked", self.remove_mapping)
        button.add(remove)

        row.add(upper_box)
        upper_box.pack_start(box, True, True, 0)
        upper_box.pack_end(button, False, True, 0)
        box.add(label)
        box.add(spin)
        return row

    def load_mappings_listbox(self):
        self.mappings_label.set_alignment(0, 0)
        self.preferences_load()

        # If there are any old children, remove them from the ListBox
        for child in self.mappings_listbox.get_children():
            self.mappings_listbox.remove(child)
            child.destroy()

        # Construct the listBoxRows
        for key, value in self.preferences['tag_mapping'].items():
            row = self.make_mapping_row(label_text=key, spin_value=value)
            self.mappings_listbox.add(row)

        self.add_row = Gtk.ListBoxRow()
        box = Gtk.HBox(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_homogeneous(True)

        add_icon = Gio.ThemedIcon(name="list-add-symbolic")
        add = Gtk.Image.new_from_gicon(add_icon, Gtk.IconSize.BUTTON)
        box.add(add)

        event_box = Gtk.EventBox()
        event_box.connect("button-press-event", self.add_mapping_clicked)
        event_box.add(box)

        self.add_row.add(event_box)
        self.mappings_listbox.add(self.add_row)

    def add_mapping_clicked(self, widget, event):
        self.new_mapping_dialog.set_transient_for(self.pref_dialog)

        self.new_mapping_entry.set_text("")
        self.new_mapping_spinner.set_value(0)

        self.new_mapping_dialog.show_all()

    def remove_mapping(self, widget, event=None):
        self.mappings_listbox.remove(self.get_row_from_remove_mapping(widget))

    def get_row_from_remove_mapping(self, button):
        return button.get_parent().get_parent()

    def get_tag_value_from_mapping_row(self, row):
        box = row.get_child().get_children()[0]
        box_children = box.get_children()
        return (box_children[0], box_children[1])

    def on_dismiss_new_mapping(self, widget=None, event=None):
        self.new_mapping_dialog.hide()

    def on_add_new_mapping(self, widget=None, event=None):
        if tag := self.new_mapping_entry.get_text():
            row = self.make_mapping_row(label_text=tag,
                                        spin_value=self.new_mapping_spinner.get_value())
            self.mappings_listbox.remove(self.add_row)
            self.mappings_listbox.add(row)
            self.mappings_listbox.add(self.add_row)
            self.mappings_listbox.show_all()

            self.on_dismiss_new_mapping()

    def load_general_listbox(self):
        self.general_label.set_alignment(0, 0)
        self.target_label.set_alignment(0, 0)
        self.ui_label.set_alignment(0, 0)

        self.load_ui_mode()
        self.load_target_task()

        for child in self.general_listbox.get_children():
            self.general_listbox.remove(child)

        target_row = Gtk.ListBoxRow()
        target_row.add(self.target_tasks)

        ui_row = Gtk.ListBoxRow()
        ui_row.add(self.ui_mode)

        self.general_listbox.add(target_row)
        self.general_listbox.add(ui_row)

    def load_target_task(self):
        self.preferences_load()
        self.target_spinbutton.set_value(self.preferences['goal'])

    def load_ui_mode(self):
        self.preferences_load()
        if self.preferences['ui_type'] == 'FULL':
            self.ui_combobox.set_active(0)
        elif self.preferences['ui_type'] == 'BUTTON':
            self.ui_combobox.set_active(1)
        else:
            self.ui_combobox.set_active(2)

