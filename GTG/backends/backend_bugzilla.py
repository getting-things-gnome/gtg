# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

'''
Bugzilla backend allows user to add remote Bugzilla service to convert bug link
to a normal task automatically.
'''

from GTG.core.translations import _
from GTG.backends.bugzilla.bugzilla import sync_bug_info
from GTG.backends.genericbackend import GenericBackend

__all__ = ('Backend',)


BACKEND_DESCRIPTION = _('Bugzilla synchronization service replaces each '
                        'valid bug URL with corresponding bug\'s information. '
                        'Task\'s title will be replaced with bug\'s summary, '
                        'and bug\'s components will be as the tags. '
                        'Currently, task\'s content is just simply same as '
                        'title.')


class Backend(GenericBackend):
    '''Bugzilla backend allowing user to add remote Bugzilla service'''

    _general_description = {
        GenericBackend.BACKEND_NAME: 'backend_bugzilla',
        GenericBackend.BACKEND_HUMAN_NAME: _('Bugzilla'),
        GenericBackend.BACKEND_AUTHORS: ['Chenxiong Qi'],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READONLY,
        GenericBackend.BACKEND_DESCRIPTION: BACKEND_DESCRIPTION
    }

    _static_parameters = {
        'bugzilla-tag-use-priority': {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: False,
        },
        'bugzilla-tag-use-severity': {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: False,
        },
        'bugzilla-tag-use-component': {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: False,
        },
        'bugzilla-tag-customized': {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: 'Bug',
        },
        'bugzilla-add-comment': {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: False,
        },
    }

    def set_task(self, task):
        if not self.is_initialized():
            return

        sync_bug_info(task, self)
