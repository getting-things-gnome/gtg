import abc
import datetime
from GTG.core.task import Task


class ViewBase:
    __metaclass__ = abc.ABCMeta  # marks methods of this class as abstract

    def __init__(self, parent, requester):
        self.par = parent
        self.req = requester

        self.header = None
        self.background = None

        self.numdays = None
        self.selected_task = None

        # callbacks to set
        self.edit_task = None
        self.add_new_task  = None
        self.delete_task = None

    def get_selected_task(self):
        """ Returns which task is being selected. """
        return self.selected_task

    def set_selected_task(self, task_id):
        """ Sets which task is the selected task. """
        self.selected_task = task_id

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

    def edit_task_callback(self, func):
        """
        Callback function to edit a task

        @param func: the function to be called in order to edit the task
        """
        self.edit_task = func

    def new_task_callback(self, func):
        """
        Callback function to add a new task

        @param func: the function to be called in order to add the new task
        """
        self.add_new_task = func

    def delete_task_callback(self, func):
        """
        Callback function to delete a task

        @param func: the function to be called to perform the deletion
        """
        self.delete_task = func

    def ask_add_new_task(self, start_date, due_date):
        """
        Adds a new task with @start_date and @due_date, and updates the View.

        @param start_date: datetime object, the start date of the new Task
        @param due_date: datetime object, the due date of the new Task
        """
        new_task = self.req.new_task()
        new_task.set_start_date(start_date)
        new_task.set_due_date(due_date)
        self.add_new_task(new_task.get_id())
        self.set_selected_task(new_task.get_id())
        self.update()

    def ask_edit_task(self, task_id):
        """
        Edits a task given by @task_id and updates the View.

        @param task_id: str, the id of a Task to be edited
        """
        self.edit_task(task_id)
        self.update()

    def ask_delete_task(self, task_id):
        """
        Deletes a task given by @task_id and updates the View.

        @param task_id: str, the id of a Task to be deleted
        """
        self.delete_task(task_id=task_id)
        self.unselect_task()
        self.update()
