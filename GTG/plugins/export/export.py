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

import os
import gtk
import shutil
import gobject
import tempfile
import threading
import subprocess
from Cheetah.Template  import Template as CheetahTemplate
from xdg.BaseDirectory import xdg_config_home

from GTG                          import _
from GTG.plugins.export.task_str  import tree_to_TaskStr
from GTG.plugins.export.templates import TemplateFactory
from GTG.tools.logger             import Log



class pluginExport:


    def __init__(self):
        '''Initialize all the GTK widgets'''
        self.__init_gtk()

    def activate(self, plugin_api):
        '''loads the saved preferences'''
        self.plugin_api = plugin_api
        self.preferences_load()
        self.preferences_apply()

    def deactivate(self, plugin_api):
        '''Removes the gtk widgets before quitting'''
        self.__gtk_deactivate()

## CALLBACK AND CORE FUNCTIONS ################################################

    def load_template(self):
        self.template = TemplateFactory().create_template(\
                                            self.combo_get_path(self.combo))
        return self.template

    def export_generate(self, document_ready):
        #Template loading and cutting
        timespan = None
        if self.export_all_active.get_active():
            tree = self.plugin_api.get_requester().get_tasks_tree(name='active')
            tree.apply_filter('active')
        elif self.export_all_finished.get_active():
            tree = self.plugin_api.get_requester().get_tasks_tree(name='closed')
            tree.apply_filter('closed')
        elif self.export_finished_last_week.get_active():
            tree = self.plugin_api.get_requester().get_tasks_tree(name='closed')
            tree.apply_filter('closed')
            timespan = -7
        meta_root_node = tree.get_root()
        root_nodes = [tree.get_node(c)
                                        for c in meta_root_node.get_children()]
        tasks_str = tree_to_TaskStr(tree, root_nodes, self.plugin_api, timespan)
        document = str(CheetahTemplate(
                                file = self.template.get_path(),
                                searchList = [{'tasks':      tasks_str,
                                               'plugin_api': self.plugin_api}]))
        self.__purge_saved_document()
        #we save the created document in a temporary file with the same suffix
        #as the template (it's script-friendly)
        with tempfile.NamedTemporaryFile(\
                            suffix = ".%s" % self.template.get_suffix(),
                            delete = False) as f:
            f.write(document)
            self.document_path = f.name
        if self.template.get_script_path():
            def __script_worker(self):
                try:
                    self.document_path = \
                        subprocess.Popen(args = ['/bin/sh',
                                             '-c',
                                             self.template.get_script_path() + \
                                             " " + self.document_path],
                                            shell = False,
                                            stdout = subprocess.PIPE\
                                    ).communicate()[0]
                except:
                    pass
                if self.document_path == "ERROR":
                    Log.debug("Document creation failed")
                    self.document_path = None
                document_ready.set()
            worker_thread = threading.Thread(
                            target = __script_worker,
                            args   = (self, ))
            worker_thread.setDaemon(True)
            worker_thread.start()
        else:
            document_ready.set()

    def export_execute_with_ui(self, document_ready):
        if not self.load_template():
            self.show_error_dialog(_("Template not found"))
            return False
        #REMOVE ME
        try:
            self.export_generate(document_ready)
        except Exception, e:
            self.show_error_dialog( \
                            _("Could not generate the document: %s") % e)
            return False
        return True

    def on_export_open(self, widget = None, saving = False):
        document_ready = threading.Event()
        self.export_execute_with_ui(document_ready)
        self.save_button.set_sensitive(False)
        self.open_button.set_sensitive(False)
        if saving:
            filename = self.__get_filename_from_gtk_dialog()
        else:
            filename = None
        def __wait_for_document_ready(self, document_ready, filename, saving):
            document_ready.wait()
            if filename:
                if saving:
                    shutil.copyfile(self.document_path, filename)
            else:
                subprocess.Popen(['xdg-open', self.document_path])
            gobject.idle_add(self.save_button.set_sensitive, True)
            gobject.idle_add(self.open_button.set_sensitive, True)

        event_thread = threading.Thread( \
                        target = __wait_for_document_ready,
                        args = (self, document_ready, filename, saving))
        event_thread.setDaemon(True)
        event_thread.start()

    def on_export_save(self, widget = None):
        self.on_export_open(saving = True)

    def hide(self):
        self.__gtk_hide()
        self.__purge_saved_document()

    def __purge_saved_document(self):
        try:
            os.remove(self.document_path)
        except:
            pass

## GTK FUNCTIONS #############################################################

    def __init_gtk(self):
        self.menu_entry = False
        self.toolbar_entry = False
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.menu_item = gtk.MenuItem(_("Export the tasks currently listed"))
        self.menu_item.connect('activate', self.__gtk_activate)
        self.tb_button = gtk.ToolButton(gtk.STOCK_PRINT)
        self.tb_button.connect('clicked', self.__gtk_activate)
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
                                  os.path.dirname(os.path.abspath(__file__)) + \
                                   "/export.ui"))
        self.combo = self.builder.get_object("export_combo_templ")
        self.export_dialog      = self.builder.get_object("export_dialog")
        self.export_image       = self.builder.get_object("export_image")
        self.preferences_dialog = self.builder.get_object("preferences_dialog")
        self.pref_chbox_menu    = self.builder.get_object("pref_chbox_menu")
        self.pref_chbox_toolbar = self.builder.get_object("pref_chbox_toolbar")
        self.description_label  = self.builder.get_object("label_description")
        self.save_button        = self.builder.get_object("export_btn_save")
        self.open_button        = self.builder.get_object("export_btn_open")

        self.export_all_active         = self.builder.get_object("export_all_active_rb")
        self.export_finished_last_week = self.builder.get_object("export_finished_last_week_rb")
        self.export_all_finished       = self.builder.get_object("export_all_finished_rb")

        SIGNAL_CONNECTIONS_DIC = {
            "on_export_btn_open_clicked": 
                self.on_export_open,
            "on_export_btn_save_clicked": 
                self.on_export_save,
            "on_export_dialog_delete_event": 
                self.__gtk_hide,
            "on_export_combo_templ_changed":
                self.__on_combo_changed,
            "on_preferences_dialog_delete_event":
                self.on_preferences_cancel,
            "on_btn_preferences_cancel_clicked":
                self.on_preferences_cancel,
            "on_btn_preferences_ok_clicked":
                self.on_preferences_ok
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

    def __gtk_activate(self, widget):
        #Populating combo boxes
        self.export_dialog.set_transient_for(\
                                self.plugin_api.get_ui().get_window())
        self.combo_decorator(self.combo, TemplateFactory().get_templates_paths())
        self.export_dialog.show_all()

    def __gtk_deactivate(self):
        try:
            self.plugin_api.remove_menu_item(self.menu_item)
        except:
            pass
        self.menu_entry = False
        try:
            self.plugin_api.remove_toolbar_item(self.tb_button)
        except:
            pass
        self.toolbar_entry = False

    def __gtk_hide(self, sender = None, data = None):
        self.export_dialog.hide()

    def __on_combo_changed(self, widget = None):
        if self.load_template():
            image_path = self.template.get_image_path()
            if image_path:
                pixbuf = gtk.gdk.pixbuf_new_from_file(image_path)
                [w,h] = self.export_image.get_size_request()
                pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
                self.export_image.set_from_pixbuf(pixbuf)
            else:
                self.export_image.clear()
        description = self.template.get_description()
        self.description_label.set_markup("<i>%s</i>" % description)

    def empty_tree_model(self, model):
        if model == None:
            return
        iter = model.get_iter_first()
        while iter:
            this_iter =  iter
            iter = model.iter_next(iter)
            model.remove(this_iter)

    def combo_list_store(self, list_store, a_list):
        if list_store == None:
            list_store = gtk.ListStore(gobject.TYPE_STRING,
                                       gobject.TYPE_STRING)
        self.empty_tree_model(list_store)
        for template_path in a_list:
            iter = list_store.append()
            list_store.set(iter, 0,
                 TemplateFactory().create_template(template_path).get_title())
            list_store.set(iter, 1, template_path)
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

    def combo_get_path(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return None
        return model[active][1]

    def combo_decorator(self, combobox, a_list):
        first_run = not hasattr(self, "combo_templ_entry")
        if first_run:
            self.combo_templ_entry = gtk.Entry()
            combobox.add(self.combo_templ_entry)
            self.export_list_store = gtk.ListStore(gobject.TYPE_STRING,
                                                    gobject.TYPE_STRING)
            self.combo_templ_entry.set_completion(
                        self.combo_completion(self.export_list_store))
            combobox.set_model(self.export_list_store)
            combobox.connect('changed', self.combo_set_text,
                         self.combo_templ_entry)
            #render the combo-box drop down menu
            cell = gtk.CellRendererText()
            combobox.pack_start(cell, True)
            combobox.add_attribute(cell, 'text', 0) 
       #wrap the combo-box if it's too long
        if len(a_list) > 15:
            combobox.set_wrap_width(5)
        #populate the combo-box
        self.combo_list_store(self.export_list_store, a_list)
        if not hasattr(self, "combo_active"):
            self.combo_active = 0
        combobox.set_active(self.combo_active)

    def show_error_dialog(self, message):
        dialog = gtk.MessageDialog(
            parent         = self.export_dialog,
            flags          = gtk.DIALOG_DESTROY_WITH_PARENT,
            type           = gtk.MESSAGE_ERROR,
            buttons        = gtk.BUTTONS_OK,
            message_format = message)
        dialog.run() 
        dialog.destroy()

    def __get_filename_from_gtk_dialog(self):
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
        if response == gtk.RESPONSE_OK:
            return filename
        else:
            return None

## Helper methods ############################################################

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

    DEFAULT_PREFERENCES = {"menu_entry":     True,
                            "toolbar_entry": True}
    PLUGIN_NAME = "export"

    def is_configurable(self):
        """A configurable plugin should have this method and return True"""
        return True

    def configure_dialog(self, manager_dialog):
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

