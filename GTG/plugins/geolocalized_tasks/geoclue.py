#This class will be called for gelocalized_task

import dbus
from dbus.mainloop.glib import DBusGMainLoop
class Geoclue:

    GEOCLUE2_BUS_NAME = 'org.freedesktop.GeoClue2'
    MANAGER_INTERFACE_NAME = 'org.freedesktop.GeoClue2.Manager'
    CLIENT_INTERFACE_NAME = 'org.freedesktop.GeoClue2.Client'
    LOCATION_INTERFACE_NAME ='org.freedesktop.GeoClue2.Location'
    PROPERTIES_INTERFACE_NAME = 'org.freedesktop.DBus.Properties'

    def __init__(self):
        dbus_loop = DBusGMainLoop(set_as_default=True)
        system_bus = dbus.SystemBus (mainloop = dbus_loop)
        manager_object = system_bus.get_object(self.GEOCLUE2_BUS_NAME, '/org/freedesktop/GeoClue2/Manager')
        manager = dbus.Interface(manager_object, self.MANAGER_INTERFACE_NAME)

        client_path = manager.GetClient()
        client_object = system_bus.get_object(self.GEOCLUE2_BUS_NAME, client_path)
        client_properties = dbus.Interface(client_object, self.PROPERTIES_INTERFACE_NAME)
        client_properties.Set(self.CLIENT_INTERFACE_NAME, 'DistanceThreshold', dbus.UInt32(100))

        self.client = dbus.Interface(client_object, self.CLIENT_INTERFACE_NAME)
        self._system_bus = system_bus
