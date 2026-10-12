import os
import xml.etree.ElementTree as ET
from unittest import TestCase

import gi
gi.require_version('Gtk', '4.0')

from GTG.core.dirs import local_rootdir
from GTG.gtk.browser.main_window import start_tomorrow_tooltip

MAIN_WINDOW_UI = os.path.join(local_rootdir, 'GTG', 'gtk', 'data',
                              'main_window.ui')


class StartTomorrowTooltipTest(TestCase):
    """The "Start Tomorrow" tooltip states plainly what the button does
    and uses real plural forms (#1366). "task(s)" cannot be translated
    properly, and Orca read the parentheses aloud."""

    def test_singular(self):
        self.assertEqual(start_tomorrow_tooltip(1),
                         'Start 1 selected task tomorrow')

    def test_plural(self):
        self.assertEqual(start_tomorrow_tooltip(3),
                         'Start 3 selected tasks tomorrow')

    def test_nothing_selected(self):
        self.assertEqual(start_tomorrow_tooltip(0),
                         'Start the selected tasks tomorrow')

    def test_static_tooltip_has_no_pseudo_plural(self):
        root = ET.parse(MAIN_WINDOW_UI).getroot()
        tooltip = root.find(
            ".//object[@id='defer_task_button']/property[@name='tooltip_text']")
        self.assertNotIn('(s)', tooltip.text)
        self.assertEqual(tooltip.text, start_tomorrow_tooltip(0))
