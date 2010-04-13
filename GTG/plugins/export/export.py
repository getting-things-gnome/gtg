# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import with_statement
import sys
try:
    import pygtk
    pygtk.require("2.0")
except: # pylint: disable-msg=W0702
    sys.exit(1)
try:
    import gtk
except: # pylint: disable-msg=W0702
    sys.exit(1)

import os
import subprocess
import gobject
from Cheetah.Template import Template
from xdg.BaseDirectory import xdg_config_home

from GTG import _


class pluginExport:

    DEFAULT_PREFERENCES = {"menu_entry": True,
                            "toolbar_entry": True}
    PLUGIN_NAME = "export"

    def __init__(self):
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.menu_item = gtk.MenuItem("E_xport tasks")
        self.menu_item.connect('activate', self.on_export)
        self.tb_button = gtk.ToolButton(gtk.STOCK_PRINT)
        self.tb_button.connect('clicked', self.on_export)
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
                                  os.path.dirname(os.path.abspath(__file__)) + \
                                   "/export.ui"))
        self.export_dialog      = self.builder.get_object("export_dialog")
        self.export_combo_templ = self.builder.get_object("export_combo_templ")
        self.export_image       = self.builder.get_object("export_image")
        self.preferences_dialog = self.builder.get_object("preferences_dialog")
        self.pref_chbox_menu    = self.builder.get_object("pref_chbox_menu")
        self.pref_chbox_toolbar = self.builder.get_object("pref_chbox_toolbar")

        self.export_all_active         = self.builder.get_object("export_all_active_rb")
        self.export_finished_last_week = self.builder.get_object("export_finished_last_week_rb")
        self.export_all_finished       = self.builder.get_object("export_all_finished_rb")

        SIGNAL_CONNECTIONS_DIC = {
            "on_export_btn_open_clicked": 
                self.on_export_open,
            "on_export_btn_save_clicked": 
                self.on_export_save,
            "on_export_dialog_delete_event": 
                self.on_export_cancel,
            "on_export_combo_templ_changed":
                self.on_export_combo_changed,
            "on_preferences_dialog_delete_event":
                self.on_preferences_cancel,
            "on_btn_preferences_cancel_clicked":
                self.on_preferences_cancel,
            "on_btn_preferences_ok_clicked":
                self.on_preferences_ok
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

    def activate(self, plugin_api):
        self.menu_entry = False
        self.toolbar_entry = False
        self.plugin_api = plugin_api
        self.preferences_load()
        self.preferences_apply()
        self.plugin_api.set_parent_window(self.export_dialog)

    def onTaskClosed(self, plugin_api):
        pass

    def onTaskOpened(self, plugin_api):
        pass

    def deactivate(self, plugin_api):
        if self.menu_entry:
            plugin_api.remove_menu_item(self.menu_item)
        if self.toolbar_entry:
            plugin_api.remove_toolbar_item(self.tb_button)
        self.menu_entry = False
        self.toolbar_entry = False

## CALLBACK AND CORE FUNCTIONS #################################################

    class TaskStr:
        def __init__(self,
                     title,
                     text,
                     subtasks,
                     status,
                     modified,
                     due_date,
                     closed_date,
                     start_date,
                     days_left,
                     tags
                    ):
            self.title         = title
            self.text          = text
            self.subtasks      = subtasks
            self.status        = status
            self.modified      = modified
            self.due_date      = due_date
            self.closed_date   = closed_date
            self.start_date    = start_date
            self.days_left     = days_left
            self.tags          = tags
        has_title         = property(lambda s: s.title       != "")
        has_text          = property(lambda s: s.text        != "")
        has_subtasks      = property(lambda s: s.subtasks    != [])
        has_status        = property(lambda s: s.status      != "")
        has_modified      = property(lambda s: s.modified    != "")
        has_due_date      = property(lambda s: s.due_date    != "")
        has_closed_date   = property(lambda s: s.closed_date != "")
        has_start_date    = property(lambda s: s.start_date  != "")
        has_days_left     = property(lambda s: s.days_left   != "")
        has_tags          = property(lambda s: s.tags        != [])

    def on_export(self, widget):
        #Generating lists
        self.export_template_paths = [xdg_config_home + "/gtg/export_templates/",
                    os.path.dirname(os.path.abspath(__file__)) + \
                                      "/export_templates/"]
        template_list = []
        for dir in self.export_template_paths: 
            if os.path.exists(dir):
                template_list = filter(lambda str: str.startswith("template_"),
                                  os.listdir(dir))
        #Creating combo-boxes
        self.export_combo_decorator(self.export_combo_templ, template_list)
        self.export_dialog.show_all()

    def on_export_cancel(self, widget = None, data = None):
        self.export_dialog.hide()
        return True

    def on_export_combo_changed(self, widget = None):
        if self.export_check_template():
            image_path = os.path.dirname(self.export_template_path)
            image_path = image_path + '/' + os.path.basename(\
                 self.export_template_path).replace("template_","thumbnail_")
            if  os.path.isfile(image_path):
                pixbuf = gtk.gdk.pixbuf_new_from_file(image_path)
                [w,h] = self.export_image.get_size_request()
                pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
                self.export_image.set_from_pixbuf(pixbuf)
            else:
                self.export_image.clear()

    def export_check_template(self):
        #Check template file 
        #NOTE: if two templates have the same name, the user provided one takes
        #      precedence over ours
        supposed_template = self.combo_get_text(self.export_combo_templ)
        if supposed_template == None:
            return False
        self.export_combo_active = self.export_combo_templ.get_active()
        supposed_template_paths = map (lambda x: x + supposed_template,
                                       self.export_template_paths)
        template_paths = filter (lambda x: os.path.isfile(x),
                                 supposed_template_paths)
        if len(template_paths) >0:
            template_path = template_paths[0]
        else:
            return False
        self.export_template_path = template_path
        self.export_template_filename = supposed_template
        return True

    def task_to_TaskStr(self, task):
        return self.TaskStr(task.get_title(),
                           str(task.get_text()),
                           [],
                           task.get_status(),
                           str(task.get_modified()),
                           str(task.get_due_date()),
                           str(task.get_closed_date()),
                           str(task.get_start_date()),
                           str(task.get_days_left()),
                           map(lambda t: t.get_name(), task.get_tags()))

    def is_task_in_timespan (self, task, days):
        if not days:
            return True
        elif days < 0 and task.get_closed_date():
            age = task.get_closed_date().days_left() * (-1)
            if age <= days*(-1):
                return True
        elif days > 0 and task.get_days_left() <= days:
            return True
        return False

    def treemodel_to_TaskStr(self, model, task_iter, days=None):
        """This function performs a depth-first tree visits on a treemodel 
            using task_iter as root. For each node of the tree it encounters,
            it generates a TaskStr object and returns that.
            The resulting TaskStr will be linked to its subtasks in the same
            way as the treemodel, forming a tree"""
        tasks_str = []
        while task_iter:
            task = model.get_value(task_iter, 1) # tagtree.COL_OBJ)
            task_str = self.task_to_TaskStr(task)
            if model.iter_has_child(task_iter):
                task_str.subtasks = \
                    self.treemodel_to_TaskStr(model, model.iter_children(task_iter), days)
            #The task_str is added to the result only if it satisfies the time
            # limit imposed with the @days parameter of this function
            if self.is_task_in_timespan(task, days):
                    tasks_str.append(task_str)

            task_iter = model.iter_next(task_iter)
        return tasks_str

    def taskslist_to_TaskStr(self, tasks_list, days=None):
        """This function performs several depth-first tree visits on a task_list 
            using each task of the list as  root.
            For each node of the tree it encounters, it generates a TaskStr 
            object and returns that.
            The resulting TaskStr will be linked to its subtasks in the same
            way as the treemodel, forming a tree"""
        tasks_str = []
        for task in tasks_list:
            task_str = self.task_to_TaskStr(task)
            if task.has_subtasks():
                requester = self.plugin_api.get_requester()
                task_str.subtasks = self.taskslist_to_TaskStr(task.get_subtasks(), days)
            #The task_str is added to the result only if it satisfies the time
            # limit imposed with the @days parameter of this function
            if self.is_task_in_timespan(task, days):
                    tasks_str.append(task_str)

        return tasks_str

    def export_generate(self):
        #Template loading and cutting
        if self.export_all_active.get_active():
            #Export the active tasks in the current view (the ones visible in
            # the Task Browser
            model = self.plugin_api.get_task_modelsort()
            tasks_str = self.treemodel_to_TaskStr(model, model.get_iter_first())
        elif self.export_finished_last_week.get_active() or \
                        self.export_all_finished.get_active():
            #Export done tasks
            model = self.plugin_api.get_ctask_modelsort()
            #Step 1:
            # Generate the list of task_ids in the current browser view (if a
            # tag is selected, only the closed task with that tag will be
            #visible
            task_iter = model.get_iter_first()
            tids_list = []
            while task_iter:
                task = model.get_value(task_iter, 1) # tagtree.COL_OBJ)
                task_iter = model.iter_next(task_iter)
                tids_list.append(task.get_id())
            #Step 2:
            #Create the task list with all the root {"Done", "Dismissed"}
            #tasks, that is all the tasks whose parents' status is not one of
            #those, or which simply have no parent
            task_iter = model.get_iter_first()
            tids_set = set(tids_list)
            tasks_list = []
            while task_iter:
                task = model.get_value(task_iter, 1) # tagtree.COL_OBJ)
                task_iter = model.iter_next(task_iter)
                if tids_set.isdisjoint(set(task.get_parents())):
                    if task.get_status() == task.STA_DONE:
                        tasks_list.append(task)
            if self.export_finished_last_week.get_active():
                timespan = -7
            else:
                timespan = None
            tasks_str = self.taskslist_to_TaskStr(tasks_list, timespan)

        parameters_dict = {'tasks': tasks_str,
                           'plugin_api': self.plugin_api}
        self.export_document = str(Template (file = self.export_template_path,
                         searchList = [parameters_dict]))
        return True

    def export_execute_with_ui(self):
        call = [(self.export_check_template, _("Template not found")),\
                (self.export_generate      , _("Can't load the template file") )]
        for step in call:
            if not step[0]():
                dialog = gtk.MessageDialog(parent = \
                     self.export_dialog,
                     flags = gtk.DIALOG_DESTROY_WITH_PARENT,
                     type = gtk.MESSAGE_ERROR,
                     buttons=gtk.BUTTONS_OK,
                     message_format=step[1])
                dialog.run() 
                dialog.destroy()
                return False
        return True

    def export_save_file(self, output_path):
        with open(output_path, 'w+b') as file:
            file.write(self.export_document)

    def on_export_open(self, widget = None):
        if not self.export_execute_with_ui():
            return
        path = '/tmp/' + self.export_template_filename
        self.export_save_file(path)
        subprocess.Popen(['xdg-open', path])

    def on_export_save(self, widget = None):
        if not self.export_execute_with_ui():
            return
        chooser = gtk.FileChooserDialog(\
                title = _("Choose where to save your list"),
                parent = self.export_dialog,
                action = gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons = (gtk.STOCK_CANCEL,
                           gtk.RESPONSE_CANCEL,
                           gtk.STOCK_SAVE,
                           gtk.RESPONSE_OK))
        chooser.set_do_overwrite_confirmation(True)
        desktop_dir = self.get_user_dir("XDG_DESKTOP_DIR")
        #NOTE: using ./scripts/debug.sh, it doesn't detect the Desktop
        # dir, as the XDG directories are changed. That is why during 
        # debug it defaults to the Home directory ~~Invernizzi~~
        if desktop_dir != None and os.path.exists(desktop_dir):
            chooser.set_current_folder(desktop_dir)
        else:
            chooser.set_current_folder(os.environ['HOME'])
        chooser.set_default_response(gtk.RESPONSE_OK)
        response = chooser.run()
        filename = chooser.get_filename()
        chooser.destroy()
        if response == gtk.RESPONSE_OK and filename != None:
            self.export_save_file(filename)
        self.on_export_cancel()


## HELPER FUNCTIONS ############################################################

    def empty_tree_model(self, model):
        if model == None: 
            return
        iter = model.get_iter_first()
        while iter:
            this_iter =  iter
            iter = model.iter_next(iter)
            model.remove(this_iter)

    def combo_list_store(self, list_store, list_obj):
        if list_store == None:
            list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.empty_tree_model(list_store)
        for elem in list_obj:
            iter = list_store.append()
            list_store.set(iter, 0, elem)
        return self.export_list_store

    def combo_completion(self, list_store):
        completion = gtk.EntryCompletion()
        completion.set_minimum_key_length(0)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_model(list_store)

    def combo_set_text(self, combobox, entry):
        model = combobox.get_model()
        index = combobox.get_active()
        if index > -1:
            entry.set_text(model[index][0])

    def combo_get_text(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return None
        return model[active][0]

    def export_combo_decorator(self, combobox, list_obj):
        first_run = not hasattr(self, "export_combo_templ_entry")
        if first_run:
            self.export_combo_templ_entry = gtk.Entry()
            combobox.add(self.export_combo_templ_entry)
            self.export_list_store = gtk.ListStore(gobject.TYPE_STRING)
            self.export_combo_templ_entry.set_completion(
                        self.combo_completion(self.export_list_store))
            combobox.set_model(self.export_list_store)
            combobox.connect('changed', self.combo_set_text,
                         self.export_combo_templ_entry )
            #render the combo-box drop down menu
            cell = gtk.CellRendererText()
            combobox.pack_start(cell, True)
            combobox.add_attribute(cell, 'text', 0) 
       #wrap the combo-box if it's too long
        if len(list_obj) > 15:
            combobox.set_wrap_width(5)
        #populate the combo-box
        self.combo_list_store(self.export_list_store, list_obj)
        if not hasattr(self, "export_combo_active"):
            self.export_combo_active = 0
        combobox.set_active(self.export_combo_active)

    def get_user_dir(self, key):
        """
        http://www.freedesktop.org/wiki/Software/xdg-user-dirs
            XDG_DESKTOP_DIR
            XDG_DOWNLOAD_DIR
            XDG_TEMPLATES_DIR
            XDG_PUBLICSHARE_DIR
            XDG_DOCUMENTS_DIR
            XDG_MUSIC_DIR
            XDG_PICTURES_DIR
            XDG_VIDEOS_DIR

        Taken from FrontBringer
        (distributed under the GNU GPL v3 license),
        courtesy of Jean-François Fortin Tam.
        """
        user_dirs_dirs = os.path.expanduser(xdg_config_home + "/user-dirs.dirs")
        if os.path.exists(user_dirs_dirs):
            f = open(user_dirs_dirs, "r")
            for line in f.readlines():
                if line.startswith(key):
                    return os.path.expandvars(line[len(key)+2:-2])

## Preferences methods #########################################################

    def is_configurable(self):
        """A configurable plugin should have this method and return True"""
        return True

    def configure_dialog(self, plugin_apis, manager_dialog):
        self.preferences_load()
        self.preferences_dialog.set_transient_for(manager_dialog)
        self.pref_chbox_menu.set_active(self.preferences["menu_entry"])
        self.pref_chbox_toolbar.set_active(self.preferences["toolbar_entry"])
        self.preferences_dialog.show_all()

    def on_preferences_cancel(self, widget = None, data = None):
        self.preferences_dialog.hide()
        return True

    def on_preferences_ok(self, widget = None, data = None):
        self.preferences["menu_entry"] = self.pref_chbox_menu.get_active()
        self.preferences["toolbar_entry"] = self.pref_chbox_toolbar.get_active()
        self.preferences_apply()
        self.preferences_store()
        self.preferences_dialog.hide()

    def preferences_load(self):
        data = self.plugin_api.load_configuration_object(self.PLUGIN_NAME,\
                                                         "preferences")
        if data == None or type(data) != type (dict()):
            self.preferences = self.DEFAULT_PREFERENCES
        else:
            self.preferences = data

    def preferences_store(self):
        self.plugin_api.save_configuration_object(self.PLUGIN_NAME,\
                                                  "preferences", \
                                                  self.preferences)

    def preferences_apply(self):
        if self.preferences["menu_entry"] and self.menu_entry == False:
            self.plugin_api.add_menu_item(self.menu_item)
            self.menu_entry = True
        elif self.preferences["menu_entry"]==False and self.menu_entry == True:
            self.plugin_api.remove_menu_item(self.menu_item)
            self.menu_entry = False

        if self.preferences["toolbar_entry"] and self.toolbar_entry == False:
            self.plugin_api.add_toolbar_item(self.tb_button)
            self.toolbar_entry = True
        elif self.preferences["toolbar_entry"]==False and self.toolbar_entry == True:
            self.plugin_api.remove_toolbar_item(self.tb_button)
            self.toolbar_entry = False

