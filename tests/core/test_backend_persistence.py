from tempfile import mkdtemp
from unittest import TestCase

from GTG.backends import BackendFactory
from GTG.backends import generic_backend as gb_module
from GTG.core import config as config_module
from GTG.core.config import CoreConfig
from GTG.core.datastore import Datastore


class FakeKeyring:
    store = {}

    def set_password(self, name, password):
        FakeKeyring.store[name] = password
        return name

    def get_password(self, name):
        return FakeKeyring.store.get(name, '')


class BackendPersistenceTest(TestCase):
    """Backend configuration must survive a restart: written on
    registration, on parameter/state changes, removed on deletion
    (regression tests for #930 and #845)."""

    def setUp(self):
        self._old_config_dir = config_module.CONFIG_DIR
        self._old_keyring = gb_module.Keyring
        config_module.CONFIG_DIR = mkdtemp()
        gb_module.Keyring = FakeKeyring
        dic = BackendFactory().get_new_backend_dict(
            'backend_caldav',
            {'service-url': 'https://example.test/dav/',
             'username': 'alice', 'password': 'secret'})
        self.backend = dic['backend']
        self.pid = dic['pid']
        self.ds = Datastore()
        self.ds.register_backend({'backend': self.backend,
                                  'pid': self.pid,
                                  'first_run': True,
                                  'enabled': False})

    def tearDown(self):
        config_module.CONFIG_DIR = self._old_config_dir
        gb_module.Keyring = self._old_keyring

    def test_registering_persists_the_backend(self):
        config = CoreConfig()
        self.assertEqual([self.pid], config.get_all_backends())
        section = config.get_backend_config(self.pid)
        self.assertEqual('backend_caldav', section.get('module'))
        self.assertEqual('alice', section.get('username'))

    def test_state_toggle_persists_fresh_parameters(self):
        self.backend.set_parameter('username', 'renamed')
        self.ds._on_backend_state_toggled_persist(
            None, self.backend.get_id())
        section = CoreConfig().get_backend_config(self.pid)
        self.assertEqual('renamed', section.get('username'))

    def test_removing_deletes_the_section(self):
        self.ds.remove_backend(self.backend.get_id())
        self.assertEqual([], CoreConfig().get_all_backends())

    def test_saving_a_parameter_the_backend_lacks(self):
        """A config written before a parameter was added to a backend
        simply lacks it -- which is every config out there, the day a
        parameter is added (default-calendar, Feb 2026).
        get_saved_backends_list() drops what it can't read, and the
        rest of the code copes: the parameter panels check before
        reading, the caldav backend falls back on its own default.
        Saving must cope too, rather than demand a value nobody has.
        """
        config = CoreConfig()
        section = config.get_backend_config(self.pid)
        del section._section['default-calendar']
        config.save_backends_config()

        loaded = [b for b in BackendFactory().get_saved_backends_list()
                  if b['pid'] == self.pid]
        self.assertEqual(1, len(loaded))
        backend = loaded[0]['backend']
        self.assertNotIn('default-calendar', backend.get_parameters())

        self.ds.save_backend_config(backend)  # used to raise KeyError

        self.assertEqual('alice',
                         CoreConfig().get_backend_config(self.pid)
                         .get('username'))

    def test_migration_carries_over_what_it_cannot_read(self):
        """Moving a section to its pid must carry values we can't
        produce ourselves. A password reference is useless to us when
        the keyring is down, but it's the user's: dropping it would
        lose it for good."""
        config = CoreConfig()
        legacy = config.get_backend_config('backend_caldav')
        legacy.set('module', 'backend_caldav')
        legacy.set('pid', self.pid)
        legacy.set('a-value-we-cannot-read', 'must survive')
        config.save_backends_config()

        self.ds.save_backend_config(self.backend)

        moved = CoreConfig().get_backend_config(self.pid)
        self.assertEqual('must survive',
                         moved.get('a-value-we-cannot-read'))
        self.assertNotIn('backend_caldav', CoreConfig().get_all_backends())

    def test_legacy_module_named_section_is_cleaned_up(self):
        legacy = CoreConfig()
        legacy.get_backend_config('backend_caldav').set('module',
                                                        'backend_caldav')
        self.ds.save_backend_config(self.backend)
        self.assertNotIn('backend_caldav',
                         CoreConfig().get_all_backends())
