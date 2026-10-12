from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import gi
gi.require_version('Gtk', '4.0')

from GTG.gtk.browser import sidebar
from GTG.gtk.browser.sidebar import Sidebar


class FakeGesture:
    """Just enough of a Gtk.GestureSingle for on_tag_RMB_click."""

    def __init__(self, tag):
        self._widget = SimpleNamespace(tag=tag)

    def get_widget(self):
        return self._widget

    def get_point(self, sequence):
        return SimpleNamespace(x=0, y=0)


class FakeSidebar:
    """Stands in for the Sidebar widget: a selection, and select_tag()."""

    def __init__(self, selected):
        self.ds = self.app = None
        self.selected = list(selected)

    def selected_tags(self, names_only=False):
        return list(self.selected)

    def select_tag(self, name, unselect_rest=True):
        tag = SimpleNamespace(name=name)
        self.selected = [tag] if unselect_rest else self.selected + [tag]


class FakeMenu:
    """Records the tags the context menu was built for."""

    built_for = None

    def __init__(self, ds, app, tags):
        FakeMenu.built_for = tags

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class TagRightClickTest(TestCase):
    """The tag context menu acts on the tag under the pointer (#1377).

    With a tag already selected, right-clicking another one used to
    build the menu for the old selection, so Edit, Delete and the
    others silently applied to the wrong tag.
    """

    def setUp(self):
        FakeMenu.built_for = None
        self.work = SimpleNamespace(name='work')
        self.home = SimpleNamespace(name='home')

    def right_click(self, fake, tag):
        with patch.object(sidebar, 'TagContextMenu', FakeMenu):
            Sidebar.on_tag_RMB_click(fake, FakeGesture(tag), None)

    def test_right_click_outside_selection_targets_clicked_tag(self):
        fake = FakeSidebar(selected=[self.work])
        self.right_click(fake, self.home)
        self.assertEqual(FakeMenu.built_for, [self.home])

    def test_right_click_outside_selection_selects_clicked_tag(self):
        fake = FakeSidebar(selected=[self.work])
        self.right_click(fake, self.home)
        self.assertEqual([t.name for t in fake.selected], ['home'])

    def test_right_click_inside_selection_keeps_whole_selection(self):
        fake = FakeSidebar(selected=[self.work, self.home])
        self.right_click(fake, self.home)
        self.assertEqual(FakeMenu.built_for, [self.work, self.home])
        self.assertEqual(fake.selected, [self.work, self.home])

    def test_right_click_without_selection_targets_clicked_tag(self):
        fake = FakeSidebar(selected=[])
        self.right_click(fake, self.home)
        self.assertEqual(FakeMenu.built_for, [self.home])
