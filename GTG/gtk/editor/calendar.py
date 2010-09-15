# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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
import gobject
import gtk
from gtk import gdk
import datetime

from GTG.tools               import dates



class GTGCalendar(gobject.GObject):
    '''
    Wrapper around gtk.Calendar object
    '''

    #CONSTANTS
    DATE_KIND_DUE = "due"
    DATE_KIND_START = "start"
    DATE_KIND_CLOSED = "closed"

    #Gobject signal description
    __signal_type__ = (gobject.SIGNAL_RUN_FIRST,
                       gobject.TYPE_NONE,
                       [])

    __gsignals__ = {'date-changed': __signal_type__, }


    def __init__(self, gtk_builder):
        super(GTGCalendar, self).__init__()
        self.__builder = gtk_builder
        self.__date_kind = None
        self.__date = dates.NoDate()
        self.__init_gtk__()

    def __init_gtk__(self):
        self.__window = self.__builder.get_object("calendar")
        self.__calendar = self.__builder.get_object("calendar1")
        self.__fuzzydate_btns = self.__builder.get_object("fuzzydate_btns")
        self.__builder.get_object("button_clear").connect("clicked",
                                    lambda w: self.__day_selected(w, "NoDate"))
        self.__builder.get_object("button_now").connect("clicked",
                                    lambda w: self.__day_selected(w, "FuzzyNow"))
        self.__builder.get_object("button_soon").connect("clicked",
                                    lambda w: self.__day_selected(w, "FuzzySoon"))
        self.__builder.get_object("button_later").connect("clicked",
                                    lambda w: self.__day_selected(w, "FuzzyLater"))

    def set_date(self, date, date_kind):
        self.__date_kind = date_kind
        if date_kind in (GTGCalendar.DATE_KIND_DUE):
            self.__fuzzydate_btns.show()
        else:
            self.__fuzzydate_btns.hide()
        if not date:
            # we set the widget to today's date if there is not a
            #date defined
            date = dates.date_today()
        self.__date = date
        if isinstance(date, dates.RealDate):
            self.__calendar.select_day(date.day())
            cal_date = self.__from_datetime_to_calendar(date.to_py_date())
            self.__calendar.select_month(cal_date.month, cal_date.year)

    def __mark_today_in_bold(self):
        today = datetime.date.today()
        date = self.__from_calendar_date_to_datetime(\
                                        self.__calendar.get_date())
        #if it's an actual RealDate, and the month and year coincide with
        #today's date
        if not isinstance(self.__date, dates.FuzzyDate) and \
               date.year == today.year and date.month == today.month:
            self.__calendar.mark_day(today.day)
        else:
            self.__calendar.unmark_day(today.day)


    def show_at_position(self, x, y):
        width, height = self.__window.get_size()
        self.__window.move(x - width, y - height)
        self.__window.show()
        ##some window managers ignore move before you show a window. (which
        # ones? question by invernizzi)
        self.__window.move(x - width, y - height)
        self.__window.grab_add()
        #We grab the pointer in the calendar
        gdk.pointer_grab(self.__window.window, True,
                         gdk.BUTTON1_MASK | gdk.MOD2_MASK)
        self.__window.connect('button-press-event', self.__focus_out)
        self.__sigid = self.__calendar.connect("day-selected",
                                               self.__day_selected,
                                              "RealDate")
        self.__sigid_month = self.__calendar.connect("month-changed",
                                                     self.__month_changed)
        #Problem: gtk.Calendar does not tell you directly if the "day-selected"
        #         signal was caused by the user clicking on a date, or just
        #         browsing the calendar.
        #Solution: we track that in a variable
        self.__is_user_just_browsing_the_calendar = False
        self.__mark_today_in_bold()

    def __focus_out(self, w = None, e = None):
        #We should only close if the pointer click is out of the calendar !
        p = self.__window.window.get_pointer()
        s = self.__window.get_size()
        if not(0 <= p[0] <= s[0] and 0 <= p[1] <= s[1]):
            self.close_calendar()

    def close_calendar(self, widget = None, e = None):
        self.__window.hide()
        gtk.gdk.pointer_ungrab()
        self.__window.grab_remove()
        try:
            self.__calendar.disconnect(self.__sigid)
        except:
            pass
        try:
            self.__calendar.disconnect(self.__sigid_month)
        except:
            pass

    def __day_selected(self, widget, date_type):
        self.__date_type = date_type
        if date_type == "RealDate":
            date = self.__from_calendar_date_to_datetime(\
                                        self.__calendar.get_date())
            #we check that the user isn't just browsing the calendar
            self.__date = dates.RealDate(date)
        elif date_type == "NoDate":
            self.__date = dates.no_date
        elif date_type == "FuzzyNow":
            self.__date = dates.NOW
        elif date_type == "FuzzySoon":
            self.__date = dates.SOON
        elif date_type == "FuzzyLater":
            self.__date = dates.LATER
        if self.__is_user_just_browsing_the_calendar:
            #this day-selected signal was caused by a month/year change. 
            # We discard it
            self.__is_user_just_browsing_the_calendar = False
        else:
            self.close_calendar()
            #we inform the Editor that the date has changed
            gobject.idle_add(self.emit, "date-changed")
            try:
                self.__calendar.disconnect(self.__mouse_sigid)
            except:
                pass

    def __from_calendar_date_to_datetime(self, calendar_date):
        '''
        gtk.Calendar uses a 0-based convention for counting months.
        The rest of the world, including the datetime module, starts from 1.
        This is a converter between the two. GTG follows the datetime
        convention.
        '''
        year, month, day = calendar_date
        return datetime.date(year, month + 1, day)

    def __from_datetime_to_calendar(self, date):
        '''Opposite of __from_calendar_date_to_datetime'''
        return datetime.date(date.year, date.month - 1, date.day)

    def __month_changed(self, widget):
        self.__is_user_just_browsing_the_calendar = True
        self.__mark_today_in_bold()

    def get_selected_date(self):
        return self.__date, self.__date_kind

    def __getattr__(self, attr):
        return getattr(self.__window, attr)
