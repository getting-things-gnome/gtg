# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The GTG Team
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
# -----------------------------------------------------------------------------

"""Task pane and list."""

from gi.repository import Gtk, GObject, Gdk, Gio, Pango
from GTG.core.tasks import Task, Status, FilteredTaskTreeManager
from GTG.core.filters import TaskFilter
from GTG.core.sorters import (TaskAddedSorter, TaskDueSorter,
                              TaskModifiedSorter, TaskStartSorter,
                              TaskTagSorter, TaskTitleSorter)
from GTG.gtk.browser.tag_pill import TagPill
from gettext import gettext as _


BIND_FLAGS = GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE

class TaskBox(Gtk.Box):
    """Box subclass to keep a pointer to the tag object"""

    task = GObject.Property(type=Task)

    def __init__(self, config, is_actionable=False):
        self.config = config
        super().__init__(valign=Gtk.Align.CENTER)

        self.add_css_class('task-box')

        self.expander = Gtk.TreeExpander()
        self.expander.add_css_class('arrow-only-expander')
        self.expander.set_indent_for_icon(True)
        self.expander.set_indent_for_depth(True)

        self.check = Gtk.CheckButton()

        self.append(self.expander)
        self.append(self.check)

        self.is_actionable = is_actionable


    @GObject.Property(type=bool, default=True)
    def has_children(self) -> None:
        return


    @has_children.setter
    def set_has_children(self, value) -> bool:

        if self.is_actionable:
            value = False


    @GObject.Property(type=bool, default=True)
    def is_active(self) -> None:
        return


    @is_active.setter
    def set_is_active(self, value) -> bool:
        if value:
            self.remove_css_class('closed-task')
        else:
            self.add_css_class('closed-task')


    @GObject.Property(type=str)
    def row_css(self) -> None:
        return


    @row_css.setter
    def set_row_css(self, value) -> None:
        show = self.config.get('bg_color_enable')
        context = self.get_style_context()

        if not value or not show:
            try:
                context.remove_provider(self.provider)
                return
            except AttributeError:
                return

        val = str.encode(value)

        self.provider = Gtk.CssProvider()
        self.provider.load_from_data(val)
        context.add_provider(self.provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)


def unwrap(row, expected_type):
    """Find an item in TreeRow widget (sometimes nested)."""

    item = row.get_item()

    while type(item) is not expected_type:
        item = item.get_item()

    return item


class TaskPane(Gtk.ScrolledWindow):
    """The task pane widget"""

    def __init__(self, browser, pane):

        super(TaskPane, self).__init__()
        self.ds = browser.app.ds
        self.app = browser.app
        self.browser = browser
        self.pane = pane
        self.searching = False

        self.set_vexpand(True)
        self.set_hexpand(True)

        # -------------------------------------------------------------------------------
        # Title
        # -------------------------------------------------------------------------------
        title_box = Gtk.Box()
        title_box.set_valign(Gtk.Align.START)

        self.title = Gtk.Label()
        self.title.set_halign(Gtk.Align.START)
        self.title.set_hexpand(True)
        self.title.add_css_class('title-1')
        title_box.append(self.title)

        self.sort_btn = Gtk.MenuButton()
        self.sort_btn.set_icon_name('view-more-symbolic')
        self.sort_btn.add_css_class('flat')

        title_box.append(self.sort_btn)


        # -------------------------------------------------------------------------------
        # Task List
        # -------------------------------------------------------------------------------

        self.task_filter = TaskFilter(self.app.ds, pane)
        self.filter_manager = FilteredTaskTreeManager(self.app.ds.tasks,self.task_filter)
        self.filtered = self.filter_manager.get_tree_model()

        self.sort_model = Gtk.TreeListRowSorter()
        self.sort_model.set_sorter(TaskTitleSorter())

        self.main_sorter = Gtk.SortListModel()
        self.main_sorter.set_model(self.filtered)
        self.main_sorter.set_sorter(self.sort_model)

        self.task_selection = Gtk.MultiSelection.new(self.main_sorter)

        tasks_signals = Gtk.SignalListItemFactory()
        tasks_signals.connect('setup', self.task_setup_cb)
        tasks_signals.connect('bind', self.task_bind_cb)
        tasks_signals.connect('unbind', self.task_unbind_cb)

        view = Gtk.ListView.new(self.task_selection, tasks_signals)
        view.set_show_separators(True)
        view.add_css_class('rich-list')
        view.add_css_class('task-list')

        view_drop = Gtk.DropTarget.new(Task, Gdk.DragAction.COPY)
        view_drop.connect("drop", self.on_toplevel_tag_drop)
        view.add_controller(view_drop)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-released', self.on_key_released)
        view.add_controller(key_controller)
        view.connect('activate', self.on_listview_activated)

        self.set_child(view)
        self.set_title()


    @GObject.Signal(name='expand-all')
    def expand_all(self, *_):
        """Emit this signal to expand all TreeRowExpanders"""


    @GObject.Signal(name='collapse-all')
    def collapse_all(self, *_):
        """Emit this signal to collapse all TreeRowExpanders"""


    def set_title(self) -> None:
        """Change pane title."""

        if not self.task_filter.tags:
           if self.pane == 'active':
               self.title.set_text(_('All Open Tasks'))
           if self.pane == 'workview':
               self.title.set_text(_('Actionable Tasks'))
           if self.pane == 'closed':
               self.title.set_text(_('All Closed Tasks'))

        else:
           tags = ', '.join('@' + t.name for t in self.task_filter.tags)

           if self.pane == 'active':
               self.title.set_text(_('{0} (Open)'.format(tags)))
           if self.pane == 'workview':
               self.title.set_text(_('{0} (Actionable)'.format(tags)))
           if self.pane == 'closed':
               self.title.set_text(_('{0} (Closed)'.format(tags)))


    def set_search_query(self, query) -> None:
        """Change tasks filter."""

        self.task_filter.set_pane(self.pane)
        self.task_filter.set_query(query)
        self.searching = True


    def set_filter_pane(self, pane) -> None:
        """Change tasks filter."""

        if self.searching:
            self.searching = False

        self.pane = pane
        self.task_filter.set_pane(pane)
        self.set_title()


    def set_filter_tags(self, tags=[]) -> None:
        """Change tasks filter."""

        self.task_filter.set_required_tags(tags)
        self.set_title()


    def set_filter_notags(self, tags=[]) -> None:
        """Change tasks filter."""

        self.task_filter.allow_untagged_only()
        self.set_title()


    def refresh(self):
        """Refresh the task filter"""

        self.task_filter.changed(Gtk.FilterChange.DIFFERENT)
        self.main_sorter.items_changed(0,0,0)


    def set_sorter(self, method=None) -> None:
        """Change tasks filter."""

        sorter = None

        if method == 'Start':
            sorter = TaskStartSorter()
        if method == 'Due':
            sorter = TaskDueSorter()
        if method == 'Modified':
            sorter = TaskModifiedSorter()
        elif method == 'Added':
            sorter = TaskAddedSorter()
        elif method == 'Tags':
            sorter = TaskTagSorter()
        elif method == 'Title':
            sorter = TaskTitleSorter()

        self.sort_model.set_sorter(sorter)


    def set_sort_order(self, reverse: bool) -> None:
        """Set order for the sorter."""

        self.sort_model.get_sorter().reverse = reverse


    def on_listview_activated(self, listview, position, user_data = None):
        """Callback when double clicking on a row."""

        self.app.browser.on_edit_active_task()


    def on_key_released(self, controller, keyval, keycode, state):
        """Callback when a key is released. """

        is_enter = keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter)
        is_left = keyval == Gdk.KEY_Left
        is_right = keyval == Gdk.KEY_Right

        if is_enter:
            self.app.browser.on_edit_active_task()
        elif is_left:
            self.expand_selected(False)
        elif is_right:
            self.expand_selected(True)


    def select_last(self) -> None:
        """Select last position in the task list."""

        position = self.filtered.get_n_items()
        self.task_selection.select_item(position - 1, True)


    def select_task(self, task: Task) -> None:
        """Select a task in the list."""

        position = None

        for i in range(self.main_sorter.get_n_items()):
            item = unwrap(self.main_sorter.get_item(i), Task)

            if item == task:
                position = i
                break

        if position is not None:
            self.task_selection.select_item(position, True)


    def get_selection(self, indices: bool = False) -> list:
        """Get the currently selected tasks."""

        selection = self.task_selection.get_selection()
        result, iterator, _ = Gtk.BitsetIter.init_first(selection)
        selected = []

        while iterator.is_valid():
            val = iterator.get_value()

            if indices:
                selected.append(val)
            else:
                selected.append(unwrap(self.task_selection.get_item(val), Task))

            iterator.next()

        return selected


    def expand_selected(self, expand) -> None:
        """Get the box widgets of the selected tasks."""

        selection = self.task_selection.get_selection()
        result, iterator, _ = Gtk.BitsetIter.init_first(selection)

        while iterator.is_valid():
            val = iterator.get_value()
            row = self.task_selection.get_item(val)
            row.set_expanded(expand)

            iterator.next()


    def get_selected_number(self) -> int:
        """Get number of items currently selected."""

        selection = self.task_selection.get_selection()
        return selection.get_size()


    def on_checkbox_toggled(self, button, task=None):
        """Callback when clicking a checkbox."""

        if task.status == Status.DISMISSED:
            task.toggle_dismiss()
        else:
            task.toggle_active()

        task.notify('is_active')
        self.task_filter.changed(Gtk.FilterChange.DIFFERENT)


    def task_setup_cb(self, factory, listitem, user_data=None):
        """Setup widgets for rows"""

        box = TaskBox(self.app.config, self.pane == 'workview')
        label = Gtk.Label()
        separator = Gtk.Separator()
        icons = Gtk.Label()
        color = TagPill()
        due = Gtk.Label()
        due_icon = Gtk.Image.new_from_icon_name('alarm-symbolic')
        start = Gtk.Label()
        start_icon = Gtk.Image.new_from_icon_name('media-playback-start-symbolic')
        recurring_icon = Gtk.Label()

        color.set_size_request(16, 16)

        color.set_vexpand(False)
        color.set_valign(Gtk.Align.CENTER)

        separator.set_margin_end(6)

        def on_notify_visibility(obj, gparamstring):
            val = ((recurring_icon.is_visible()
                    or due_icon.is_visible()
                    or start_icon.is_visible())
                   and
                   (color.is_visible() or icons.is_visible()))
            separator.set_visible(val)

        for widget in (recurring_icon, due_icon, start_icon, color, icons):
            widget.connect("notify::visible", on_notify_visibility)

        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_margin_end(6)
        label.set_xalign(0)

        recurring_icon.set_margin_end(12)
        recurring_icon.set_label('\u2B6E')

        due.set_margin_end(18)

        start.set_margin_end(6)

        # DnD stuff
        source = Gtk.DragSource()
        source.connect('prepare', self.drag_prepare)
        source.connect('drag-begin', self.drag_begin)
        source.connect('drag-end', self.drag_end)
        box.add_controller(source)

        # Set drop for DnD
        drop = Gtk.DropTarget.new(Task, Gdk.DragAction.COPY)
        drop.connect('drop', self.drag_drop)
        drop.connect('enter', self.drop_enter)

        box.add_controller(drop)

        task_RMB_controller = Gtk.GestureSingle(button=Gdk.BUTTON_SECONDARY)
        task_RMB_controller.connect('end', self.on_task_RMB_click)
        box.add_controller(task_RMB_controller)

        self.connect('expand-all', lambda s: box.expander.activate_action('listitem.expand'))
        self.connect('collapse-all', lambda s: box.expander.activate_action('listitem.collapse'))

        box.append(label)
        box.append(recurring_icon)
        box.append(due_icon)
        box.append(due)
        box.append(start_icon)
        box.append(start)
        box.append(separator)
        box.append(color)
        box.append(icons)
        listitem.set_child(box)


    def task_bind_cb(self, factory, listitem, user_data=None):
        """Bind values to the widgets in setup_cb"""

        box = listitem.get_child()
        expander = box.get_first_child()
        check = expander.get_next_sibling()
        label = check.get_next_sibling()
        recurring_icon = label.get_next_sibling()
        due_icon = recurring_icon.get_next_sibling()
        due = due_icon.get_next_sibling()
        start_icon = due.get_next_sibling()
        start = start_icon.get_next_sibling()
        separator = start.get_next_sibling()
        color = separator.get_next_sibling()
        icons = color.get_next_sibling()

        item = unwrap(listitem, Task)

        box.props.task = item
        box.expander.set_list_row(listitem.get_item())

        def not_empty(binding, value, user_data=None):
            return len(value) > 0

        def show_start(binding, value, user_data=None):
            return value and self.pane == 'active'


        listitem.bindings = [
            item.bind_property('has_children', box, 'has_children', BIND_FLAGS),
            item.bind_property('has_children', expander, 'hide-expander', BIND_FLAGS
                               ,lambda _,x: not self.filter_manager.has_matching_children(item)),

            item.bind_property('title', label, 'label', BIND_FLAGS),
            item.bind_property('excerpt', box, 'tooltip-text', BIND_FLAGS),

            item.bind_property('is_recurring', recurring_icon, 'visible', BIND_FLAGS),

            item.bind_property('has_date_due', due_icon, 'visible', BIND_FLAGS),
            item.bind_property('has_date_start', start_icon, 'visible', BIND_FLAGS, show_start),

            item.bind_property('date_due_str', due, 'label', BIND_FLAGS),
            item.bind_property('date_start_str', start, 'label', BIND_FLAGS),
            item.bind_property('date_start_str', start, 'visible', BIND_FLAGS, show_start),

            item.bind_property('is_active', box, 'is_active', BIND_FLAGS),
            item.bind_property('icons', icons, 'label', BIND_FLAGS),
            item.bind_property('icons', icons, 'visible', BIND_FLAGS, not_empty),
            item.bind_property('row_css', box, 'row_css', BIND_FLAGS),

            item.bind_property('tag_colors', color, 'color_list', BIND_FLAGS),
            item.bind_property('show_tag_colors', color, 'visible', BIND_FLAGS),
        ]

        box.check.set_active(item.status == Status.DONE)
        box.check.connect('toggled', self.on_checkbox_toggled, item)


    def task_unbind_cb(self, factory, listitem, user_data=None):
        """Clean up bindings made in task_bind_cb"""
        for binding in listitem.bindings:
            binding.unbind()
        listitem.bindings.clear()
        box = listitem.get_child()
        box.check.disconnect_by_func(self.on_checkbox_toggled)


    def drag_prepare(self, source, x, y):
        """Callback to prepare for the DnD operation"""

        selection = self.get_selection()

        if len(selection) > 1:
            data = Gio.ListStore()
            data.splice(0, 0, selection)

            content = Gdk.ContentProvider.new_for_value(GObject.Value(Gio.ListModel, data))
            return content

        else:
            # Get content from source
            data = source.get_widget().props.task

            # Set it as content provider
            content = Gdk.ContentProvider.new_for_value(data)
            return content


    def drag_begin(self, source, drag):
        """Callback when DnD beings"""

        source.get_widget().set_opacity(0.25)
        icon = Gtk.DragIcon.get_for_drag(drag)
        frame = Gtk.Frame()
        picture = Gtk.Picture.new_for_paintable(
            Gtk.WidgetPaintable.new(source.get_widget()))

        frame.set_child(picture)
        icon.set_child(frame)


    def drag_end(self, source, drag, unused):
        """Callback when DnD ends"""

        if source.get_widget():
            source.get_widget().set_opacity(1)


    def drop_enter(self, target, x, y, user_data=None):
        """Callback when the mouse hovers over the drop target."""

        expander = target.get_widget().get_first_child()

        if target.get_widget().task.children:
            expander.activate_action('listitem.expand')

        # There's a funny bug in here. If the expansion of the row
        # makes the window larger, Gtk won't recognize the new drop areas
        # and will think you're dragging outside the window.

        return Gdk.DragAction.COPY


    def drag_drop(self, target, task, x, y):
        """Callback when dropping onto a target"""

        dropped = target.get_widget().props.task

        if not task.is_parentable_to(dropped):
            return

        if task.parent:
            self.ds.tasks.unparent(task.id)

        self.ds.tasks.parent(task.id, dropped.id)
        self.refresh()


    def on_task_RMB_click(self, gesture, sequence) -> None:
        """Callback when right-clicking on an open task."""

        widget = gesture.get_widget()
        task = widget.task

        if self.get_selected_number() <= 1:
            self.select_task(task)

        if task.status == Status.ACTIVE:
            menu = self.browser.open_menu
        else:
            menu = self.browser.closed_menu

        point = gesture.get_point(sequence)
        x, y = widget.translate_coordinates(self.browser, point.x, point.y)

        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y

        menu.set_pointing_to(rect)
        menu.popup()


    def on_toplevel_tag_drop(self, drop_target, task, x, y):
        if task.parent:
            self.ds.tasks.unparent(task.id)
            self.filtered.emit('items-changed', 0, 0, 0)
            self.refresh()

            return True
        else:
            return False
