import os
from unittest import TestCase
from tempfile import mkdtemp

from GTG.core import dirs
from GTG.core import versioning
from GTG.core.datastore import Datastore

OLD_TASKS = (
    '<?xml version="1.0" ?>\n'
    '<project>\n'
    '<task id="1@1" status="Active" tags="" '
    'uuid="aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa">\n'
    '<title>old parent</title>\n'
    '<modified>2020-01-01T10:00:00</modified>\n'
    '<content>parent content</content>\n'
    '<subtask>2@1</subtask>\n'
    '</task>\n'
    '<task id="2@1" status="Active" tags="" '
    'uuid="bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb">\n'
    '<title>old child</title>\n'
    '<modified>2020-01-01T10:00:00</modified>\n'
    '<content>child content</content>\n'
    '</task>\n'
    '</project>\n'
)

OLD_TAGS = '<?xml version="1.0" ?>\n<tagstore>\n</tagstore>\n'


class OldFormatMigrationTest(TestCase):
    """The 0.6 data migration must be reachable and functional
    (regression tests for #855: converter dead since e43eee0a and
    never wired into startup)."""

    def setUp(self):
        self._old_data_dir = dirs.DATA_DIR
        self.tmp = mkdtemp()
        dirs.DATA_DIR = self.tmp
        # versioning imported DATA_DIR by value at module load time
        versioning.DATA_DIR = self.tmp
        with open(os.path.join(self.tmp, 'gtg_tasks.xml'), 'w') as f:
            f.write(OLD_TASKS)
        with open(os.path.join(self.tmp, 'tags.xml'), 'w') as f:
            f.write(OLD_TAGS)

    def tearDown(self):
        dirs.DATA_DIR = self._old_data_dir
        versioning.DATA_DIR = self._old_data_dir

    def test_convert_parses_old_file(self):
        tree = versioning.convert(
            os.path.join(self.tmp, 'gtg_tasks.xml'))
        self.assertEqual(2, len(tree.findall('.//task')))

    def test_startup_migrates_old_data(self):
        ds = Datastore()
        ds.find_and_load_file(os.path.join(self.tmp, 'gtg_data.xml'))
        titles = {t.title for t in ds.tasks.lookup.values()}
        self.assertIn('old parent', titles)
        self.assertIn('old child', titles)
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp, 'gtg_tasks.xml.imported')))
