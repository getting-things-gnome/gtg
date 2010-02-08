import dbus
import dbus.glib
import dbus.service

from GTG.core import CoreConfig
from GTG.tools import dates

BUSNAME = CoreConfig.BUSNAME
BUSFACE = CoreConfig.BUSINTERFACE


def dsanitize(data):
    # Clean up a dict so that it can be transmitted through D-Bus
    for k, v in data.items():
        # Manually specify an arbitrary content type for empty Python arrays
        # because D-Bus can't handle the type conversion for empty arrays
        if not v and isinstance(v, list):
            data[k] = dbus.Array([], "s")
        # D-Bus has no concept of a null or empty value so we have to convert
        # None types to something else. I use an empty string because it has
        # the same behavior as None in a Python conditional expression
        elif v == None:
            data[k] = ""

    return data


def task_to_dict(task):
    # Translate a task object into a D-Bus dictionary
    return dbus.Dictionary(dsanitize({
          "id": task.get_id(),
          "status": task.get_status(),
          "title": task.get_title(),
          "duedate": str(task.get_due_date()),
          "startdate": str(task.get_start_date()),
          "donedate": str(task.get_closed_date()),
          "tags": task.get_tags_name(),
          "text": task.get_text(),
          "subtask": task.get_subtask_tids(),
          }), signature="sv")


class DBusTaskWrapper(dbus.service.Object):

    # D-Bus service object that exposes GTG's task store to third-party apps
    def __init__(self, req, ui):
        # Attach the object to D-Bus
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(BUSNAME, bus=self.bus)
        dbus.service.Object.__init__(self, bus_name, BUSFACE)
        self.req = req
        self.ui = ui

    @dbus.service.method(BUSNAME)
    def get_task_ids(self):
        # Retrieve a list of task ID values
        return self.req.get_tasks_list(
          status=["Active", "Done"], started_only=False)

    @dbus.service.method(BUSNAME)
    def get_task(self, tid):
        # Retrieve a specific task by ID and return the data
        toret = task_to_dict(self.req.get_task(tid))
        return toret

    @dbus.service.method(BUSNAME)
    def get_tasks(self):
        # Retrieve a list of task data dicts
        return [self.get_task(id) for id in self.get_task_ids()]

    @dbus.service.method(BUSNAME, in_signature="asasbb")
    def get_task_ids_filtered(self, tags, status, started_only, is_root):
        # Retrieve a list of task IDs filtered by specified parameters
        tags_obj = []
        for t in tags:
            zetag = self.req.get_tag(t)
            if zetag:
                tags_obj.append(zetag)
        ids = self.req.get_tasks_list(
            tags_obj, status, False, started_only, is_root)
        # If there are no matching tasks, return an empty D-Bus array
        return ids if ids else dbus.Array([], "s")

    @dbus.service.method(BUSNAME, in_signature="asasbb")
    def get_tasks_filtered(self, tags, status, started_only, is_root):
        # Retrieve a list of task data dicts filtered by specificed parameters
        tasks = self.get_task_ids_filtered(
            tags, status, started_only, is_root)
        # If no tasks match the filter, return an empty D-Bus array
        if tasks:
            return [self.get_task(id) for id in tasks]
        else:
            return dbus.Array([], "s")

    @dbus.service.method(BUSNAME)
    def has_task(self, tid):
        return self.req.has_task(tid)

    @dbus.service.method(BUSNAME)
    def delete_task(self, tid):
        self.req.delete_task(tid)

    @dbus.service.method(BUSNAME, in_signature="sssssassas")
    def new_task(self, status, title, duedate, startdate, donedate, tags,
                 text, subtasks):
        # Generate a new task object and return the task data as a dict
        nt = self.req.new_task(tags=tags)
        for sub in subtasks:
            nt.add_subtask(sub)
        nt.set_status(status, donedate=dates.strtodate(donedate))
        nt.set_title(title)
        nt.set_due_date(dates.strtodate(duedate))
        nt.set_start_date(dates.strtodate(startdate))
        nt.set_text(text)
        return task_to_dict(nt)

    @dbus.service.method(BUSNAME)
    def modify_task(self, tid, task_data):
        # Apply supplied task data to the task object with the specified ID
        task = self.req.get_task(tid)
        task.set_status(task_data["status"], donedate=task_data["donedate"])
        task.set_title(task_data["title"])
        task.set_due_date(task_data["duedate"])
        task.set_start_date(task_data["startdate"])
        task.set_text(task_data["text"])

        for tag in task_data["tags"]:
            task.add_tag(tag)
        for sub in task_data["subtask"]:
            task.add_subtask(sub)
        return task_to_dict(task)

    @dbus.service.method(BUSNAME)
    def open_task_editor(self, tid):
        self.ui.open_task(tid)
        
    @dbus.service.method(BUSNAME, in_signature="ss")
    def open_new_task(self, title, description):
        nt = self.req.new_task(newtask=True)
        nt.set_title(title)
        if description != "":
            nt.set_text(description)
        uid = nt.get_id()
        self.ui.open_task(uid,thisisnew=True)

    @dbus.service.method(BUSNAME)
    def hide_task_browser(self):
        self.ui.window.hide()

    @dbus.service.method(BUSNAME)
    def show_task_browser(self):
        self.ui.window.present()
        self.ui.window.move(
          self.ui.priv["window_xpos"], self.ui.priv["window_ypos"])
