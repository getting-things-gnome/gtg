from types import SimpleNamespace
from unittest import TestCase

import gi
gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')

from GTG.core.tags import TagStore
from GTG.gtk.colors import (background_color, get_colored_tag_markup,
                            get_colored_tags_markup)


class ColoredTagMarkupTest(TestCase):
    """Tag coloring must read the Tag.color property, not the removed
    get_attribute() API.

    The new GTK4 core turned tag attributes into GObject properties:
    a Tag no longer answers get_attribute("color"), it exposes .color.
    colors.py kept calling the old method, so every code path that
    renders an attached tag with a color raised AttributeError. In the
    backends dialog that meant a flood of tracebacks as soon as a
    CalDAV account was configured to sync a tag (#1323, #1324); in the
    task editor the same call was swallowed by a broad except, silently
    falling back to a default color (tags never showed their real one).
    """

    def _ds_with_tags(self):
        store = TagStore()
        red = store.new('red')
        red.color = '#ff0000'
        store.new('plain')  # color stays None by default
        return SimpleNamespace(tags=store)

    def test_colored_tag_gets_pango_span(self):
        ds = self._ds_with_tags()
        self.assertEqual(get_colored_tag_markup(ds, 'red'),
                         '<span color="#ff0000">red</span>')

    def test_colored_tag_gets_html_span(self):
        ds = self._ds_with_tags()
        self.assertEqual(get_colored_tag_markup(ds, 'red', html=True),
                         '<span style="color:#ff0000">red</span>')

    def test_uncolored_tag_is_plain_name(self):
        ds = self._ds_with_tags()
        self.assertEqual(get_colored_tag_markup(ds, 'plain'), 'plain')

    def test_missing_tag_is_plain_name(self):
        # A name still attached to a backend but gone from the store:
        # TagStore.find() raises KeyError rather than returning None,
        # which used to crash the backends dialog when it colored the
        # attached-tag list (#1323).
        ds = self._ds_with_tags()
        self.assertEqual(get_colored_tag_markup(ds, 'ghost'), 'ghost')
        # and the same through the list helper the dialog actually calls
        self.assertEqual(get_colored_tags_markup(ds, ['ghost']), 'ghost')

    def test_markup_for_list_does_not_raise(self):
        ds = self._ds_with_tags()
        markup = get_colored_tags_markup(ds, ['red', 'plain'])
        self.assertIn('red', markup)
        self.assertIn('plain', markup)

    def test_background_color_reads_color_property(self):
        # background_color() iterates real Tag objects and used to hit
        # the same removed get_attribute("color"); it must now derive a
        # color from a colored tag instead of raising.
        ds = self._ds_with_tags()
        color = background_color([ds.tags.find('red')])
        self.assertIsNotNone(color)
        self.assertTrue(color.startswith('#'))
