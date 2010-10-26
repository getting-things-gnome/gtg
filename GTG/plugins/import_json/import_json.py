# -*- coding: utf-8 -*-
# Copyright (c) 2010 - Bryce Harrington <bryce@canonical.com>
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

# This plugin was built for a specific purpose and is not a general-purpose or
# full-featured JSON importer.
#
# It imports JSON files with the following syntax.
#
# There just be a top-level key named "specs", with key names of your choosing.
# Each sub sub-hash must have a "details_url" or "url" key, whose values
# becomes part of the description of every item in the "work_items" array.
# There is no way to set any other description, nor it is possible to import
# tags, or dates.
#
# Only items with a "status" of "todo" are imported, the rest are skipped.

# The software will first scan the file to find all the "assignee" values in the file
# And then pop-up a dialog as you to choose an username. It then imports only the TODO
# items for those usernames. The username is not actually imported.

# {
#  "specs": {
#   "my-spec": {
#    "details_url": "http://www.gnome.org/",
#    "work_items": [
#     {
#      "assignee": "john-doe",
#      "description": "Do something",
#      "spec": "my-spec",
#      "status": "todo"
#     },
#     ...
#    ]
#   },
#   "another-spec": {
#   ...
#   },
#   ...
#  },
# }

import gtk
import os
import re
import urllib2
import simplejson as json
from GTG.tools.readurl import readurl

class pluginImportJson:
    
    def __init__(self):
        self.plugin_api = None

        self.menu_item = gtk.MenuItem("Import from _JSON")
        self.menu_item.connect('activate', self.on_import_json_activate)
        
        self.tb_button = gtk.ToolButton(gtk.STOCK_INFO)
        self.tb_button.set_label("Import from JSON")
        self.tb_button.connect('clicked', self.on_import_json_activate)
        self.separator = gtk.SeparatorToolItem()

        self.dialog = None
        self.txtImport = None
        self.json_tasks = None

        self.dialog_select_username = None
        self.select_username = None
        self.usernames = []

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.plugin_api.add_menu_item(self.menu_item)
        self.plugin_api.add_toolbar_item(self.separator)
        self.plugin_api.add_toolbar_item(self.tb_button)

    def onTaskClosed(self, plugin_api):
        pass
        
    def onTaskOpened(self, plugin_api):
        pass
        
    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)
        plugin_api.remove_toolbar_item(self.tb_button)
        plugin_api.remove_toolbar_item(self.separator)
        self.txtImport = None

    def loadDialog(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
                os.path.dirname(os.path.abspath(__file__)) + \
                    "/import_json.ui"))

        self.dialog = self.builder.get_object("dlg_import_json")
        if not self.dialog:
            return
        self.txtImport = self.builder.get_object("txt_import")

        self.dialog.connect("delete_event", self.close_dialog)
        self.dialog.connect("response", self.on_response)
        
        self.dialog.show_all()

    def loadDialogSelectUsername(self):
        path = os.path.dirname(os.path.abspath(__file__))

        self.dialog_select_username = self.builder.get_object("dlg_select_username")
        if not self.dialog_select_username or len(self.usernames) < 1:
            return
        self.dialog_select_username.set_title("Select username")
        self.dialog_select_username.set_transient_for(self.dialog)
        self.dialog_select_username.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        # TODO:  Handle ok and cancel buttons
        self.dialog_select_username.connect("response", self.on_response_select_username)
        self.dialog_select_username.connect("delete_event", self.close_dialog_select_username)

        username_model = gtk.ListStore(str)
        self.select_username = self.builder.get_object("select_username")
        self.select_username.set_model(username_model)
        for u in self.usernames:
            self.select_username.append_text(u)
        self.select_username.set_active(0)

        self.dialog_select_username.show_all()

    def print_selected(self, widget, data=None):
        print self.select_username.get_active()

    def close_dialog(self, widget, data=None):
        self.dialog.destroy()
        return True    
    
    def close_dialog_select_username(self, widget, data=None):
        self.dialog_select_username.destroy()
        return True    
    
    # plugin features
    def on_import_json_activate(self, widget):
        self.loadDialog()

    def on_response(self, widget, response_id):
        if response_id == -7 or response_id == -4:
            self.close_dialog(widget)
        elif response_id == 0 and self.txtImport:
            self.import_json(widget)
        else:
            print "Error:  Unknown response id %d" %(response_id)

    def on_response_select_username(self, widget, response_id):
        if response_id == -7:
            self.dialog.show_all()
            self.close_dialog_select_username(widget)
        elif response_id == -4:
            self.close_dialog_select_username(widget)
        elif response_id == 0:
            self.import_tasks(widget)
            self.close_dialog_select_username(widget)
        else:
            print "Error:  Unknown response id %d" %(response_id)
        return response_id

    def import_json(self, widget):
        url = self.txtImport.get_text()
        json_text = readurl(url)
        if not json_text:
            # TODO:  Pop up error dialog
            print "Error: Could not load url %s" % url
            return

        # Convert to json
        self.json_tasks = json.loads(json_text)

        # TODO:  Create listing of usernames available
        self.usernames = [ ]
        for specname,spec in self.json_tasks['specs'].items():
            for wi in spec['work_items']:
                if wi['status'] != "todo":
                    continue
                if wi['assignee'] in self.usernames:
                    continue
                if not wi['assignee']:
                    continue
                self.usernames.append(wi['assignee'])
        self.usernames.sort()

        # Pop up dialog allowing user to select username
        self.loadDialogSelectUsername()
        self.dialog.hide_all()
        self.dialog_select_username.run()

    def import_tasks(self, widget):
        username = self.usernames[self.select_username.get_active()]
        re_dehtml = re.compile(r'<.*?>')

        for specname,spec in self.json_tasks['specs'].items():
            for wi in spec['work_items']:
                if wi['assignee'] != username:
                    continue
                if wi['status'] != 'todo':
                    continue

                text = ""
                if spec['details_url']:
                    text = spec['details_url']
                elif spec['url']:
                    text = spec['url']
                task = self.plugin_api.get_requester().new_task(pid=None, tags=None, newtask=True)
                task.set_title(re_dehtml.sub('', wi['description']))
                task.set_text(re_dehtml.sub('', text))
                task.sync()
                # TODO:  Do something with spec['priority']

        self.close_dialog_select_username(widget)
        self.close_dialog(widget)
