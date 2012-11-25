# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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
Utils to stop and quit gracefully a thread, issuing the command from
another one
'''


class Interrupted(Exception):
    '''Exception raised when a thread should be interrupted'''
    pass


def interruptible(fn):
    '''
    A decorator that makes a function interruptible. It should be applied only
    to the function which is the target of a Thread object.
    '''

    def new(*args):
        try:
            return fn(*args)
        except Interrupted:
            return
    return new


def _cancellation_point(test_function):
    '''
    This function checks a test_function and, if it evaluates to True, makes
    the thread quit (similar to pthread_cancel() in C)
    It starts with a _ as it's mostly used in a specialized form, as::
        cancellation_point = functools.partial(_cancellation_point,
                                               lambda: quit_condition == True)

    @param test_function: the function to test before cancelling
    '''
    if test_function():
        raise Interrupted
