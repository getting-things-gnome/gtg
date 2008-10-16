#!/usr/bin/env python
#
#===============================================================================
#
# GTD-gnome: a gtd organizer for GNOME
#
# @author : B. Rousseau
# @date   : June 2008
#
#=============================================================================== 

#=== IMPORT ====================================================================

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import xml.dom.minidom
import gtk.glade
import datetime, time

#=== OBJECTS ===================================================================

class tag_utils:

    def __init__(self):
        pass

    def tags_to_string(tags):
        tag_str = ""
        for tag in tags:
            tag_str = tag_str + ',' + tag
        tag_str = tag_str[1:]
        return tag_str

    tags_to_string = staticmethod(tags_to_string)

class o_tag:
    """Tag class: define tags that can be applied to tasks"""

    def __init__(self, name=""):
        self.name   = name

class o_task:
    """Task class: define an object representing a task"""

    def __init__(self, title="", tags="", duedate=int(time.time()), is_done=False, parents=[], children=[]):
        self.title    = title
        self.tags     = tags
        self.duedate  = duedate
        self.is_done  = is_done
        self.parents  = parents
        self.children = children

    def get_list(self):
        """@return: a list containing object data"""
        d = datetime.datetime.fromtimestamp(self.duedate)
        return [self, self.title, self.tags, d.strftime("%d/%m/%Y"), self.is_done ]       

    def get_parents_str(self):
        s = ""
        for p in self.parents:
            s = s + p.title + ","
        return s[0:-1] 

class o_task_edit_dialog:
    """Class for task edition dialog window"""
    
    def __init__(self, task=None):
    
        self.gladefile = "gtd-gnome.glade"

        if (task) : self.task = task
        else      : self.task = o_task()
        
    def run(self):   
        
        #load the dialog from the glade file      
        self.wTree = gtk.glade.XML(self.gladefile, "task_edit_dlg") 
        self.dlg = self.wTree.get_widget("task_edit_dlg")
        
        #Get all of the Entry Widgets and set their text
        self.header_lbl  = self.wTree.get_widget("header_lbl")
        self.title_ent   = self.wTree.get_widget("title_ent")
        self.tag_ent     = self.wTree.get_widget("tag_ent")
        self.duedate_ent = self.wTree.get_widget("duedate_ent")
        self.is_done_ent = self.wTree.get_widget("is_done_ent")
        self.deps_tview  = self.wTree.get_widget("deps_tview")

        # Set values
        self.title_ent.set_text(self.task.title)
        self.tag_ent.set_text(tag_utils.tags_to_string(self.task.tags))
        self.duedate_ent.set_property("time",self.task.duedate)
        self.is_done_ent.set_active(self.task.is_done)
    
        # Add dependence list
        self.deps_ts = gtk.ListStore(str)
        column = gtk.TreeViewColumn("Task title", gtk.CellRendererText(), markup=0)
        column.set_resizable(False)        
        column.set_sort_column_id(0)
        self.deps_tview.append_column(column)
        for p in self.task.parents:
            self.deps_ts.append([p.title])
        self.deps_tview.set_model(self.deps_ts)

        #run the dialog and store the response        
        self.result = self.dlg.run()
        #get the value of the entry fields
        self.task.title   = self.title_ent.get_text()
        self.task.tags    = self.tag_ent.get_text().split(',')
        self.task.duedate = self.duedate_ent.get_property("time")
        self.task.is_done = self.is_done_ent.get_active()
        
        #we are done with the dialog, destory it
        self.dlg.destroy()
        
        #return the result and the wine
        return self.result,self.task

#=== MAIN CLASS ================================================================

class Base:

    def __init__(self):
        
        #Set the Glade file
        self.gladefile = "gtd-gnome.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 
        
        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", gtk.main_quit)

        #Create our dictionay and connect it
        dic = {
                "on_add_task"       : self.on_add_task,
                "on_edit_task"      : self.on_edit_task,
                "on_delete_task"    : self.on_delete_task,
                "on_mark_as_done"   : self.on_mark_as_done,
                "gtk_main_quit"     : gtk.main_quit,
                "on_select_tag" : self.on_select_tag
              }
        self.wTree.signal_autoconnect(dic)

    def add_column_to_todoview(self, title, column_id):
        
        self.task_tview = self.wTree.get_widget("task_tview")
        column = gtk.TreeViewColumn(title, gtk.CellRendererText(), markup=column_id)
        column.set_resizable(True)        
        column.set_sort_column_id(column_id)
        self.task_tview.append_column(column)        
        return column

    def on_add_task(self, widget):
        """Called when the use wants to add a task"""
        
        #Create the dialog, show it, and store the results
        task_dlg = o_task_edit_dialog()        
        result,new_task = task_dlg.run()

        if (result == gtk.RESPONSE_OK):
            self.tasks.append(new_task)
            self.task_ts.append(None, new_task.get_list())

    def on_delete_task(self, widget):
        """Called when the use wants to delete a task"""

        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()

        if (selection_iter):
            task = self.task_ts.get_value(selection_iter, self.c_task_object)
            self.tasks.remove(task)
            self.task_ts.remove(selection_iter)

    def on_edit_task(self, widget, row=None ,col=None):
        """Called when the user wants to edit a wine entry"""

        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()

        if (selection_iter):
            task = self.task_ts.get_value(selection_iter, self.c_task_object)
            # Create the wine dialog, based off of the current selection
            task_dlg = o_task_edit_dialog(task);
            result,new_task = task_dlg.run()

            if (result == gtk.RESPONSE_OK):
                """The user clicked Ok, so let's save the changes back
                into the gtk.ListStore"""
                self.task_ts.set(selection_iter
                        , self.c_task_object, new_task
                        , self.c_title,   new_task.title
                        , self.c_tags,    new_task.tags
                        , self.c_duedate, new_task.duedate
                        , self.c_isdone,  new_task.is_done)

    def on_mark_as_done(self, widget):
        """Called when the user wants to edit a wine entry"""

        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()

        if (selection_iter):
            title = self.task_ts.get_value(selection_iter, self.c_title)
            title = "<span strikethrough=\"true\">"+title+"</span>"
            self.task_ts.set_value(selection_iter, self.c_title, title)
            # Create the wine dialog, based off of the current selection
            print "DONE!"

    def on_select_tag(self, widget, row=None ,col=None):

        tag = None

        # Get the selection in the gtk.TreeView
        selection = self.tag_tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()

        if (selection_iter):
            tag = self.tag_list.get_value(selection_iter, self.c_sel_tag)

        self.task_ts = gtk.ListStore(gobject.TYPE_PYOBJECT, str, str, str, bool)

        # Populate with data
        done_tasks = []
        for t in self.tasks:
            if (tag == None) or (tag in t.tags):
                l = t.get_list()
                if not t.is_done:
                    self.task_ts.append(l)

        # Append completed task at the end of the list
        for dt in done_tasks:
            self.task_ts.append(dt)

        self.task_tview.set_model(self.task_ts)
        self.task_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)

    def open_from_xml(self, f):

        task_dict = {}
        tag_list  = []
        
        # sanitize the pretty XML
        stringed = f.read().replace('\n','').replace('\t','')
        try :
            dom = xml.dom.minidom.parseString(stringed)
        except :
            return 0

        # Create task object from each task tag
        for i in dom.getElementsByTagName("task"):

            # extract data
            id         = i.getAttribute('id')
            title      = i.getAttribute('title')
            tags       = i.getAttribute('tags').split(",")
            duedate    = int(i.getAttribute('duedate'))
            isdone     = i.getAttribute('isdone') == "True"
            par_list   = []
            par_ids    = i.getAttribute('parents').split(",")
            if par_ids != [""]:            
                for p in par_ids:
                    if p not in task_dict.keys(): task_dict[p] = o_task()
                    par_list.append(task_dict[p])
            child_list = []
            child_ids  = i.getAttribute('children').split(",")
            if child_ids != [""]:            
                for c in child_ids:
                    if c not in task_dict.keys(): task_dict[c] = o_task()
                    child_list.append(task_dict[c])

            # Convert empty tags
            undef_tags_count = len([t for t in tags if t == ''])
            for r in range(undef_tags_count): tags[tags.index('')] = "Untagged"

            # Store task in dictionary
            if id not in task_dict.keys():
                task_dict[id] = o_task(title, tags, duedate, isdone, par_list, child_list)
            else:
                task_dict[id].title    = title
                task_dict[id].tags     = tags
                task_dict[id].duedate  = duedate
                task_dict[id].is_done  = isdone
                task_dict[id].children = child_list
                task_dict[id].parents  = par_list

            # Store tags
            for tag in tags:
                if (tag not in tag_list) and tag != "Untagged": tag_list.append(tag)

        return (task_dict.values(), tag_list)

    def save_as_xml(self):

        f = open("data.xml",'w')
        doc  = xml.dom.minidom.Document()
        
        root = doc.createElement("task_list")
        doc.appendChild(root)

        for t in self.tasks:
            ti = doc.createElement("task")
            ti.setAttribute("id", str(self.tasks.index(t)))
            ti.setAttribute("title", t.title)
            ti.setAttribute("tags", tag_utils.tags_to_string(t.tags))
            ti.setAttribute("duedate", str(t.duedate))
            ti.setAttribute("isdone", str(t.is_done))
            p_idx = []
            for p in t.parents: p_idx.append(self.tasks.index(p))
            ti.setAttribute("parents", str(p_idx)[1:-1].replace(" ",""))
            c_idx = []
            for c in t.children: c_idx.append(self.tasks.index(c))
            ti.setAttribute("children", str(c_idx)[1:-1].replace(" ",""))
            root.appendChild(ti)

        f.write(doc.toprettyxml())
        f.close()

    def main(self):

        self.tasks    = []
        self.tags     = []
        
        # Open database XML file

        f = open("data.xml")
        try:    (self.tasks, self.tags) = self.open_from_xml(f)
        except: print "Could not load data file." 
    
        # Initialize model & views

        self.c_task_object = 0
        self.c_title       = 1
        self.c_tags        = 2
        self.c_duedate     = 3
        self.c_isdone      = 4

        self.task_tview = self.wTree.get_widget("task_tview")
        self.cellBool = gtk.CellRendererToggle()
        self.cell     = gtk.CellRendererText()
        col = gtk.TreeViewColumn("Actions", markup=self.c_title)
        col.pack_start(self.cellBool)
        col.pack_start(self.cell)
        col.set_resizable(True)        
        col.set_sort_column_id(self.c_title)
        col.set_attributes(self.cell, markup=1)
        col.add_attribute(self.cellBool, 'active', 5)
        #self.cellBool.connect('toggled', self.toggle_done_cb, None)
        self.task_tview.append_column(col)

        #self.add_column_to_todoview("Tags",self.c_tags)
        
        self.task_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, str, str, bool)
        self.task_tview.set_model(self.task_ts)
        self.task_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)


        # Populate with data

        visitable_tasks = []
        tasks_ts_iter   = {}

        for t in self.tasks:
            if len(t.parents) == 0: visitable_tasks.append(t)

        while len(visitable_tasks) != 0:

            t = visitable_tasks.pop()

            for p in t.parents:
                if not t.is_done:
                    ts_iter = self.task_ts.append(tasks_ts_iter[p], t.get_list())
                    tasks_ts_iter[t] = ts_iter
            if len(t.parents) == 0:
                if not t.is_done:
                   ts_iter = self.task_ts.append(None, t.get_list())
                   tasks_ts_iter[t] = ts_iter

            for c in t.children:
                visited_parents = [p for p in c.parents if p in tasks_ts_iter.keys()]  
                if len(visited_parents) == len(c.parents):
                    visitable_tasks.append(c)

        # Initialize tag model & views

        self.c_sel_tag = 0
        self.tag_tview = self.wTree.get_widget("tag_tview")
        self.cellpb   = gtk.CellRendererPixbuf()
        self.cell     = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Tags", markup=self.c_sel_tag)
        column.pack_start(self.cellpb, False)
        column.pack_start(self.cell, True)

        column.set_attributes(self.cellpb, stock_id=1)
        column.set_attributes(self.cell,   markup=2)

        column.set_resizable(True)        
        column.set_sort_column_id(self.c_sel_tag)
        self.tag_tview.append_column(column)

        self.tag_list = gtk.ListStore(str, str, str)
        self.tag_tview.set_model(self.tag_list)

        # Populate with data
        self.tag_list.append([None, None, '<span weight=\"bold\">All</span>'])
        self.tags.sort()
        for t in self.tags:
            self.tag_list.append([t,'',t])

        # Initialize folder model & views

        self.c_sel_folder = 0
        self.folder_tview = self.wTree.get_widget("folder_tview")
        self.cellpb = gtk.CellRendererPixbuf()
        self.cell   = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Folders", markup=self.c_sel_folder)
        column.pack_start(self.cellpb, False)
        column.pack_start(self.cell, True)

        column.set_attributes(self.cellpb, stock_id=1)
        column.set_attributes(self.cell,   markup=2)

        column.set_resizable(False)        
        self.folder_tview.append_column(column)

        self.folder_list = gtk.ListStore(str, str, str)
        self.folder_tview.set_model(self.folder_list)

        # Populate with data
        self.folder_list.append([None, gtk.STOCK_EXECUTE, '<span weight=\"bold\">Actions</span>'])
        self.folder_list.append([None, gtk.STOCK_DND_MULTIPLE, '<span weight=\"bold\">Projects</span>'])
        self.folder_list.append([None, gtk.STOCK_APPLY, 'Recently completed actions'])

        # start application
        gtk.main()

        # save data before exiting
        self.save_as_xml()
        
        return 0

#=== EXECUTION =================================================================

if __name__ == "__main__":
    base = Base()
    base.main()
