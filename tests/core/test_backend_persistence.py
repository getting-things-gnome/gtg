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

    def test_legacy_module_named_section_is_cleaned_up(self):
        legacy = CoreConfig()
        legacy.get_backend_config('backend_caldav').set('module',
                                                        'backend_caldav')
        self.ds.save_backend_config(self.backend)
        self.assertNotIn('backend_caldav',
                         CoreConfig().get_all_backends())
