import os

class GnomeConfig :
    current_rep = os.path.dirname(os.path.abspath(__file__))
    GLADE_FILE    = os.path.join(current_rep,"taskeditor.glade")
    
    MARK_DONE = "Mark as done"
    MARK_UNDONE = "Mark as not done"
    MARK_DISMISS = "Dismiss"
    MARK_UNDISMISS = "Undismiss"
    KEEP_NOTE = "Keep as Note"
    MAKE_TASK = "Make a Task"
    
    #Number of second between to save in the task editor
    SAVETIME = 10
