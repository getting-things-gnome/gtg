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

'''Show bug information synchronization message to user.'''

__all__ = ("send_notification", )


from GTG.backends.backendsignals import BackendSignals


def send_notification(backend, error_no, error_message):
    '''
    Show notification in InfoBar

    @param backend: the instance of Bugzilla backend
    @param error_no: the error number defianed BackendSignals. Passing this
                     follows the BackendSignals and CustomInfoBar protocol
    @param error_message: the text message to be shown in InfoBar
    '''
    BackendSignals().backend_failed(backend.get_id(),
                                    error_no,
                                    {'message': error_message})
