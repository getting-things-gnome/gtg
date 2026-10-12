import os
import xml.etree.ElementTree as ET
from unittest import TestCase

from GTG.core.dirs import local_rootdir

MAIN_WINDOW_UI = os.path.join(local_rootdir, 'GTG', 'gtk', 'data',
                              'main_window.ui')


class DeferMenuButtonLabelTest(TestCase):
    """The icon-only deferral menu button must tell screen readers and
    mouse users what it does (#1367). Without any text, Orca only
    announced "Togglebutton menu, not pressed"."""

    def setUp(self):
        root = ET.parse(MAIN_WINDOW_UI).getroot()
        self.button = root.find(".//object[@id='defer_menu_btn']")
        self.assertIsNotNone(self.button)

    def test_has_translatable_tooltip(self):
        tooltip = self.button.find("property[@name='tooltip_text']")
        self.assertIsNotNone(tooltip)
        self.assertEqual(tooltip.get('translatable'), 'yes')
        self.assertTrue(tooltip.text.strip())

    def test_has_translatable_accessible_label(self):
        label = self.button.find("accessibility/property[@name='label']")
        self.assertIsNotNone(label)
        self.assertEqual(label.get('translatable'), 'yes')
        self.assertTrue(label.text.strip())
