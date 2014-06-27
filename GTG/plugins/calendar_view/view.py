import abc
import datetime
from tasks import Task


class ViewBase:
    __metaclass__ = abc.ABCMeta  # marks methods of this class as abstract

    def __init__(self, parent, requester):
        self.par = parent
        self.req = requester

        self.header = None
        self.background = None

        self.numdays = None
        self.selected_task = None

    def get_selected_task(self):
        """ Returns which task is being selected. """
        if self.selected_task:
            return self.selected_task.task

    def unselect_task(self):
        """ Unselects the task that was selected before. """
        self.selected_task = None

    @abc.abstractmethod
    def first_day(self):
        """ Returns the first day of the view being displayed """
        return

    @abc.abstractmethod
    def last_day(self):
        """ Returns the last day of the view being displayed """
        return

    @abc.abstractmethod
    def update(self):
        """ Updates all the content whenever a change is required. """
        return

    @abc.abstractmethod
    def next(self, days=None):
        """
        Advances the dates being displayed by a given number of @days.

        @param days: integer, the number of days to advance.
         If none is given, the default self.numdays will be used.
        """
        return

    @abc.abstractmethod
    def previous(self, days=None):
        """
        Regresses the dates being displayed by a given number of @days.

        @param days: integer, the number of days to go back.
         If none is given, the default self.numdays will be used.
        """
        return

    @abc.abstractmethod
    def show_today(self):
        """
        Shows the range of dates in the current view with the date
        corresponding to today among it.
        """
        return

    def is_in_days_range(self, task):
        """
        Returns true if the given @task have either the start or due days
        between the current first and last day being displayed.
        Useful to know if @task should be drawn in the current screen.

        @param task: a Task object
        """
        return (task.get_due_date().date() >= self.first_day()) and \
               (task.get_start_date().date() <= self.last_day())

    def get_current_year(self):
        """
        Gets the correspondent year of the days
        being displayed in the calendar view
        """
        if self.first_day().year != self.last_day().year:
            return ("%s / %s" % (self.first_day().year, self.last_day().year))
        return str(self.first_day().year)

    def is_today_being_shown(self):
        """
        Returns true if the date for today is being
        shown in the current view
        """
        today = datetime.date.today()
        return today >= self.first_day() and today <= self.last_day()

    @abc.abstractmethod
    def dnd_start(self, widget, event):
        """ User clicked the mouse button, starting drag and drop """
        return

    @abc.abstractmethod
    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        return

    @abc.abstractmethod
    def dnd_stop(self, widget, event):
        """ User released a button, stopping drag and drop. """
        return

    def add_new_task(self, title, start_date, due_date, color):
        new_task = self.req.new_task()
        new_task.set_title(title)
        new_task.set_start_date(start_date)
        new_task.set_due_date(due_date)
        new_task.set_color(color)
        self.update()

    def edit_task(self, tid, new_title=None, new_start_date=None,
                  new_due_date=None, is_done=False):
        task = self.req.get_task(tid)
        if new_title:
            task.set_title(new_title)
        if new_start_date:
            task.set_start_date(new_start_date)
        if new_due_date:
            task.set_due_date(new_due_date)
        if is_done is not None:
            if is_done:
                task.set_status(Task.STA_DONE)
            else:
                task.set_status(Task.STA_ACTIVE)
        self.update()

    def delete_task(self, tid):
        self.req.delete_task(tid)
        self.unselect_task()
        self.update()
