# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2015 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

from unittest import TestCase
import configparser

from mock import patch, mock_open, Mock

from GTG.core.config import open_config_file, SectionConfig


class TestOpenConfigFile(TestCase):
    def setUp(self):
        self.mock_parser = patch(
            'GTG.core.config.configparser.ConfigParser.read').start()
        self.mock_os = patch('GTG.core.config.os').start()
        self.mock_path = patch('GTG.core.config.os.path').start()
        self.mock_open = patch(
            'GTG.core.config.open', mock_open(), create=True).start()

    def tearDown(self):
        patch.stopall()

    def test_reads_configuration(self):
        open_config_file('gtg.conf')
        self.mock_parser.assert_called_once_with('gtg.conf')

    @patch('GTG.core.config.Log')
    def test_falls_back_when_there_is_config_error(self, mock_log):
        self.mock_parser.side_effect = configparser.Error()
        open_config_file('gtg.conf')
        self.mock_parser.assert_called_once_with('gtg.conf')
        self.assertTrue(mock_log.warning.called)

    def test_creates_config_folder_when_missing(self):
        self.mock_path.exists.return_value = False
        self.mock_path.dirname.return_value = 'config'
        open_config_file('config/gtg.conf')
        self.mock_os.makedirs.assert_called_once_with('config')

    def test_creates_config_file_when_missing(self):
        self.mock_path.exists.side_effect = lambda name: name != 'gtg.conf'
        open_config_file('gtg.conf')
        self.mock_open.assert_called_with('gtg.conf', 'w')

    def test_raises_error_when_config_is_not_accessible(self):
        self.mock_os.access.return_value = False
        with self.assertRaises(Exception):
            open_config_file('gtg.conf')


class TestSectionConfig(TestCase):
    def make_section_config(self, config_dict):
        """ Creates a section from a dictionary """
        config = configparser.ConfigParser()
        config.read_dict({'section': config_dict})
        return config['section']

    @patch('GTG.core.config.Log')
    def test_warns_when_no_default_value_is_provided(self, mock_log):
        config = self.make_section_config({'option': '1'})
        section = SectionConfig('Name', config, {}, Mock())
        value = section.get('option')
        self.assertTrue(mock_log.warning.called)
        self.assertEqual('1', value)

    @patch('GTG.core.config.Log')
    def test_warns_when_value_is_wrong_type(self, mock_log):
        config = self.make_section_config({'option': 'text'})
        section = SectionConfig('Name', config, {'option': 42}, Mock())
        value = section.get('option')
        self.assertTrue(mock_log.warning.called)
        # It should fall back to default value as 'text' is not an int
        self.assertEqual(42, value)

    def test_returns_int_when_expected_int(self):
        config = self.make_section_config({'option': '42'})
        section = SectionConfig('Name', config, {'option': 42}, Mock())
        value = section.get('option')
        self.assertEqual(int, type(value))
        self.assertEqual(42, value)

    def test_returns_bool_when_expected_bool(self):
        config = self.make_section_config({'option': 'False'})
        section = SectionConfig('Name', config, {'option': False}, Mock())
        value = section.get('option')
        self.assertEqual(bool, type(value))
        self.assertEqual(False, value)

    def test_returns_string_when_expected_string(self):
        config = self.make_section_config({'option': 'Hello'})
        section = SectionConfig('Name', config, {'option': 'World'}, Mock())
        value = section.get('option')
        self.assertEqual(str, type(value))
        self.assertEqual('Hello', value)

    def test_returns_empty_list_for_non_existing_value(self):
        config = self.make_section_config({})
        section = SectionConfig('Name', config, {'option': []}, Mock())
        value = section.get('option')
        self.assertEqual([], value)

    def test_returns_empty_list_for_empty_value(self):
        config = self.make_section_config({'option': ''})
        section = SectionConfig('Name', config, {'option': []}, Mock())
        value = section.get('option')
        self.assertEqual([], value)

    def test_returns_list_from_previous_configuration(self):
        # Config from GTG 0.2.4
        config = self.make_section_config({
            'opened_tasks': '8@1, 6@1, 4@1'})
        section = SectionConfig('Name', config, {'opened_tasks': []}, Mock())
        value = section.get('opened_tasks')
        self.assertEqual(['8@1', '6@1', '4@1'], value)

    def test_returns_empty_list_from_previous_empty_configuration(self):
        # Config from GTG 0.2.4
        config = self.make_section_config({
            'opened_tasks': ','})
        section = SectionConfig('Name', config, {'opened_tasks': []}, Mock())
        value = section.get('opened_tasks')
        self.assertEqual([], value)

    def test_returns_list_of_tuples(self):
        # Splitting only by ',' caused bugs
        #  - https://bugs.launchpad.net/gtg/+bug/1218093
        #  - https://bugs.launchpad.net/gtg/+bug/1216807
        config = self.make_section_config({
            'collapsed_tasks': "('0@1', '6@1'),('0@1', '8@1', '3@1', '5@1')"})
        section = SectionConfig(
            'Name', config, {'collapsed_tasks': []}, Mock())
        value = section.get('collapsed_tasks')
        self.assertEqual(
            ["('0@1', '6@1')", "('0@1', '8@1', '3@1', '5@1')"],
            value)

    @patch('GTG.core.config.Log')
    def test_raises_an_error_when_no_value_and_no_default_value(
            self, mock_log):
        config = self.make_section_config({})
        section = SectionConfig('Name', config, {}, Mock())
        with self.assertRaises(ValueError):
            section.get('option')
        self.assertTrue(mock_log.warning.called)

    def test_can_set_value(self):
        config = self.make_section_config({})
        save_mock = Mock()
        section = SectionConfig('Name', config, {}, save_mock)
        section.set('option', 42)
        self.assertEqual('42', config['option'])
        # Automatically saved value
        save_mock.assert_any_call()

    def test_can_set_list(self):
        config = self.make_section_config({})
        save_mock = Mock()
        section = SectionConfig('Name', config, {}, save_mock)
        section.set('list', [1, True, 'Hello'])
        self.assertEqual('1,True,Hello', config['list'])
        # Automatically saved value
        save_mock.assert_any_call()

    def test_can_set_tuple(self):
        config = self.make_section_config({})
        save_mock = Mock()
        section = SectionConfig('Name', config, {}, save_mock)
        section.set('list', (1, 2))
        self.assertEqual('1,2', config['list'])
        # Automatically saved value
        save_mock.assert_any_call()
