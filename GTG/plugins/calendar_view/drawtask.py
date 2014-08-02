from GTG.core.task import Task
from GTG.plugins.calendar_view.utils import convert_grid_to_screen_coord, \
    rounded_edges_or_pointed_ends_rectangle, create_vertical_gradient, \
    center_text_on_rect

TASK_HEIGHT = 30


class DrawTask:
    def __init__(self, task):
        self.task = task
        self.position = (None, None, None, None)
        self.overflow_R = False
        self.overflow_L = False

    def get_id(self):
        return self.task.get_id()

    def get_label(self):
        return self.task.get_title()

    def get_color(self, selected=False):
        # if task is selected, use yellow
        if selected:
            return (0.8, 0.8, 0)
        return self.task.get_color()

    def set_font(self, font):
        self.font = font

    def set_position(self, x, y, w, h):
        self.position = (x, y, w, h)

    def get_position(self):
        return self.position

    def is_overflowing_R(self):
        return self.overflow_R

    def is_overflowing_L(self):
        return self.overflow_L

    def set_overflowing_R(self, last_day):
        self.overflow_R = self.task.get_due_date().date() > last_day

    def set_overflowing_L(self, first_day):
        self.overflow_L = self.task.get_start_date().date() < first_day

    def is_done(self):
        return self.task.get_status() == Task.STA_DONE

    def draw(self, ctx, grid_width, padding=0, selected=False):
        task_x, task_y, task_w, task_h = self.get_position()
        pos = self.get_position()

        base_x, base_y, width, height = convert_grid_to_screen_coord(
            grid_width, TASK_HEIGHT, task_x, task_y, task_w, task_h, padding)

        # restrict drawing to exposed area: no unnecessary drawing is done
        ctx.rectangle(base_x, base_y, width, height)
        ctx.clip()

        # create path to draw task
        rounded_edges_or_pointed_ends_rectangle(ctx, base_x, base_y,
                                                width, height,
                                                self.overflow_R,
                                                self.overflow_L)

        # task color
        color = self.get_color(selected)
        if self.is_done():
            alpha = 0.5
        else:
            alpha = 1

        # background
        grad = create_vertical_gradient(base_x, base_y, height, color, alpha)
        ctx.set_source(grad)
        ctx.fill()

        # task label
        label = self.get_label()
        pos = (base_x, base_y, width, height)
        label, base_x, base_y = center_text_on_rect(ctx, label, *pos,
                                                    crop=True)
        ctx.move_to(base_x, base_y)
        ctx.set_source_rgba(1, 1, 1, alpha)
        ctx.text_path(label)
        ctx.stroke()
