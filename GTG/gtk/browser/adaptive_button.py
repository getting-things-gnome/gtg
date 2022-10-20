import logging
import dataclasses
from typing import Optional, List, Tuple

from gi.repository import GObject, GLib, Gtk, Gdk


log = logging.getLogger(__name__)


class AdaptiveFittingWidget(Gtk.Container):
    """
    This widget chooses the biggest but fitting children widgets and displays
    that one. This is useful to switch out between text and an icon in an
    button if the window gets smaller.
    Note that this is heavily "adjusted" what GTG uses this widget for.
    """

    __gtype_name__ = "GTGAdaptiveFittingWidget"

    @dataclasses.dataclass
    class ChildItem:
        """
        Represents a child widget with some useful to have properties to use
        later.
        """
        widget: Gtk.Widget
        """Widget to possibly draw and request data from"""

        request_mode: Gtk.SizeRequestMode = Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH
        """What request mode the widget is in"""

        minimum_width: int = 0
        """The minimum width the widget claims to have"""
        natural_width: int = 0
        """The natural width the widget claims to have"""

        minimum_height: int = 0
        """The minimum height the widget claims to have"""
        natural_height: int = 0
        """The natural height the widget claims to have"""

    def __init__(self, *args, **kwargs):
        self._children: List[ChildItem] = []
        """Child widgets to consider together with internal bookkeeping data"""

        self._child_to_draw: Optional[ChildItem] = None
        """Current child to draw"""

        self._draw_smallest_child_if_smaller: bool = True
        """Whenever to draw the smallest child even if it doesn't fit"""

        self._spammy_debug: bool = False
        """Show more debug messages related to this widget"""

        super().__init__(*args, **kwargs)

    @classmethod
    def new(cls):
        return cls()

    @GObject.Property(type=bool, default=True)
    def draw_smallest_child_if_smaller(self) -> bool:
        """
        If this widget is smaller than the smallest child widget allows, just
        draw the smallest child. Ensures that something is always being
        displayed when at least one child exists.
        """

        return self._draw_smallest_child_if_smaller

    @draw_smallest_child_if_smaller.setter
    def draw_smallest_child_if_smaller(self, value: bool):
        self._draw_smallest_child_if_smaller = value

    @GObject.Property(type=Gtk.Widget)
    def active_child(self) -> Optional[Gtk.Widget]:
        """Currently active children chosen to being drawn."""

        try:
            return self._child_to_draw.widget
        except AttributeError:
            return None

    def _determine_active_child(self, width: Optional[int] = None
                                ) -> Optional[ChildItem]:
        """
        Determines the child widget to use. It uses the current allocation
        to determine the available size. Also, the _children attribute needs
        to be sorted by minimum_width ascending.
        """

        if width is None:
            allocation = self.get_allocation()
            width = allocation.width
        active_child: Optional[Gtk.Widget] = None

        # Requires to be sorted by minimum_width
        for ci in self._children:
            if width < ci.minimum_width:
                break
            if ci.widget.get_visible():
                active_child = ci

        if active_child is None \
                and self._draw_smallest_child_if_smaller \
                and self._children != []:
            active_child = self._children[0]

        return active_child

    def _determine_and_save_active_child(self):
        """
        Determines the child widget to use via _determine_active_child,
        and saves it in attribute _child_to_draw, so calculation doesn't need
        to be done when drawing (which may be called often).
        """
        old_child = self._child_to_draw
        self._child_to_draw = self._determine_active_child()
        if old_child is not self._child_to_draw:
            self.notify('active-child')
            self.queue_draw()

    # ------------------------------------------------------------------------
    # Gtk.Widget implementation
    # ------------------------------------------------------------------------

    def do_get_request_mode(self) -> Gtk.SizeRequestMode:
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_get_preferred_width(self) -> Tuple[int, int]:
        if self._children == []:
            log.debug("No children - return minimum=0, natural=0")
            return (0, 0)  # Allow to be as small as possible

        minimum, natural = GLib.MAXINT32, 0
        for ci in self._children:
            ci.minimum_width, ci.natural_width = \
                ci.widget.get_preferred_width()
            if self._spammy_debug:
                log.debug("child=%r minimum=%r natural=%r",
                          ci.widget, ci.minimum_width, ci.natural_width)
            minimum = min(minimum, ci.minimum_width)
            natural = max(natural, ci.natural_width)

        self._children.sort(key=lambda ci: ci.minimum_width)
        self._determine_and_save_active_child()

        if self._spammy_debug:
            log.debug("return minimum=%r, natural=%r", minimum, natural)
        return (minimum, natural)

    def do_get_preferred_height_for_width(self, width: int) -> Tuple[int, int]:
        if self._children == []:
            log.debug("No children - return minimum=0, natural=0")
            return (0, 0)  # Allow to be as small as possible

        minimum, natural = GLib.MAXINT32, 0
        for ci in self._children:
            ci.minimum_height, ci.natural_height = \
                ci.widget.get_preferred_height_for_width(width)
            minimum = min(minimum, ci.minimum_height)
            natural = max(natural, ci.natural_height)

            if self._spammy_debug:
                log.debug("child=%r minimum=%r natural=%r",
                          ci.widget, ci.minimum_height, ci.natural_height)
        self._determine_and_save_active_child()

        if self._spammy_debug:
            log.debug("(width=%r) return minimum=%r, natural=%r",
                      width, minimum, natural)
        return (minimum, natural)

    def do_get_preferred_height(self) -> Tuple[int, int]:
        # As suggested by the GtkContainer docs
        min_width, nat_width = self.get_preferred_width()
        minimum, natural = self.get_preferred_height_for_width(min_width)

        if self._spammy_debug:
            log.debug("return minimum=%r, natural=%r", minimum, natural)
        return (minimum, natural)

    def do_get_preferred_width_for_height(self, height: int
                                          ) -> Tuple[int, int]:
        # As suggested by the GtkContainer docs
        minimum, natural = self.get_preferred_width()

        if self._spammy_debug:
            log.debug("(height=%r) return minimum=%r, natural=%r",
                      height, minimum, natural)
        return (minimum, natural)

    def do_draw(self, cr):
        allocation = self.get_allocation()
        width = allocation.width

        if self._spammy_debug:
            log.debug("width=%r, children=%r", width,
                      list(map(lambda ci: ci.minimum_width, self._children)))

        draw_child = self._child_to_draw
        if draw_child is not None:
            draw_child.widget.draw(cr)
        else:
            log.debug("Found no suitable child")

    def do_realize(self):
        self.set_realized(True)

        allocation = self.get_allocation()
        if self._spammy_debug:
            log.debug("allocation={x=%r, y=%r, w=%r, h=%r}",
                      allocation.x, allocation.y,
                      allocation.width, allocation.height)

        attributes = Gdk.WindowAttr()
        attributes.window_type = Gdk.WindowType.CHILD
        attributes.x = allocation.x
        attributes.y = allocation.y
        attributes.width = allocation.width
        attributes.height = allocation.height
        attributes.wclass = Gdk.WindowWindowClass.INPUT_OUTPUT
        attributes.visual = self.get_visual()
        attributes.event_mask = self.get_events() | Gdk.EventMask.EXPOSURE_MASK

        window = Gdk.Window.new(self.get_parent_window(), attributes,
                                Gdk.WindowAttributesType.VISUAL |
                                Gdk.WindowAttributesType.X |
                                Gdk.WindowAttributesType.Y)
        self.register_window(window)
        self.set_window(window)

    def do_size_allocate(self, allocation: Gdk.Rectangle):
        if self._spammy_debug:
            log.debug("allocation={x=%r, y=%r, w=%r, h=%r}",
                      allocation.x, allocation.y,
                      allocation.width, allocation.height)

        self.set_allocation(allocation)
        Gtk.Container.do_size_allocate(self, allocation)  # Resizes Gdk.Window

        for ci in self._children:
            ci.widget.size_allocate(allocation)

        self._determine_and_save_active_child()

    # ------------------------------------------------------------------------
    # Gtk.Container implementation
    # ------------------------------------------------------------------------

    def do_add(self, widget: Gtk.Widget):
        log.debug("widget=%r", widget)
        if widget in map(lambda ci: ci.widget, self._children):
            log.warning("Trying to add already added widget %r to %r",
                        widget, self)
        else:
            widget.set_parent(self)
            self._children.append(self.ChildItem(widget))
            self.queue_resize()

    def do_remove(self, widget: Gtk.Widget):
        for i, ci in enumerate(self._children):
            if ci.widget == widget:
                del self._children[i]
                self.queue_resize()
                return
        log.warning("Tried to remove non-existing child: %r (from %r)",
                    widget, self)

    def do_forall(self, include_internals: bool, callback, *args):
        try:
            for ci in self._children:
                try:
                    callback(ci.widget)
                except Exception as e:
                    log.warning("Silenced exception: %r", e)
        except AttributeError as e: # ... object has no attribute '_children'
            log.warning("Got error in for but it should have stayed valid: %r", e)

    def do_child_type(self):
        log.debug("returning %r", Gtk.Widget.__gtype__)
        return Gtk.Widget.__gtype__

    def do_get_child_property(self, child: Gtk.Widget, property_id: int,
                              value: GObject.Value, pspec: GObject.ParamSpec):
        # We don't have any child properties anyway
        log.debug("Unimplemented child=%r, property_id=%r, value=%r, pspec=%r",
                  child, property_id, value, pspec)

    def do_set_child_property(self, child: Gtk.Widget, property_id: int,
                              value: GObject.Value, pspec: GObject.ParamSpec):
        # We don't have any child properties anyway
        log.debug("Unimplemented child=%r, property_id=%r, value=%r, pspec=%r",
                  child, property_id, value, pspec)
