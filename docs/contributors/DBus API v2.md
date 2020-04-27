This was originally in the wiki at Apps/gtg/DBus (yeah, not the same thing)
That page was written by Paul Kishimoto on 2010-08-16.

# GTG DBus API 2
This page describes a '''new DBus API for GTG''', as implemented a long time ago in https://code.launchpad.net/~gtg-contributors/gtg/dbus-server.

The major change of the version 2 API is that it exposes ''all'' the core functionality of GTG! In the major version following GTG! 0.3, the GTK+ user interface (and all other user interfaces) will be 100% through DBus. This follows the example of NetworkManager, APT daemon, etc.

This means you can write code to interact with GTG! tasks in any language with [DBus bindings](http://www.freedesktop.org/wiki/Software/DBusBindings).

## Bus Name
GTG uses the bus name '''`org.gnome.GTG`''' on the session bus. Trying to access this bus name will cause the GTG daemon to be started, if it's not already running.

## Object Paths
Every Task and Tag in GTG can be accessed directly on the bus by its own ''object path''—there is no need to call any method like `get_task()` on the server.

|  '''Path''' | '''Interfaces''' ¹ | '''Object''' | 
|-------------|---------------------|--------------|
|  `/org/gnome/GTG/Server` |  `org.gnome.GTG.Server`  | The GTG! daemon  | 
|  `/org/gnome/GTG/Tag/[uuid]` |   `org.gnome.GTG.Tag` <br> `org.freedesktop.DBus.Properties`²  | Individual tags by UUID³  | 
|  `/org/gnome/GTG/Task/[uuid]` |  `org.gnome.GTG.Task` <br> `org.freedesktop.DBus.Properties`²  | Individual tasks by UUID³  | 

Notes:

1. Because GTG! is implemented in Python, all objects also support the [org.freedesktop.DBus.Introspectable](http://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-introspectable) interface.
2. The `org.freedesktop.DBus.Properties` interface is extended in GTG! See below.
3. These are [version 4 (random) Universally Unique Identifiers](http://en.wikipedia.org/wiki/Universally_unique_identifier#Version_4_.28random.29). Because DBus does not allow hyphens in object paths, they are in hexadecimal form (`550e8400e29b41d4a716446655440000`) **not** "canonical form" (`550e8400-e29b-41d4-a716-446655440000`).

## Interfaces

### org.freedesktop.DBus.Properties
This is a standard interface that is [described in the DBus specification](http://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties). It allows `Get`-ing and `Set`-ing of arbitrary named properties of any object.

In GTG!, the interface is extended with ''one'' extra method named `List`:
```
org.freedesktop.DBus.Properties.List (in STRING interface_name,
                                      out ARRAY<STRING> props); 
```

`List` is a faster alternative to `GetAll` that avoids a `Get` of ''every'' property. That can be slow, especially where some properties are computed instead of stored in variables.

### org.gnome.GTG.Server

```
<interface name="org.gnome.GTG.Server">
  <method name="get_tasks_json">
    <arg type="s" direction="out"/>
  </method>
  <method name="get_tags_json">
    <arg type="s" direction="out"/>
  </method>
```

 These methods retrieve a string that describes all tasks (or tags) in JSON format.

```
  <method name="new_task">
    <arg name="tags" type="as" direction="in"/>
    <arg name="newtask" type="b" direction="in"/>
    <arg type="o" directions="out"/>
  </method>
```

 Create a new Task, with some optional ''tags''. The return value is the valid DBus [Object Path](http://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-marshaling) of the new Task. If for any reason a new Task is not created, a DBus error will be raised.

  The boolean argument ''newtask'' must be '''True'''.

```
  <method name="new_tag">
    <arg name="tagname" type="s" direction="in"/>
    <arg type="o" directions="out"/>
  </method>
```

  Create a new Tag with the label ''tagname''. The return value is the valid DBus [Object Path](http://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-marshaling) of the new Task. If for any reason a new Task is not created, a DBus error will be raised.

```
  <method name="list_tasks">
    <arg type="as" direction="out"/>
  </method>
  <method name="list_tags">
    <arg type="as" direction="out"/>
```

 These methods retrieve the IDs of all Tasks (or Tags) in an array of strings. Unlike `get_tasks_json` and `get_tags_json`, there is no information about hierarchy.

```
  </method>
  <method name="shutdown"/>
</interface>
```

 The `shutdown` method causes the daemon to save all of its data and terminate. This is identical to sending the `SIGQUIT` signal to the daemon process.

### org.gnome.GTG.Tag

```
<interface name="org.gnome.GTG.Tag">
  <property name="Color" type="s" access="readwrite"/>
  <property name="Name" type="s" access="read"/>
  <property name="Removable" type="s" access="read"/>
</interface>
```

### org.gnome.GTG.Task

```
<interface name="org.gnome.GTG.Task">
  <property name="Closed_Date" type="s" access="readwrite"/>
  <property name="Content" type="s" access="readwrite"/>
  <property name="Due_Date" type="s" access="readwrite"/>
  <property name="Duration" type="s" access="readwrite"/>
  <property name="Modified" type="s" access="read"/>
  <property name="Priority" type="d" access="readwrite"/>
  <property name="Status" type="y" access="readwrite"/>
  <property name="Start_Date" type="s" access="readwrite"/>
  <property name="Tags" type="as" access="readwrite"/>
  <property name="Title" type="s" access="readwrite"/>
</interface>
```

### org.gnome.GTG.GtkUI

```
<interface name="org.gnome.GTG.GtkUI">
  <method name="ShowBrowser"/>
  <method name="HideBrowser"/>
  <method name="IconifyBrowser"/>
  <method name="OpenTask">
    <arg name="task" type="o" direction="in"/>
  </method>
  <method name="OpenNewTask"/>
  <property name="BrowserIsVisible" type="b" access="read"/>
</interface>
```
