# -----------------------------------------------------------------------------
# GTG Developer Console
# Based on Pitivi Developer Console
# Copyright (c) 2017-2018, Fabian Orccon <cfoch.fabian@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""The developer console widget."""

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from GTG.plugins.dev_console.buffer import ConsoleBuffer


class ConsoleView(Gtk.TextView):
    """A TextView which removes tags from pasted text."""

    def do_paste_clipboard(self):
        # pylint: disable=arguments-differ
        buf = self.get_buffer()
        insert = buf.get_insert()
        paste_mark = buf.create_mark("paste-mark", buf.get_iter_at_mark(insert),
                                     left_gravity=True)

        Gtk.TextView.do_paste_clipboard(self)

        start = buf.get_iter_at_mark(paste_mark)
        end = buf.get_iter_at_mark(insert)

        buf.remove_all_tags(start, end)
        buf.delete_mark(paste_mark)


class ConsoleWidget(Gtk.ScrolledWindow):
    """An emulated Python console.

    The console can be used to access an app, window, or anything through the
    provided namespace. It works redirecting stdout and stderr to a
    GtkTextBuffer. This class is (and should be) independent of the application
    it is integrated with.
    """

    __gsignals__ = {
        "eof": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, namespace, welcome_message=""):
        Gtk.ScrolledWindow.__init__(self)
        self._view = ConsoleView()
        buf = ConsoleBuffer(namespace, welcome_message)
        self._view.set_buffer(buf)
        self._view.set_editable(True)
        self.add(self._view)

        self._view.connect("key-press-event", self.__key_press_event_cb)
        buf.connect("mark-set", self.__mark_set_cb)
        buf.connect("insert-text", self.__insert_text_cb)

        # Font color and style.
        self._provider = Gtk.CssProvider()
        self._css_values = {
            'textview': {
                'font-family': None,
                'font-size': None,
                'font-style': None,
                'font-variant': None,
                'font-weight': None,
                'caret-color': '#888888',
            },
            'textview > text': {
                'background-color': '#191919'
            },
            'textview > *': {
                'color': None
            }
        }

        self._view.set_left_margin(25)
        self._view.set_right_margin(25)
        self._view.set_top_margin(25)
        self._view.set_bottom_margin(25)

    def scroll_to_end(self):
        """Scrolls the view to the end."""
        end_iter = self._view.get_buffer().get_end_iter()
        self._view.scroll_to_iter(end_iter, within_margin=0.0, use_align=False,
                                  xalign=0, yalign=0)
        return False

    def set_font(self, font_desc):
        """Sets the font.

        Args:
            font_desc (str): a PangoFontDescription as a string.
        """
        pango_font_desc = Pango.FontDescription.from_string(font_desc)
        self._css_values["textview"]["font-family"] = pango_font_desc.get_family()
        self._css_values["textview"]["font-size"] = "%dpt" % int(pango_font_desc.get_size() / Pango.SCALE)
        self._css_values["textview"]["font-style"] = pango_font_desc.get_style().value_nick
        self._css_values["textview"]["font-variant"] = pango_font_desc.get_variant().value_nick
        self._css_values["textview"]["font-weight"] = int(pango_font_desc.get_weight())
        self._apply_css()

    def set_color(self, color):
        """Sets the color.

        Args:
            color (Gdk.RGBA): a color.
        """
        self._css_values["textview > *"]["color"] = color.to_string()
        self._apply_css()

    def _apply_css(self):
        css = ""
        for css_klass, props in self._css_values.items():
            css += "%s {" % css_klass
            for prop, value in props.items():
                if value is not None:
                    css += "%s: %s;" % (prop, value)
            css += "} "
        css = css.encode("UTF-8")
        self._provider.load_from_data(css)
        Gtk.StyleContext.add_provider(self._view.get_style_context(),
                                      self._provider,
                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def set_stdout_color(self, color):
        """Sets the color of the stdout text."""
        self._view.get_buffer().output.set_property("foreground-rgba", color)

    def set_stderr_color(self, color):
        """Sets the color of the stderr text."""
        self._view.get_buffer().error.set_property("foreground-rgba", color)

    # pylint: disable=too-many-return-statements
    def __key_press_event_cb(self, view, event):
        buf = view.get_buffer()
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        if event.keyval == Gdk.KEY_Return:
            buf.process_command_line()
            return True

        if event.keyval in (Gdk.KEY_KP_Down, Gdk.KEY_Down):
            buf.history.down(buf.get_command_line())
            return True
        if event.keyval in (Gdk.KEY_KP_Up, Gdk.KEY_Up):
            buf.history.up(buf.get_command_line())
            return True

        if event.keyval in (Gdk.KEY_KP_Left, Gdk.KEY_Left, Gdk.KEY_BackSpace):
            return buf.is_cursor(at=True)

        if event.keyval in (Gdk.KEY_KP_Home, Gdk.KEY_Home):
            buf.place_cursor(buf.get_iter_at_mark(buf.prompt_mark))
            return True

        if (ctrl and event.keyval == Gdk.KEY_d) or event.keyval == Gdk.KEY_Escape:
            return self.emit("eof")

        return False

    def __mark_set_cb(self, buf, unused_iter, mark):
        if not mark.props.name == "insert":
            return

        self._view.set_editable(buf.is_cursor(at=True, after=True))

    def __insert_text_cb(self, buf, unused_iter, unused_text, unused_len):
        GLib.idle_add(self.scroll_to_end)

