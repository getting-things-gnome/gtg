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

from calendar import timegm
import datetime
import dbus
import os
import re
import time

from gi.repository import Gtk, GdkPixbuf

from GTG.core.task import Task
from gettext import gettext as _
from GTG.core.logger import log


class HamsterPlugin():
    PLUGIN_NAMESPACE = 'hamster-plugin'
    DEFAULT_PREFERENCES = {
        "activity": "title",
        "category": "auto",
        "description": "contents",
        "tags": "existing",
    }
    TOOLTIP_TEXT_START_ACTIVITY = _("Start a new activity in Hamster Time" +
                                    " Tracker based on the selected task")
    TOOLTIP_TEXT_STOP_ACTIVITY = _("Stop tracking the current activity in" +
                                   " Hamster Time Tracker corresponding" +
                                   " to the selected task")
    START_ACTIVITY_LABEL = _("Start task in Hamster")
    STOP_ACTIVITY_LABEL = _("Stop Hamster Activity")
    START_ACTIVITY_BUTTON_LABEL = _("Start Tracking")
    STOP_ACTIVITY_BUTTON_LABEL = _("Stop Tracking")
    BUFFER_TIME = 60  # secs
    PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))

    def __init__(self):
        # task editor widget
        self.vbox = None
        self.button = Gtk.ToggleButton()
        self.other_stop_button = self.button

        self.tree = None
        self.liblarch_callbacks = []
        self.tracked_task_id = None

    def get_icon_image(self, image_name):
        icon = Gtk.Image()
        icon.set_from_icon_name(image_name, Gtk.IconSize.BUTTON)
        icon.show()
        return icon

    # Interaction with Hamster ###
    def sendTask(self, task):
        """Send a gtg task to hamster-applet"""
        if task is None:
            return
        gtg_title = task.get_title()
        gtg_tags = [t.lstrip('@').lower() for t in task.get_tags_name()]

        activity = "Other"
        if self.preferences['activity'] == 'tag':
            hamster_activities = set([str(x[0]).lower()
                                      for x in self.hamster.GetActivities('')])
            activity_candidates = hamster_activities.intersection(
                set(gtg_tags))
            if len(activity_candidates) >= 1:
                activity = list(activity_candidates)[0]
        elif self.preferences['activity'] == 'title':
            activity = gtg_title
        # hamster can't handle ',' or '@' in activity name
        activity = activity.replace(',', '')
        activity = re.sub('\ +@.*', '', activity)

        category = ""
        if self.preferences['category'] == 'auto_tag':
            hamster_activities = dict([(str(x[0]), x[1])
                                       for x in
                                       self.hamster.GetActivities('')])
            if (gtg_title in hamster_activities or gtg_title.replace(",", "") in hamster_activities):
                category = f"{hamster_activities[gtg_title]}"

        if (self.preferences['category'] == 'tag' or
           (self.preferences['category'] == 'auto_tag' and not category)):
            # See if any of the tags match existing categories
            categories = dict([(str(x[1]).lower(), str(x[1]))
                               for x in self.hamster.GetCategories()])
            lower_gtg_tags = set([x.lower() for x in gtg_tags])
            intersection = set(categories.keys()).intersection(lower_gtg_tags)
            if len(intersection) > 0:
                category = f"{categories[intersection.pop()]}"
            elif len(gtg_tags) > 0:
                # Force category if not found
                category = gtg_tags[0]

        description = ""
        if self.preferences['description'] == 'title':
            description = gtg_title
        elif self.preferences['description'] == 'contents':
            description = task.get_excerpt(strip_tags=True,
                                           strip_subtasks=True)

        tag_candidates = []
        try:
            if self.preferences['tags'] == 'existing':
                hamster_tags = set([str(x[1]) for x in
                                    self.hamster.GetTags(False)])
                tag_candidates = list(hamster_tags.intersection(set(gtg_tags)))
            elif self.preferences['tags'] == 'all':
                tag_candidates = gtg_tags
        except dbus.exceptions.DBusException:
            # old hamster version, doesn't support tags
            pass
        tag_str = "".join([" #" + x for x in tag_candidates])

        # Format of first argument of AddFact -
        # `[-]start_time[-end_time] activity@category,, description #tag1 #tag2`
        fact = activity
        if category:
            fact += f"@{category}"
        fact += f",, {description}{tag_str}"
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
                d = self.hamster.GetFact(i)
                if d and i not in valid_ids:
                    records.append(d)
                    valid_ids.append(i)
                    continue
            except dbus.DBusException:
                pass
            modified = True
            print("Removing invalid fact", i)
        if modified:
            self.set_hamster_ids(task, valid_ids)
        return records

    def get_active_id(self):
        todays_facts = self.hamster.GetTodaysFacts()
        if todays_facts and todays_facts[-1][2] == 0:
            # todays_facts is a list. todays_facts[-1] gives the latest fact
            # if todays_facts[-1][-1] is the start time, and
            # todays_facts[-1][-2] is the end time of the fact (value 0 means
            # it is still being tracked upon which we return id of the fact)
            return todays_facts[-1][0]
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
        a = task.get_attribute("id-list", namespace=self.PLUGIN_NAMESPACE)
        if not a:
            return []
        else:
            return a.split(',')

    def set_hamster_ids(self, task, ids):
        task.set_attribute("id-list", ",".join(ids),
                           namespace=self.PLUGIN_NAMESPACE)

    def on_task_deleted(self, task_id, path):
        """ Stop tracking a deleted task if it is being tracked """
        log.info('Hamster: task deleted %s', task_id)
        self.stop_task(task_id)

    def on_task_modified(self, task_id, path):
        """ Stop task if it is tracked and it is Done/Dismissed """
        log.debug('Hamster: task modified %s', task_id)
        task = self.plugin_api.get_requester().get_task(task_id)
        if not task:
            return
        if task.get_status() in (Task.STA_DISMISSED, Task.STA_DONE):
            self.stop_task(task_id)

    # Plugin api methods ###
    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.hamster = dbus.SessionBus().get_object('org.gnome.Hamster',
                                                    '/org/gnome/Hamster')

        # add button
        if plugin_api.is_browser():
            self.button.set_image(self.get_icon_image('alarm-symbolic'))
            self.button.set_tooltip_text(self.TOOLTIP_TEXT_START_ACTIVITY)
            self.button.set_sensitive(False)
            self.button.connect('clicked', self.browser_cb, plugin_api)
            self.button.show()
            header_bar = plugin_api.get_gtk_builder().get_object('browser_headerbar')
            header_bar.pack_end(self.button)
            plugin_api.set_active_selection_changed_callback(self.selection_changed)

        self.subscribe_task_updates([
            ("node-modified-inview", self.on_task_modified),
            ("node-deleted-inview", self.on_task_deleted),
        ])

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
        # get the opened task
        task = plugin_api.get_ui().get_task()

        if task.get_status() != Task.STA_ACTIVE:
            return

        # add button
        self.taskbutton = Gtk.Button()
        self.decide_button_mode(self.taskbutton, task)
        self.taskbutton.connect('clicked', self.task_cb, plugin_api)
        self.taskbutton.show()
        plugin_api.add_widget_to_taskeditor(self.taskbutton)

        records = self.get_records(task)
        self.render_record_list(records, plugin_api)

    def get_total_duration(self, records):
        total = 0
        for fact in records:
            total += calc_duration(fact)
        return total

    def render_record_list(self, records, plugin_api):
        if len(records):
            records.reverse()
            # add section to bottom of window
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            inner_grid = Gtk.Grid()
            if len(records) > 4:
                inner_container = Gtk.ScrolledWindow()
                inner_container.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                v = Gtk.Viewport()
                v.add(inner_grid)
                inner_container.add(v)
                v.set_shadow_type(Gtk.ShadowType.NONE)
                inner_container.set_size_request(-1, 80)
            else:
                inner_container = inner_grid

            outer_grid = Gtk.Grid()
            vbox.pack_start(inner_container, True, True, 4)
            vbox.pack_start(Gtk.Separator(), True, True, 0)
            vbox.pack_start(outer_grid, True, True, 4)

            total = 0

            def add(row, content_1, content_2, top_offset, active=False):
                if not active:
                    content_1 = f"<span color='#444444'>{content_1}</span>"
                    content_2 = f"<span color='#444444'>{content_2}</span>"

                column_1 = Gtk.Label(label=content_1)
                column_1.set_margin_start(18)
                column_1.set_margin_end(18)
                column_1.set_margin_top(6)
                column_1.set_margin_bottom(6)
                column_1.set_use_markup(True)
                column_1.set_alignment(xalign=Gtk.Align.START,
                                        yalign=Gtk.Align.CENTER)
                row.attach(column_1, 0, top_offset, 1, 1)

                column_2 = Gtk.Label(label=content_2)
                column_2.set_use_markup(True)
                column_2.set_margin_end(18)
                column_2.set_margin_top(6)
                column_2.set_margin_bottom(6)
                column_2.set_alignment(xalign=Gtk.Align.END,
                                       yalign=Gtk.Align.CENTER)
                row.attach(column_2, 1, top_offset, 4, 1)

            active_id = self.get_active_id()
            for offset, fact in enumerate(records):
                duration = calc_duration(fact)
                total += duration
                add(inner_grid,format_date(fact), format_duration(duration), offset, fact[0] == active_id)

            add(outer_grid, "<b>Total</b>", f"<b>{format_duration(total)}</b>", 1)
            if isinstance(inner_container, Gtk.ScrolledWindow):
                adj = inner_container.get_vadjustment()
                adj.set_value(adj.get_upper() - adj.get_page_size())

            self.vbox = plugin_api.add_widget_to_taskeditor(vbox)

    def deactivate(self, plugin_api):
        if plugin_api.is_browser():
            plugin_api.remove_toolbar_item(self.button)
        else:
            plugin_api.remove_toolbar_item(self.taskbutton)
            plugin_api.remove_widget_from_taskeditor(self.vbox)

        # Deactivate LibLarch callbacks
        for callback_id, event in self.liblarch_callbacks:
            self.tree.deregister_cllbck(event, callback_id)
        self.liblarch_callbacks = []

    def browser_cb(self, widget, plugin_api):
        task_id = plugin_api.get_browser().get_selected_task()
        task = plugin_api.get_requester().get_task(task_id)
        self.decide_start_or_stop_activity(task, widget)

    def task_cb(self, widget, plugin_api):
        task = plugin_api.get_ui().get_task()
        self.decide_start_or_stop_activity(task, widget)

    def decide_start_or_stop_activity(self, task, widget):
        if self.is_task_active(task.get_id()):
            self.change_button_to_start_activity(widget)
            self.stop_task(task.get_id())
        elif task.get_status() == Task.STA_ACTIVE:
            self.change_button_to_stop_activity(widget)
            self.sendTask(task)

    def selection_changed(self, selection):
        if selection.count_selected_rows() == 1:
            self.button.set_sensitive(True)
            task_id = self.plugin_api.get_browser().get_selected_task()
            task = self.plugin_api.get_requester().get_task(task_id)
            self.decide_button_mode(self.button, task)
        else:
            self.change_button_to_start_activity(self.button)
            self.button.set_sensitive(False)

    def decide_button_mode(self, button, task):
        if self.is_task_active(task.get_id()):
            self.change_button_to_stop_activity(button)
        else:
            self.change_button_to_start_activity(button)

    def change_button_to_start_activity(self, button):
        button.set_tooltip_text(self.TOOLTIP_TEXT_START_ACTIVITY)
        button.set_image(self.get_icon_image('alarm-symbolic'))

    def change_button_to_stop_activity(self, button):
        button.set_tooltip_text(self.TOOLTIP_TEXT_STOP_ACTIVITY)
        button.set_image(self.get_icon_image('process-stop-symbolic'))

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

        self.preferences_dialog.show_all()

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
        path = "%s/prefs.ui" % os.path.dirname(os.path.abspath(__file__))
        self.builder.add_from_file(path)
        self.preferences_dialog = self.builder.get_object("dialog1")
        SIGNAL_CONNECTIONS_DIC = {
            "prefs_close": self.on_preferences_close,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)


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