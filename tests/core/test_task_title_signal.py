from unittest import TestCase
from GTG.core.datastore import Datastore


class TitleChangeNotifiesTest(TestCase):

    def test_renaming_a_task_emits_task_filterably_changed(self):
        """Backends only learn about a change through this signal, and
        search filters on the title. Without it, a rename never leaves
        GTG: the CalDAV sync kept whatever title the task had when some
        other signal last fired -- in practice the first letters typed.
        """
        ds = Datastore()
        task = ds.tasks.new('original')
        seen = []
        ds.tasks.connect('task-filterably-changed',
                         lambda _, t: seen.append(t.title))
        task.title = 'renamed'
        self.assertEqual(['renamed'], seen)
