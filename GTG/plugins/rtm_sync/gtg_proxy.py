import sys
import os
# IMPORTANT This add's the plugin's path to python sys path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from generic_task import GtgTask
from generic_proxy import GenericProxy

class GtgProxy(GenericProxy):
    def __init__(self, plugin_api):
        super(GtgProxy, self).__init__()
        self.plugin_api = plugin_api

    def generateTaskList(self):
        tasks = map (self.plugin_api.get_task, \
                     self.plugin_api.get_requester().get_active_tasks_list())
        map (lambda task: self.task_list.append(GtgTask(task)), tasks)

    def newTask(self, title, never_seen_before):
        new_task =  GtgTask (self.plugin_api.get_requester().new_task(
                             newtask=never_seen_before))
        new_task.title = title
        self.task_list.append(new_task)
        return new_task


