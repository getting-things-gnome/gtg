from gi.repository import Gdk, Gtk, Pango

class RecurringMenu():
    """ RecurringMenu provides a simple layer of abstraction
    for the menu where the user enables a task to be repeating
    """
    PREFIX = "Every "

    def __init__(self, task, builder):
        # General attributes
        self.selected_recurring_term = task.get_recurring_term()
        self.task = task
        # Getting the necessary Gtk objects
        self.title = builder.get_object("title_label")
        self.title_separator = builder.get_object("title_separator")
        self.repeat_button = builder.get_object("repeat_checkbutton")
        self.repeat_icon = builder.get_object("repeat_icon")
        self.icon_style = self.repeat_icon.get_style_context()

        # Update the editor using the task recurring status
        self.update_header()
        self.repeat_button.set_active(task.get_recurring())
        if task.get_recurring():
            self.icon_style.add_class('recurring-active')

    def update_repeat_button(self, active=True):
        if active:
            self.icon_style.add_class('recurring-active')
        else:
            self.icon_style.remove_class('recurring-active')

    def is_term_set(self):
        return self.selected_recurring_term is not None

    def set_selected_term(self, string):
        self.selected_recurring_term = string

    def update_tick(self):
        if self.repeat_button.get_active():
            if not self.update_task(True):
                # we have to reset the button to off, if no term is selected.
                self.repeat_button.set_active(False)
            else:
                self.update_repeat_button()
        else:
            self.update_task(False)
            self.update_repeat_button(active=False)

    def update_term(self):
        self.update_header()
        if self.repeat_button.get_active():
            self.update_task(True)

    def update_task(self, enable=True):
        """ Updates the task object """
        done = False
        if enable:
            if self.is_term_set():
                self.task.set_recurring(enable, self.selected_recurring_term, newtask=True)
                done = True
        else:
            self.task.set_recurring(enable)
            done = True
        return done
            
    def update_header(self):
        """ Updates the header anytime a term is selected """
        if self.is_term_set():
            self.title.show()
            self.title_separator.show()
            self.title.set_markup(f"{RecurringMenu.PREFIX} <b>{self.selected_recurring_term}</b>")
        else:
            self.title.hide()
            self.title_separator.hide()
