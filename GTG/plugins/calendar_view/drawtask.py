#from gi.repository import Gtk, Gdk, GObject
import cairo
import datetime
from tasks import Task

TASK_HEIGHT = 30

def rounded_edges_or_pointed_ends_rectangle(ctx, x, y, w, h, r=8, arrow_right=False,
                                            arrow_left=False):
  """
  Draws a rectangle with either rounded edges, or with right and/or left pointed
  ends. The non-pointed end, if any, will have rounded edges as well.

    x      w   @param ctx: a Cairo context
    v      v   @param x: the leftmost x coordinate of the bounding box
  y> A****BQ   @param y: the topmost y coordinate of the bounding box
    H      C   @param w: the width of the bounding box
    J      K   @param h: the height of the bounding box
    G      D   @param r: the radius of the rounded edges. Default = 8
  h> F****E    @param arrow_right: bool, whether there should be an arrow to the right
               @param arrow_left: bool, whether there should be an arrow to the left
  """
  ctx.move_to(x+r,y)                        # Move to A
  ctx.line_to(x+w-r,y)                      # Straight line to B
  if arrow_right:
    ctx.line_to(x+w, y+h/2)                 # Straight line to K
    ctx.line_to(x+w-r, y+h)                 # Straight line to E
  else:
    ctx.curve_to(x+w,y,x+w,y,x+w,y+r)       # Curve to C, Control points are both at Q
    ctx.line_to(x+w,y+h-r)                  # Move to D
    ctx.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h) # Curve to E
  ctx.line_to(x+r,y+h)                      # Line to F
  if arrow_left:
    ctx.line_to(x, y+h/2)                   # Straight line to J
    ctx.line_to(x+r, y)                     # Straight line to A
  else:
    ctx.curve_to(x,y+h,x,y+h,x,y+h-r)       # Curve to G
    ctx.line_to(x,y+r)                      # Line to H
    ctx.curve_to(x,y,x,y,x+r,y)             # Curve to A

class DrawTask():
    def __init__(self, task):
        #super(Task, self).__init__()
        self.task = task
        self.position = (None, None, None, None)
        self.selected = False
        self.PADDING = 5
        self.header_size = 40

    def get_id(self):
        return self.task.get_id()

    def set_day_width(self, day_width):
        self.day_width = day_width

    def set_position(self, x, y, w, h):
        self.position = (x, y, w, h)

    def get_position(self):
        return self.position

    def draw(self, ctx, pos, start_day, end_day, selected=False): #area):
    #def draw_task(self, ctx, task, pos):
        """
        Draws a given @task in a relative postion @pos.

        @param ctx: a Cairo context
        """
        # avoid tasks overflowing to/from next/previous weeks
        view_start_day = start_day
        view_end_day = end_day

        overflow_l = overflow_r = False
        if self.task.get_start_date().date() < view_start_day:
          overflow_l = True
        if self.task.get_due_date().date() > view_end_day:
          overflow_r = True

        start = (max(self.task.get_start_date().date(), view_start_day) - view_start_day).days
        end = (min(self.task.get_due_date().date(), view_end_day) - view_start_day).days
        duration = end - start + 1
        label = self.task.get_title()
        complete = self.task.get_status()

        if len(label) > duration * self.day_width/12 + 2:
            crop_at = int(duration*(self.day_width/12))
            label = label[:crop_at] + "..."

        if complete == Task.STA_DONE:
            alpha = 0.5
        else:
            alpha = 1

        # getting bounding box rectangle for task duration
        base_x = start * self.day_width
        base_y = self.header_size + pos * TASK_HEIGHT
        width = duration * self.day_width
        height = TASK_HEIGHT
        base_y += self.PADDING
        height -= self.PADDING

        # restrict drawing to exposed area, so that no unnecessary drawing is done
        ctx.save()
        ctx.rectangle(base_x, base_y, width, height)
        ctx.clip()

        # draw the task
        rounded_edges_or_pointed_ends_rectangle(ctx, base_x, base_y, width, height,
                                                arrow_right=overflow_r, arrow_left=overflow_l)

        # keep record of positions for discovering task when using drag and drop
        #self.task_positions[task.get_id()] = (base_x, base_y, width, height)
        self.set_position(base_x, base_y, width, height)

        color = self.task.get_color()

        # selected task in yellow
        if selected:
        #if self.selected_task == self.get_id():
          color = (0.8, 0.8, 0)

        # create gradient
        grad = cairo.LinearGradient(base_x, base_y, base_x, base_y+height)
        c = [x + 0.1 for x in color]
        grad.add_color_stop_rgba(0, c[0], c[1], c[2], alpha)
        grad.add_color_stop_rgba(0.2, color[0], color[1], color[2], alpha)
        grad.add_color_stop_rgba(0.8, color[0], color[1], color[2], alpha)
        grad.add_color_stop_rgba(1, c[0], c[1], c[2], alpha)

        # background
        ctx.set_source(grad)
        ctx.fill()

        # printing task label
        ctx.set_source_rgba(1, 1, 1, alpha)
        (x, y, w, h, dx, dy) = ctx.text_extents(label)
        base_x = (start+duration/2.0) * self.day_width - w/2.0
        base_y = self.header_size + pos*TASK_HEIGHT + (TASK_HEIGHT)/2.0 + h
        #base_y += self.PADDING
        ctx.move_to(base_x, base_y)
        ctx.text_path(label)
        ctx.stroke()

        # restore old context
        ctx.restore()
