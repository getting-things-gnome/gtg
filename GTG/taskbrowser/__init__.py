#This is the gnome_frontend package. It's a GTK interface that want to be
#simple, HIG compliant and well integrated with Gnome.

#Files are :

#Taskbrowser.py
#--------------
#This is the main interface with the list of tasks

#Taskeditor.py
#-------------
#This is the window that contains one and only one task.
#The main part of the window is the TaskView widget.

#Taskview.py
#-----------
#TaskView is an implementation of the gtk.TextView widget. TaskView widget
#is used in the TaskEditor.

#Taskviewserial.py
#-----------------
#Contains the functions used to serialize and deserialize the content of
#the Gtk.TextBuffer (our task)

#Gtg-gnome.glade
#---------------
#This is the glade file of the interface. It should be noted that the TextView
#widget in the TaskEditor is dummy and is replaced at runtime by a TaskView.
import os

class GnomeConfig :
    current_rep = os.path.dirname(os.path.abspath(__file__))
    GLADE_FILE    = os.path.join(current_rep,"taskbrowser.glade")
    
    MARK_DONE      = "Mark as done"
    MARK_UNDONE    = "Mark as not done"
    MARK_DISMISS   = "Dismiss"
    MARK_UNDISMISS = "Undismiss"
