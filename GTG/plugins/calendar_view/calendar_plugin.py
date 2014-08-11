#!/usr/bin/python3
from gi.repository import Gtk, Gdk, GObject
import os

from GTG.plugins.calendar_view.controller import Controller


class CalendarPlugin(GObject.GObject):
    """
    This class is a plugin to display tasks into a dedicated view, where tasks
    can be selected, edited, moved around by dragging and dropping, etc.
    """
    def __init__(self, requester, vmanager):
        super(CalendarPlugin, self).__init__()

        self.req = requester
        self.vmanager = vmanager

        self.first_day = self.last_day = self.numdays = None

        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
        self.glade_file = os.path.join(self.plugin_path, "calendar_view.ui")

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

        self.controller = Controller(self, self.req)
        vbox = builder.get_object("vbox")
        vbox.add(self.controller)
        vbox.reorder_child(self.controller, 1)

        self.current_view = None
        self.combobox = builder.get_object("combobox")
        # get combobox content from available views
        for label in self.controller.get_view_labels():
            self.combobox.append_text(label)
        self.combobox.set_active(0)

        self.window.show_all()
        self.window.add_events(Gdk.EventMask.FOCUS_CHANGE_MASK)
        # self.window.connect("focus-in-event", self.controller.update_tasks)
        self.vmanager.connect('task-status-changed',
                              self.controller.update_tasks)

    def close_window(self, window, arg):
        """ Hide window instead destroying it """
        window.hide()
        return True

    def on_add_clicked(self, button=None):
        """ Asks the controller to add a new task. """
        self.current_view.add_new_task()

    def on_edit_clicked(self, button=None):
        """ Asks the controller to edit the selected task. """
        task_id = self.current_view.get_selected_task()
        if task_id and self.current_view.req.has_task(task_id):
            self.current_view.ask_edit_task(task_id)

    def on_remove_clicked(self, button=None):
        """
        Asks the controller to remove the selected task from the datastore.
        """
        task_id = self.current_view.get_selected_task()
        if task_id and self.current_view.req.has_task(task_id):
            self.current_view.ask_delete_task(task_id)

    def on_next_clicked(self, button, days=None):
        """ Advances the dates being displayed by a given number of @days """
        self.current_view.next(days)
        self.content_refresh()

    def on_previous_clicked(self, button, days=None):
        """ Regresses the dates being displayed by a given number of @days """
        self.current_view.previous(days)
        self.content_refresh()

    def on_today_clicked(self, button):
        """ Show the day corresponding to today """
        self.current_view.show_today()
        self.content_refresh()

    def on_combobox_changed(self, combo):
        """
        User chose a combobox entry: change the view_type according to it
        """
        view_type = combo.get_active_text()
        self.controller.on_view_changed(view_type)

        if self.current_view != self.controller.get_visible_view():
            # diconnect signals from previous view
            if self.current_view is not None:
                self._disconnect_view_signals()
            self.current_view = self.controller.get_visible_view()
            # start listening signals from the new view
            self._connect_view_signals()
        self.content_refresh()

    def on_dates_changed(self, widget=None):
        """ Callback to update date-related objects in main window """
        self.header.set_text(self.current_view.date_range_to_string())
        self.today_button.set_sensitive(
            not self.current_view.is_today_being_shown())

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

    def _connect_view_signals(self):
        """
        Connect to signals emitted from current view to add/edit a task or when
        dates displayed changed
        """
        # self.current_view.connect("on_edit_task", self.on_edit_clicked)
        # self.current_view.connect("on_add_task", self.on_add_clicked)
        self.current_view.connect("dates-changed", self.on_dates_changed)
        self.current_view.connect('selection-changed',
                                  self.update_buttons_sensitivity)

    def _disconnect_view_signals(self):
        """
        Disconnect signals emitted from current view to add/edit a task or
        when dates displayed changed
        """
        # self.current_view.disconnect_by_func(self.on_edit_clicked)
        # self.current_view.disconnect_by_func(self.on_add_clicked)
        self.current_view.disconnect_by_func(self.on_dates_changed)
        self.current_view.disconnect_by_func(self.update_buttons_sensitivity)

# If we want to test only the Plugin (outside GTG):
tests = False
if tests:
    from GTG.core.datastore import DataStore
    ds = DataStore()
    ds.populate()  # hard-coded tasks
    CalendarPlugin(ds.get_requester())
    Gtk.main()
