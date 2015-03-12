# -*- coding: utf-8 -*-
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

import datetime

from gi.repository import GObject, Gdk, Gtk

from GTG.gtk.editor import GnomeConfig
from GTG.tools.dates import Date


class GTGCalendar(GObject.GObject):
    """ Wrapper around Gtk.Calendar object """

    # CONSTANTS
    DATE_KIND_DUE = "due"
    DATE_KIND_START = "start"
    DATE_KIND_CLOSED = "closed"

    # Gobject signal description
    __signal_type__ = (GObject.SignalFlags.RUN_FIRST,
                       None,
                       [])

    __gsignals__ = {'date-changed': __signal_type__, }

    def __init__(self):
        super(GTGCalendar, self).__init__()
        self.__builder = Gtk.Builder()
        self.__builder.add_from_file(GnomeConfig.CALENDAR_UI_FILE)
        self.__date_kind = None
        self.__date = Date.no_date()
        self.__init_gtk__()

    def __init_gtk__(self):
        self.__window = self.__builder.get_object("calendar")
        self.__calendar = self.__builder.get_object("calendar1")
        self.__fuzzydate_btns = self.__builder.get_object("fuzzydate_btns")
        self.__builder.get_object("button_clear").connect(
            "clicked", lambda w: self.__day_selected(w, ""))
        self.__builder.get_object("button_now").connect(
            "clicked", lambda w: self.__day_selected(w, "now"))
        self.__builder.get_object("button_soon").connect(
            "clicked", lambda w: self.__day_selected(w, "soon"))
        self.__builder.get_object("button_someday").connect(
            "clicked", lambda w: self.  __day_selected(w, "someday"))

    def set_date(self, date, date_kind):
        self.__date_kind = date_kind
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            self.__fuzzydate_btns.show()
        else:
            self.__fuzzydate_btns.hide()
        if not date:
            # we set the widget to today's date if there is not a date defined
            date = Date.today()
        self.__date = date
        if not date.is_fuzzy():
            self.__calendar.select_day(date.day)
            # Calendar use 0..11 for a month so we need -1
            # We can't use conversion through python's datetime
            # because it is often an invalid date
            self.__calendar.select_month(date.month - 1, date.year)

    def __mark_today_in_bold(self):
        """ Mark today in bold

        If the current showed month is the current month (has the same year
        and month), then make the current day bold. Otherwise no day should
        be bold.
        """
        today = datetime.date.today()

        # Get the current displayed month
        # (month must be corrected because calendar is 0-based)
        year, month, day = self.__calendar.get_date()
        month += 1

        if today.year == year and today.month == month:
            self.__calendar.mark_day(today.day)
        else:
            # If marked day is 31th, and the next month does not have 31th day,
            # unmark_day raises a warning. Clear_marks() is clever way how
            # to let GTK solve it's bussiness.
            self.__calendar.clear_marks()

    def move_calendar_inside(self, width, height, x, y):
        """ This method moves the calender inside the screen whenever part of
        it is displayed outside the screen """
        screen_width = Gdk.Screen.width()
        # To display calendar inside the screen when editor window is
        # outside leftside of the screen
        if x < width:
            self.__window.move(2, y - height)
        # To display calendar inside the screen when editor window is outside
        # rightside of the screen
        elif x > (screen_width - 2):
            self.__window.move(screen_width - width - 2, y - height)
        else:
            self.__window.move(x - width, y - height)

    def show_at_position(self, x, y):
        width, height = self.__window.get_size()
        self.move_calendar_inside(width, height, x, y)
        self.__window.show()
        self.__window.grab_add()

        # We grab the pointer in the calendar
        # Gdk.pointer_grab(
        #   self.__window.get_window(),
        #   True,
        #   Gdk.ModifierType.BUTTON1_MASK | Gdk.ModifierType.MOD2_MASK
        # )
        # FIXME THIS DOES NOT WORK!!!!!!!
        Gdk.pointer_grab(
            self.get_window(),
            True,
            # Gdk.ModifierType.BUTTON1_MASK | Gdk.ModifierType.MOD2_MASK,
            # FIXME!!!! JUST GUESSING THE TYPE
            Gdk.EventMask.ALL_EVENTS_MASK,
            None,
            None,
            0,
        )

        if self.get_decorated():
            self.__window.connect("delete-event", self.close_calendar)
        else:
            self.__window.connect('button-press-event', self.__focus_out)
        self.__sigid = self.__calendar.connect("day-selected",
                                               self.__day_selected,
                                               "RealDate",)

        self.__sigid_month = self.__calendar.connect("month-changed",
                                                     self.__month_changed)
        # Problem: Gtk.Calendar does not tell you directly if the
        #          "day-selected" signal was caused by the user clicking on
        #          a date, or just browsing the calendar.
        # Solution: we track that in a variable
        self.__is_user_just_browsing_the_calendar = False
        self.__mark_today_in_bold()

    def __focus_out(self, w=None, e=None):
        # We should only close if the pointer click is out of the calendar !
        p = self.__window.get_window().get_pointer()
        s = self.__window.get_size()
        if not(0 <= p[1] <= s[0] and 0 <= p[2] <= s[1]):
            self.close_calendar()

    def close_calendar(self, widget=None, e=None):
        self.__window.hide()
        Gdk.pointer_ungrab(0)
        self.__window.grab_remove()
        if self.__sigid is not None:
            self.__calendar.disconnect(self.__sigid)
            self.__sigid = None

        if self.__sigid_month is not None:
            self.__calendar.disconnect(self.__sigid_month)
            self.__sigid_month = None
        return True

    def __day_selected(self, widget, date_type):
        if date_type == "RealDate":
            calendar_date = self.__calendar.get_date()
            date = self.__from_calendar_date_to_datetime(calendar_date)
            self.__date = Date(date)
        else:
            self.__date = Date(date_type)

        if self.__is_user_just_browsing_the_calendar:
            # this day-selected signal was caused by a month/year change
            self.__is_user_just_browsing_the_calendar = False
        else:
            # inform the Editor that the date has changed
            self.close_calendar()
            GObject.idle_add(self.emit, "date-changed")

    def __from_calendar_date_to_datetime(self, calendar_date):
        '''
        Gtk.Calendar uses a 0-based convention for counting months.
        The rest of the world, including the datetime module, starts from 1.
        This is a converter between the two. GTG follows the datetime
        convention.
        '''
        year, month, day = calendar_date
        return datetime.date(year, month + 1, day)

    def __month_changed(self, widget):
        self.__is_user_just_browsing_the_calendar = True
        self.__mark_today_in_bold()

    def get_selected_date(self):
        return self.__date, self.__date_kind

    def __getattr__(self, attr):
        return getattr(self.__window, attr)
