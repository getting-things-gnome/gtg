from gi.repository import Gtk, Gdk, GObject
from week_view import WeekView, TwoWeeksView, MonthView

class Controller(Gtk.DrawingArea):
    WEEK, TWO_WEEKS, MONTH = ["Week", "2 Weeks", "Month"]

    def __init__(self, parent, requester):
        super(Controller, self).__init__()
        self.req = requester
        
        self.week_view = WeekView(parent, self.req)
        self.two_weeks_view = TwoWeeksView(parent, self.req)
        self.month_view = MonthView(parent, self.req)

        # Needs GNOME 3.10
        # self.view_stack = Gtk.Stack()
        # self.view_stack.add_titled(week_view, 0, self.WEEK)
        # self.view_stack.add_titled(month_view, 1, self.MONTH)
        # self.view_stack.connect("visible-child", self.on_view_changed)

        # To call the Controller:
        # controller = Controller(self, requester)
        # self.view_switcher = Gtk.StackSwitcher()
        # self.view_switcher.set_stack(view_stack) OR
        # self.view_switcher.set_stack(controller.get_views())

    def get_selected_task(self):
        """ Returns which task is being selected. """
        return self.get_visible_view().get_selected_task()

    def unselect_task(self):
        """ Unselects the task that was selected before. """
        self.get_visible_view().unselect_task()

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
            raise ValueError("\'%s\' is not a valid value for View Type." % view_type)
            return
        self.view_type = view_type

    def get_visible_view(self):
        #return self.view_stack.get_visible_child()
        if self.view_type == self.WEEK:
            return self.on_view_week()
        if self.view_type == self.TWO_WEEKS:
            return self.on_view_2weeks()
        elif self.view_type == self.MONTH:
            return self.on_view_month()

    #def get_views(self):
    #    return self.view_stack

    def on_view_week(self):
        #self.view_stack.set_visible_child(self.week_view)
        return self.week_view

    def on_view_2weeks(self):
        #self.view_stack.set_visible_child(self.two_week_view)
        return self.two_weeks_view


    def on_view_month(self):
        #self.view_stack.set_visible_child(self.month_view)
        return self.month_view

    def update(self):
        self.get_visible_view().update()

    def next(self, days):
        self.get_visible_view().next(days)

    def previous(self, days):
        self.get_visible_view().previous(days)

    def is_today_being_shown(self):
        return self.get_visible_view().is_today_being_shown()

    def show_today(self):
        self.get_visible_view().show_today()

    def get_current_year(self):
        return self.get_visible_view().get_current_year()
