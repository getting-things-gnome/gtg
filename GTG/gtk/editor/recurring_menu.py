# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The GTG Team and contributors
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

import os
from gettext import gettext as _
from datetime import datetime
from gi.repository import Gtk, Gio, GLib, GObject
from GTG.core.dirs import UI_DIR


@Gtk.Template(filename=os.path.join(UI_DIR, 'recurring_menu.ui'))
class RecurringMenu(Gtk.PopoverMenu):
    """Provides a simple layer of abstraction
       for the menu where the user enables a task to be repeating
    """

    __gtype_name__ = 'RecurringMenu'

    _menu_model = Gtk.Template.Child()

    _month_calendar = Gtk.Template.Child()
    _year_calendar = Gtk.Template.Child()

    def __init__(self, editor, task):
        # Setting up the actions
        # Before super().__init__ as install_*_action acts on the class,
        # and in this case doesn't work for all instances if you do it after
        # initialization.
        prefix = 'recurring_menu'
        for action_disc in [
            ('is_recurring', 'is-task-recurring'),
            ('recurr_every_day', self._on_recurr_every_day, None),
            ('recurr_every_otherday', self._on_recurr_every_otherday, None),
            ('recurr_every_week', self._on_recurr_every_week, None),
            ('recurr_week_day', self._on_recurr_week_day, 's'),
            ('recurr_month_today', self._on_recurr_month_today, None),
            ('recurr_year_today', self._on_recurr_year_today, None),
        ]:
            # is property action (property name instead of callback)
            if type(action_disc[1]) == str:
                self.install_property_action('.'.join([prefix, action_disc[0]]), action_disc[1])
            else:
                self.install_action('.'.join([prefix, action_disc[0]]), action_disc[2], action_disc[1])

        super().__init__()

        # General attributes
        self.task = task
        self._editor = editor
        self._selected_recurring_term = self.task.recurring_term

        self._is_header_menu_item_shown = False

        self._update_header()
        self._update_calendar()

        # Prevent user from switching month in month calendar with
        # scrollwheel.
        # Why not only set month? Because if the month is the first or last
        # of the year, the year switches and then we switch the month, which
        # won't be the same one.
        self._original_month = self._month_calendar.props.month
        self._original_year = self._month_calendar.props.year
        self._month_calendar.connect(
            'notify::month',
            lambda o, g : self._month_calendar.set_property('month', self._original_month)
        )
        self._month_calendar.connect(
            'notify::year',
            lambda o, g : self._month_calendar.set_property('year', self._original_year)
        )

    @GObject.Property(type=bool, default=False)
    def is_task_recurring(self):
        """
        Wrapper property for changing the tasks recurring status because
        to have a checkbutton in a GtkPopoverMenu you need to use a
        GPropertyAction, however the tag class itself doesn't use GObject
        properties.
        """
        return self.task._is_recurring

    @is_task_recurring.setter
    def is_task_recurring(self, recurs: bool):
        if recurs:
            if not self._is_term_set():
                self._set_selected_term('day')
            self._update_term()
        else:
            self._update_task(False)
            self._update_header()

        self._editor.refresh_editor()

    def _is_term_set(self):
        return self._selected_recurring_term is not None

    def _set_selected_term(self, string):
        self._selected_recurring_term = string

    def _update_term(self):
        """
        Update the header and the underlying task object.
        NOTE: You should not call this, but set the GObject property instead
        to ensure that the check in the menu is in sync.
        """
        self._update_task(True)
        self._update_header()
        self._update_calendar()

    def _update_task(self, enable=True):
        """
        Updates the task object.
        NOTE: You should not call this, but set the GObject property instead
        to ensure that the check in the menu is in sync.
        """
        if enable:
            self.task.set_recurring(enable, self._selected_recurring_term, newtask=True)
        else:
            self.task.set_recurring(enable)

    def _update_header(self):
        """ Updates the header anytime a term is selected """
        if self._is_term_set():
            if self._selected_recurring_term.isdigit():
                if len(self._selected_recurring_term) <= 2:  # Recurring monthly from selected date
                    # Translators: Recurring monthly
                    mdval = datetime.strptime(f'{self._selected_recurring_term}', '%d')
                    mdval = mdval.strftime('%d')
                    markup = _('Every <b>{month_day} of the month</b>').format(month_day=mdval)
                else:  # Recurring yearly from selected date
                    val = f'{self._selected_recurring_term[:2:]}-{self._selected_recurring_term[2::]}'
                    date = datetime.strptime(val, '%m-%d')
                    # Translators: Recurring yearly
                    markup = _('Every <b>{month} {day}</b>').format(
                        month=date.strftime('%B'), day=date.strftime('%d'))
            elif self._selected_recurring_term == 'day':  # Recurring daily
                markup = _('Every <b>day</b>')
            elif self._selected_recurring_term == 'other-day':  # Recurring every other day
                markup = _('Every <b>other day</b>')
            elif self._selected_recurring_term == 'week':  # Recurring weekly from today
                markup = _('Every <b>{week_day}</b>').format(
                    week_day=self.task.recurring_updated_date.strftime('%A'))
            elif self._selected_recurring_term == 'month':  # Recurring monthly from today
                markup = _('Every <b>{month_day} of the month</b>').format(
                    month_day=self.task.recurring_updated_date.strftime('%d'))
            elif self._selected_recurring_term == 'year':  # Recurring yearly from today
                date = self.task.recurring_updated_date
                markup = _('Every <b>{month} {day}</b>').format(
                    month=date.strftime('%B'), day=date.strftime('%d'))
            else:  # Recurring weekly from selected week day
                week_day = _(self._selected_recurring_term)
                markup = _('Every <b>{week_day}</b>').format(week_day=week_day)
            menu_item = Gio.MenuItem.new(markup, None)
            menu_item.set_attribute_value('use-markup', GLib.Variant.new_boolean(True))

            if self._is_header_menu_item_shown:
                self._menu_model.remove(0)
            self._menu_model.insert_item(0, menu_item)
            self._is_header_menu_item_shown = True

            # HACK: we need to enable use-markup on the header label,
            # this used to be the default for labels in PopoverMenus, but
            # later that bug was fixed as it wasn't intended.
            # In **extremely** recent versions of GTK4, PopoverMenu supports
            # 'use-markup' attribute on menu items to enable Pango Markup.
            # However that just doesn't work, (it is set above 100% correctly)
            # At first I wanted to bundle a patched version of GTK instead,
            # however I dicided to instead recursively traverse the widget tree
            # and enable use-markup on all our labels.
            def try_enable_markup_recursive(c: Gtk.Widget):
                for c in c:
                    try:
                        c.set_property('use-markup', True)
                    except TypeError:
                        pass
                    try_enable_markup_recursive(c)
            try_enable_markup_recursive(self)
        else:
            if self._is_header_menu_item_shown:
                self._menu_model.remove(0)

    def _update_calendar(self, update_monthly=True, update_yearly=True):
        """
        Update the calendar widgets with the correct date of the recurring
        task, if set.
        """
        self._month_calendar.set_property('month', 0)
        if self._is_term_set():
            need_month_hack = False
            if self._selected_recurring_term in ('month', 'year'):
                # Recurring monthly/yearly from 'today'
                d = self.task.recurring_updated_date.date()
                need_month_hack = self._set_selected_term == 'month'
            elif self._selected_recurring_term.isdigit():
                if len(self._selected_recurring_term) <= 2:
                    # Recurring monthly from selected date
                    d = datetime.strptime(f'{self._selected_recurring_term}', '%d')
                    need_month_hack = True
                else:
                    # Recurring yearly from selected date
                    val = f'{self._selected_recurring_term[:2:]}-{self._selected_recurring_term[2::]}'
                    d = datetime.strptime(val, '%m-%d')

                d = d.replace(year=datetime.today().year)  # Don't be stuck at 1900

            else:
                return

            if update_monthly:
                self._month_calendar.set_property('day', d.day)
            if need_month_hack:
                # Don't show that we're secretly staying on January since it has
                # 31 days
                month = datetime.today().month
                year = datetime.today().year
                while True:
                    try:
                        d = d.replace(month=month, year=year)
                        break
                    except ValueError:  # day is out of range for month
                        month += 1
                        if month == 13:
                            month = 1
                            year += 1
            if update_yearly:
                gtime = GLib.DateTime.new_local(d.year, d.month, d.day, 0, 0, 0)
                self._year_calendar.select_day(gtime)

    def _on_recurr_every_day(self, widget, action_name, param: None):
        self._set_selected_term('day')
        self.set_property('is-task-recurring', True)

    def _on_recurr_every_otherday(self, widget, action_name, param: None):
        self._set_selected_term('other-day')
        self.set_property('is-task-recurring', True)

    def _on_recurr_every_week(self, widget, action_name, param: None):
        self._set_selected_term('week')
        self.set_property('is-task-recurring', True)

    def _on_recurr_week_day(self, widget, action_name, param: GLib.Variant):
        week_day = ''.join(param.get_string())
        self._set_selected_term(week_day)
        self.set_property('is_task_recurring', True)

    def _on_recurr_month_today(self, widget, action_name, param: None):
        self._set_selected_term('month')
        self.set_property('is-task-recurring', True)

    def _on_recurr_year_today(self, widget, action_name, param: None):
        self._set_selected_term('year')
        self.set_property('is-task-recurring', True)

    @Gtk.Template.Callback()
    def _on_monthly_selected(self, widget):
        self._set_selected_term(str(self._month_calendar.props.day))
        self.set_property('is-task-recurring', True)

    @Gtk.Template.Callback()
    def _on_yearly_selected(self, widget):
        date_string = self._year_calendar.get_date().format(
            r'%m%d'
        )
        self._set_selected_term(date_string)
        self.set_property('is-task-recurring', True)
