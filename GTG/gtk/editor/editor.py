# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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
"""
This is the TaskEditor

It's the window you see when you double-click on a Task
The main text widget is a home-made TextView called TaskView (see taskview.py)
The rest is the logic of the widget: date changing widgets, buttons, ...
"""
import datetime
import logging
import os
import time
from gettext import gettext as _, ngettext

from gi.repository import Gdk, Gtk, GLib, Pango
from gi.repository.GObject import signal_handler_block
from GTG.core.dates import Accuracy, Date
from GTG.core.dirs import UI_DIR
from GTG.core.plugins.api import PluginAPI
from GTG.core.plugins.engine import PluginEngine
from GTG.core.task import Task
from GTG.gtk.editor import GnomeConfig
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.editor.recurring_menu import RecurringMenu
from GTG.gtk.editor.taskview import TaskView
from GTG.gtk.tag_completion import tag_filter
from GTG.gtk.colors import rgb_to_hex
from GTG.core.tasks2 import Task2

"""
TODO (jakubbrindza): re-factor tag_filter into a separate module
"""

log = logging.getLogger(__name__)


@Gtk.Template(filename=os.path.join(UI_DIR, "task_editor.ui"))
class TaskEditor(Gtk.Window):
    __gtype_name__ = "TaskEditor"

    editormenu = Gtk.Template.Child("editor_menu")
    donebutton = Gtk.Template.Child("mark_as_done")
    undonebutton = Gtk.Template.Child("mark_as_undone")
    add_subtask = Gtk.Template.Child()
    tag_store = Gtk.Template.Child()
    parent_button = Gtk.Template.Child("parent")
    scrolled = Gtk.Template.Child("scrolledtask")

    # Closed date
    closed_box = Gtk.Template.Child()
    closed_popover = Gtk.Template.Child()
    closed_entry = Gtk.Template.Child()
    closed_calendar = Gtk.Template.Child()

    # Start date
    start_box = Gtk.Template.Child()
    start_popover = Gtk.Template.Child()
    start_entry = Gtk.Template.Child("startdate_entry")
    start_calendar = Gtk.Template.Child("calendar_start")

    # Due date
    due_popover = Gtk.Template.Child()
    due_entry = Gtk.Template.Child("duedate_entry")
    due_calendar = Gtk.Template.Child("calendar_due")

    def __init__(self,
                 requester,
                 app,
                 task,
                 thisisnew=False,
                 clipboard=None):
        """
        req is the requester
        app is the view manager
        thisisnew is True when a new task is created and opened
        """
        super().__init__()
        self.req = requester
        self.app = app
        self.browser_config = self.req.get_config('browser')
        self.config = self.req.get_task_config(task.get_id())
        self.time = None
        self.clipboard = clipboard

        # Recurrence
        self.recurring_menu = RecurringMenu(self.req, task.tid, self.builder)

        # TODO: Remove old code when new core is stable
        # If new add to new DS
        if thisisnew and task.tid not in self.app.ds.tasks.lookup.keys():
            new_task = Task2(task.tid, task.get_title())
            self.app.ds.tasks.add(new_task)

        self.set_application(app)

        if task.has_parent():
            self.parent_button.set_label(_('Open Parent'))
        else:
            self.parent_button.set_label(_('Add Parent'))

        # Connect signals for the calendar
        self.start_handle = self.start_calendar.connect(
            'day-selected', lambda c: self.on_date_selected(c, GTGCalendar.DATE_KIND_START))

        self.due_handle = self.due_calendar.connect(
            'day-selected', lambda c: self.on_date_selected(c, GTGCalendar.DATE_KIND_DUE))

        self.closed_handle = self.closed_calendar.connect(
            'day-selected', lambda c: self.on_date_selected(c, GTGCalendar.DATE_KIND_CLOSED))

        # Removing the Normal textview to replace it by our own
        # So don't try to change anything with glade, this is a home-made
        # widget
        textview = self.get_template_child("textview")
        scrolled.set_child(None)
        self.textview = TaskView(self.req, self.clipboard)
        self.textview.set_vexpand(True)
        scrolled.set_child(self.textview)
        conf_font_value = self.browser_config.get("font_name")
        if conf_font_value != "":
            self.textview.override_font(Pango.FontDescription(conf_font_value))

        self.textview.browse_tag_cb = app.select_tag
        self.textview.new_subtask_cb = self.new_subtask
        self.textview.get_subtasks_cb = task.get_children
        self.textview.delete_subtask_cb = self.remove_subtask
        self.textview.rename_subtask_cb = self.rename_subtask
        self.textview.open_subtask_cb = self.open_subtask
        self.textview.save_cb = self.light_save
        self.textview.add_tasktag_cb = self.tag_added
        self.textview.remove_tasktag_cb = self.tag_removed
        self.textview.refresh_cb = self.refresh_editor
        self.textview.get_tagslist_cb = task.get_tags_name
        self.textview.tid = task.tid

        # Voila! it's done
        self.textview.connect('focus-in-event', self.on_textview_focus_in)
        self.textview.connect('focus-out-event', self.on_textview_focus_out)

        """
        TODO(jakubbrindza): Once all the functionality in editor is back and
        working, bring back also the accelerators! Dayleft_label needs to be
        brought back, however its position is unsure.
        """
        # self.dayleft_label = self.builder.get_object("dayleft")

        self.task = task
        tags = task.get_tags()
        text = self.task.get_text()
        title = self.task.get_title()

        # Insert text and tags as a non_undoable action, otherwise
        # the user can CTRL+Z even this inserts.
        self.textview.buffer.begin_not_undoable_action()
        self.textview.buffer.set_text(f"{title}\n")

        if text:
            self.textview.insert(text)

            # Insert any remaining tags
            if tags:
                tag_names = [t.get_name() for t in tags]
                self.textview.insert_tags(tag_names)
        else:
            # If not text, we insert tags
            if tags:
                tag_names = [t.get_name() for t in tags]
                self.textview.insert_tags(tag_names)
                start = self.textview.buffer.get_end_iter()
                self.textview.buffer.insert(start, '\n')

        # Insert subtasks if they weren't inserted in the text
        subtasks = task.get_children()
        for sub in subtasks:
            if sub not in self.textview.subtasks['tags']:
                self.textview.insert_existing_subtask(sub)

        if thisisnew:
            self.textview.select_title()
        else:
            self.task.set_to_keep()

        self.textview.buffer.end_not_undoable_action()
        self.connect("destroy", self.destruction)

        # Connect search field to tags popup
        self.tags_entry = self.builder.get_object("tags_entry")
        self.tags_tree = self.builder.get_object("tags_tree")

        self.tags_tree.set_search_entry(self.tags_entry)
        self.tags_tree.set_search_equal_func(self.search_function, None)

        # plugins
        self.pengine = PluginEngine()
        self.plugin_api = PluginAPI(self.req, self.app, self)
        self.pengine.register_api(self.plugin_api)
        self.pengine.onTaskLoad(self.plugin_api)

        # Putting the refresh callback at the end make the start a lot faster
        self.refresh_editor()
        self.textview.grab_focus()

        self.init_dimensions()

        self.insert_action_group('app', app)
        self.insert_action_group('win', app.browser)

        self.textview.set_editable(True)
        self.set_transient_for(self.app.browser)
        self.show()


    def tag_added(self, name):

        self.task.tag_added(name)
        t = self.app.ds.tasks.get(self.task.tid)
        t.add_tag(self.app.ds.tags.new(name))


    def tag_removed(self, name):

        self.task.remove_tag(name)
        t = self.app.ds.tasks.get(self.task.tid)
        t.remove_tag(name)


    @Gtk.Template.Callback()
    def show_popover_start(self, widget, event):
        """Open the start date calendar popup."""

        start_date = (self.task.get_start_date() or Date.today()).date()

        with signal_handler_block(self.start_calendar, self.start_handle):
            self.start_calendar.select_day(start_date.day)
            self.start_calendar.select_month(start_date.month - 1,
                                             start_date.year)

        self.start_popover.popup()

    @Gtk.Template.Callback()
    def show_popover_due(self, widget, popover):
        """Open the due date calendar popup."""

        due_date = self.task.get_due_date()

        if not due_date or due_date.is_fuzzy():
            due_date = Date.today()

        due_date = due_date.date()

        with signal_handler_block(self.due_calendar, self.due_handle):
            self.due_calendar.select_day(due_date.day)
            self.due_calendar.select_month(due_date.month - 1,
                                           due_date.year)

        self.due_popover.popup()

    @Gtk.Template.Callback()
    def show_popover_closed(self, widget, popover):
        """Open the closed date calendar popup."""

        closed_date = self.task.get_closed_date().date()

        with signal_handler_block(self.closed_calendar, self.closed_handle):
            self.closed_calendar.select_day(closed_date.day)
            self.closed_calendar.select_month(closed_date.month - 1,
                                              closed_date.year)

        self.closed_popover.popup()

    def open_tags_popover(self):
        self.tag_store.clear()

        tags = self.req.get_tag_tree().get_all_nodes()

        used_tags = self.task.get_tags()

        special_tags = ["search",
                        "gtg-tags-all",
                        "gtg-tags-none",
                        "gtg-tags-sep"]

        for tagname in tags:
            tag = self.req.get_tag(tagname)
            if tag_filter(tag) \
                    and tagname not in special_tags \
                    and "__SAVED_SEARCH_" not in tagname:
                is_used = tag in used_tags
                self.tag_store.append([is_used, tagname])
                """
                TODO(jakubbrindza): add sorting of the tags based on
                True | False and within each sub-group arrange them
                alphabetically
                """

    def set_dismissable_in_menu(self, dismissable):
        """
        Set the task editor's menu items to how they are when the
        task is already dismissed/isn't. This shouldn't be called more than once with
        different arguments
        """
        # For some reason here using the menu section directly from the UI file
        # causes a crash and a weird reference count assertion error. Retrieving it from
        # the main menu instead avoids the cryptic crash
        __, __, editor_menu_con_sec = self.editormenu.iterate_item_links(0).get_next()

        # Plugins may add menu items to here, which is why we need to only remove
        # the specific item that we need instead of everything
        # Manual iteration without GI overrides is ugly
        length = editor_menu_con_sec.get_n_items()
        i = 0
        while i < length:
            name = ''.join(editor_menu_con_sec.get_item_attribute_value(
                i,
                'label',
                GLib.VariantType.new('s')).get_string()
            )
            # this might cause problems with localization if it isn't translated
            # here the same
            if name == (_("Undismiss") if dismissable else _("Dismiss")):
                editor_menu_con_sec.remove(i)
                return
            i += 1

    @Gtk.Template.Callback()
    def on_tag_toggled(self, widget, path, column):
        """We toggle by tag_row variable. tag_row is
        meant to be a tuple (is_used, tagname)"""
        tag_row = self.tag_store[path]
        tag_row[0] = not tag_row[0]

        if tag_row[0]:
            self.textview.insert_tags([tag_row[1]])
        """
        TODO(jakubbrindza): Add else case that will remove tag.
        """

    @Gtk.Template.Callback()
    def on_repeat_icon_toggled(self, widget):
        """ Reset popup stack to the first page every time you open it """
        if widget.get_active():
            self.recurring_menu.reset_stack()

    @Gtk.Template.Callback()
    def toggle_recurring_status(self, widget):
        self.recurring_menu.update_repeat_checkbox()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_every_day(self, widget):
        self.recurring_menu.set_selected_term('day')
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_every_otherday(self, widget):
        self.recurring_menu.set_selected_term('other-day')
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_every_week(self, widget):
        self.recurring_menu.set_selected_term('week')
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_every_month(self, widget):
        self.recurring_menu.set_selected_term('month')
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_every_year(self, widget):
        self.recurring_menu.set_selected_term('year')
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_week_day(self, widget):
        self.recurring_menu.set_selected_term(widget.get_property("name"))
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_month(self, widget):
        self.recurring_menu.set_selected_term(str(widget.get_date()[2]))
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def set_recurring_term_year(self, widget):
        month = str(widget.get_date()[1] + 1)
        day = str(widget.get_date()[2])
        if len(month) < 2:
            month = "0" + month
        if len(day) < 2:
            day = "0" + day
        self.recurring_menu.set_selected_term(month + day)
        self.recurring_menu.update_term()
        self.refresh_editor()

    @Gtk.Template.Callback()
    def startingdate_changed(self, w):
        self.date_changed(w, GTGCalendar.DATE_KIND_START)

    @Gtk.Template.Callback()
    def startdate_cleared(self, w):
        self.on_date_cleared(w, GTGCalendar.DATE_KIND_START)

    @Gtk.Template.Callback()
    def startdate_focus_out(self, w, e):
        self.date_focus_out(w, e, GTGCalendar.DATE_KIND_START)

    @Gtk.Template.Callback()
    def duedate_changed(self, w):
        self.date_changed(w, GTGCalendar.DATE_KIND_DUE)

    @Gtk.Template.Callback()
    def duedate_now_selected(self, w):
        self.on_duedate_fuzzy(w, Date.now())

    @Gtk.Template.Callback()
    def duedate_soon_selected(self, w):
        self.on_duedate_fuzzy(w, Date.soon())

    @Gtk.Template.Callback()
    def duedate_someday_selected(self, w):
        self.on_duedate_fuzzy(w, Date.someday())

    @Gtk.Template.Callback()
    def duedate_cleared(self, w):
        self.on_date_cleared(w, GTGCalendar.DATE_KIND_DUE)

    @Gtk.Template.Callback()
    def duedate_focus_out(self, w, e):
        self.date_focus_out(w, e, GTGCalendar.DATE_KIND_DUE)

    @Gtk.Template.Callback()
    def closeddate_changed(self, w):
        self.date_changed(w, GTGCalendar.DATE_KIND_CLOSED)

    @Gtk.Template.Callback()
    def closeddate_focus_out(self, w, e):
        self.date_focus_out(w, e, GTGCalendar.DATE_KIND_CLOSED)

    def search_function(self, model, column, key, iter, *search_data):
        """Callback when searching in the tags popup."""

        if not key.startswith('@'):
            key = f'@{key}'

        # The return value is reversed. False if it matches, True
        # otherwise.
        return not model.get(iter, column)[0].startswith(key)

    @staticmethod
    def get_monitor_dimensions() -> Gdk.Rectangle:
        """Get dimensions for the first monitor."""
        return Gdk.Display.get_default().get_monitor(0).get_geometry()

    def init_dimensions(self):
        """ Restores position and size of task if possible """

        position = self.config.get('position')
        size = self.config.get('size')
        screen_size = self.get_monitor_dimensions()

        if size and len(size) == 2:
            try:
                self.resize(int(size[0]), int(size[1]))
            except ValueError:
                log.warning('Invalid size configuration for task %s: %s',
                            self.task.get_id(), size)

        can_move = True
        if position and len(position) == 2:
            try:
                x = max(0, int(position[0]))
                y = max(0, int(position[1]))
                can_move = True
            except ValueError:
                can_move = False
                log.warning('Invalid position configuration for task %s:%s',
                            self.task.get_id(), position)
        else:
            gdk_window = self.get_window()
            if gdk_window is None:
                log.debug("Using default display to position editor window")
                display = Gdk.Display.get_default()
            else:
                # TODO: AFAIK never happens because window is not realized at
                #       this point, but maybe we should just in case the display
                #       is actually different.
                display = gdk_window.get_display()
            seat = display.get_default_seat()
            pointer = seat.get_pointer()
            if pointer is None:
                can_move = False
                log.debug("Didn't receiver pointer info, can't move editor window")
            else:
                screen, x, y = pointer.get_position()
                assert isinstance(x, int)
                assert isinstance(y, int)

        if can_move:
            width, height = self.get_size()

            # Clamp positions to current screen size
            x = min(x, screen_size.width - width)
            y = min(y, screen_size.height - height)

            self.move(x, y)

    # Can be called at any time to reflect the status of the Task
    # Refresh should never interfere with the TaskView.
    # If a title is passed as a parameter, it will become
    # the new window title. If not, we will look for the task title.
    # Refreshtext is whether or not we should refresh the TaskView
    # (doing it all the time is dangerous if the task is empty)
    def refresh_editor(self, title=None, refreshtext=False):
        if self is None:
            return
        to_save = False
        # title of the window
        if title:
            self.set_title(title)
            to_save = True
        else:
            self.set_title(self.task.get_title())

        status = self.task.get_status()
        if status == Task.STA_DISMISSED:
            self.donebutton.show()
            self.undonebutton.hide()
            self.set_dismissable_in_menu(False)
        elif status == Task.STA_DONE:
            self.donebutton.hide()
            self.undonebutton.show()
            self.set_dismissable_in_menu(True)
        else:
            self.donebutton.show()
            self.undonebutton.hide()
            self.set_dismissable_in_menu(True)

        # Refreshing the parent button
        if self.task.has_parent():
            # Translators: Button label to open the parent task
            self.parent_button.set_label(_('Open Parent'))
        else:
            # Translators: Button label to add an new parent task
            self.parent_button.set_label(_('Add Parent'))

        # Refreshing the status bar labels and date boxes
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            self.start_box.hide()
            self.closed_box.show()
        else:
            self.closed_box.hide()
            self.start_box.show()

        # refreshing the start date field
        startdate = self.task.get_start_date()
        try:
            prevdate = Date.parse(self.start_entry.get_text())
            update_date = startdate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.start_entry.set_text(startdate.localized_str)

        # refreshing the due date field
        duedate = self.task.get_due_date()
        try:
            prevdate = Date.parse(self.due_entry.get_text())
            update_date = duedate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.due_entry.set_text(duedate.localized_str)

        # refreshing the closed date field
        closeddate = self.task.get_closed_date()
        prevcldate = Date.parse(self.closed_entry.get_text())
        if closeddate != prevcldate:
            self.closed_entry.set_text(closeddate.localized_str)

        # refreshing the day left label
        """
        TODO(jakubbrindza): re-enable refreshing the day left.
        We need to come up how and where this information is viewed
        in the editor window.
        """
        # self.refresh_day_left()

        if refreshtext:
            self.textview.modified(refresheditor=False)
        if to_save:
            self.light_save()

    def refresh_day_left(self):
        # If the task is marked as done, we display the delay between the
        # due date and the actual closing date. If the task isn't marked
        # as done, we display the number of days left.
        status = self.task.get_status()
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            delay = self.task.get_days_late()
            if delay is None:
                txt = ""
            elif delay == 0:
                txt = "Completed on time"
            elif delay >= 1:
                txt = ngettext("Completed %(days)d day late",
                               "Completed %(days)d days late", delay) % \
                    {'days': delay}
            elif delay <= -1:
                abs_delay = abs(delay)
                txt = ngettext("Completed %(days)d day early",
                               "Completed %(days)d days early", abs_delay) % \
                    {'days': abs_delay}
        else:
            due_date = self.task.get_due_date()
            result = due_date.days_left()
            if due_date.is_fuzzy():
                txt = ""
            elif result > 0:
                txt = ngettext("Due tomorrow!", "%(days)d days left", result)\
                    % {'days': result}
            elif result == 0:
                txt = _("Due today!")
            elif result < 0:
                abs_result = abs(result)
                txt = ngettext("Due yesterday!", "Was %(days)d days ago",
                               abs_result) % {'days': abs_result}

        style_context = self.get_style_context()
        color = style_context.get_color().to_color()
        self.dayleft_label.set_markup(
            f"<span color='{rgb_to_hex(color)}'>{txt}</span>")

    def reload_editor(self):
        task = self.task
        textview = self.textview
        task_text = task.get_text()
        task_title = task.get_title()
        textview.set_text(f"{task_title}\n")
        if task_text:
            textview.insert(f"{task_text}")
        task.set_title(task_title)
        textview.modified(full=True)

    def date_changed(self, widget, data):
        try:
            Date.parse(widget.get_text())
            valid = True
        except ValueError:
            valid = False

        if valid:
            # If the date is valid, we write with default color in the widget
            # "none" will set the default color.
            widget.override_color(Gtk.StateType.NORMAL, None)
            widget.override_background_color(Gtk.StateType.NORMAL, None)
        else:
            # We should write in red in the entry if the date is not valid
            text_color = Gdk.RGBA()
            text_color.parse("#F00")
            widget.override_color(Gtk.StateType.NORMAL, text_color)

            bg_color = Gdk.RGBA()
            bg_color.parse("#F88")
            widget.override_background_color(Gtk.StateType.NORMAL, bg_color)

    def date_focus_out(self, widget, event, date_kind):
        try:
            datetoset = Date.parse(widget.get_text())
        except ValueError:
            datetoset = None

        if datetoset is not None:
            # TODO: New Core
            t = self.app.ds.tasks.get(self.task.tid)

            if date_kind == GTGCalendar.DATE_KIND_START:
                self.task.set_start_date(datetoset)
                t.date_start = datetoset
                self.start_popover.popdown()

            elif date_kind == GTGCalendar.DATE_KIND_DUE:
                self.task.set_due_date(datetoset)
                t.date_due = datetoset
                self.due_popover.popdown()

            elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
                self.task.set_closed_date(datetoset)
                t.date_closed = datetoset
                self.closed_popover.popdown()

            self.refresh_editor()

    def calendar_to_datetime(self, calendar):
        """
        Gtk.Calendar uses a 0-based convention for counting months.
        The rest of the world, including the datetime module, starts from 1.
        This is a converter between the two. GTG follows the datetime
        convention.
        """

        year, month, day = calendar.get_date()
        return datetime.date(year, month + 1, day)

    def on_duedate_fuzzy(self, widget, date):
        """ Callback when a fuzzy date is selected through the popup. """

        self.task.set_due_date(date)
        self.due_entry.set_text(date.localized_str)

    def on_date_cleared(self, widget, kind):
        """ Callback when a date is cleared through the popups. """

        if kind == GTGCalendar.DATE_KIND_START:
            self.task.set_start_date(Date.no_date())
            self.start_entry.set_text('')

        elif kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(Date.no_date())
            self.due_entry.set_text('')

    def on_date_selected(self, calendar, kind):
        """ Callback when a day is selected in the calendars."""

        date = self.calendar_to_datetime(calendar)

        if kind == GTGCalendar.DATE_KIND_START:
            self.task.set_start_date(Date(date))
            self.start_entry.set_text(Date(date).localized_str)

        elif kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(Date(date))
            self.due_entry.set_text(Date(date).localized_str)

        elif kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.set_closed_date(Date(date))
            self.closed_entry.set_text(Date(date).localized_str)

    def on_date_changed(self, calendar):
        date, date_kind = calendar.get_selected_date()
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_START:
            self.task.set_start_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.set_closed_date(date)
        self.refresh_editor()

    def close_all_subtasks(self):
        all_subtasks = []

        def trace_subtasks(root):
            for i in root.get_subtasks():
                if i not in all_subtasks:
                    all_subtasks.append(i)
                    trace_subtasks(i)

        trace_subtasks(self.task)

        for task in all_subtasks:
            self.app.close_task(task.get_id())

    def dismiss(self):
        stat = self.task.get_status()
        t = self.app.ds.tasks.get(self.task.tid)
        t.toggle_dismissed()

        if stat == Task.STA_DISMISSED:
            self.task.set_status(Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.task.set_status(Task.STA_DISMISSED)
            self.close_all_subtasks()
            self.close(None)

    def change_status(self):
        stat = self.task.get_status()
        t = self.app.ds.tasks.get(self.task.tid)
        t.toggle_active()

        if stat == Task.STA_DONE:
            self.task.set_status(Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.task.set_status(Task.STA_DONE)
            self.close_all_subtasks()
            self.close(None)

    def reopen(self):
        t = self.app.ds.tasks.get(self.task.tid)
        t.toggle_active()

        self.task.set_status(Task.STA_ACTIVE)
        self.refresh_editor()

    def open_subtask(self, tid):
        """Open subtask (closing parent task)."""

        task = self.req.get_task(tid)
        self.app.open_task(tid)
        self.app.close_task(task.parents[0])

    # Take the title as argument and return the subtask ID
    def new_subtask(self, title=None, tid=None):
        if tid:
            self.task.add_child(tid)
            self.app.ds.tasks.parent(self.task.tid, tid)
        elif title:
            subt = self.task.new_subtask()
            subt.set_title(title)
            tid = subt.get_id()

            # TODO: New Core
            t = self.app.ds.tasks.new(title, self.task.tid)
            t.id = tid
            self.app.ds.tasks.refresh_lookup_cache()

        return tid

    def remove_subtask(self, tid):
        """Remove a subtask of this task."""

        self.task.remove_child(tid)
        self.app.ds.tasks.unparent(tid, self.task.tid)

    def rename_subtask(self, tid, new_title):
        """Rename a subtask of this task."""

        try:
            self.req.get_task(tid).set_title(new_title)
            self.app.ds.tasks.get(tid).title = new_title
        except (AttributeError, KeyError):
            # There's no task at that tid
            pass


    def insert_subtask(self, action=None, param=None):
        self.textview.insert_new_subtask()
        self.textview.grab_focus()

    def inserttag_clicked(self, widget):
        itera = self.textview.get_insert()
        if itera.starts_line():
            self.textview.insert_text("@", itera)
        else:
            self.textview.insert_text(" @", itera)

    def open_parent(self):
        """
        Open (or create) the parent task,
        then close the child to avoid various window management issues
        and to prevent visible content divergence when the child title changes.
        """
        parents = self.task.get_parents()
        self.save()

        if not parents:
            tags = [t.get_name() for t in self.task.get_tags()]
            parent = self.req.new_task(tags=tags, newtask=True)
            parent_id = parent.get_id()

            self.task.set_parent(parent_id)

            # TODO: New Core, remove old code when stable
            parent2 = Task2(title=_('New Task'), id=parent_id)
            parent2.tags = self.app.ds.tasks.get(self.task.tid).tags
            self.app.ds.tasks.add(parent2)
            self.app.ds.tasks.parent(self.task.tid, parent2.id)


            self.app.open_task(parent_id)
            # Prevent WM issues and risks of conflicting content changes:
            self.close()

        elif len(parents) == 1:
            self.app.open_task(parents[0])
            # Prevent WM issues and risks of conflicting content changes:
            self.close()

        elif len(parents) > 1:
            self.show_multiple_parent_popover(parents)

    def show_multiple_parent_popover(self, parent_ids):
        parent_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        for parent in parent_ids:
            parent_name = self.req.get_task(parent).get_title()
            button = Gtk.ToolButton.new(None, parent_name)
            button.connect("clicked", self.on_parent_item_clicked, parent)
            parent_box.append(button)

        self.parent_popover = Gtk.Popover.new(self.parent_button)
        self.parent_popover.set_child(parent_box)
        self.parent_popover.set_transitions_enabled(True)
        self.parent_popover.show()

    # On click handler for open_parent menu items in the case of multiple parents
    def on_parent_item_clicked(self, widget, parent_id):
        self.app.open_task(parent_id)
        if self.parent_popover.get_visible():
            self.parent_popover.hide()
        # Prevent WM issues and risks of conflicting content changes:
        self.close()

    def save(self):
        self.task.set_title(self.textview.get_title())
        self.task.set_text(self.textview.get_text())
        self.task.sync()
        if self.config is not None:
            self.config.save()
        self.time = time.time()

        # TODO: New core, remove previous code once stable
        t = self.app.ds.tasks.get(self.task.tid)
        t.title = self.textview.get_title()
        t.contents = self.textview.get_text()
        self.app.ds.save()


    # light_save save the task without refreshing every 30seconds
    # We will reduce the time when the get_text will be in another thread

    def light_save(self):
        # if self.time is none, we never called any save
        if self.time:
            diff = time.time() - self.time
            tosave = diff > GnomeConfig.SAVETIME
        else:
            # we don't want to save a task while opening it
            tosave = self.textview.get_editable()
            diff = None
        if tosave:
            self.save()

    @Gtk.Template.Callback()
    def on_move(self, widget, event):
        """ Save position and size of window """

        self.config.set('position', list(self.get_position()))
        self.config.set('size', list(self.get_size()))

    def on_textview_focus_in(self, widget, event):
        self.app.browser.toggle_delete_accel(False)

    def on_textview_focus_out(self, widget, event):
        self.app.browser.toggle_delete_accel(True)

    # We define dummy variable for when close is called from a callback
    def close(self, action=None, param=None):

        # We should also destroy the whole taskeditor object.
        if self:
            self.destroy()
            self = None

    def destruction(self, _=None):
        """Callback when destroying the window."""

        # Save should be also called when buffer is modified
        self.pengine.onTaskClose(self.plugin_api)
        self.pengine.remove_api(self.plugin_api)

        tid = self.task.get_id()

        if self.task.is_new():
            self.req.delete_task(tid)
            self.app.ds.tasks.remove(tid)
        else:
            self.save()
            [sub.set_to_keep() for sub in self.task.get_subtasks() if sub]

        try:
            del self.app.open_tasks[tid]
        except KeyError:
            log.debug('Task %s was already removed from the open list', tid)

    def get_task(self):
        return self.task

    def get_textview(self):
        return self.textview

    def get_window(self):
        return self
# -----------------------------------------------------------------------------
