# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
#               2012 - Izidor Matušov <izidor.matusov@gmail.com>
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

""" Export plugin
Plugin for exporting into nice lists in TXT, HTML or PDF """

import os
import shutil
import webbrowser
import subprocess

from xdg.BaseDirectory import xdg_config_home
import gobject
import gtk

from GTG import _
from GTG.plugins.export.task_str import get_task_wrappers
from GTG.plugins.export.templates import Template, get_templates_paths


# Enforce external dependencies
for dependence in "pdflatex", "pdftk", "pdfjam":
    retval = subprocess.call(["which", dependence], stdout=subprocess.PIPE)
    if retval != 0:
        raise ImportError("Missing command %s" % dependence)


def get_user_dir(key):
    """
    http://www.freedesktop.org/wiki/Software/xdg-user-dirs
     - XDG_DESKTOP_DIR
     - XDG_DOWNLOAD_DIR
     - XDG_TEMPLATES_DIR
     - XDG_PUBLICSHARE_DIR
     - XDG_DOCUMENTS_DIR
     - XDG_MUSIC_DIR
     - XDG_PICTURES_DIR
     - XDG_VIDEOS_DIR

    Taken from FrontBringer
    (distributed under the GNU GPL v3 license),
    courtesy of Jean-François Fortin Tam.
    """
    user_dirs_dirs = os.path.join(xdg_config_home, "user-dirs.dirs")
    user_dirs_dirs = os.path.expanduser(user_dirs_dirs)
    if not os.path.exists(user_dirs_dirs):
        return
    for line in open(user_dirs_dirs, "r"):
        if line.startswith(key):
            return os.path.expandvars(line[len(key) + 2:-2])


def get_desktop_dir():
    """ Returns path to desktop dir based on XDG.

    If XDG is not setup corectly, use home directory instead """
    desktop_dir = get_user_dir("XDG_DESKTOP_DIR")
    if desktop_dir is not None and os.path.exists(desktop_dir):
        return desktop_dir
    else:
        return os.path.expanduser('~')


class PluginExport:
    """ Export plugin - handle UI and trigger exporting tasks """

    # Allow initilization outside __init__() and don't complain
    # about too many attributes

    PLUGIN_NAME = "export"

    DEFAULT_PREFERENCES = {
        "menu_entry": True,
        "toolbar_entry": True,
        "last_template": None,
    }

    def __init__(self):
        self.filename = None
        self.template = None

    def activate(self, plugin_api):
        """ Loads saved preferences """
        self.plugin_api = plugin_api
        self._init_gtk()
        self._preferences_load()
        self._preferences_apply()

    def deactivate(self, plugin_api):
        """ Removes the gtk widgets before quitting """
        self._gtk_deactivate()

## CALLBACK AND CORE FUNCTIONS ################################################
    def on_export_start(self, saving):
        """ Start generating a document.
        If saving == True, ask user where to store the document. Otherwise,
        open it afterwards. """

        model = self.combo.get_model()
        active = self.combo.get_active()
        self.template = Template(model[active][0])

        tasks = self.get_selected_tasks()
        if len(tasks) == 0:
            self.show_error_dialog(_("No task matches your criteria. "
                                     "Empty report can't be generated."))
            return

        self.filename = None
        if saving:
            self.filename = self.choose_file()
            if self.filename is None:
                return

        self.save_button.set_sensitive(False)
        self.open_button.set_sensitive(False)

        try:
            self.template.generate(tasks, self.plugin_api,
                                   self.on_export_finished)
        except Exception, err:
            self.show_error_dialog(
                _("GTG could not generate the document: %s") % err)
            raise

    def on_export_finished(self):
        """ Save generated file or open it, reenable buttons
        and hide dialog """
        document_path = self.template.get_document_path()
        if document_path:
            if self.filename:
                shutil.copyfile(document_path, self.filename)
            else:
                webbrowser.open(document_path)
        else:
            self.show_error_dialog("Document creation failed. "
                                   "Ensure you have all needed programs.")

        self.save_button.set_sensitive(True)
        self.open_button.set_sensitive(True)
        self.export_dialog.hide()

    def get_selected_tasks(self):
        """ Filter tasks based on user option """
        timespan = None
        req = self.plugin_api.get_requester()

        if self.export_all_active.get_active():
            treename = 'active'
        elif self.export_all_finished.get_active():
            treename = 'closed'
        elif self.export_finished_last_week.get_active():
            treename = 'closed'
            timespan = -7

        tree = req.get_tasks_tree(name=treename)
        if treename not in tree.list_applied_filters():
            tree.apply_filter(treename)

        return get_task_wrappers(tree, timespan)

## GTK FUNCTIONS ##############################################################
    def _init_gtk(self):
        """ Initialize all the GTK widgets """
        self.menu_entry = False
        self.toolbar_entry = False

        self.menu_item = gtk.MenuItem(_("Export the tasks currently listed"))
        self.menu_item.connect('activate', self.show_dialog)
        self.menu_item.show()

        self.tb_button = gtk.ToolButton(gtk.STOCK_PRINT)
        self.tb_button.connect('clicked', self.show_dialog)
        self.tb_button.show()

        builder = gtk.Builder()
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        builder_file = os.path.join(cur_dir, "export.ui")
        builder.add_from_file(builder_file)

        self.combo = builder.get_object("export_combo_templ")
        templates_list = gtk.ListStore(gobject.TYPE_STRING,
                                       gobject.TYPE_STRING,
                                       gobject.TYPE_STRING, gobject.TYPE_STRING
                                       )
        self.combo.set_model(templates_list)
        cell = gtk.CellRendererText()
        self.combo.pack_start(cell, True)
        self.combo.add_attribute(cell, 'text', 1)

        self.export_dialog = builder.get_object("export_dialog")
        self.export_image = builder.get_object("export_image")
        self.preferences_dialog = builder.get_object("preferences_dialog")
        self.pref_menu = builder.get_object("pref_chbox_menu")
        self.pref_toolbar = builder.get_object("pref_chbox_toolbar")
        self.description_label = builder.get_object("label_description")
        self.save_button = builder.get_object("export_btn_save")
        self.open_button = builder.get_object("export_btn_open")

        self.export_all_active = builder.get_object(
            "export_all_active_rb")
        self.export_all_active.set_active(True)
        self.export_finished_last_week = builder.get_object(
            "export_finished_last_week_rb")
        self.export_all_finished = builder.get_object(
            "export_all_finished_rb")

        builder.connect_signals({
            "on_export_btn_open_clicked":
            lambda widget: self.on_export_start(False),
            "on_export_btn_save_clicked":
            lambda widget: self.on_export_start(True),
            "on_export_dialog_delete_event":
            self._hide_dialog,
            "on_export_combo_templ_changed":
            self.on_combo_changed,
            "on_preferences_dialog_delete_event":
            self.on_preferences_cancel,
            "on_btn_preferences_cancel_clicked":
            self.on_preferences_cancel,
            "on_btn_preferences_ok_clicked":
            self.on_preferences_ok,
        })

    def _gtk_deactivate(self):
        """ Remove Toolbar Button and Menu item for this plugin """
        if self.menu_entry:
            self.plugin_api.remove_menu_item(self.menu_item)
            self.menu_entry = False

        if self.toolbar_entry:
            self.plugin_api.remove_toolbar_item(self.tb_button)
            self.toolbar_entry = False

    def show_dialog(self, widget):
        """ Show dialog with options for export """
        parent_window = self.plugin_api.get_ui().get_window()
        self.export_dialog.set_transient_for(parent_window)
        self._update_combobox()
        self.export_dialog.show_all()

    def _hide_dialog(self, sender=None, data=None):

        """ Hide dialog """
        self.export_dialog.hide()
        return True

    def _update_combobox(self):
        """ Reload list of templates """
        model = self.combo.get_model()
        model.clear()

        templates = get_templates_paths()
        active_entry = None
        for i, path in enumerate(templates):
            template = Template(path)
            if path == self.preferences["last_template"]:
                active_entry = i

            model.append((path,
                          template.get_title(),
                          template.get_description(),
                          template.get_image_path()))

        # wrap the combo-box if it's too long
        if len(templates) > 15:
            self.combo.set_wrap_width(5)

        if active_entry is None:
            active_entry = 0
        self.combo.set_active(active_entry)

    def on_combo_changed(self, combo):
        """ Display details about the selected template """
        model = combo.get_model()
        active = combo.get_active()
        if not 0 <= active < len(model):
            return
        description, image = model[active][2], model[active][3]

        if image:
            pixbuf = gtk.gdk.pixbuf_new_from_file(image)
            width, height = self.export_image.get_size_request()
            pixbuf = pixbuf.scale_simple(width, height,
                                         gtk.gdk.INTERP_BILINEAR)
            self.export_image.set_from_pixbuf(pixbuf)
        else:
            self.export_image.clear()
        self.description_label.set_markup("<i>%s</i>" % description)

        # Remember the last selected path
        self.preferences["last_template"] = model[active][0]
        self._preferences_store()

    def show_error_dialog(self, message):
        """ Display an error """
        dialog = gtk.MessageDialog(
            parent=self.export_dialog,
            flags=gtk.DIALOG_DESTROY_WITH_PARENT,
            type=gtk.MESSAGE_ERROR,
            buttons=gtk.BUTTONS_OK,
            message_format=message)
        dialog.run()
        dialog.destroy()

    def choose_file(self):
        """ Let user choose a file to save and return its path """
        chooser = gtk.FileChooserDialog(
            title=_("Choose where to save your list"),
            parent=self.export_dialog,
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        chooser.set_do_overwrite_confirmation(True)
        chooser.set_default_response(gtk.RESPONSE_OK)
        chooser.set_current_folder(get_desktop_dir())
        response = chooser.run()
        filename = chooser.get_filename()
        chooser.destroy()
        if response == gtk.RESPONSE_OK:
            return filename
        else:
            return None

## Preferences methods ########################################################
    @classmethod
    def is_configurable(cls):
        """A configurable plugin should have this method and return True"""
        return True

    def configure_dialog(self, manager_dialog):
        """ Display configuration dialog """
        self._preferences_load()
        self.preferences_dialog.set_transient_for(manager_dialog)
        self.pref_menu.set_active(self.preferences["menu_entry"])
        self.pref_toolbar.set_active(self.preferences["toolbar_entry"])
        self.preferences_dialog.show_all()

    def on_preferences_cancel(self, widget, data=None):

        """ Only hide the dialog """
        self.preferences_dialog.hide()
        return True

    def on_preferences_ok(self, widget):
        """ Apply and store new preferences """
        self.preferences["menu_entry"] = self.pref_menu.get_active()
        self.preferences["toolbar_entry"] = self.pref_toolbar.get_active()
        self.preferences_dialog.hide()

        self._preferences_apply()
        self._preferences_store()

    def _preferences_load(self):
        """ Restore user preferences """
        self.preferences = self.plugin_api.load_configuration_object(
            self.PLUGIN_NAME, "preferences",
            default_values=self.DEFAULT_PREFERENCES)

    def _preferences_store(self):
        """ Store user preferences """
        self.plugin_api.save_configuration_object(
            self.PLUGIN_NAME, "preferences", self.preferences)

    def _preferences_apply(self):
        """ Add/remove menu entry/toolbar entry """
        if self.preferences["menu_entry"] and not self.menu_entry:
            self.plugin_api.add_menu_item(self.menu_item)
            self.menu_entry = True
        elif not self.preferences["menu_entry"] and self.menu_entry:
            self.plugin_api.remove_menu_item(self.menu_item)
            self.menu_entry = False

        if self.preferences["toolbar_entry"] and not self.toolbar_entry:
            self.plugin_api.add_toolbar_item(self.tb_button)
            self.toolbar_entry = True
        elif not self.preferences["toolbar_entry"] and self.toolbar_entry:
            self.plugin_api.remove_toolbar_item(self.tb_button)
            self.toolbar_entry = False
