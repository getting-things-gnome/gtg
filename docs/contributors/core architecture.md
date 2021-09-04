# GTG Core Architecture

This document is intended as an overview to GTG's core for new contributors.
Note that the new core detailed here is still a work in progress.


## The data types

GTG currently holds three types of data:

- Tags
- Saved Searches
- Tasks

Each one of these has its own module in the `core` directory. The modules
include the datatype class, its datastore class and related enums and utilities.

Datatypes can be instantiated directly or through their datastore's `new()` method.
Each type has its own methods and properties but they all have two in common:

- an **id** property, a UUID to identify the type
- a **children** list

Every type keeps track of its children, but the only type that keeps
track of its parent is tasks. That's because we need to take precautions
when changing tasks' status.
Don't add children directly to this list though, use the datastore's
`parent()` and `unparent()` methods. These methods will keep the caches in sync
and emit Gtk signals that can be used by the UI and plugins.


## The stores

The store classes take care of managing the data types. Data is held in the 
`data` property. There's also a cache called `lookup`, which is a dictionary
you can use to access items by their id. Some stores might other caches on top
of that. In addition to accessing by id, you can also use the `find()` method in the
`TagStore` to get a tag by name. 

As mentioned above, the stores take care of (un)parenting, as well as adding an
existing item, creating a new one, or removing one. The `TaskStore` also
includes sorting and filtering methods. All of these things emit Gtk signals.

Finally, stores take care of parsing and serializing data into the
corresponding xml elements. You can find the common methods and properties for
stores (including the signals definition) in the `BaseStore` class.


## The Datastore

The Datastore is a "store of stores". It sits at the top of hierarchy and takes
care of initializing and coordinating all the stores. It also handles backends.

Finding the `gtg_data.xml` file, loading and writing to it are also
responsibilities of the datastore (along with backups). It also takes care of
purging unused tags and old closed tasks.

You can instantiate new datastores to test things with the developer console.
There's even a function to fill the datastore with random data to test things
out.


## Configuration

Configuration is managed by the `CoreConfig` class from the `config` module.
This includes general settings, per-task window state and active backends.


## Using the development console

You can play with all these classes without messing the UI or the current data.
Simply enable the development console plugin and press `F12` (or open it from the menu).

The development console is basically a Python interpreter where you can run
commands. You can access the application's datastore, or instantiate a new one
and fill it with test data like this:


```python

from GTG.core.datastore2 import DataStore2
ds = DataStore2()
ds.fill_with_samples(200)
ds.print_info()
```

## Tips

- Don't add to tags or children lists manually. Always use the parenting
  methods, or for tasks `add_tag()` and `remove_tag()`
- Use the `toggle_status()` and `dismiss()` functions for tasks. Don't change
  the status directly
- Always call `update_modified()` after making changes to a task
