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
import os
import urllib2
import simplejson as json

class pluginImportJson:
    
    def __init__(self):
        self.menu_item = gtk.MenuItem("Import from _JSON")
        self.menu_item.connect('activate', self.on_import_json_activate)
        
        self.tb_button = gtk.ToolButton(gtk.STOCK_INFO)
        self.tb_button.set_label("Import from JSON")
        self.tb_button.connect('clicked', self.on_import_json_activate)
        self.separator = gtk.SeparatorToolItem()
        self.txtImport = None
        self.plugin_api = None

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
        wTree = gtk.glade.XML(glade_file, "import_json")
        self.dialog = wTree.get_widget("import_json")
        if not self.dialog:
            return

        self.txtImport = wTree.get_widget("txt_import")

        self.dialog.connect("delete_event", self.close_dialog)
        self.dialog.connect("response", self.on_response)
        
        self.dialog.show_all()
    
    def close_dialog(self, widget, data=None):
        self.dialog.destroy()
        return True    
    
    # plugin features
    def on_import_json_activate(self, widget):
        self.loadDialog()

    def on_response(self, widget, response_id):
        if response_id == -7:
            self.close_dialog(widget)
        elif response_id == 0 and self.txtImport:
            self.import_json(widget)
        else:
            print "Error:  Unknown response id %d" %(response_id)

    def import_json(self, widget):
        url = self.txtImport.get_text()
        json_text = loadurl(url)
        if not json_text:
            # TODO:  Pop up error dialog
            print "Error: Could not load url %s" % url
            return

        # Convert to json
        json_tasks = json.loads(json_text)

        # TODO:  Pop up dialog allowing user to select username
        #        username = self.txtUserName.get_text()
        for u in json_tasks:
            # Insert name into dropdown widget
            print u
        username = 'bryceharrington'
            
        for t in json_tasks[username]['todo']:
            (category, title, priority, reference) = (t)
            # TODO:  Omit html
            # TODO:  Turn 'category' into a tag
            # TODO:  Define pid from category?  Decide whether to do category as a tag or a project
            task = self.plugin_api.get_requester().new_task(pid=None, tags=None, newtask=False)
            task.title = title
            task.content = reference
            # TODO:  Set task.start_date, task.due_date, task.closed_date
            # TODO:  Do something with the priority
        # TODO:  Should completed tasks be imported too?

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

