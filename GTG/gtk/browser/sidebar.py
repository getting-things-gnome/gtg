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

"""Sidebar widgets."""

from gi.repository import Gtk, GObject, Gdk, Gio

from gettext import gettext as _

from GTG.core.tags import Tag
from GTG.core.tasks import Task
from GTG.core.filters import TagEmptyFilter
from GTG.core.saved_searches import SavedSearch
from GTG.core.datastore import Datastore
from GTG.gtk.browser.sidebar_context_menu import TagContextMenu, SearchesContextMenu
from GTG.gtk.browser.tag_pill import TagPill


class TagBox(Gtk.Box):
    """Box subclass to keep a pointer to the tag object"""

    tag = GObject.Property(type=Tag)


class SearchBox(Gtk.Box):
    """Box subclass to keep a pointer to the search object"""

    search = GObject.Property(type=SavedSearch)


def unwrap(row, expected_type):
    """Find an item in TreeRow widget (sometimes nested)."""

    item = row.get_item()

    while type(item) is not expected_type:
        item = item.get_item()

    return item


# Shorthands
BIND_FLAGS = GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
signal_block = GObject.signal_handler_block


class Sidebar(Gtk.ScrolledWindow):
    """The sidebar widget"""

    def __init__(self, app, ds: Datastore, browser):

        super(Sidebar, self).__init__()
        self.ds = ds
        self.app = app
        self.browser = browser

        wrap_box = Gtk.Box()
        wrap_box.set_orientation(Gtk.Orientation.VERTICAL)
        wrap_box.set_vexpand(True)
        wrap_box.set_hexpand(True)

        # Create an invisible dummy button to catch focus in some edge cases
        self.dummy = Gtk.Button()
        self.dummy.set_size_request(0, 0)
        self.dummy.add_css_class('dummy')
        wrap_box.append(self.dummy)

        # -------------------------------------------------------------------------------
        # General Filters
        # -------------------------------------------------------------------------------

        self.general_box = Gtk.ListBox()
        self.general_box.get_style_context().add_class('navigation-sidebar')

        all_count = str(ds.task_count['open']['all'])
        untag_count = str(ds.task_count['open']['untagged'])

        self.all_btn = self.btn_item('emblem-documents-symbolic', _('All Tasks'), 'task_count_all')
        self.none_btn = self.btn_item('task-past-due-symbolic', _('Tasks With No Tags'), 'task_count_no_tags')

        self.general_box.append(self.all_btn)
        self.general_box.append(self.none_btn)
        wrap_box.append(self.general_box)

        separator = Gtk.Separator()
        separator.set_sensitive(False)
        wrap_box.append(separator)

        self.general_box.select_row(self.general_box.get_row_at_index(0))
        self.box_handle = self.general_box.connect('row-selected', self.on_general_box_selected)

        # -------------------------------------------------------------------------------
        # Saved Searches Section
        # -------------------------------------------------------------------------------
        searches_btn_box = Gtk.Box()
        searches_button = Gtk.Button()
        searches_button_label = Gtk.Label()
        searches_button_label.set_markup(_('Saved Searches'))
        searches_button_label.set_xalign(0)
        searches_button.get_style_context().add_class('flat')

        searches_button.set_margin_top(6)
        searches_button.set_margin_start(6)
        searches_button.set_margin_end(6)

        searches_icon = Gtk.Image.new_from_icon_name('folder-saved-search-symbolic')
        searches_icon.set_margin_end(6)
        searches_btn_box.append(searches_icon)
        searches_btn_box.append(searches_button_label)
        searches_button.set_child(searches_btn_box)
        searches_button.connect('clicked', self.on_search_reveal)

        self.searches_selection = Gtk.SingleSelection.new(ds.saved_searches.model)
        self.searches_selection.set_autoselect(False)
        self.searches_selection.set_can_unselect(True)
        self.searches_selection.unselect_item(0)
        self.search_handle = self.searches_selection.connect('selection-changed', self.on_search_selected)

        searches_signals = Gtk.SignalListItemFactory()
        searches_signals.connect('setup', self.searches_setup_cb)
        searches_signals.connect('bind', self.searches_bind_cb)
        searches_signals.connect('unbind', self.searches_unbind_cb)

        searches_view = Gtk.ListView.new(self.searches_selection, searches_signals)
        searches_view.get_style_context().add_class('navigation-sidebar')
        searches_view.set_hexpand(True)

        self.searches_revealer = Gtk.Revealer()
        self.searches_revealer.set_child(searches_view)
        self.searches_revealer.set_reveal_child(True)

        # -------------------------------------------------------------------------------
        # Tags Section
        # -------------------------------------------------------------------------------
        self.tags_filter = TagEmptyFilter(ds, 'open_view')
        self.filtered_tags = Gtk.FilterListModel()
        self.filtered_tags.set_model(ds.tags.tree_model)
        self.filtered_tags.set_filter(self.tags_filter)

        self.tag_selection = Gtk.MultiSelection.new(self.filtered_tags)
        self.tag_handle = self.tag_selection.connect('selection-changed', self.on_tag_selected)

        tags_signals = Gtk.SignalListItemFactory()
        tags_signals.connect('setup', self.tags_setup_cb)
        tags_signals.connect('bind', self.tags_bind_cb)
        tags_signals.connect('unbind', self.tags_unbind_cb)

        view = Gtk.ListView.new(self.tag_selection, tags_signals)
        view.get_style_context().add_class('navigation-sidebar')
        view.set_vexpand(True)
        view.set_hexpand(True)

        view_drop = Gtk.DropTarget.new(Tag, Gdk.DragAction.COPY)
        view_drop.connect("drop", self.on_toplevel_tag_drop)
        view.add_controller(view_drop)

        self.revealer = Gtk.Revealer()
        self.revealer.set_child(view)
        self.revealer.set_reveal_child(True)

        btn_box = Gtk.Box()
        button = Gtk.Button()
        button_label = Gtk.Label()
        button_label.set_markup(_('Tags'))
        button_label.set_xalign(0)
        button.get_style_context().add_class('flat')

        button.set_margin_top(6)
        button.set_margin_start(6)
        button.set_margin_end(6)

        tags_icon = Gtk.Image.new_from_icon_name('view-list-symbolic')
        tags_icon.set_margin_end(6)
        btn_box.append(tags_icon)
        btn_box.append(button_label)
        button.set_child(btn_box)
        button.connect('clicked', self.on_tag_reveal)

        self.expanders = set()

        # -------------------------------------------------------------------------------
        # Bring everything together
        # -------------------------------------------------------------------------------

        wrap_box.append(searches_button)
        wrap_box.append(self.searches_revealer)
        wrap_box.append(button)
        wrap_box.append(self.revealer)
        self.set_child(wrap_box)


    def refresh_tags(self) -> None:
        """Refresh tags list."""

        self.filtered_tags.items_changed(0, 0, 0)
        self.tags_filter.changed(Gtk.FilterChange.DIFFERENT)


    def change_pane(self, pane: str) -> None:
        """Change pane for the tag list."""

        self.tags_filter.pane = pane
        self.tags_filter.changed(Gtk.FilterChange.DIFFERENT)


    @GObject.Signal
    def selection_changed(self) -> None:
        """Selection of tags or searches has changed."""


    def on_tag_RMB_click(self, gesture, sequence) -> None:
        """Callback when right-clicking on a tag."""

        menu = TagContextMenu(self.ds, self.app, self.selected_tags())
        menu.set_parent(gesture.get_widget())
        menu.set_halign(Gtk.Align.START)
        menu.set_position(Gtk.PositionType.BOTTOM)

        point = gesture.get_point(sequence)
        rect = Gdk.Rectangle()
        rect.x = point.x
        rect.y = point.y
        menu.set_pointing_to(rect)
        menu.popup()


    def on_searches_RMB_click(self, gesture, sequence) -> None:
        """Callback when right-clicking on a search."""

        menu = SearchesContextMenu(self.ds, self.app, gesture.get_widget().search)
        menu.set_parent(gesture.get_widget())
        menu.set_halign(Gtk.Align.START)
        menu.set_position(Gtk.PositionType.BOTTOM)

        point = gesture.get_point(sequence)
        rect = Gdk.Rectangle()
        rect.x = point.x
        rect.y = point.y
        menu.set_pointing_to(rect)
        menu.popup()


    def btn_item(self, icon_name:str, text: str, count_prop: str) -> Gtk.Box:
        """Generate a button for the main listbox."""

        box = Gtk.Box()

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_margin_end(6)
        box.append(icon)

        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_text(text)
        box.append(label)

        count_label = Gtk.Label()
        count_label.set_halign(Gtk.Align.START)
        count_label.add_css_class('dim-label')
        box.append(count_label)

        self.ds.tasks.bind_property(count_prop, count_label, 'label', BIND_FLAGS)

        return box


    def tags_setup_cb(self, factory, listitem, user_data=None) -> None:
        """Setup for a row in the tags listview"""

        box = TagBox()
        label = Gtk.Label()
        expander = Gtk.TreeExpander()
        icon = Gtk.Label()
        color = TagPill()
        open_count_label = Gtk.Label()
        actionable_count_label = Gtk.Label()
        closed_count_label = Gtk.Label()

        expander.set_margin_end(6)
        expander.add_css_class('arrow-only-expander')
        expander.set_indent_for_icon(True)
        expander.set_indent_for_depth(True)
        icon.set_margin_end(6)
        color.set_margin_end(6)
        color.set_size_request(16, 16)

        color.set_valign(Gtk.Align.CENTER)
        color.set_halign(Gtk.Align.CENTER)
        color.set_vexpand(False)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)

        open_count_label.set_halign(Gtk.Align.START)
        open_count_label.add_css_class('dim-label')
        open_count_label.set_text('0')

        actionable_count_label.set_halign(Gtk.Align.START)
        actionable_count_label.add_css_class('dim-label')
        actionable_count_label.set_text('0')

        closed_count_label.set_halign(Gtk.Align.START)
        closed_count_label.add_css_class('dim-label')
        closed_count_label.set_text('0')


        # Drag ...
        source = Gtk.DragSource()
        source.connect('prepare', self.prepare)
        source.connect('drag-begin', self.drag_begin)
        source.connect('drag-end', self.drag_end)
        box.add_controller(source)

        # ... and drop
        drop = Gtk.DropTarget.new(Tag, Gdk.DragAction.COPY)
        drop.connect('drop', self.drag_drop)
        drop.connect('enter', self.drop_enter)
        box.add_controller(drop)

        task_drop = Gtk.DropTarget.new(Task, Gdk.DragAction.COPY)
        task_drop.connect('drop', self.task_drag_drop)
        task_drop.connect('enter', self.drop_enter)
        box.add_controller(task_drop)

        multi_task_drop = Gtk.DropTarget.new(Gio.ListModel, Gdk.DragAction.COPY)
        multi_task_drop.connect('drop', self.multi_task_drag_drop)
        multi_task_drop.connect('enter', self.drop_enter)
        box.add_controller(multi_task_drop)


        box.append(expander)
        box.append(color)
        box.append(icon)
        box.append(label)
        box.append(open_count_label)
        box.append(actionable_count_label)
        box.append(closed_count_label)
        listitem.set_child(box)

        # Right click event controller
        tags_RMB_controller = Gtk.GestureSingle(button=Gdk.BUTTON_SECONDARY)
        tags_RMB_controller.connect('begin', self.on_tag_RMB_click)
        box.add_controller(tags_RMB_controller)

        self.expanders.add(expander)


    def tags_bind_cb(self, signallistitem, listitem, user_data=None) -> None:
        """Bind properties for a specific row in the tags listview"""

        box = listitem.get_child()
        expander = box.get_first_child()
        color = expander.get_next_sibling()
        icon = color.get_next_sibling()
        label = icon.get_next_sibling()

        open_count_label = label.get_next_sibling()
        actionable_count_label = open_count_label.get_next_sibling()
        closed_count_label = actionable_count_label.get_next_sibling()

        item = unwrap(listitem, Tag)

        box.props.tag = item
        expander.set_list_row(listitem.get_item())

        listitem.bindings = [
            item.bind_property('name', label, 'label', BIND_FLAGS),
            item.bind_property('icon', icon, 'label', BIND_FLAGS),
            item.bind_property('color', color, 'color_list', BIND_FLAGS),

            item.bind_property('has_icon', color, 'visible', BIND_FLAGS, lambda b, v: not v),
            item.bind_property('has_icon', icon, 'visible', BIND_FLAGS),

            item.bind_property('task_count_open', open_count_label, 'label', BIND_FLAGS),
            item.bind_property('task_count_actionable', actionable_count_label, 'label', BIND_FLAGS),
            item.bind_property('task_count_closed', closed_count_label, 'label', BIND_FLAGS),

            item.bind_property('children_count',expander,'hide-expander',BIND_FLAGS, lambda _,x: x==0),
        ]

        self.browser.bind_property('is_pane_open', open_count_label, 'visible', BIND_FLAGS)
        self.browser.bind_property('is_pane_actionable', actionable_count_label, 'visible', BIND_FLAGS)
        self.browser.bind_property('is_pane_closed', closed_count_label, 'visible', BIND_FLAGS)


    def tags_unbind_cb(self, signallistitem, listitem, user_data=None) -> None:
        """Clean up bindings made in tags_bind_cb"""
        for binding in listitem.bindings:
            binding.unbind()


    def unselect_tags(self) -> None:
        """Clear tags selection"""
        self.browser.config.set("selected_tag", '')

        with signal_block(self.tag_selection, self.tag_handle):
            self.tag_selection.unselect_all()


    def unselect_searches(self) -> None:
        """Clear selection for saved searches"""

        with signal_block(self.searches_selection, self.search_handle):
            search_id = self.searches_selection.get_selected()
            self.searches_selection.unselect_item(search_id)
            self.app.browser.get_pane().set_search_query('')


    def unselect_general_box(self) -> None:
        """Clear selection for saved searches"""

        with signal_block(self.general_box, self.box_handle):
            self.general_box.unselect_all()


    def on_general_box_selected(self, listbox, user_data=None):
        """Callback when clicking on a row in the general listbox"""

        self.unselect_tags()
        self.unselect_searches()
        index = listbox.get_selected_row().get_index()
        self.app.browser.get_pane().emit('expand-all')

        if index == 0:
            self.app.browser.get_pane().set_filter_tags()
        elif index == 1:
            self.app.browser.get_pane().set_filter_notags()

        self.emit('selection_changed')


    def on_search_selected(self, model, position, user_data=None):
        """Callback when selecting a saved search"""

        self.unselect_tags()
        self.unselect_general_box()

        item = model.get_item(position)
        self.app.browser.get_pane().emit('expand-all')
        self.app.browser.get_pane().set_search_query(item.query)
        self.emit('selection_changed')


    def select_tag(self, name: str, unselect_rest: bool = True) -> None:
        """Select a tag by name."""

        for i in range(self.tag_selection.get_n_items()):
            item = unwrap(self.tag_selection.get_item(i), Tag)

            if item.name == name:
                self.tag_selection.select_item(i, unselect_rest)

    def selected_tags(self, names_only: bool = False) -> list:
        """Get a list of selected tags"""

        selection = self.tag_selection.get_selection()
        result, iterator, _ = Gtk.BitsetIter.init_first(selection)
        selected = []

        while iterator.is_valid():
            val = iterator.get_value()
            item = unwrap(self.tag_selection.get_item(val), Tag)
            selected.append(item.name if names_only else item)
            iterator.next()

        return selected


    def on_tag_selected(self, model, position, n_items, user_data=None):
        """Callback when selecting one or more tags"""

        self.unselect_general_box()
        self.unselect_searches()

        self.app.browser.get_pane().emit('expand-all')
        self.app.browser.get_pane().set_filter_tags(set(self.selected_tags()))

        tags = self.selected_tags(names_only=True)

        if tags:
            self.browser.config.set("selected_tag", tags[0])

        self.emit('selection_changed')


    def on_tag_reveal(self, event) -> None:
        """Callback for clicking on the tags title button (revealer)."""

        self.revealer.set_reveal_child(not self.revealer.get_reveal_child())


    def on_search_reveal(self, event) -> None:
        """Callback for clicking on the search title button (revealer)."""

        self.searches_revealer.set_reveal_child(not self.searches_revealer.get_reveal_child())


    def searches_setup_cb(self, factory, listitem, user_data=None) -> None:
        """Setup for a row in the saved searches listview"""

        box = SearchBox()
        label = Gtk.Label()
        icon = Gtk.Label()

        icon.set_margin_end(6)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)

        box.set_margin_start(18)

        box.append(icon)
        box.append(label)
        listitem.set_child(box)

        searches_RMB_controller = Gtk.GestureSingle(button=Gdk.BUTTON_SECONDARY)
        searches_RMB_controller.connect('begin', self.on_searches_RMB_click)
        box.add_controller(searches_RMB_controller)


    def searches_bind_cb(self, signallistitem, listitem, user_data=None) -> None:
        """Bind properties for a specific row in the searches listview"""

        icon = listitem.get_child().get_first_child()
        label = icon.get_next_sibling()
        box = listitem.get_child()

        item = unwrap(listitem, SavedSearch)
        box.search = item

        listitem.bindings = [
            item.bind_property('name', label, 'label', BIND_FLAGS),
            item.bind_property('icon', icon, 'label', BIND_FLAGS),
        ]

    def searches_unbind_cb(self, signallistitem, listitem, user_data=None) -> None:
        """Clean up bindings made in searches_bind_cb"""
        for binding in listitem.bindings:
            binding.unbind()
        listitem.bindings.clear()


    # -------------------------------------------------------------------------------------------
    # Drag and drop
    # -------------------------------------------------------------------------------------------

    def prepare(self, source, x, y):
        """Callback to prepare for the DnD operation"""

        # Get content from source
        data = source.get_widget().props.tag

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


    def drag_drop(self, target, value, x, y):
        """Callback when dropping onto a target"""
        dropped = target.get_widget().props.tag

        if not value.is_parentable_to(dropped):
            return

        if value.parent:
            self.ds.tags.unparent(value.id)

        self.ds.tags.parent(value.id, dropped.id)
        self.ds.refresh_tag_stats()
        self.ds.tags.tree_model.emit('items-changed', 0, 0, 0)
        self.refresh_tags()



    def drop_enter(self, target, x, y, user_data=None):
        """Callback when the mouse hovers over the drop target."""

        expander = target.get_widget().get_first_child()

        if target.get_widget().tag.children:
            expander.activate_action('listitem.expand')

        # There's a funny bug in here. If the expansion of the row
        # makes the window larger, Gtk won't recognize the new drop areas
        # and will think you're dragging outside the window.

        return Gdk.DragAction.COPY


    def task_drag_drop(self, target, task, x, y):
        """Callback when dropping onto a target"""

        tag = target.get_widget().props.tag
        task.add_tag(tag)
        self.notify_task(task)

        self.ds.tasks.notify('task_count_no_tags')


    def multi_task_drag_drop(self, target, tasklist, x, y):
        """Callback when dropping onto a target"""

        for task in list(tasklist):
            tag = target.get_widget().props.tag
            task.add_tag(tag)
            self.notify_task(task)

        self.ds.tasks.notify('task_count_no_tags')


    def notify_task(self, task: Task) -> None:
        """Notify that tasks props have changed."""

        task.notify('row_css')
        task.notify('icons')
        task.notify('tag_colors')


    def on_toplevel_tag_drop(self, drop_target, tag, x, y):
        if tag.parent:
            self.ds.tags.unparent(tag.id)
            self.ds.refresh_tag_stats()
            self.refresh_tags()
            try:
                for expander in self.expanders:
                    expander.activate_action('listitem.toggle-expand')
                    expander.activate_action('listitem.toggle-expand')
            except RuntimeError:
                pass

            self.ds.tags.tree_model.emit('items-changed', 0, 0, 0)
            return True
        else:
            return False
