# system_info.py: Collect system information
# Copyright (C) 2024 GTG Contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import platform
import importlib

from GTG.core import info

from gi.repository import Gdk, Gtk, GObject, GLib, Xdp


class SystemInfo:
    def get_system_info(self, report: bool = False) -> str:
        """
        Get system information based on their
        availability and installed version.
        """
        self.report = report

        sys_info = ""
        sys_info += self.__format_info("GTG", info.VERSION)

        if Xdp.Portal.running_under_flatpak():
            sys_info += self.__format_info("Flatpak", self.__get_flatpak_version())
        else:
            sys_info += self.__format_info("Flatpak", "False")

        sys_info += self.__format_info("Snap", Xdp.Portal.running_under_snap())
        sys_info += self.__format_info("Display Name", Gdk.Display.get_default().get_name())
        sys_info += self.__format_info("Desktop", os.environ.get("XDG_CURRENT_DESKTOP"))

        sys_info += "\n"
        sys_info += self.__format_info("lxml", self.__get_python_module("lxml"))
        sys_info += self.__format_info("caldav", self.__get_python_module("caldav"))
        sys_info += self.__format_info("liblarch", self.__get_python_module("liblarch"))
        sys_info += self.__format_info("Cheetah3", self.__get_python_module("Cheetah"))
        sys_info += self.__format_info("dbus-python", self.__get_python_module("dbus"))
        sys_info += self.__format_info("pdflatex", self.__get_python_module("pdflatex"))
        sys_info += self.__format_info("pypdftk", self.__get_python_module("pdftk"))

        # Only display OS info when user isn't running as Flatpak/Snap
        if not Xdp.Portal.running_under_sandbox():
            sys_info += "\n"
            sys_info += self.__format_info("OS", GLib.get_os_info("PRETTY_NAME"))

            sys_info += self.__format_info(
                "Python", f"{platform.python_implementation()} {platform.python_version()}"
            )

            sys_info += self.__format_info("GLib", self.__version_to_string(GLib.glib_version))
            sys_info += self.__format_info("PyGLib", self.__version_to_string(GLib.pyglib_version))

            sys_info += self.__format_info(
                "PyGObject", self.__version_to_string(GObject.pygobject_version)
            )

            sys_info += self.__format_info("GTK", self.__version_to_string(self.__get_gtk_version()))

        return sys_info


    def __version_to_string(self, version: tuple) -> str:
        """
        Convert version tuple (major, micro, minor)
        version to string (major.micro.minor).
        """
        return ".".join(map(str, version))


    def __format_info(self, lib: str, getter) -> str:
        """
        Pretty-format library and availability
        """
        if self.report:
            return f"**{lib}:** {getter}\n"
        else:
            return f"{lib}: {getter}\n"


    def __get_flatpak_version(self) -> str:
        """Get Flatpak version."""
        with open("/.flatpak-info") as flatpak_info:
            for line in flatpak_info:
                if line.startswith("flatpak-version"):
                    flatpak_version = line.split("=")[1].strip()
                    return flatpak_version


    def __get_gtk_version(self) -> str:
        """Get GTK version."""
        return (
            Gtk.get_major_version(),
            Gtk.get_micro_version(),
            Gtk.get_minor_version(),
        )


    def __get_python_module(self, module: str) -> bool:
        """Check if Python module is installed."""
        return bool(importlib.util.find_spec(module))
