from gi.repository import Gtk, Gdk

from drawtask import DrawTask, TASK_HEIGHT
from all_day_tasks import AllDayTasks


class DayCell(Gtk.Dialog):
    """
    This class is a dialog that displays all the tasks in a single day. It is
    used by the MonthView, when there are more tasks to be displayed than it
    fits on the cell height.
    """

    def __init__(self, parent, day, tasks):
        self.day = day
        title = day.strftime("%a, %b %d %Y")

        Gtk.Dialog.__init__(self, title, parent, 0)

        self.all_day_tasks = AllDayTasks(self, rows=1, cols=1)
        self.all_day_tasks.connect("button-press-event", self.dnd_start)
        self.create_drawtasks(tasks)

        self.set_resizable(False)
        self.compute_size()

        box = self.get_content_area()
        box.add(self.all_day_tasks)
        self.show_all()

    def create_drawtasks(self, tasks):
        """
        Creates a list of DrawTask objects given a list of @tasks. The created
        objects contain the appropriate place where they should be drawn.

        @param tasks: a list of Task objects.
        """
        self.drawtasks = []
        for y, task in enumerate(tasks):
            dtask = DrawTask(task)
            self.drawtasks.append(dtask)
            self.set_task_position(dtask, y)
        self.all_day_tasks.set_tasks_to_draw(self.drawtasks)

    def set_task_position(self, dtask, y):
        """
        Calculates and sets the position of a @dtask.

        @param dtask: a DrawingTask object.
        @param y: integer, the row the task should appear in.
        """
        dtask.set_position(0, y, 1, 1)
        dtask.set_overflowing_L(self.day)
        dtask.set_overflowing_R(self.day)

    def compute_size(self):
        """ Computes and requests the size needed to draw everything. """
        width = 160
        height = len(self.drawtasks) * TASK_HEIGHT
        self.all_day_tasks.set_size_request(width, height)

    def dnd_start(self, widget, event):
        """ User clicked the mouse button, starting drag and drop """
        # find which task was clicked, if any
        selected_task, drag_action, cursor = \
            self.all_day_tasks.identify_pointed_object(event, clicked=True)

        if selected_task:
            # double-click opens task to edit
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                # FIXME: open TaskEditor
                print('Open \'%s\' to edit' % selected_task)
