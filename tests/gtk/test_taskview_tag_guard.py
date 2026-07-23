from unittest import TestCase

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GtkSource', '5')

from GTG.gtk.editor.taskview import tag_is_faithfully_representable


class TagGuardTest(TestCase):
    """insert_tags only writes tags the parser reads back identically.

    Tags imported from CalDAV may carry characters the inline '@'
    marker cannot (colons, quotes, commas...). Writing them in the
    task text used to truncate them on re-parse, which re-added a
    second, mangled tag on every open (#1265) . The previous fix
    instead mangled the tag name itself at import, overwriting the
    server data (#1305). The guard keeps both properties: the store
    holds the faithful name, and the text only carries tags that
    survive their own round trip through the editor's parser.
    """

    def test_plain_tags_are_representable(self):
        for name in ('1-Urgent', 'my_first_category', 'work', 'a-b_c',
                     'côté', 'v1.2', 'x(y)', '50%'):
            self.assertTrue(tag_is_faithfully_representable(name), name)

    def test_calendar_tag_with_colon_stays_out_of_the_text(self):
        # the #1265 scenario: writing @DAV_Deck:_Server in the text
        # reads back as @DAV_Deck and forks a truncated duplicate
        self.assertFalse(tag_is_faithfully_representable('DAV_Deck:_Server'))

    def test_apostrophe_tag_stays_out_of_the_text(self):
        # the #1305 scenario, after the reversible projection: the
        # store holds 7-N'importe_ou faithfully, the text cannot
        self.assertFalse(tag_is_faithfully_representable("7-N'importe_ou"))

    def test_comma_tag_stays_out_of_the_text(self):
        # a comma would also break the ', '.join() of the tag line
        self.assertFalse(tag_is_faithfully_representable('a,b'))

    def test_empty_name_is_not_representable(self):
        self.assertFalse(tag_is_faithfully_representable(''))
