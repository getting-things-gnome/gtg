from unittest import TestCase

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GtkSource', '5')

from GTG.gtk.editor.taskview import subtask_bullet_span


class SubtaskBulletTest(TestCase):
    """The "- " bullet removal must be consistent with its detection.

    detect_subtasks() accepts a bullet line after leading whitespace
    (text.lstrip().startswith('- ')), but the removal used to cut a
    fixed 2 characters from the raw line and build the title from
    text[2:]. On an indented bullet those 2 characters were not the
    "- ", so the leftover whitespace or dash leaked into the stored
    <title> (e.g. a line " - sousou" produced the title " sousou").
    subtask_bullet_span() computes the offset and the title from the
    same stripped position, keeping them in sync.
    """

    def test_plain_bullet(self):
        self.assertEqual(subtask_bullet_span('- sousou'), (2, 'sousou'))

    def test_single_indented_bullet(self):
        # regression: used to yield the title ' sousou'
        self.assertEqual(subtask_bullet_span(' - sousou'), (3, 'sousou'))

    def test_double_indented_bullet(self):
        # regression: used to yield the title '- sousou'
        self.assertEqual(subtask_bullet_span('  - sousou'), (4, 'sousou'))

    def test_tab_indented_bullet(self):
        self.assertEqual(subtask_bullet_span('\t- tabbed'), (3, 'tabbed'))

    def test_title_keeps_inner_content(self):
        # only the leading whitespace and the first "- " are stripped:
        # a genuine second dash typed by the user stays in the title
        self.assertEqual(subtask_bullet_span('- - dashed'), (2, '- dashed'))

    def test_not_a_bullet(self):
        self.assertIsNone(subtask_bullet_span('just text'))

    def test_bullet_without_title_is_ignored(self):
        self.assertIsNone(subtask_bullet_span('- '))
        self.assertIsNone(subtask_bullet_span('   - '))

    def test_dash_without_space_is_not_a_bullet(self):
        self.assertIsNone(subtask_bullet_span('-nospace'))
