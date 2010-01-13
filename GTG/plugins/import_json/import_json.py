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

# Imports JSON files with the following syntax:
# {
#  "my_name": {
#   "done": [
#   [ "task-id-name", "My Task", "Essential", "http://my.url/description1.html" ],
#   [ "task2-id-name", "Task #2", "Medium", "http://my.url/description2.html" ]
#   "postponed": [],
#   "todo": []
#  },
#  "someone_else": { }
# }

import gtk
import gobject
import os
import re
import urllib2
import simplejson as json

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
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "import_json.glade")
        wTree = gtk.glade.XML(glade_file, "dlg_import_json")

        self.dialog = wTree.get_widget("dlg_import_json")
        if not self.dialog:
            return
        self.txtImport = wTree.get_widget("txt_import")

        self.dialog.connect("delete_event", self.close_dialog)
        self.dialog.connect("response", self.on_response)
        
        self.dialog.show_all()

    def loadDialogSelectUsername(self):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "import_json.glade")
        wTree = gtk.glade.XML(glade_file, "dlg_select_username")

        self.dialog_select_username = wTree.get_widget("dlg_select_username")
        if not self.dialog_select_username or len(self.usernames) < 1:
            return
        self.dialog_select_username.set_title("Select username")
        self.dialog_select_username.set_transient_for(self.dialog)
        self.dialog_select_username.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        # TODO:  Handle ok and cancel buttons
        self.dialog_select_username.connect("response", self.on_response_select_username)
        self.dialog_select_username.connect("delete_event", self.close_dialog_select_username)

        self.select_username = wTree.get_widget("select_username")
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
        json_text = loadurl(url)
        if not json_text:
            # TODO:  Pop up error dialog
            print "Error: Could not load url %s" % url
            return

        # Convert to json
        self.json_tasks = json.loads(json_text)

        # Pop up dialog allowing user to select username
        self.usernames = [ ]
        for u in sorted(self.json_tasks):
            self.usernames.append(u)
        self.loadDialogSelectUsername()
        self.dialog.hide_all()
        self.dialog_select_username.run()

    def import_tasks(self, widget):
        username = self.usernames[self.select_username.get_active()]
        re_dehtml = re.compile(r'<.*?>')

        for t in self.json_tasks[username]['todo']:
            (category, title, priority, reference) = (t)

            # Remove html <something> and </something>
            title = re_dehtml.sub('', title)
            reference = re_dehtml.sub('', reference)

            # TODO:  Turn 'category' into a tag
            # TODO:  Define pid from category?  Decide whether to do category as a tag or a project
            task = self.plugin_api.get_requester().new_task(pid=None, tags=None, newtask=False)
            task.title = title
            task.content = reference
            # TODO:  Set task.start_date, task.due_date, task.closed_date
            # TODO:  Do something with the priority
        # TODO:  Should completed tasks be imported too?

        self.close_dialog_select_username(widget)
        self.close_dialog(widget)

### UTILITIES ###
def loadurl(url):
    try:
        in_file = urllib2.urlopen(url, "r")
        text = in_file.read()
        in_file.close()
        return text
    except:
        return ''

