import gobject, dbus.glib, dbus, dbus.service

def dsanitize(data):
  for k, v in data.items():
    if not v and isinstance(v, list):
      data[k] = dbus.Array([], "s")
    elif v == None:
      data[k] = ""

  return data

def task_to_dict(task):
  return dbus.Dictionary(dsanitize({
      "id": task.get_id(),
      "status": task.get_status(),
      "title": task.get_title(),
      "duedate": task.get_due_date(),
      "startdate": task.get_start_date(),
      "donedate": task.get_closed_date(),
      "tags": task.get_tags_name(),
      "text": task.get_text(),
      "subtask": task.get_subtasks_tid(),
    }), signature="sv")

class DBusTaskWrapper(dbus.service.Object):
  def __init__(self, req, ui):
    self.bus = dbus.SessionBus()
    bus_name = dbus.service.BusName("com.fritalk.GTG", bus=self.bus)
    dbus.service.Object.__init__(self, bus_name, "/com/fritalk/GTG")
    self.req = req
    self.ui = ui

  @dbus.service.method("com.fritalk.GTG")
  def get_task_ids(self):
    return self.req.get_tasks_list(status=["Active", "Done"], started_only=False)

  @dbus.service.method("com.fritalk.GTG")
  def get_task(self, tid):
    return task_to_dict(self.req.get_task(tid))

  @dbus.service.method("com.fritalk.GTG")
  def get_tasks(self):
    return [self.get_task(id) for id in self.get_task_ids()]

  @dbus.service.method("com.fritalk.GTG", in_signature="asasbb")
  def get_task_ids_filtered(self, tags, status, started_only, is_root):
    ids = self.req.get_tasks_list(tags, status, False, started_only, is_root)
    return ids if ids else dbus.Array([], "s")

  @dbus.service.method("com.fritalk.GTG", in_signature="asasbb")
  def get_tasks_filtered(self, tags, status, started_only, is_root):
    tasks = self.get_task_ids_filtered(tags, status, started_only, is_root)
    return [self.get_task(id) for id in tasks] if tasks else dbus.Array([], "s")

  @dbus.service.method("com.fritalk.GTG")
  def has_task(self, tid):
    return self.req.has_task(tid)

  @dbus.service.method("com.fritalk.GTG")
  def delete_task(self, tid):
    self.req.delete_task(tid)

  @dbus.service.method("com.fritalk.GTG", in_signature="sssssassas")
  def new_task(self, status, title, duedate, startdate, donedate, tags, text, subtasks):
    nt = self.req.new_task()
    for sub in subtasks: nt.add_subtask(sub)
    for tag in tags: nt.add_tag(tag)
    nt.set_status(status, donedate=donedate)
    nt.set_title(title)
    nt.set_due_date(duedate)
    nt.set_start_date(startdate)
    nt.set_text(text)
    return task_to_dict(nt)

  @dbus.service.method("com.fritalk.GTG")
  def modify_task(self, tid, task_data):
    task = self.req.get_task(tid)
    task.set_status(task_data["status"], donedate=task_data["donedate"])
    task.set_title(task_data["title"])
    task.set_due_date(task_data["duedate"])
    task.set_start_date(task_data["startdate"])
    task.set_text(task_data["text"])

    for tag in task_data["tags"]: task.add_tag(tag)
    for sub in task_data["subtask"]: task.add_subtask(sub)
    return task_to_dict(task)

  @dbus.service.method("com.fritalk.GTG")
  def open_task_editor(self, tid):
    self.ui.open_task(tid)

  @dbus.service.method("com.fritalk.GTG")
  def hide_task_browser(self):
    self.ui.window.hide()
  
  @dbus.service.method("com.fritalk.GTG")
  def show_task_browser(self):
    self.ui.window.present()
    self.ui.window.move(self.ui.priv["window_xpos"], self.ui.priv["window_ypos"])
