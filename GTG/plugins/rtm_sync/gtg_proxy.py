import sys
import os
# IMPORTANT This add's the plugin's path to python sys path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from generic_task import GtgTask

class GtgProxy:
    def __init__(self, plugin_api):
        self.plugin_api = plugin_api
        self.task_list = []

    def generateTaskList(self):
        #TODO: RTM allows multiple task with the same name, gtg does not. Solve!
        #FIXME:  from here on we assume that purging of the multiple entries has
        #  been done     (keep an eye on the "set" objects, since they do the
        #  purging silently)
        tasks = map (self.plugin_api.get_task, \
                     self.plugin_api.get_requester().get_active_tasks_list())
        map (lambda task: self.task_list.append(GtgTask(task)), tasks)

