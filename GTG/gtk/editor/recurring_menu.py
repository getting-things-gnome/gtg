from gi.repository import Gdk, Gtk, Pango
class RecurringMenu():
    """ RecurringMenu provides a simple layer of abstraction
    for the menu where the user enables a task to be repeating
    """
    PREFIX = "Every: "

    def __init__(self, task, builder):
        # General attributes
        self.selected_recurring_term = task.get_recurring_term()
        self.task = task
        # Getting the necessary Gtk objects
        self.title = builder.get_object("title_label")
        self.repeat_button = builder.get_object("repeat_checkbutton")
        self.repeat_icon = builder.get_object("repeat_icon")
        self.icon_style = self.repeat_icon.get_style_context()

        # Update the editor using the task recurring status
        self.update_header()
        self.repeat_button.set_active(task.get_recurring())
        if task.get_recurring():
            self.icon_style.add_class('recurring-active')

    def is_term_set(self):
        return self.selected_recurring_term is not None

    def set_selected_term(self, string):
        self.selected_recurring_term = string

    def update_task(self):
        if self.repeat_button.get_active() and self.is_term_set():
            self.task.set_recurring(True, self.selected_recurring_term, newtask=True)
            self.icon_style.remove_class('recurring-inactive')
            self.icon_style.add_class('recurring-active')
            return True
        else:
            self.task.set_recurring(False)
            self.icon_style.remove_class('recurring-active')
            self.icon_style.add_class('recurring-inactive')
            return True
        return False

    def update_header(self):
        self.title.set_text(RecurringMenu.PREFIX + 
                self.selected_recurring_term if self.is_term_set() else RecurringMenu.PREFIX + '')
