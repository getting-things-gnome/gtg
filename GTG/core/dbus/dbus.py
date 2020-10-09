from gi.repository import GLib, Gio
import logging
import os
import traceback


log = logging.getLogger(__name__)


def _get_installed_xml_from_interface_name(interface_name: str):
    """Return an DBus interface XML from system installed folders"""
    raw_paths = GLib.get_system_data_dirs()
    raw_paths.append(GLib.get_user_data_dir())
    for raw_path in raw_paths:
        full_path = os.path.join(raw_path, 'dbus-1', 'interfaces',
                                 interface_name + ".xml")
        try:
            with open(full_path, 'rt') as f:
                log.debug(f"Found file {full_path}")
                return f.read()
        except OSError:
            pass
    return None


def _get_internal_xml_from_interface_name(interface_name: str):
    """Return an DBus interface XML from internal data folders"""
    log.debug("TODO: Implement this later")
    pass


def get_xml_from_interface_name(interface_name: str,
                                use_internal: bool = True,
                                use_system: bool = True):
    """
    Return an DBus interface XML from either provided by the system (distro)
    or internal.
    """
    if use_internal:
        xml = _get_internal_xml_from_interface_name(interface_name)
        if xml is not None:
            return xml
    if use_system:
        xml = _get_installed_xml_from_interface_name(interface_name)
        if xml is not None:
            return xml
    return None


class DBusReturnError(Exception):
    """
    An error that an DBus interface implementation can throw to indicate
    that it should return with that error.
    """
    def __init__(self, name, message):
        super().__init__(message)
        self.name = str(name)
        self.message = str(message)


class DBusInterfaceImplService():
    INTERFACE_NAME = None
    NODE_INFO = None
    INTERFACE_INFO = None
    _object_id = None
    _dbus_connection = None

    def __init__(self, wrapped_object=None):
        if wrapped_object is None:
            wrapped_object = self
        self._wrapped_object = wrapped_object

    def __get_interface_info_from_node_info(self):
        for interface in self.NODE_INFO.interfaces:
            if interface.name == self.INTERFACE_NAME:
                return interface
        return None

    def __get_node_info(self):
        xml = get_xml_from_interface_name(self.INTERFACE_NAME)
        if xml is not None:
            return Gio.DBusNodeInfo.new_for_xml(xml)
        return None

    def _get_info(self):
        if self.NODE_INFO is None and self.INTERFACE_NAME is not None:
            self.NODE_INFO = self.__get_node_info()
            log.debug(f"Got node info for %r: %r",
                      self.INTERFACE_NAME, self.NODE_INFO)
        if self.NODE_INFO is not None and self.INTERFACE_INFO is None:
            self.INTERFACE_INFO = self.__get_interface_info_from_node_info()
            log.debug(f"Got interface info for %r: %r",
                      self.INTERFACE_NAME, self.INTERFACE_INFO)

    def dbus_register(self, dbus_connection, object_path):
        """
        Register this implementation on the specified connection and object.
        """
        self._get_info()
        self._object_id = dbus_connection.register_object(
            object_path,
            self.INTERFACE_INFO,
            self._handle_method_call,
            self._handle_get_property, self._handle_set_property)
        self._dbus_connection = dbus_connection
        return self._object_id

    def dbus_unregister(self):
        """Unregister this implementation."""
        if self._dbus_connection is not None and self._object_id is not None:
            log.debug("Unregister %r on %r via %r",
                      self.INTERFACE_NAME,
                      self._dbus_connection,
                      self._object_id)
            ret = self._dbus_connection.unregister_object(self._object_id)
            self._dbus_connection = None
            self._object_id = None
            if not ret:
                log.warn("Unregister for %r failed!", self.INTERFACE_NAME)
            return ret
        else:
            log.warn("Trying to unregister not-registered %r",
                     self.INTERFACE_NAME)
        return False

    def _handle_method_call(self, connection,
                            sender, object_path,
                            interface_name, method_name,
                            parameters, invocation):
        dbg = "%s.%s%s on %s by %s"
        dbg_args = (interface_name, method_name, parameters,
                    object_path, sender)
        log.debug(f"Called {dbg}", *dbg_args)

        try:
            method = self._wrapped_object.__getattribute__(method_name)
        except AttributeError as e:
            log.debug(f"{dbg} → Internal python exception: %s", *dbg_args, e)
            invocation.return_dbus_error("python." + type(e).__name__, str(e))
            return

        try:
            ret = method(*parameters.unpack())
        except GLib.Error as e:
            log.debug(f"{dbg} → GLib Error: %s", *dbg_args, e)
            invocation.return_gerror(e)
        except DBusReturnError as e:
            log.debug(f"{dbg} → Custom Error: %s: %s",
                      *dbg_args, e.name, e.message)
            invocation.return_dbus_error(e.name, e.message)
        except Exception as e:
            log.warn(f"{dbg} → Python exception: %s", *dbg_args, e)
            traceback.print_exc()
            invocation.return_dbus_error("python." + type(e).__name__, str(e))
        else:
            if type(ret) != GLib.Variant:
                if len(invocation.get_method_info().out_args) == 1:
                    ret = (ret,) # Make one-value return work as expected
                ret = GLib.Variant(self.__get_return_variant(invocation), ret)
            log.debug(f"{dbg} → Returning %r", *dbg_args, ret)
            invocation.return_value(ret)

    def _handle_get_property(self, *args):
        """Get a DBus-available property"""
        log.debug(f"TODO: Handle get property: {args}") # Not used currently
        return None

    def _handle_set_property(self, *args):
        """Set a DBus-available property"""
        log.debug(f"TODO: Handle set property: {args}") # Not used currently
        return None

    def __get_return_variant(self, invocation):
        """Get Variant Type string that should be returned for a DBus method"""
        info = invocation.get_method_info()
        return '(' + "".join([arg.signature for arg in info.out_args]) + ')'
