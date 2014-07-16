from gi.repository import Gtk
from week_view import WeekView
from month_view import MonthView


class Controller(Gtk.Box):
    WEEK, TWO_WEEKS, MONTH = ["Week", "2 Weeks", "Month"]

    def __init__(self, parent, requester):
        super(Gtk.Box, self).__init__()
        self.req = requester

        self.week_view = WeekView(parent, self.req)
        self.two_weeks_view = WeekView(parent, self.req, numdays=14)
        self.month_view = MonthView(parent, self.req)

        self.week_view.show_today()
        self.two_weeks_view.show_today()
        self.month_view.show_today()
        self.current_view = None

        self.notebook = Gtk.Notebook()
        self.notebook.append_page(self.week_view, None)
        self.notebook.append_page(self.two_weeks_view, None)
        self.notebook.append_page(self.month_view, None)
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)
        self.show_all()

    def on_view_changed(self, view_type):
        """
        Set what kind of view that will be displayed.
        This will determine the number of days to show.

        @param view_type: string, indicates the view to be displayed.
         It can be either "Week", "2 Weeks" or "Month"
        """
        if view_type == self.WEEK:
            self.on_view_week()
        elif view_type == self.TWO_WEEKS:
            self.on_view_2weeks()
        elif view_type == self.MONTH:
            self.on_view_month()
        else:
            raise ValueError("\'%s\' is not a valid value for View Type."
                             % view_type)
            return
        page_num = self.notebook.page_num(self.current_view)
        self.notebook.set_current_page(page_num)

    def get_visible_view(self):
        return self.current_view

    def on_view_week(self):
        self.current_view = self.week_view
        return self.week_view

    def on_view_2weeks(self):
        self.current_view = self.two_weeks_view
        return self.two_weeks_view

    def on_view_month(self):
        self.current_view = self.month_view
        return self.month_view
