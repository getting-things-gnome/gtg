This page explains the way plugins work and how you can build a plugin for GTG.
It's a work in progress, feel free to add more information about the plugin engine!

# Files needed

A plugin has to have at least two files. A config file and the plugin itself. The config file tells GTG where the plugin can be found and all the info (name, version, authors, dependencies, etc).

The second file or directory is the python code and both need to be placed in GTG/plugins directory. Plugins can also be located in the xdg_config_home's gtg plugin folder, xdg_config_home/gtg/plugins. Normally it's $HOME/.config/gtg/plugins/ .

# Plugin infrastructure

## The config file

example.gtg-plugin

```
[GTG Plugin]
Module=example
Name="Example plugin"
Description="A plugin example"
Authors="Paulo Cabido <paulo.cabido@gmail.com>"
Version=0.1
Dependencies=some_python_module
Dbus-dependencies=org.gnome.Example:/org/gnome/Example
Enabled=True
```

* Module: the location of the python code within the plugin directory. For the example, it could be either GTG/plugins/example.py or GTG/plugins/example/
* Name: the plugin name
* Description: the plugin description
* Authors: the plugin authors
* Version: the plugin version
* Dependencies: the python modules that the plugin has as dependencies
* Dbus-dependencies: the remote dbus objects that the plugin has as dependencies

Note: if the plugin has no dependencies or no dbus-dependencies you don't need to include these lines, all the others are mandatory 


## Python code
A plugin has three mandatory methods:

* activate(plugin_api): this method will initializes the plugin with GTG's main window (task browser). All the things the plugin needs to do at startup are done within this method.
  * note: this can be easily confused with the __init__ method of a class. It's not the same thing. The init initializes a class and the activate will initialize the plugin in GTG.
* deactivate(plugin_api): this method will reverse all the changes the activate method did to gtg and will terminate the execution of a plugin.
  * if you add a button while activating the plugin, here you will remove it
  * all plugins are deactivated before GTG ends so if you want to save information, this is the place to save it (for example, save the current user settings to a config file)
* onTaskOpened(plugin_api): this method will initialize the plugin's code for the task editor.
  * There is no deactivate associated with this method, when the tas editor is closed it's object is destroyed so no need to deactivate nothing, when it loads again it will load the plugin code again
 
* In all three methods the plugin_api (plugin api) is passed. This is the plugin engine's API. This is the object that contains the methods that you can use to interact with GTG. It is a work in progress but many methods are already available. The API documentation will be available real soon.

If a plugin is configurable, in the plugin manager, the preferences button will be enabled and allow the user to interact with those preferences.

* `is_configurable()`: if a plugin is configurable it should have this method and it must `return True`. If the plugin isn't configurable you can `return False` or omit the method (the first option is preferred).
* `configure_dialog(plugin_apis, plugin_manager_dialog)`: this method loads the dialog for the plugin's configurations. 
* Note: only if or after a plugin is selected to be enabled in the plugin manager will the plugin preferences button be enabled.

A python plugin example:

```
#!python
class Example:
    def __init__(self):
        self.example = "This can initialize a class"
		
    def activate(self, plugin_api):
	print "the plugin is initialized"

    def onTaskOpened(self, plugin_api):
	print "a task was opened"
		
    def deactivate(self, plugin_api):
        print "the plugin was deactivated"
```

A helloword plugin is packed along with GTG for example purposes. You can check it out to see a better example of a plugin.


# Plugin API


## General Methods

| **Method** | **Description** |
|------------|-----------------|
|add_menu_item(item) | Adds a menu to the Plugin Menu in the menu bar of the task browser. <br> **item** is the gio.MenuItem that is going to be added. |
|remove_menu_item(item) | Removes a menu from the Plugin Menu in the menu bar of the task browser. <br> **item** is the gio.MenuItem that is going to be removed. |
|add_toolbar_item(item) | Adds a button to the task browser's toolbar. <br> **item** is the gtk.ToolButton that is going to be added to the toolbar. <br> **Returns**: a integer that represents the position of the item in the toolbar. |
|remove_toolbar_item(item, n=None) | Removes a toolbar button from the task browser's toolbar. <br> **item** is the gtk.ToolButton that is going to be removed. <br> **n** is the position of the item to be removed. It's useful to remove gtk.SeparatorToolItem(). ie, remove_toolbar_item(None, 14) |
|add_task_toolbar_item(item) | Adds a button to the task editor's toolbar. <br> **item** is the gtk.ToolButton that is going to be added to the toolbar. |
|add_widget_to_taskeditor(widget) | Adds a widget to the bottom of the task editor dialog. <br> **widget** is a gtk.Widget. |
|get_requester() | **Returns**: the requester object. |
|requester_connect(action, func) | Connects a function to a requester signal. <br> **action** is the actual signal action. <br> **func** is the function that is connected to the signal. |
|change_task_tree_store(treestore) | Changes the TreeStore in the task browser's task view. <br> **treestore** is the new gtk.TreeStore model. |
|set_parent_window(child) | Sets the plugin dialog as a child of it's parent window, depending on were it is called the parent window can be either the task browser or the task editor. <br> **child** is the dialog that is meant to be set as a child. |
|get_taskview() | **Returns**: the task view object. |
|get_selected_task() | **Returns**: the selected task in the task view. |
|get_config() | **Returns**: the config object. |


## Task related methods

| **Method** | **Description** |
|------------|-----------------|
|get_all_tasks() | **Returns**: a list with all existing tasks. |
|get_task(tid=None) | **Note**: the default action is to be used with the task editor (onTaskOpened method). <br> **Returns**: the current or a matching task. <br> **tid** is the task's id. |
|get_task_title(tid=None) | **Note**: the default action is to be used with the task editor (onTaskOpened method). <br> **Returns**: the current or a matching task's title. <br> **tid** is the task's id. |
|insert_tag(tag) | **Note**: this method only works with the onTaskOpened method. <br> Inserts a tag into the current task (in the textview). <br> **tag** is the tag's name (without the '@'). |
|add_tag(tag, tid=None) | **Note**: the default action is to be used with the task editor (onTaskOpened method). <br> Adds a tag directly to a task. <br> **tag** is the tag's name (without the '@'). <br> **tid** is the task's id. |
|add_tag_attribute(attrib_name, attrib_value) | **Note**: this method only works with the onTaskOpened method. <br> Adds an attribute to a tag in the current task. <br> **attrib_name** is the attribute's name. <br> **attrib_value** is the attribute's value. |
|get_tags(tid=None) | **Note**: the default action is to be used with the task editor (onTaskOpened method). <br>  **Returns**: all the tags the current task or a matching task has. <br> **tid** is the task's id. |
|get_textview() | **Note**: this method only works with the onTaskOpened method. <br>  **Returns**: the task editor's text view (object). |


## Tag view methods

| **Method** | **Description** |
|------------|-----------------|
|add_menu_tagpopup(item) | Adds a menu to the tag popup menu of the tag view. <br> **item** is the menu that is going to be added to the tag popup menu. |
|remove_menu_tagpopup(item) | Removes a menu from the tag popup menu of the tag view. <br> **item** is the menu that is going to be removed from the tag popup menu. |
|get_tagpopup_tag() | **Returns**: the selected tag in the tag view. |


## Filtering methods

| **Method** | **Description** |
|------------|-----------------|
|add_task_to_filter(tid) | Adds a task to the task filter. <br> **tid** is the task's id. |
|remove_task_from_filter(tid) | Removes a task from the task filter. <br> **tid** is the task's id. |
|add_tag_to_filter(tag) | Adds all tasks that contain a certain tag to the task filter. <br> **tag** is the name of the tag. |
|remove_tag_from_filter(tag) | Removes all tasks that contain a certain tag from the task filter. <br> **tag** is the name of the tag. |
|register_filter_cb(func) | Registers a callback filter function with the callback filter. <br> **func** is the function that is going to be registered. |
|unregister_filter_cb(func) | Unregisters a previously registered callback filter function. <br> **func** is the function that is going to be unregistered. |
