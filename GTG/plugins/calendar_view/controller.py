from gi.repository import Gtk
from GTG.plugins.calendar_view.week_view import WeekView
from GTG.plugins.calendar_view.month_view import MonthView


class Controller(Gtk.Box):
    """
    This class is responsible for creating and controlling the Views, changing
    the current/visible view, etc. It uses a Gtk.Notebook to manage them.
    """
    WEEK, TWO_WEEKS, MONTH = ["Week", "2 Weeks", "Month"]

    def __init__(self, parent, requester):
        super(Gtk.Box, self).__init__()

        week_view = WeekView(parent, requester)
        two_weeks_view = WeekView(parent, requester, numdays=14)
        month_view = MonthView(parent, requester)

        self.views = []
        self.current_view = None

        self.notebook = Gtk.Notebook()
        self.add_view(week_view, self.WEEK)
        self.add_view(two_weeks_view, self.TWO_WEEKS)
        self.add_view(month_view, self.MONTH)

        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)
        self.show_all()

    def add_view(self, view, label):
        """
        Adds a new view to be managed by this Controller.

        @param view: a View object, the view to be added.
        @param label: string, the name the added view will have.
        """
        self.notebook.append_page(view, None)
        self.views.append((view, label))
        view.show_today()

    def get_view_labels(self):
        """
        Returns the name of the Views being managed inside the Controller.

        @return labels: list of strings, contains the name of the active views.
        """
        return [v[1] for v in self.views]

    def on_view_changed(self, view_name):
        """
        Changes the current view to @view_name.
        If there is no @view_name inside the Controller, an exception will be
        raised.

        @param view_name: string, indicates the view to be displayed.
                          It can be either "Week", "2 Weeks" or "Month".
        """
        if view_name in self.get_view_labels():
            for view, label in self.views:
                if view_name == label:
                    self.current_view = view
                    self.current_view.update_tasks()
                    break
        else:
            raise ValueError("\'%s\' is not a valid value for View Type."
                             % view_name)
            return
        page_num = self.notebook.page_num(self.current_view)
        self.notebook.set_current_page(page_num)

    def get_visible_view(self):
        """
        Returns which is the current view being displayed.

        @return current_view: a View object, the view that is currently being
                              displayed.
        """
        return self.current_view

    def update_tasks(self, widget=None, dummy1=None, dummy2=None):
        """ Updates the tasks being showed in the current View. """
        self.current_view.update_tasks()

    def new_task_callback(self, func):
        """
        Sets the callback function to add a new task in all the Views being
        managed by this Controller.

        @param func: a python fuction, the function to be called when a task
                     needs to be created.
        """
        for i in range(self.notebook.get_n_pages()):
            view = self.notebook.get_nth_page(i)
            view.new_task_callback(func)

    def edit_task_callback(self, func):
        """
        Sets the callback function to edit a task in all the Views being
        managed by this Controller.

        @param func: a python fuction, the function to be called when a task
                     needs to be edited.
        """
        for i in range(self.notebook.get_n_pages()):
            view = self.notebook.get_nth_page(i)
            view.edit_task_callback(func)

    def delete_task_callback(self, func):
        """
        Sets the callback function to delete a task in all the Views being
        managed by this Controller.

        @param func: a python fuction, the function to be called when a task
                     needs to be deleted.
        """
        for i in range(self.notebook.get_n_pages()):
            view = self.notebook.get_nth_page(i)
            view.delete_task_callback(func)
