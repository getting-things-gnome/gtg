# -*- coding: utf-8 -*-
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
import dbus
from gi.repository import Gtk, GdkPixbuf
import os
import re
import time
import datetime

from GTG import _
from GTG.core.task import Task


class hamsterPlugin:
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
    BUFFER_TIME = 60  # secs
    PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
    IMG_START_PATH = "icons/hicolor/32x32/hamster-activity-start.png"
    IMG_STOP_PATH = "icons/hicolor/32x32/hamster-activity-stop.png"

    def __init__(self):
        # task editor widget
        self.vbox = None
        self.button = Gtk.ToolButton()
        self.other_stop_button = self.button

    def get_icon_widget(self, image_path):
        image_path = os.path.join(self.PLUGIN_PATH, image_path)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(image_path, 24, 24)

        # create the image and associate the pixbuf
        icon = Gtk.Image()
        icon.set_from_pixbuf(pixbuf)
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
            if (gtg_title in hamster_activities
                    or gtg_title.replace(",", "") in hamster_activities):
                    category = "%s" % hamster_activities[gtg_title]

        if (self.preferences['category'] == 'tag' or
           (self.preferences['category'] == 'auto_tag' and not category)):
            # See if any of the tags match existing categories
            categories = dict([(str(x[1]).lower(), str(x[1]))
                               for x in self.hamster.GetCategories()])
            lower_gtg_tags = set([x.lower() for x in gtg_tags])
            intersection = set(categories.keys()).intersection(lower_gtg_tags)
            if len(intersection) > 0:
                category = "%s" % categories[intersection.pop()]
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
        # `[-]start_time[-end_time] activity@category, description #tag1 #tag2`
        fact = activity
        if category:
            fact += "@%s" % category
        fact += ",%s%s" % (description, tag_str)
        start_time = timegm(datetime.datetime.now().timetuple())
        hamster_id = self.hamster.AddFact(fact, start_time, 0, False)

        ids = self.get_hamster_ids(task)
        ids.append(str(hamster_id))
        self.set_hamster_ids(task, ids)

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

    def is_task_active(self, task):
        records = self.get_records(task)
        ids = [record[0] for record in records]
        return self.get_active_id() in ids

    def stop_task(self, task):
        if self.is_task_active(task):
            now = timegm(datetime.datetime.now().timetuple())
            # Hamster deletes an activity if it's finish time is set earlier
            # than current time. Hence, we are setting finish time
            # some buffer secs from now
            self.hamster.StopTracking(now + self.BUFFER_TIME)

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

    def tasks_deleted(self, widget, deleted_tasks):
        '''
        If a task is being tracked, and it is deleted in GTG,
        this method stops tracking it
        '''
        for task in deleted_tasks:
            self.stop_task(task)

    def task_status_changed(self, widget, task, new_status):
        '''
        If a task is being tracked and it's status is changed from
        Active -> Done/Dismissed, this method stops tracking it
        '''

        def recursive_list_tasks(task_list, root):
            '''
            Populate a list of all the subtasks and their children, recursively
            '''
            if root not in task_list:
                task_list.append(root)
                for i in root.get_subtasks():
                    recursive_list_tasks(task_list, i)

        if new_status in [Task.STA_DISMISSED, Task.STA_DONE]:
            all_my_children = []
            recursive_list_tasks(all_my_children, task)
            for task in all_my_children:
                self.stop_task(task)

    # Plugin api methods ###
    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.hamster = dbus.SessionBus().get_object('org.gnome.Hamster',
                                                    '/org/gnome/Hamster')

        # add menu item
        if plugin_api.is_browser():
            self.menu_item = Gtk.MenuItem(self.START_ACTIVITY_LABEL)
            self.menu_item.show_all()
            self.menu_item.connect('activate', self.browser_cb, plugin_api)
            self.menu_item.set_sensitive(False)
            plugin_api.add_menu_item(self.menu_item)
            # and button
            self.button.set_label(self.START_ACTIVITY_LABEL)
            start_icon_widget = self.get_icon_widget(self.IMG_START_PATH)
            self.button.set_icon_widget(start_icon_widget)
            self.button.set_tooltip_text(self.TOOLTIP_TEXT_START_ACTIVITY)
            self.button.set_sensitive(False)
            self.button.connect('clicked', self.browser_cb, plugin_api)
            self.button.show()
            plugin_api.add_toolbar_item(self.button)
            plugin_api.set_active_selection_changed_callback(
                self.selection_changed)
        plugin_api.get_view_manager().connect('tasks-deleted',
                                              self.tasks_deleted)
        plugin_api.get_view_manager().connect('task-status-changed',
                                              self.task_status_changed)
        # set up preferences
        self.preference_dialog_init()
        self.preferences_load()

    def onTaskOpened(self, plugin_api):
        # get the opened task
        task = plugin_api.get_ui().get_task()

        if task.get_status() == Task.STA_ACTIVE:
            # add button
            self.taskbutton = Gtk.ToolButton()
            self.decide_button_mode(self.taskbutton, task)
            self.taskbutton.connect('clicked', self.task_cb, plugin_api)
            self.taskbutton.show()
            plugin_api.add_toolbar_item(self.taskbutton)

        records = self.get_records(task)

        if len(records):
            # add section to bottom of window
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            inner_grid = Gtk.Grid()
            if len(records) > 8:
                s = Gtk.ScrolledWindow()
                s.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                v = Gtk.Viewport()
                v.add(inner_grid)
                s.add(v)
                v.set_shadow_type(Gtk.ShadowType.NONE)
                s.set_size_request(-1, 150)
            else:
                s = inner_grid

            outer_grid = Gtk.Grid()
            vbox.pack_start(s, True, True, 0)
            vbox.pack_start(outer_grid, True, True, 0)
            vbox.pack_end(Gtk.Separator(), True, True, 0)

            total = 0

            def add(w, a, b, offset, active=False):
                if active:
                    a = "<span color='red'>%s</span>" % a
                    b = "<span color='red'>%s</span>" % b

                dateLabel = Gtk.Label(label=a)
                dateLabel.set_use_markup(True)
                dateLabel.set_alignment(xalign=0.0, yalign=0.5)
                dateLabel.set_size_request(200, -1)
                w.attach(dateLabel, 0, offset, 1, 1)

                durLabel = Gtk.Label(label=b)
                durLabel.set_use_markup(True)
                durLabel.set_alignment(xalign=0.0, yalign=0.5)
                w.attach(durLabel, 1, offset, 1, 1)

            active_id = self.get_active_id()
            for offset, i in enumerate(records):
                t = calc_duration(i)
                total += t
                add(inner_grid, format_date(i), format_duration(t),
                    offset, i[0] == active_id)

            add(outer_grid, "<big><b>Total</b></big>",
                "<big><b>%s</b></big>" % format_duration(total), 1)

            self.vbox = plugin_api.add_widget_to_taskeditor(vbox)

    def deactivate(self, plugin_api):
        if plugin_api.is_browser():
            plugin_api.remove_menu_item(self.menu_item)
            plugin_api.remove_toolbar_item(self.button)
        else:
            plugin_api.remove_toolbar_item(self.taskbutton)
            plugin_api.remove_widget_from_taskeditor(self.vbox)

    def browser_cb(self, widget, plugin_api):
        task_id = plugin_api.get_browser().get_selected_task()
        task = plugin_api.get_requester().get_task(task_id)
        self.decide_start_or_stop_activity(task, widget)

    def task_cb(self, widget, plugin_api):
        task = plugin_api.get_ui().get_task()
        self.decide_start_or_stop_activity(task, widget)

    def decide_start_or_stop_activity(self, task, widget):
        if self.is_task_active(task):
            self.change_button_to_start_activity(widget)
            self.stop_task(task)
        elif task.get_status() == Task.STA_ACTIVE:
            self.change_button_to_stop_activity(widget)
            self.sendTask(task)

    def selection_changed(self, selection):
        if selection.count_selected_rows() == 1:
            self.button.set_sensitive(True)
            self.menu_item.set_sensitive(True)
            task_id = self.plugin_api.get_browser().get_selected_task()
            task = self.plugin_api.get_requester().get_task(task_id)
            self.decide_button_mode(self.button, task)
        else:
            self.change_button_to_start_activity(self.button)
            self.button.set_sensitive(False)
            self.menu_item.set_sensitive(False)

    def decide_button_mode(self, button, task):
        if self.is_task_active(task):
            self.change_button_to_stop_activity(button)
        else:
            self.change_button_to_start_activity(button)

    def change_button_to_start_activity(self, button):
        self.menu_item.set_label(self.START_ACTIVITY_LABEL)
        self.button.set_icon_widget(self.get_icon_widget(self.IMG_START_PATH))
        self.button.set_tooltip_text(self.TOOLTIP_TEXT_START_ACTIVITY)

    def change_button_to_stop_activity(self, button):
        self.menu_item.set_label(self.STOP_ACTIVITY_LABEL)
        self.button.set_icon_widget(self.get_icon_widget(self.IMG_STOP_PATH))
        self.button.set_tooltip_text(self.TOOLTIP_TEXT_STOP_ACTIVITY)

    # Preference Handling ###
    def is_configurable(self):
        """A configurable plugin should have this method and return True"""
        return True

    def configure_dialog(self, manager_dialog):
        self.preferences_load()
        self.preferences_dialog.set_transient_for(manager_dialog)

        def pref_to_dialog(pref):
            self.builder.get_object(pref + "_" + self.preferences[pref]) \
                .set_active(True)

        pref_to_dialog("activity")
        pref_to_dialog("category")
        pref_to_dialog("description")
        pref_to_dialog("tags")

        self.preferences_dialog.show_all()

    def on_preferences_close(self, widget=None, data=None):

        def dialog_to_pref(pref, vals):
            for val in vals:
                if self.builder.get_object(pref + "_" + val).get_active():
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
    '''
    returns minutes
    '''
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
        formatted_duration += "%dh" % (hours)
    elif hours == 0:
        # duration less than hour
        formatted_duration += "%dmin" % (minutes % 60.0)
    else:
        # x hours, y minutes
        formatted_duration += "%dh %dmin" % (hours, minutes % 60)

    return formatted_duration
