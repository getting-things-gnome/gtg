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
        self.header = builder.get_object("recurring_headerbar")
        self.switch = builder.get_object("recurring_switch")

        # Update the editor using the task recurring status
        self.update_header()
        self.switch.set_active(task.get_recurring())

    def is_term_set(self):
        return self.selected_recurring_term is not None

    def set_selected_term(self, string):
        self.selected_recurring_term = string

    def update_task(self):
        if self.switch.get_active() and self.is_term_set():
            self.task.set_recurring(True, self.selected_recurring_term, newtask=True)
            return True
        else:
            self.task.set_recurring(False)
            return True
        return False

    def update_header(self):
        self.header.set_title(RecurringMenu.PREFIX + 
                self.selected_recurring_term if self.is_term_set() else RecurringMenu.PREFIX + '')
