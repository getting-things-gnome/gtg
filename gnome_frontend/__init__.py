#This is the gnome_frontend package. It's a GTK interface that want to be
#simple, HIG compliant and well integrated with Gnome.

#Files are :

#project_ui.py
#-------------
#This is the interface to create or edit a project.

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

#Gtg-gnome.glade
#---------------
#This is the glade file of the interface. It should be noted that the TextView
#widget in the TaskEditor is dummy and is replaced at runtime by a TaskView.

class GnomeConfig :
    GLADE_FILE = "gnome_frontend/gtd-gnome.glade"
    
    MARK_DONE="Mark as done"
    MARK_UNDONE="Undone"
    MARK_DISMISS="Dismiss"
    MARK_UNDISMISS="Undismiss"
