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

from gi.repository import GObject, GLib, Gtk

from GTG.gtk.editor import GnomeConfig
from GTG.core.dates import Date


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
        super().__init__()
        self.__builder = Gtk.Builder()
        self.__builder.add_from_file(GnomeConfig.CALENDAR_UI_FILE)
        self.__date_kind = None
        self.__date = Date.no_date()
        self.__init_gtk__()

    def __init_gtk__(self):
        self.__window = self.__builder.get_object("calendar")
        self.__window.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("Escape"),
            Gtk.CallbackAction.new(self._esc_close)
        ))
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
            gtime = GLib.DateTime.new_local(
                date.date().year, date.date().month, date.date().day, 0, 0, 0
            )
            self.__calendar.select_day(gtime)

    def show(self):
        self.__window.show()

        if self.get_decorated():
            self.__window.connect("close-request", self.close_calendar)
        else:
            window_gesture_single = Gtk.GestureSingle()
            window_gesture_single.connect('begin', self.__focus_out)
            self.__window.add_controller(window_gesture_single)
        self.__sigid = self.__calendar.connect("day-selected",
                                               self.__day_selected,
                                               "RealDate",)
        # Problem: Gtk.Calendar does not tell you directly if the
        #          "day-selected" signal was caused by the user clicking on
        #          a date, or just browsing the calendar.
        # Solution: we track that in a variable
        self.__is_user_just_browsing_the_calendar = False

    def __focus_out(self, g=None, s=None):
        w = g.get_widget()
        # We should only close if the pointer click is out of the calendar !
        p = self.__window.get_window().get_pointer()
        s = self.__window.get_size()
        if not(0 <= p[1] <= s[0] and 0 <= p[2] <= s[1]):
            self.close_calendar()

    def close_calendar(self, widget=None, e=None):
        self.__window.hide()
        if self.__sigid is not None:
            self.__calendar.disconnect(self.__sigid)
            self.__sigid = None

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
            GLib.idle_add(self.emit, "date-changed")

    def __from_calendar_date_to_datetime(self, calendar_date):
        """
        Gtk.Calendar uses a GLib based convention for counting time.
        The rest of the world, including the datetime module, doesn't use GLib.
        This is a converter between the two. GTG follows the datetime
        convention.
        """
        year, month, day = (calendar_date.get_year(),
                            calendar_date.get_month(),
                            calendar_date.get_day_of_month())
        return datetime.date(year, month, day)

    def __month_changed(self, widget):
        self.__is_user_just_browsing_the_calendar = True

    def get_selected_date(self):
        return self.__date, self.__date_kind

    def __getattr__(self, attr):
        return getattr(self.__window, attr)

    def _esc_close(self, widget=None, args=None):
        """
        Callback: Close this window when pressing Escape.
        """
        self.close_calendar()
        return True
