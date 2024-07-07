import os
import random
from datetime import date
from collections import defaultdict
import logging

from gi.repository import Gtk

from gettext import gettext as _
from gettext import ngettext

from GTG.core.tasks import Task

log = logging.getLogger(__name__)
PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))


@Gtk.Template(filename=f'{PLUGIN_PATH}/prefs.ui')
class GamifyPreferences(Gtk.Window):
    __gtype_name__ = 'GamifyPreferences'

    DEFAULT_PREFERENCES = {
        "goal": 3,
        "ui_type": "FULL",
        "tag_mapping": {
            _('easy'): 1,
            _('medium'): 2,
            _('hard'): 3,
        }
    }

    entry_sizegroup = Gtk.Template.Child('entry-sizegroup')

    general_label = Gtk.Template.Child('general-label')
    general_listbox = Gtk.Template.Child('general-listbox')
    mappings_label = Gtk.Template.Child('mappings-label')
    mappings_listbox = Gtk.Template.Child('mappings-listbox')

    # target tasks
    target_tasks = Gtk.Template.Child('target-tasks')
    target_spinbutton = Gtk.Template.Child('target-spinbutton')
    target_label = Gtk.Template.Child('target-label')

    # UI mode Box
    ui_mode = Gtk.Template.Child('ui-mode')
    ui_combobox = Gtk.Template.Child('ui-combobox')
    ui_label = Gtk.Template.Child('ui-label')

    # Mappings objects
    new_mapping_dialog = Gtk.Template.Child('new-mapping-dialog')
    new_mapping_entry = Gtk.Template.Child('new-mapping-entry')
    new_mapping_spinner = Gtk.Template.Child('new-mapping-spinner')

    def __init__(self, plugin, api, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin = plugin
        self.api = api
        self.load_general_listbox()

    @Gtk.Template.Callback('on-preferences-closed')
    def on_preferences_closed(self, widget=None, data=None):
        self.hide()
        return True

    @Gtk.Template.Callback('on-preferences-changed')
    def on_preferences_changed(self, widget=None, data=None):
        self.load_preferences()

        # Get the new preferences
        self.plugin.preferences['goal'] = self.target_spinbutton.get_value_as_int()

        ui_mode = int(self.get_ui_mode_combo_value())
        if ui_mode == 0:
            self.plugin.preferences['ui_type'] = "FULL"
        elif ui_mode == 1:
            self.plugin.preferences['ui_type'] = "BUTTON"
        elif ui_mode == 2:
            self.plugin.preferences['ui_type'] = "LEVELBAR"

        # Save the new mappings
        new_tag_mapping = {}
        for row in list(self.mappings_listbox)[:-1]:
            label, value = self.get_tag_value_from_mapping_row(row)
            new_tag_mapping[label.get_label()] = value.get_value_as_int()

        self.plugin.preferences['tag_mapping'] = new_tag_mapping

        self.save_preferences()
        self.load_general_listbox()
        # Update the type of UI
        self.plugin.update_ui()
        # Update the goal in the widget(s)
        self.plugin.update_goal()

    @Gtk.Template.Callback('dismiss-new-mapping')
    def on_dismiss_new_mapping(self, widget=None, event=None):
        self.new_mapping_dialog.hide()

    @Gtk.Template.Callback('submit-new-mapping')
    def on_add_new_mapping(self, widget=None, event=None):
        if tag := self.new_mapping_entry.get_text():
            row = self.make_mapping_row(label_text=tag,
                                        spin_value=self.new_mapping_spinner.get_value(),
                                        entry_sizegroup=self.entry_sizegroup)
            self.mappings_listbox.remove(self.add_row)
            self.mappings_listbox.append(row)
            self.mappings_listbox.append(self.add_row)

            self.on_dismiss_new_mapping()

    def load_preferences(self):
        self.plugin.preferences = self.api.load_configuration_object(
            self.plugin.PLUGIN_NAMESPACE, "preferences",
            default_values=self.DEFAULT_PREFERENCES
        )

    def save_preferences(self):
        self.api.save_configuration_object(
            self.plugin.PLUGIN_NAMESPACE,
            "preferences",
            self.plugin.preferences
        )

    def make_mapping_row(self, label_text: str, spin_value, entry_sizegroup=None):
        row = Gtk.ListBoxRow()
        upper_box = Gtk.Box(spacing=3)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, halign=Gtk.Align.END)
        label = Gtk.Label(label=label_text, margin_start=6)

        spin = Gtk.SpinButton()
        spin.set_hexpand(True)
        spin.set_adjustment(Gtk.Adjustment(upper=100, step_increment=1, page_increment=10))
        spin.set_numeric(True)
        spin.set_value(int(spin_value))
        if entry_sizegroup:
            entry_sizegroup.add_widget(box)

        button = Gtk.Button(icon_name="user-trash-symbolic")
        button.connect("clicked", self.remove_mapping)

        row.set_child(upper_box)
        upper_box.append(label)
        upper_box.append(box)
        box.append(spin)
        box.append(button)
        return row

    def load_mappings_listbox(self):
        self.load_preferences()

        # If there are any old children, remove them from the ListBox
        for child in list(self.mappings_listbox):
            self.mappings_listbox.remove(child)

        # Construct the listBoxRows
        for key, value in self.plugin.preferences['tag_mapping'].items():
            row = self.make_mapping_row(
                label_text=key, spin_value=value, entry_sizegroup=self.entry_sizegroup
            )
            self.mappings_listbox.append(row)

        self.add_row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_homogeneous(True)
        box_click_gesture = Gtk.GestureSingle()
        box_click_gesture.connect("begin", self.add_mapping_clicked)
        box.add_controller(box_click_gesture)

        add = Gtk.Image(icon_name="list-add-symbolic")
        box.append(add)

        self.add_row.set_child(box)
        self.mappings_listbox.append(self.add_row)

    def add_mapping_clicked(self, controller, sequence):
        self.new_mapping_dialog.set_transient_for(self)

        self.new_mapping_entry.set_text("")
        self.new_mapping_spinner.set_value(0)

        self.new_mapping_dialog.present()

    def remove_mapping(self, widget, event=None):
        self.mappings_listbox.remove(self.get_row_from_remove_mapping(widget))

    def get_row_from_remove_mapping(self, button):
        return button.get_parent().get_parent()

    def get_tag_value_from_mapping_row(self, row):
        label = list(row.get_child())[0]
        spin = list(list(row.get_child())[1])[0]
        return (label, spin)

    def load_general_listbox(self):
        self.load_ui_mode()
        self.load_target_task()

        for child in list(self.general_listbox):
            child.set_child(None)
            self.general_listbox.remove(child)

        target_row = Gtk.ListBoxRow()
        target_row.set_child(self.target_tasks)

        ui_row = Gtk.ListBoxRow()
        ui_row.set_child(self.ui_mode)

        self.general_listbox.append(target_row)
        self.general_listbox.append(ui_row)

    def load_target_task(self):
        self.load_preferences()
        self.target_spinbutton.set_value(self.plugin.preferences['goal'])

    def get_ui_mode_combo_value(self):
        value = self.ui_combobox.get_active_id()
        return value if value else 0

    def load_ui_mode(self):
        self.load_preferences()
        if self.plugin.preferences['ui_type'] == 'FULL':
            self.ui_combobox.set_active_id(str(0))
        elif self.plugin.preferences['ui_type'] == 'BUTTON':
            self.ui_combobox.set_active_id(str(1))
        else:
            self.ui_combobox.set_active_id(str(2))


class Gamify:
    PLUGIN_NAMESPACE = 'gamify'
    DEFAULT_ANALYTICS = {
        "last_task_date": date.today(),  # The date of the last task marked as done
        "last_task_number": 0,           # The number of tasks done today
        "streak": 0,                     # The number of days in which the goal was achieved
        "goal_achieved": False,          # achieved today's goal
        "score": 0
    }
    LEVELS = {
        100: _('Beginner'),
        1000: _('Novice'),
        2000: _('Professional'),
        4000: _('Expert'),
        9000: _('Master'),
        13000: _('Master II'),
        19000: _('Grand Master'),
        25000: _('Productivity Lord')
    }

    # INIT #####################################################################

    def __init__(self):
        self.configureable = True

        self.data = None
        self.preferences = None
        self.builder = Gtk.Builder.new_from_file(f'{PLUGIN_PATH}/gamify.ui')

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.browser = plugin_api.get_browser()

        # Don't "activate" for task editors
        if plugin_api.is_editor():
            return

        # Init the preference dialog
        try:
            self.pref_dialog = GamifyPreferences(self, self.plugin_api)
        except Exception:
            self.configureable = False
            log.debug('Cannot load preference dialog widget')

        # Load preferences and data
        self.analytics_load()
        self.pref_dialog.load_preferences()

        # Settings up the menu
        self.add_ui()

        self.update_date()
        self.update_streak()
        self.analytics_save()
        self.update_widget()

    def deactivate(self, plugin_api):
        self.pref_dialog.destroy()
        self.remove_ui()

    def is_configurable(self):
        return True

    # SAVE/LOAD DATA ##########################################################

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

    def on_status_changed(self, sender, task_id, old_status, status):
        if status == Task.STA_DONE:
            self.on_marked_as_done(task_id)
        elif status == Task.STA_ACTIVE and old_status == Task.STA_DONE:
            self.on_marked_as_not_done(task_id)

    def on_marked_as_done(self, task_id):
        log.debug('a task has been marked as done')
        self.analytics_load()
        self.pref_dialog.load_preferences()

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
        self.pref_dialog.load_preferences()

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
        task = self.plugin_api.ds.tasks.lookup[task_id]
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

        if self.headerbar:
            self.headerbar.pack_start(self.headerbar_button)

    def remove_headerbar_button(self):
        self.headerbar.remove(self.headerbar_button)

    def add_levelbar(self):
        self.quickadd_pane = self.plugin_api.get_quickadd_pane()
        self.levelbar = self.builder.get_object('goal-levelbar')
        self.quickadd_pane.set_orientation(Gtk.Orientation.VERTICAL)
        self.quickadd_pane.append(self.levelbar)

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
        text = ngettext("%d point", "%d points", self.get_score())
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
            headerbar_msg.set_markup(_("<i>Good Job!</i>\nYou have achieved your daily goal."))
        elif tasks_done >= 1:
            emoji = ["\U0001F600", "\U0001F60C", "\U0000270A"]
            headerbar_label.set_markup(random.choice(emoji))
            headerbar_msg.set_markup(_("Only a few tasks to go!"))
        else:
            emoji = ["\U0001F643", "\U0001F648", "\U0001F995", "\U0001F9A5"]
            headerbar_label.set_markup(random.choice(emoji))
            headerbar_msg.set_markup(
                _("<i>Get Down to Business!</i>\nYou haven't achieved any tasks today."))

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

        self.pref_dialog.load_preferences()
        self.pref_dialog.set_transient_for(manager_dialog)

        # Tag Mapping
        self.pref_dialog.load_mappings_listbox()

        self.pref_dialog.load_ui_mode()
        self.pref_dialog.load_target_task()

        self.pref_dialog.present()
