
from gi.repository import GObject, GLib, Gtk
from gettext import gettext as _
import traceback
import sys
import os
import platform
import functools
import enum
import logging

from GTG.core import info

log = logging.getLogger(__name__)


class ExceptionHandlerDialog(Gtk.MessageDialog):
    class Response(enum.IntEnum):
        EXIT = enum.auto()
        CONTINUE = enum.auto()

    def __init__(self, exception=None, main_msg=None, ignorable: bool = False, context_info: str = None):
        self.ignorable = ignorable

        formatting = {
            'url': info.REPORT_BUG_URL,
            'urlname': info.REPORT_BUG_URL,
            'appname': info.NAME,
        }

        desc2 = _("""Please report the error with the following details and steps to trigger it to:
<a href="{url}">{urlname}</a>
Warning: Exiting may lose unsaved changes.""")
        desc2 = desc2.format(**formatting)

        if ignorable:
            title = _("{appname} encountered an error")
            desc = _("""{appname} encountered an internal error, but it'll continue running.
However, more unexpected things can happen, and thus be careful.""")
        else:
            title = _("{appname} encountered an error and needs to exit")
            desc = _("""{appname} encountered an internal fatal error and needs to exit.""")
        title = title.format(**formatting)
        desc = desc.format(**formatting)

        super().__init__(None,
                         Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                         Gtk.MessageType.ERROR,
                         Gtk.ButtonsType.NONE,
                         None)
        self.set_title(title)
        self.set_markup(desc)
        self.props.secondary_text = desc2
        self.props.secondary_use_markup = True

        self.add_button(_("Exit"), self.Response.EXIT)
        if ignorable:
            self.add_button(_("Continue"), self.Response.CONTINUE)

        self._additional_info = Gtk.TextView()
        self._additional_info.set_buffer(Gtk.TextBuffer())
        self._additional_info.set_editable(False)
        self._additional_info.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._additional_info.props.expand = True
        expander_content = Gtk.ScrolledWindow()
        expander_content.add(self._additional_info)
        self._expander = Gtk.Expander()
        self._expander.set_label(_("Details to report"))
        self._expander.add(expander_content)
        self.get_content_area().add(self._expander)
        self._expander.bind_property("expanded", self, "resizable",
                                     GObject.BindingFlags.SYNC_CREATE)
        self._expander.show_all()

        self._exception = exception
        self.context_info = context_info # Also refreshes the text

    @property
    def context_info(self):
        """Additional info to provide some context."""
        return self._context_info

    @context_info.setter
    def context_info(self, info, refresh: bool = True):
        self._context_info = str(info) if info != None else None
        if refresh:
            self._update_additional_info()

    @property
    def exception(self):
        """
        Exception that caused the error.
        Can also be any other object, which is then converted to a string.
        """
        return self._exception

    @exception.setter
    def exception(self, exception, refresh: bool = True):
        self._exception = exception
        if refresh:
            self._update_additional_info()

    def _update_additional_info(self):
        """Update the additional info section."""
        body = str(self.exception)
        if isinstance(self.exception, Exception):
            body = _format_exception(self.exception)

        text = ""
        if self._context_info is not None:
            text = text + "Context: " + self._context_info + "\n\n"
        text = text + body + "\n\n"
        text = text + _collect_versions()

        self._additional_info.get_buffer().set_text(text)


def _collect_versions() -> str:
    """Collect version information of various components."""
    def t2v(version_tuple) -> str:
        """Version tuple to a string."""
        return '.'.join(map(str, version_tuple))
    python_version = sys.version.replace('\n', '  ')
    gtk_version = (Gtk.get_major_version(),
                   Gtk.get_minor_version(),
                   Gtk.get_micro_version())
    versions = f"""{info.NAME} {info.VERSION}
{platform.python_implementation()} {python_version}
GTK {t2v(gtk_version)}, GLib {t2v(GLib.glib_version)}
PyGLib {t2v(GLib.pyglib_version)}, PyGObject {t2v(GObject.pygobject_version)}
{platform.platform()}"""
    return versions


def _format_exception(exception: Exception) -> str:
    """Format an exception the python way, as a string."""
    return "".join(traceback.format_exception(type(exception),
                                              exception,
                                              exception.__traceback__))


def handle_response(dialog: ExceptionHandlerDialog, response: int):
    """
    Handle the response of the ExceptionHandlerDialog.
    Note that this might exit the application in certain conditions.
    You need to explicitly connect it if you want to use this function:
    dialog.connect('response', handle_response)
    """
    log.debug("handling response %r", response)
    if not dialog.ignorable or response == ExceptionHandlerDialog.Response.EXIT:
        log.info("Going to exit because either of fatal error or user choice")
        os.abort()
    elif response == ExceptionHandlerDialog.Response.CONTINUE:
        pass
    elif response == Gtk.ResponseType.DELETE_EVENT:
        return # Caused by calling dialog.close() below, just ignore
    else:
        log.info("Unhandled response: %r, interpreting as continue instead", response)
    dialog.close()


def do_error_dialog(exception, context: str = None, ignorable: bool = True, main_msg=None):
    """
    Show (and return) the error dialog.
    It does NOT block execution, but should lock the UI
    (by being a modal dialog).
    """
    dialog = ExceptionHandlerDialog(exception, main_msg, ignorable, context)
    dialog.connect('response', handle_response)
    dialog.show_all()
    return dialog


def errorhandler(func, context: str = None, ignorable: bool = True, reraise: bool = True):
    """
    A decorator that produces an dialog for the user with the exception
    for them to report.
    Thrown exceptions are re-raised, in other words they are passed through.
    """
    @functools.wraps(func)
    def inner(*arg, **kwargs):
        try:
            return func(*arg, **kwargs)
        except Exception as e:
            try:
                do_error_dialog(e, context, ignorable)
            except Exception:
                log.exception("Exception occured while trying to show it")

            if reraise:
                raise e
            else:
                log.debug("Not re-raising exception because it has been explicitly disabled: %r", e)
    return inner


def errorhandler_fatal(func, *args, **kwargs):
    """
    An decorator like errorhandler, but sets ignorable to False when not
    explicitly overridden, thus only allowing the user only to exit the
    application.
    """
    if 'ignorable' not in kwargs:
        kwargs['ignorable'] = False
    return errorhandler(func, *args, **kwargs)


def replacement_excepthook(etype, value, tb, thread=None):
    """sys.excepthook compatible exception handler showing an dialog."""
    do_error_dialog(value, "Global generic exception", ignorable=True)
    original_excepthook(etype, value, tb)


original_excepthook = None


def replace_excepthook(replacement=replacement_excepthook) -> bool:
    """Replaces the (default) exception handler."""
    global original_excepthook
    if original_excepthook is not None:
        return False
    original_excepthook = sys.excepthook
    sys.excepthook = replacement
    return True


def restore_excepthook() -> bool:
    """Restore the old exception handler."""
    global original_excepthook
    if original_excepthook is None:
        return False
    sys.excepthook = original_excepthook
    original_excepthook = None

