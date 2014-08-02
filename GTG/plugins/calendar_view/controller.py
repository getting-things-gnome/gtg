from gi.repository import Gtk
from GTG.plugins.calendar_view.week_view import WeekView
#from GTG.plugins.calendar_view.month_view import MonthView


class Controller(Gtk.Box):
    WEEK, TWO_WEEKS, MONTH = ["Week", "2 Weeks", "Month"]

    def __init__(self, parent, requester):
        super(Gtk.Box, self).__init__()

        week_view = WeekView(parent, requester)
        two_weeks_view = WeekView(parent, requester, numdays=14)
        # month_view = MonthView(parent, requester)

        self.views = []
        self.current_view = None

        self.notebook = Gtk.Notebook()
        self.add_view(week_view, self.WEEK)
        self.add_view(two_weeks_view, self.TWO_WEEKS)
        # self.add_view(month_view, self.MONTH)

        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)
        self.show_all()

    def add_view(self, view, label):
        self.notebook.append_page(view, None)
        self.views.append((view, label))
        view.show_today()

    def get_view_labels(self):
        return [v[1] for v in self.views]

    def on_view_changed(self, view_type):
        """
        Set what kind of view that will be displayed.
        This will determine the number of days to show.

        @param view_type: string, indicates the view to be displayed.
         It can be either "Week", "2 Weeks" or "Month"
        """
        if view_type in self.get_view_labels():
            for view, label in self.views:
                if view_type == label:
                    self.current_view = view
                    self.current_view.update_tasks()
                    break
        else:
            raise ValueError("\'%s\' is not a valid value for View Type."
                             % view_type)
            return
        page_num = self.notebook.page_num(self.current_view)
        self.notebook.set_current_page(page_num)

    def get_visible_view(self):
        return self.current_view

    def update_tasks(self, widget=None, dummy1=None, dummy2=None):
        self.current_view.update_tasks()

    def new_task_callback(self, func):
        for i in range(self.notebook.get_n_pages()):
            view = self.notebook.get_nth_page(i)
            view.new_task_callback(func)

    def edit_task_callback(self, func):
        for i in range(self.notebook.get_n_pages()):
            view = self.notebook.get_nth_page(i)
            view.edit_task_callback(func)

    def delete_task_callback(self, func):
        for i in range(self.notebook.get_n_pages()):
            view = self.notebook.get_nth_page(i)
            view.delete_task_callback(func)
