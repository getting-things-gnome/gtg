# -*- coding: utf-8 -*-

'''
Notification is used to show messages to GTG users.
'''

import atexit
import subprocess

__all__ = ("send_notification", )

APP_NAME = "GTG"
# How many millisecond the notification area lasts
TIMEOUT = 3000


def _notify_via_pynotify(title, message):
    pynotify.init(APP_NAME)
    nt = pynotify.Notification(title, message)
    nt.set_timeout(TIMEOUT)
    try:
        nt.show()
    except:
        # Keep quiet here when notification service is not avialable currently
        # sometime. For example, if user is using LXDE, no notifyd by default.
        pass


def _notify_via_notify_send(title, message):
    cmd = "notify-send --app-name=%s --expire-time=%d \"%s\" \"%s\"" % (
        APP_NAME, TIMEOUT, title, message)
    subprocess.Popen(cmd, shell=True)


# A reference to the concrete handler that sends notification.
# By default, this reference is set to None in case all candidates are not
# available to keep silient when unexpected things happen.
_notify_handler = None
try:
    # Primarily, pynotify is used to send notification. However, it might not
    # appear in user's machine. So, we'll try another alternative.
    import pynotify
    _notify_handler = _notify_via_pynotify
except ImportError:
    # The alternative is notify-send, which is a command line utility provided
    # by libnotify package.
    proc = subprocess.Popen("which notify-send", shell=True)
    if proc.wait() == 0:
        _notify_handler = _notify_via_notify_send


def send_notification(title, message):
    ''' A proxy to send notification

    When no notification utility is available, just keep silent.
    '''

    if _notify_handler is not None:
        _notify_handler(title, message)


@atexit.register
def uinit_pynotify():
    pynotify.uninit()
