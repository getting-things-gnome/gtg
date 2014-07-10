#!/usr/bin/python3
from gi.repository import Gtk, Gdk, GObject
import os

from GTG.plugins.calendar_view.week_view import WeekView
# from GTG.plugin.calendar_view.controller import Controller


class CalendarPlugin(GObject.GObject):
    """
    This class is a plugin to display tasks into a dedicated view, where tasks
    can be selected, edited, moved around by dragging and dropping, etc.
    """
    def __init__(self, requester, vmanager):
        super(CalendarPlugin, self).__init__()

        self.req = requester
        self.vmanager = vmanager
        self.vmanager.connect('tasks-deleted', self.on_tasks_deleted)

        self.first_day = self.last_day = self.numdays = None

        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
        self.glade_file = os.path.join(self.plugin_path, "calendar_view.ui")

        # FIXME: controller drawing content is not working
        # using weekview object instead for now:
        self.controller = WeekView(self, self.req)

        builder = Gtk.Builder()
        builder.add_from_file(self.glade_file)
        handlers = {
            "on_window_destroy": self.close_window,
            "on_today_clicked": self.on_today_clicked,
            "on_combobox_changed": self.on_combobox_changed,
            "on_add_clicked": self.on_add_clicked,
            "on_edit_clicked": self.on_edit_clicked,
            "on_remove_clicked": self.on_remove_clicked,
            "on_next_clicked": self.on_next_clicked,
            "on_previous_clicked": self.on_previous_clicked,
            "on_statusbar_text_pushed": self.on_statusbar_text_pushed
        }
        builder.connect_signals(handlers)

        self.window = builder.get_object("window")
        self.window.__init__()
        self.window.set_title("GTG - Calendar View")
        self.window.connect("destroy", Gtk.main_quit)

        self.today_button = builder.get_object("today")
        self.header = builder.get_object("header")
        self.edit_button = builder.get_object("edit")
        self.remove_button = builder.get_object("remove")

        self.controller.connect('selection-changed',
                                self.update_buttons_sensitivity)
        self.controller.connect("dates-changed", self.on_dates_changed)
        self.controller.show_today()

        vbox = builder.get_object("vbox")
        vbox.add(self.controller)
        vbox.reorder_child(self.controller, 1)

        self.combobox = builder.get_object("combobox")
        self.combobox.set_active(0)

        self.statusbar = builder.get_object("statusbar")
        self.label = builder.get_object("label")

        self.window.show_all()
        self.window.add_events(Gdk.EventMask.FOCUS_CHANGE_MASK)
        # self.window.connect("focus-in-event", self.controller.update_tasks)
        self.vmanager.connect('task-status-changed',
                              self.controller.update_tasks)

    def close_window(self, arg):
        # FIXME: not working, still closes GTG main window
        self.window.hide()
        return True  # do not destroy window

    def on_statusbar_text_pushed(self, text):
        """ Adds the @text to the statusbar """
        self.label.set_text(text)
        # self.statusbar.push(0, text)

    def on_add_clicked(self, button=None):
        """ Asks the controller to add a new task. """
        self.controller.add_new_task()
        # task = self.req.get_task(self.controller.get_selected_task())
        # self.on_statusbar_text_pushed("Added task: %s" % task.get_title())

    def on_edit_clicked(self, button=None):
        """ Asks the controller to edit the selected task. """
        task_id = self.controller.get_selected_task()
        if task_id and self.controller.req.has_task(task_id):
            self.controller.ask_edit_task(task_id)
            title = self.req.get_task(task_id).get_title()
            self.on_statusbar_text_pushed("Edited task: %s" % title)

    def on_remove_clicked(self, button=None):
        """
        Asks the controller to remove the selected task from the datastore.
        """
        task_id = self.controller.get_selected_task()
        if task_id and self.controller.req.has_task(task_id):
            self.controller.ask_delete_task(task_id)

    def on_tasks_deleted(self, widget, tids):
        if tids:
            self.on_statusbar_text_pushed(
                "Deleted task: %s" % ", ".join([t.get_title() for t in tids]))
        else:
            self.on_statusbar_text_pushed("...")

    def on_next_clicked(self, button, days=None):
        """ Advances the dates being displayed by a given number of @days """
        self.controller.next(days)
        self.content_refresh()

    def on_previous_clicked(self, button, days=None):
        """ Regresses the dates being displayed by a given number of @days """
        self.controller.previous(days)
        self.content_refresh()

    def on_today_clicked(self, button):
        """ Show the day corresponding to today """
        self.controller.show_today()
        self.content_refresh()

    def on_combobox_changed(self, combo):
        """
        User chose a combobox entry: change the view_type according to it
        """
        view_type = combo.get_active_text()
        # FIXME: view switch is not working, even thought objects exist
        # try Gtk.Stack for this -> needs Gnome 3.10
        # self.controller.on_view_changed(view_type)
        print("Ignoring view change for now")
        self.content_refresh()
        self.controller.refresh()

    def on_dates_changed(self, widget=None):
        """ Callback to update date-related objects in main window """
        self.header.set_text(self.controller.get_current_year())
        self.today_button.set_sensitive(
            not self.controller.is_today_being_shown())

    def update_buttons_sensitivity(self, widget=None, selected_task=None):
        """
        Updates Edit and Remove buttons sensitivity, depeding on wheter or not
        there is a @selected_task

        @param selected_task: a string, the selected task id or None
        """
        enable = (selected_task is not None)
        self.edit_button.set_sensitive(enable)
        self.remove_button.set_sensitive(enable)

    def content_refresh(self):
        """ Performs all that is needed to update the content displayed """
        self.on_dates_changed()

# If we want to test only the Plugin (outside GTG):
tests = False
if tests:
    from GTG.core.datastore import DataStore
    ds = DataStore()
    ds.populate()  # hard-coded tasks
    CalendarPlugin(ds.get_requester())
    Gtk.main()
