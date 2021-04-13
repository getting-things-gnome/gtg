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

from gettext import gettext as _
from datetime import datetime

class RecurringMenu():
    """Provides a simple layer of abstraction
       for the menu where the user enables a task to be repeating
    """

    def __init__(self, requester, tid, builder):
        # General attributes
        self.task = requester.get_task(tid)
        self.selected_recurring_term = self.task.get_recurring_term()

        # Getting the necessary Gtk objects
        self.title = builder.get_object('title_label')
        self.title_separator = builder.get_object('title_separator')
        self.repeat_checkbox = builder.get_object('repeat_checkbutton')
        self.repeat_icon = builder.get_object('repeat_icon')
        self.icon_style = self.repeat_icon.get_style_context()
        self.stack = builder.get_object('main_stack')
        self.page1 = builder.get_object('stack_main_box')

        # Update the editor using the task recurring status
        self.update_header()
        self.repeat_checkbox.set_active(self.task.get_recurring())
        if self.task.get_recurring():
            self.icon_style.add_class('recurring-active')

    def update_repeat_button_icon(self, active=True):
        """ Update the icon color of the repeat-menu-button in the task editor """
        if active:
            self.icon_style.add_class('recurring-active')
        else:
            self.icon_style.remove_class('recurring-active')

    def is_term_set(self):
        return self.selected_recurring_term is not None

    def set_selected_term(self, string):
        self.selected_recurring_term = string

    def update_repeat_checkbox(self):
        """
        Update the task object recurring status and all indicators
        according to the repeat-checkbox-button status
        """
        if self.repeat_checkbox.get_active():
            if not self.is_term_set():
                self.set_selected_term('day')
            self.update_term()
            self.update_repeat_button_icon()
        else:
            self.update_task(False)
            self.update_repeat_button_icon(active=False)

    def update_term(self):
        """
        Update the header and the task object(only if the repeat-checkbutton is checked)
        when a new term was selected
        """
        if not self.repeat_checkbox.get_active():
            self.repeat_checkbox.set_active(True)
        self.update_task(True)
        self.update_header()

    def update_task(self, enable=True):
        """ Updates the task object """
        if enable:
            self.task.set_recurring(enable, self.selected_recurring_term, newtask=True)
        else:
            self.task.set_recurring(enable)

    def update_header(self):
        """ Updates the header anytime a term is selected """
        if self.is_term_set():
            if self.selected_recurring_term.isdigit():
                if len(self.selected_recurring_term) <= 2 : # Recurring monthly from selected date
                    # Translators: Recurring monthly
                    self.title.set_markup(_('Every <b>{month_day} of the month</b>').format(month_day=datetime.strptime(f'{self.selected_recurring_term}', '%d').strftime('%d')))
                else: # Recurring yearly from selected date
                    date = datetime.strptime(f'{self.selected_recurring_term[:2:]}-{self.selected_recurring_term[2::]}', '%m-%d')
                    # Translators: Recurring yearly
                    self.title.set_markup(_('Every <b>{month} {day}</b>').format(month=date.strftime('%B'), day=date.strftime('%d')))
            elif self.selected_recurring_term == 'day': # Recurring daily
                self.title.set_markup(_('Every <b>day</b>'))
            elif self.selected_recurring_term == 'other-day': # Recurring every other day
                self.title.set_markup(_('Every <b>other day</b>'))
            elif self.selected_recurring_term == 'week': # Recurring weekly from today
                self.title.set_markup(_('Every <b>{week_day}</b>').format(week_day=self.task.get_recurring_updated_date().date().strftime('%A')))
            elif self.selected_recurring_term == 'month': # Recurring monthly from today
                self.title.set_markup(_('Every <b>{month_day} of the month</b>').format(month_day=self.task.get_recurring_updated_date().date().strftime('%d')))
            elif self.selected_recurring_term == 'year': # Recurring yearly from today
                date = self.task.get_recurring_updated_date().date()
                self.title.set_markup(_('Every <b>{month} {day}</b>').format(month=date.strftime('%B'), day=date.strftime('%d')))
            else: # Recurring weekly from selected week day
                week_day = _(self.selected_recurring_term)
                self.title.set_markup(_('Every <b>{week_day}</b>').format(week_day=week_day))
            self.title.show()
            self.title_separator.show()
        else:
            self.title.hide()
            self.title_separator.hide()

    def reset_stack(self):
        """ Reset popup stack to the first page """
        self.stack.set_transition_duration(0)
        self.stack.set_visible_child(self.page1)
        self.stack.set_transition_duration(200)
