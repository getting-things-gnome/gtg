# -----------------------------------------------------------------------------
# Hamster Task Tracker Plugin for Getting Things GNOME!
# Copyright (c) 2009 Kevin Mehall
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

import logging
import datetime
import os
import time
from calendar import timegm
from gettext import gettext as _

import dbus
from gi.repository import Gtk, Gio

from GTG.core.tasks import Task
from GTG.plugins.hamster.helper import FactBuilder

log = logging.getLogger(__name__)

class HamsterPlugin():
    PLUGIN_NAMESPACE = 'hamster-plugin'
    DEFAULT_PREFERENCES = {
        "activity": "title",
        "category": "auto",
        "description": "contents",
        "tags": "existing",
    }
    TOOLTIP_TEXT_START_ACTIVITY = _("Start a new activity in Hamster Time"
                                    " Tracker based on the selected task")
    TOOLTIP_TEXT_STOP_ACTIVITY = _("Stop tracking the current activity in"
                                   " Hamster Time Tracker corresponding"
                                   " to the selected task")
    START_ACTIVITY_LABEL = _("Start task in Hamster")
    STOP_ACTIVITY_LABEL = _("Stop Hamster Activity")
    EDIT_ACTIVITY_ACTION = "edit_task"
    # having dots in prefix causes CRASH
    EDIT_ACTIVITY_ACTION_PREF = "app_editor_" + PLUGIN_NAMESPACE
    EDIT_ACTIVITY_ACTION_FULL = ".".join(
        [EDIT_ACTIVITY_ACTION_PREF, EDIT_ACTIVITY_ACTION]
    )
    BUFFER_TIME = 60  # secs
    PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))

    def __init__(self):
        # task editor widget
        self.vbox_id = None
        self.button = Gtk.Button()
        self.task_menu_items = {}

        self.tree = None
        self.liblarch_callbacks = []
        self.tracked_task_id = None

    # Interaction with Hamster ###
    def send_task(self, task):
        """Send a gtg task to hamster-applet"""
        if task is None:
            return
        fact = FactBuilder(self.hamster, self.preferences).build(task)
        start_time = timegm(datetime.datetime.now().timetuple())
        hamster_id = self.hamster.AddFact(fact, start_time, 0, False)

        ids = self.get_hamster_ids(task)
        ids.append(str(hamster_id))
        self.set_hamster_ids(task, ids)
        self.tracked_task_id = task.get_id()

    def get_records(self, task):
        """Get a list of hamster facts for a task"""
        ids = self.get_hamster_ids(task)
        records = []
        modified = False
        valid_ids = []
        for i in ids:
            try:
                fact = self.hamster.GetFact(i)
                if fact and i not in valid_ids:
                    records.append(fact)
                    valid_ids.append(i)
                    continue
            except dbus.DBusException:
                pass
            modified = True
        if modified:
            self.set_hamster_ids(task, valid_ids)
        return records

    def get_active_id(self):
        """ returns active hamster task id, or None if hamster don't have active task """
        todays_facts = self.hamster.GetTodaysFacts()
        ID_INDEX = 0
        END_TIME_INDEX = 2
        if todays_facts and todays_facts[-1][END_TIME_INDEX] == 0:
            # todays_facts is a list. todays_facts[-1] gives the latest fact
            # if todays_facts[-1][-1] is the start time, and
            # todays_facts[-1][-2] is the end time of the fact (value 0 means
            # it is still being tracked upon which we return id of the fact)
            return todays_facts[-1][ID_INDEX]
        else:
            return None

    def is_task_active(self, task_id):
        return self.tracked_task_id == task_id

    def stop_task(self, task_id):
        if self.is_task_active(task_id):
            now = timegm(datetime.datetime.now().timetuple())
            # Hamster deletes an activity if it's finish time is set earlier
            # than current time. Hence, we are setting finish time
            # some buffer secs from now
            self.hamster.StopTracking(now + self.BUFFER_TIME)
            self.tracked_task_id = None

    # Datastore ###
    def get_hamster_ids(self, task):
        ids = task.get_attribute("id-list", namespace=self.PLUGIN_NAMESPACE)
        if not ids:
            return []
        else:
            return ids.split(',')

    def set_hamster_ids(self, task, ids):
        task.set_attribute("id-list", ",".join(ids),
                           namespace=self.PLUGIN_NAMESPACE)

    def on_task_deleted(self, store, task):
        """ Stop tracking a deleted task if it is being tracked """
        self.stop_task(task.id)

    def on_task_modified(self, store, task):
        """ Stop task if it is tracked and it is Done/Dismissed """
        if task.get_status() in (Task.STA_DISMISSED, Task.STA_DONE):
            self.stop_task(task_id)

    # Plugin api methods ###
    def activate(self, plugin_api):
        self.plugin_api = plugin_api

        try:
            self.hamster = dbus.SessionBus().get_object('org.gnome.Hamster',
                                                        '/org/gnome/Hamster')
        except dbus.exceptions.DBusException:
            log.error('Hamster plugin failed to activate. Is Hamster installed?')
            return

        # add button
        if plugin_api.is_browser():
            self.button.set_icon_name('alarm-symbolic')
            self.button.set_tooltip_text(self.TOOLTIP_TEXT_START_ACTIVITY)
            self.button.set_sensitive(False)
            self.button.connect('clicked', self.browser_cb, plugin_api)
            self.button.show()
            header_bar = plugin_api.get_header()
            header_bar.pack_end(self.button)
            plugin_api.set_active_selection_changed_callback(self.selection_changed)

        # self.subscribe_task_updates([
        #     ("node-modified-inview", self.on_task_modified),
        #     ("node-deleted-inview", self.on_task_deleted),
        # ])

        plugin_api.ds.tasks.connect('task-filterably-changed', self.on_task_modified)
        plugin_api.ds.tasks.connect('removed', self.on_task_deleted)

        # set up preferences
        self.preference_dialog_init()
        self.preferences_load()

    def subscribe_task_updates(self, signal_callbacks):
        """ Subscribe to updates about tasks """
        self.tree = self.plugin_api.get_requester().get_tasks_tree()
        self.liblarch_callbacks = []
        for event, callback in signal_callbacks:
            callback_id = self.tree.register_cllbck(event, callback)
            self.liblarch_callbacks.append((callback_id, event))

    def onTaskOpened(self, plugin_api):
        task = plugin_api.get_ui().get_task()

        if task.get_status() != Task.STA_ACTIVE:
            return

        group = Gio.SimpleActionGroup()
        track_task_action = Gio.SimpleAction.new(self.EDIT_ACTIVITY_ACTION, None)
        track_task_action.connect('activate', self.task_cb, plugin_api)
        group.add_action(track_task_action)
        plugin_api.get_ui().insert_action_group(self.EDIT_ACTIVITY_ACTION_PREF, group)

        task_menu_item = Gio.MenuItem.new(
            (self.STOP_ACTIVITY_LABEL if self.is_task_active(task.get_id())
             else self.START_ACTIVITY_LABEL),
            self.EDIT_ACTIVITY_ACTION_FULL
        )
        self.task_menu_items.update({task.get_id(): task_menu_item})
        if self.is_task_active(task.get_id()):
            task_menu_item.props.text = self.STOP_ACTIVITY_LABEL
        else:
            task_menu_item.props.text = self.START_ACTIVITY_LABEL
        task_menu_item.show_all()
        task_menu_item.connect('clicked', self.task_cb, plugin_api)
        plugin_api.add_menu_item(task_menu_item)

        records = self.get_records(task)
        self.render_record_list(records, plugin_api)

    def onTaskClosed(self, plugin_api):
        task = plugin_api.get_ui().get_task()
        plugin_api.get_ui().insert_action_group(self.EDIT_ACTIVITY_ACTION_PREF, None)
        if task.get_id() in self.task_menu_items:
            del self.task_menu_items[task.get_id()]
        self.check_task_selected()

    def render_record_list(self, records, plugin_api):
        """ show a table with previous records of facts in the current task view. """
        if records:
            records.reverse()
            # add section to bottom of window
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            inner_grid = Gtk.Grid()
            if len(records) > 4:
                inner_container = Gtk.ScrolledWindow()
                inner_container.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                viewport = Gtk.Viewport()
                viewport.add(inner_grid)
                inner_container.add(viewport)
                viewport.set_shadow_type(Gtk.ShadowType.NONE)
                inner_container.set_size_request(-1, 80)
            else:
                inner_container = inner_grid

            header_grid = Gtk.Grid()
            outer_grid = Gtk.Grid()
            vbox.append(header_grid)
            vbox.append(Gtk.Separator())
            vbox.append(inner_container)
            vbox.append(Gtk.Separator())
            vbox.append(outer_grid)

            total = 0

            def add(row, content_1, content_2, top_offset, active=False):
                """
                Add a row with two columns at the bottom of task view.
                here is used to display total of time or fact records.
                """
                if not active:
                    content_1 = f"<span color='#444444'>{content_1}</span>"
                    content_2 = f"<span color='#444444'>{content_2}</span>"

                column_1 = Gtk.Label(label=content_1)
                column_1.set_xalign(0.0)
                column_1.set_margin_start(18)
                column_1.set_margin_end(18)
                column_1.set_margin_top(6)
                column_1.set_margin_bottom(6)
                column_1.set_use_markup(True)
                row.attach(column_1, 0, top_offset, 1, 1)

                column_2 = Gtk.Label(label=content_2)
                column_2.set_hexpand(True)
                column_2.set_use_markup(True)
                column_2.set_xalign(1.0)
                column_2.set_margin_end(18)
                column_2.set_margin_top(6)
                column_2.set_margin_bottom(6)
                row.attach(column_2, 1, top_offset, 4, 1)

            add(header_grid, "<b>Hamster Time Tracker Records:</b>", "", 0)

            active_id = self.get_active_id()
            for offset, fact in enumerate(records):
                duration = calc_duration(fact)
                total += duration
                add(inner_grid, format_date(fact), format_duration(duration),
                    offset, fact[0] == active_id)

            add(outer_grid, "<b>Total</b>", f"<b>{format_duration(total)}</b>", 1)
            if isinstance(inner_container, Gtk.ScrolledWindow):
                adj = inner_container.get_vadjustment()
                adj.set_value(adj.get_upper() - adj.get_page_size())

            self.vbox_id = plugin_api.add_widget_to_taskeditor(vbox)

    def deactivate(self, plugin_api):
        if plugin_api.is_browser():
            # plugin_api.remove_toolbar_item(self.button)
            header_bar = plugin_api.get_header()
            header_bar.remove(self.button)
        else:
            for _, menu_button in self.task_menu_items.items():
                plugin_api.remove_menu_item(menu_button)
            plugin_api.remove_widget_from_taskeditor(self.vbox_id)

        # Deactivate LibLarch callbacks
        for callback_id, event in self.liblarch_callbacks:
            self.tree.deregister_cllbck(event, callback_id)
        self.liblarch_callbacks = []

    def browser_cb(self, widget, plugin_api):
        task_id = plugin_api.browser.get_pane().get_selection()[0]
        task = plugin_api.ds.tasks.lookup[task_id]
        self.decide_start_or_stop_activity(task, widget)

    def task_cb(self, action, gparam, plugin_api):
        task = plugin_api.get_ui().get_task()
        self.decide_start_or_stop_activity(task, plugin_api)

    def decide_start_or_stop_activity(self, task, plugin_api):
        if self.is_task_active(task.get_id()):
            self.change_button_to_start_activity(self.button)
            self.change_task_menu_to_start_activity(task.get_id(), plugin_api)
            self.stop_task(task.get_id())
        elif task.get_status() == Task.STA_ACTIVE:
            self.change_button_to_stop_activity(self.button)
            self.change_task_menu_to_stop_activity(task.get_id(), plugin_api)
            self.send_task(task)

    def selection_changed(self, selection):
        if selection.count_selected_rows() == 1:
            self.button.set_sensitive(True)
            self.check_task_selected()
        else:
            self.change_button_to_start_activity(self.button)
            self.button.set_sensitive(False)

    def check_task_selected(self):
        task_id = self.plugin_api.get_browser().get_selected_task()
        if not task_id:
            return
        task = self.plugin_api.ds.tasks.lookup[task_id]
        self.decide_button_mode(self.button, task)

    def decide_button_mode(self, button, task):
        if self.is_task_active(task.get_id()):
            self.change_button_to_stop_activity(button)
        else:
            self.change_button_to_start_activity(button)

    def change_button_to_start_activity(self, button):
        button.set_tooltip_text(self.TOOLTIP_TEXT_START_ACTIVITY)
        button.set_icon_name('alarm-symbolic')

    def change_button_to_stop_activity(self, button):
        button.set_tooltip_text(self.TOOLTIP_TEXT_STOP_ACTIVITY)
        button.set_icon_name('process-stop-symbolic')

    def change_task_menu_to_start_activity(self, task_id, plugin_api):
        if task_id in self.task_menu_items:
            plugin_api.remove_menu_item(self.task_menu_items[task_id][0])
            replacement_item = Gio.MenuItem.new(
                self.START_ACTIVITY_LABEL, self.EDIT_ACTIVITY_ACTION_FULL
            )
            self.task_menu_items[task_id] = replacement_item
            plugin_api.add_menu_item(replacement_item)

    def change_task_menu_to_stop_activity(self, task_id, plugin_api):
        if task_id in self.task_menu_items:
            plugin_api.remove_menu_item(self.task_menu_items[task_id][0])
            replacement_item = Gio.MenuItem.new(
                self.STOP_ACTIVITY_LABEL, self.EDIT_ACTIVITY_ACTION_FULL
            )
            self.task_menu_items[task_id] = replacement_item
            plugin_api.add_menu_item(replacement_item)

    # Preference Handling ###
    def is_configurable(self):
        """A configurable plugin should have this method and return True"""
        return True

    def configure_dialog(self, manager_dialog):
        self.preferences_load()
        self.preferences_dialog.set_transient_for(manager_dialog)

        def pref_to_dialog(pref):
            combo = self.builder.get_object(pref)
            combo.set_active_id(self.preferences[pref])

        pref_to_dialog("activity")
        pref_to_dialog("category")
        pref_to_dialog("description")
        pref_to_dialog("tags")

        self.preferences_dialog.present()

    def on_preferences_close(self, widget=None, data=None):

        def dialog_to_pref(pref, values):
            for val in values:
                combo = self.builder.get_object(pref)
                if combo.get_active_id() == val:
                    self.preferences[pref] = val
                    break

        dialog_to_pref("activity", ["tag", "title"])
        dialog_to_pref("category", ["auto", "tag", "auto_tag"])
        dialog_to_pref("description", ["title", "contents", "none"])
        dialog_to_pref("tags", ["all", "existing", "none"])

        self.preferences_store()
        self.preferences_dialog.hide()
        return True

    def preferences_load(self):
        self.preferences = self.plugin_api.load_configuration_object(
            self.PLUGIN_NAMESPACE, "preferences",
            default_values=self.DEFAULT_PREFERENCES)

    def preferences_store(self):
        self.plugin_api.save_configuration_object(self.PLUGIN_NAMESPACE,
                                                  "preferences",
                                                  self.preferences)

    def preference_dialog_init(self):
        self.builder = Gtk.Builder()
        path = f"{self.PLUGIN_PATH}/prefs.ui"
        self.builder.add_from_file(path)
        self.preferences_dialog = self.builder.get_object("dialog1")
        self.preferences_dialog.connect("close-request", self.on_preferences_close)


def format_date(task):
    start_time = time.gmtime(task[1])
    return time.strftime("<b>%A, %b %e</b> %l:%M %p", start_time)


def calc_duration(fact):
    """
    returns minutes
    """
    start = fact[1]
    end = fact[2]
    if end == 0:
        end = timegm(time.localtime())
    return (end - start) / 60


def format_duration(minutes):
    # Based on hamster-applet code -  hamster/stuff.py
    """formats duration in a human readable format."""

    if not minutes:
        return "0min"

    hours = minutes / 60
    minutes = minutes % 60
    formatted_duration = ""

    if minutes % 60 == 0:
        # duration in round hours
        formatted_duration += f"{hours:d}h"
    elif hours == 0:
        # duration less than hour
        formatted_duration += "%dmin" % (minutes % 60.0)
    else:
        # x hours, y minutes
        formatted_duration += "%dh %dmin" % (hours, minutes % 60)

    return formatted_duration
