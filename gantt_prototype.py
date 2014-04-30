from gi.repository import Gtk
import cairo
import datetime
from tasks import Task
from datastore import DataStore

def date_generator(start, end = None, numdays = None):
    """ 
    Generates a tuple (days, weekdays), such that days is a list of strings in
    the format ' %m/%d', and weekdays is a list of strings in the format '%a'.
    Both tuples have a specific size, so that they represent the days starting
    from @start.
    The lists will either end on a given @end date, or will have size @numdays.
    If the end date is specified, the numdays parameter is ignored - unless end
    is before start. If neither parameter is specified, the list will have size
    7 (a week).

    @param start: must be a datetime object, first date to be included in the list
    @param end: must be a datetime object, last date in the list. Default = None
    @param numdays: size of the list. Only considered if @end is not given. Default = 7 days
    @return days: list of strings containing dates in the format '%m/%d'
    @return weekdays: list of strings containing abbreviated weekdays for the dates in @days
    """
    #base = datetime.datetime.strptime(start, '%Y-%m-%d')
    if end and end > start:
        numdays = (end - start).days + 1
    elif not numdays:
        numdays = 7
    date_list = [start + datetime.timedelta(days=x) for x in range(numdays)]
    days = [x.strftime("%m/%d") for x in date_list]
    weekdays = [x.strftime("%a") for x in date_list]
    return days, weekdays
    
class Calendar(Gtk.DrawingArea):

    def __init__(self, parent, ex_tasks = None):
        self.par = parent
        super(Calendar, self).__init__()

        # DataStore object
        self.data = DataStore()
        if ex_tasks:
            self.data.populate(ex_tasks) #hard-coded tasks

        self.view_start_day = self.view_end_day = self.numdays = None
        self.view_start_day = min([t.get_start_date().date() for t in self.data.get_all_tasks()])
        #self.view_end_day = max([t.get_due_date().date() for t in self.data.get_all_tasks()])

        #only for tests:
        #self.view_start_day = self.view_start_day - datetime.timedelta(days=2)
        #self.view_end_day = self.view_end_day + datetime.timedelta(days=1) 
        #if not self.view_end_day:
        #    self.numdays = 10

        (self.days, self.week_days) = date_generator(self.view_start_day, self.view_end_day, self.numdays)
        self.numdays = len(self.days)
 
        #self.set_size_request(-1, 30)
        self.connect("draw", self.draw)
    
    def print_header(self, ctx):
        ctx.set_source_rgb(0.35, 0.31, 0.24) 
        for i in range(0, len(self.week_days)):
            ctx.move_to(i*self.step, 5)
            ctx.line_to(i*self.step, 35)
            ctx.stroke()

            (x, y, w, h, dx, dy) = ctx.text_extents(self.week_days[i])
            ctx.move_to(i*self.step - (w-self.step)/2.0, 15) 
            ctx.text_path(self.week_days[i])
            ctx.stroke()

            (x, y, w, h, dx, dy) = ctx.text_extents(self.days[i])
            ctx.move_to(i*self.step - (w-self.step)/2.0, 30) 
            ctx.text_path(self.days[i])
            ctx.stroke()

        ctx.move_to(len(self.week_days)*self.step, 5)
        ctx.line_to(len(self.week_days)*self.step, 35)
        ctx.stroke()
        
    def draw_task(self, ctx, task, t):
        label = task.get_title()
        start = (task.get_start_date().date() - self.view_start_day).days
        end = (task.get_due_date().date() - self.view_start_day).days + 1
        complete = task.get_status()
        duration = end - start

        if len(label) > duration * self.step/10 + 2:
            crop_at = int(duration*(self.step/10))
            label = label[:crop_at] + "..."

        if complete == Task.STA_DONE:
            alpha = 0.5
        else:
            alpha = 1

        # drawing rectangle for task duration 
        ctx.set_source_rgba(0.5, start/6.0, end/6.0, alpha)
        ctx.rectangle(start*self.step, self.header_size+t*self.task_width, duration * self.step, self.task_width)
        ctx.fill()

        # printing task label
        ctx.set_source_rgba(1, 1, 1, alpha)
        (x, y, w, h, dx, dy) = ctx.text_extents(label)
        ctx.move_to((start+duration/2.0)*self.step-w/2.0, self.header_size+(t+1)*self.task_width-h/2.0)
        ctx.text_path(label)
        ctx.stroke()

    def draw(self, widget, ctx): 
        ctx.set_line_width(0.8)
        ctx.select_font_face("Courier", cairo.FONT_SLANT_NORMAL, 
                            cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(11)

        rect = self.get_allocation()
        self.step = round(rect.width / float(self.numdays))
        self.header_size = 40
        self.task_width = 20

        # printing header
        self.print_header(ctx)

        # drawing all tasks
        for t, task in enumerate(self.data.get_all_tasks()):
            self.draw_task(ctx, task, t)
        
 
class PyApp(Gtk.Window): 

    def __init__(self):
        super(PyApp, self).__init__()
        
        self.set_title("Gantt Chart View")
        self.set_size_request(350, 280)        
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)
       
        vbox = Gtk.VBox(False, 2)

        # hard coded tasks to populate calendar view
        # (title, start_date, due_date, done?)
        ex_tasks = [("task1", "2014-03-17", "2014-03-17", True), 
                    ("task2", "2014-03-22", "2014-03-22", False), 
                    ("task3", "2014-03-18", "2014-03-20", False),
                    ("task4", "2014-03-20", "2014-03-21", True),
                    ("task5", "2014-03-17", "2014-03-23", False),
                    ("task6: very very long task", "2014-03-19", "2014-03-20", False),
                    ("task7", "2014-03-22", "2014-03-24", False)
                   ]

        self.calendar = Calendar(self, ex_tasks)
        vbox.pack_start(self.calendar, True, True, 0)

        # for use in the future
        self.label = Gtk.Label("...")
        fix = Gtk.Fixed()
        fix.put(self.label, 40, 10)
        vbox.pack_end(fix, False, False, 0)

        self.add(vbox)
        self.show_all()
    

PyApp()
Gtk.main()
