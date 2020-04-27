This was originally in the wiki at Apps/gtg/dbus
That page was written by Luca Invernizzi on 2010-02-27.

# Interacting with Getting Things GNOME! via dbus
If you are on this page, you're probably interested in integrating some uber-cool software with GTG. 
First of all, kudos for that. It's good karma.

## Python

Very simple script listing the "Active" tasks (that are the ones *not* marked as done or dismissed)

```
#!python
import dbus
bus = dbus.SessionBus()
obj = bus.get_object("org.GTG", "/org/GTG")
gtg = dbus.Interface(obj, "org.GTG")
for t in gtg.get_tasks(): 
    print t
    print t["title"]
```

As you can see if you run the code above, tasks are simple dictionaries.
The next example is a little less trivial:

```
#!python
import dbus
bus = dbus.SessionBus()
obj = bus.get_object("org.GTG", "/org/GTG")
gtg = dbus.Interface(obj, "org.GTG")
for tid in gtg.get_task_ids("Active, Dismissed"): 
    #the task id is a string which identifies the task
    print tid
    #if you want to get task properties, you need to do
    task = gtg.get_task(tid)
    #the task object is a simple dictionary (print it 
    #  to see the key values)
    print task["title"]
    # once you modify that dictionary, you can feed it back to
    # GTG by:
    # task["title"] = "new_title"
    # gtg.modify_task(tid, task)
   # these lines are commented because they WILL modify your GTG data
```

Now you're ready for the real stuff (from Ryan Paul a.k.a. segphault):

```
#!python
#!/usr/bin/env python

import dbus

bus = dbus.SessionBus()
obj = bus.get_object("org.GTG", "/org/GTG")
gtg = dbus.Interface(obj, "org.GTG")

for t in gtg.get_tasks(): print t

for t in gtg.get_tasks_filtered([], ["Active"], False, False):
  print t["id"], t["title"], t["tags"]
  
for t in gtg.get_task_ids_filtered([], ["Active"], False, False):
  print t

t1 = gtg.new_task(
    "Active", # status
    "This is another test", # title
    "2009-07-10", # due date
    "2009-07-07", # start date
    "", # finish date
    ["@ars"], # tags
    "This is more test content!", # text
    []) # subtask ids

t2 = gtg.new_task(
    "Active", # status
    "This is a test", # title
    "2009-07-10", # due date
    "2009-07-07", # start date
    "", # finish date
    ["@ars", "@article"], # tags
    "This is test content!", # text
    [t1["id"]]) # subtask ids

for t in gtg.get_tasks():
  if "test" in t["title"]:
    gtg.delete_task(t["id"])

tid = "4@1"

if gtg.has_task(tid):
  t = gtg.get_task("4@1")
  t["title"] = "I've changed the title!"
  t["tags"].append("@test")
  gtg.modify_task(tid, t)

for t in gtg.get_tasks():
  if "Qt" in t["title"]:
    gtg.open_task_editor(t["id"])

gtg.hide_task_browser()
#gtg.show_task_browser()
```

# Documentation
Not much yet, but feel free to fill in the gaps!
All the function you can exploit are in this file: [GTG-dbuswrapper](http://bazaar.launchpad.net/~gtg/gtg/trunk/annotate/head:/GTG/core/dbuswrapper.py)

# Apps that interface with GTG

* docky
* cairo dock
* mutt (via cli gtg_new_task)
