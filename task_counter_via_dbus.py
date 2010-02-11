from __future__ import with_statement
import dbus
from GTG.core import CoreConfig

def get_task_ids():
    d=dbus.SessionBus().get_object(CoreConfig.BUSNAME,\
                                  CoreConfig.BUSINTERFACE)
    return d.get_task_ids("Active")

    

if __name__ == "__main__":
    # init logging system
    config = CoreConfig()
    print "GTG currently has " + \
            str(len(get_task_ids())) + \
            " tasks"
