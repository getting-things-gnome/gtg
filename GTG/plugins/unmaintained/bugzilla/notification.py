

"""
Notification is used to show messages to GTG users.
"""

import subprocess

__all__ = ("send_notification", )

APP_NAME = "GTG"
# How many millisecond the notification area lasts
TIMEOUT = 3000


def _notify_via_notify(title, message):
    Notify.init(APP_NAME)
    nt = Notify.Notification.new(title, message)
    nt.set_timeout(TIMEOUT)
    try:
        nt.show()
    except Exception:
        # Keep quiet here when notification service is not avialable currently
        # sometime. For example, if user is using LXDE, no notifyd by default.
        pass
    Notify.uninit()


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
    from gi.repository import Notify
    _notify_handler = _notify_via_notify
except ImportError:
    # The alternative is notify-send, which is a command line utility provided
    # by libnotify package.
    proc = subprocess.Popen("which notify-send", shell=True)
    if proc.wait() == 0:
        _notify_handler = _notify_via_notify_send


def send_notification(title, message):
    """ A proxy to send notification

    When no notification utility is available, just keep silent.
    """

    if _notify_handler is not None:
        _notify_handler(title, message)
