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
import gtk
import os
import re
import time

from GTG import _


class hamsterPlugin:
    PLUGIN_NAMESPACE = 'hamster-plugin'
    DEFAULT_PREFERENCES = {
        "activity": "tag",
        "category": "auto",
        "description": "title",
        "tags": "existing",
    }
    TOOLTIP_TEXT = _("Start a new activity in Hamster Time Tracker " +
                     "based on the selected task")

    def __init__(self):
        # task editor widget
        self.vbox = None
        self.button = gtk.ToolButton()

    #### Interaction with Hamster
    def sendTask(self, task):
        """Send a gtg task to hamster-applet"""
        if task is None:
            return
        gtg_title = task.get_title()
        gtg_tags = [t.lstrip('@').lower() for t in task.get_tags_name()]

        activity = "Other"
        if self.preferences['activity'] == 'tag':
            hamster_activities = set([unicode(x[0]).lower()
                                      for x in self.hamster.GetActivities()])
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
            hamster_activities = dict([(unicode(x[0]), unicode(x[1]))
                                       for x in self.hamster.GetActivities()])
            if (gtg_title in hamster_activities
                    or gtg_title.replace(",", "") in hamster_activities):
                    category = "%s" % hamster_activities[gtg_title]

        if (self.preferences['category'] == 'tag' or
           (self.preferences['category'] == 'auto_tag' and not category)):
            # See if any of the tags match existing categories
            categories = dict([(unicode(x[1]).lower(), unicode(x[1]))
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
                hamster_tags = set([unicode(x) for x in
                                    self.hamster.GetTags()])
                tag_candidates = list(hamster_tags.intersection(set(gtg_tags)))
            elif self.preferences['tags'] == 'all':
                tag_candidates = gtg_tags
        except dbus.exceptions.DBusException:
            # old hamster version, doesn't support tags
            pass
        tag_str = "".join([" ," + x for x in tag_candidates])

        # print '%s%s,%s%s'%(activity, category, description, tag_str)
        hamster_id = self.hamster.AddFact(activity, tag_str, 0, 0,
                                          category, description)

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
                d = self.hamster.GetFactById(i)
                if d.get("id", None) and i not in valid_ids:
                    records.append(d)
                    valid_ids.append(i)
                    continue
            except dbus.DBusException:
                pass
            modified = True
            print "Removing invalid fact", i
        if modified:
            self.set_hamster_ids(task, valid_ids)
        return records

    def get_active_id(self):
        f = self.hamster.GetCurrentFact()
        if f:
            return f['id']
        else:
            return None

    def is_task_active(self, task):
        records = self.get_records(task)
        ids = [record['id'] for record in records]
        return self.get_active_id() in ids

    def stop_task(self, task):
        if self.is_task_active(self, task):
            self.hamster.StopTracking()

    #### Datastore
    def get_hamster_ids(self, task):
        a = task.get_attribute("id-list", namespace=self.PLUGIN_NAMESPACE)
        if not a:
            return []
        else:
            return a.split(',')

    def set_hamster_ids(self, task, ids):
        task.set_attribute("id-list", ",".join(ids),
                           namespace=self.PLUGIN_NAMESPACE)

    #### Plugin api methods
    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.hamster = dbus.SessionBus().get_object('org.gnome.Hamster',
                                                    '/org/gnome/Hamster')

        # add menu item
        if plugin_api.is_browser():
            self.menu_item = gtk.MenuItem(_("Start task in Hamster"))
            self.menu_item.show_all()
            self.menu_item.connect('activate', self.browser_cb, plugin_api)
            plugin_api.add_menu_item(self.menu_item)
            # and button
            self.button.set_label(_("Start in Hamster"))
            self.button.set_icon_name('hamster-applet')
            self.button.set_tooltip_text(self.TOOLTIP_TEXT)
            self.button.connect('clicked', self.browser_cb, plugin_api)
            self.button.show()
            plugin_api.add_toolbar_item(self.button)
        # set up preferences
        self.preference_dialog_init()
        self.preferences_load()

    def onTaskOpened(self, plugin_api):
        # add button
        self.taskbutton = gtk.ToolButton()
        self.taskbutton.set_label("Start")
        self.taskbutton.set_icon_name('hamster-applet')
        self.taskbutton.set_tooltip_text(self.TOOLTIP_TEXT)
        self.taskbutton.connect('clicked', self.task_cb, plugin_api)
        self.taskbutton.show()
        plugin_api.add_toolbar_item(self.taskbutton)

        task = plugin_api.get_ui().get_task()
        records = self.get_records(task)

        if len(records):
            # add section to bottom of window
            vbox = gtk.VBox()
            inner_table = gtk.Table(rows=len(records), columns=2)
            if len(records) > 8:
                s = gtk.ScrolledWindow()
                s.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
                v = gtk.Viewport()
                v.add(inner_table)
                s.add(v)
                v.set_shadow_type(gtk.SHADOW_NONE)
                s.set_size_request(-1, 150)
            else:
                s = inner_table

            outer_table = gtk.Table(rows=1, columns=2)
            vbox.pack_start(s)
            vbox.pack_start(outer_table)
            vbox.pack_end(gtk.HSeparator())

            total = 0

            def add(w, a, b, offset, active=False):
                if active:
                    a = "<span color='red'>%s</span>" % a
                    b = "<span color='red'>%s</span>" % b

                dateLabel = gtk.Label(a)
                dateLabel.set_use_markup(True)
                dateLabel.set_alignment(xalign=0.0, yalign=0.5)
                dateLabel.set_size_request(200, -1)
                w.attach(dateLabel, left_attach=0, right_attach=1,
                         top_attach=offset, bottom_attach=offset + 1,
                         xoptions=gtk.FILL, xpadding=20, yoptions=0)

                durLabel = gtk.Label(b)
                durLabel.set_use_markup(True)
                durLabel.set_alignment(xalign=0.0, yalign=0.5)
                w.attach(durLabel, left_attach=1, right_attach=2,
                         top_attach=offset, bottom_attach=offset + 1,
                         xoptions=gtk.FILL, yoptions=0)

            active_id = self.get_active_id()
            for offset, i in enumerate(records):
                t = calc_duration(i)
                total += t
                add(inner_table, format_date(i), format_duration(t),
                    offset, i['id'] == active_id)

            add(outer_table, "<big><b>Total</b></big>",
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
        task_id = plugin_api.get_ui().get_selected_task()
        self.sendTask(plugin_api.get_requester().get_task(task_id))

    def task_cb(self, widget, plugin_api):
        task = plugin_api.get_ui().get_task()
        self.sendTask(task)

    #### Preference Handling
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
        self.builder = gtk.Builder()
        path = "%s/prefs.ui" % os.path.dirname(os.path.abspath(__file__))
        self.builder.add_from_file(path)
        self.preferences_dialog = self.builder.get_object("dialog1")
        SIGNAL_CONNECTIONS_DIC = {
            "prefs_close": self.on_preferences_close,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

#### Helper Functions


def format_date(task):
    start_time = time.gmtime(task['start_time'])
    return time.strftime("<b>%A, %b %e</b> %l:%M %p", start_time)


def calc_duration(fact):
    start = fact['start_time']
    end = fact['end_time']
    if not end:
        end = timegm(time.localtime())
    return end - start


def format_duration(seconds):
    # Based on hamster-applet code -  hamster/stuff.py
    """formats duration in a human readable format."""

    minutes = seconds / 60

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
