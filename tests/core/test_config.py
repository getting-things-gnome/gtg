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

from mock import patch, mock_open

from GTG.core.config import open_config_file


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
        mock_log.warning.assert_called()

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
