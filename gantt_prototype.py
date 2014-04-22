from gi.repository import Gtk, Gdk
import cairo

class Calendar(Gtk.DrawingArea):

    def __init__(self, parent):
        self.par = parent
        super(Calendar, self).__init__()
 
        self.days = ( "3/17", "3/18", "3/19", "3/20", "3/21", "3/22", "3/23")
        self.week_days = ( "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

        # label, week_start_day, week_end_day, complete?
        self.tasks = [("task1", 0, 0, True), 
                      ("task2", 5, 5, False), 
                      ("task3", 1, 3, False),
                      ("task4", 3, 4, True),
                      ("task5", 0, 6, False),
                      ("task6: very very long task", 2, 3, False)
                      ]
 
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
        label = task[0]
        start = task[1]
        end = task[2] + 1
        complete = task[3]
        duration = end - start

        if len(label) > duration * self.step/10 + 2:
            crop_at = int(duration*(self.step/10))
            label = label[:crop_at] + "..."

        if complete:
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
        self.step = round(rect.width / 7.0)
        self.header_size = 40
        self.task_width = 20

        # printing header
        self.print_header(ctx)

        # drawing all tasks
        for t, task in enumerate(self.tasks):
            self.draw_task(ctx, task, t)
        
 
class PyApp(Gtk.Window): 

    def __init__(self):
        super(PyApp, self).__init__()
        
        Gtk.Window.__init__(self, title='Gantt Chart View')
        #self.set_title("Gantt Chart View")
        self.set_size_request(350, 280)        
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)
       
        vbox = Gtk.VBox(False, 2)

        self.calendar = Calendar(self)
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
