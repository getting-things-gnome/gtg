import os
import re
from unittest import TestCase

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from GTG.core.dirs import local_rootdir

SIDEBAR = os.path.join(local_rootdir, 'GTG', 'gtk', 'browser', 'sidebar.py')
BUNDLED = os.path.join(local_rootdir, 'data', 'icons')


class SidebarIconsTest(TestCase):
    """Every icon the sidebar asks for must resolve with only the stock
    Adwaita theme plus GTG's own bundled icons (#1371).

    'tag-symbolic' is not part of Adwaita, so on a stock system the
    "Tags" row showed a broken image until GTG bundled it.
    """

    def test_sidebar_icons_resolve(self):
        with open(SIDEBAR, encoding='utf-8') as f:
            source = f.read()
        names = set(re.findall(r"['\"]([a-z0-9-]+-symbolic)['\"]", source))
        self.assertIn('tag-symbolic', names)

        theme = Gtk.IconTheme.new()
        theme.set_theme_name('Adwaita')
        theme.set_search_path(['/usr/share/icons', BUNDLED])

        missing = sorted(n for n in names if not theme.has_icon(n))
        self.assertEqual(missing, [])
