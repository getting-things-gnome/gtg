
from gi.repository import GObject, Gtk
from gettext import gettext as _
import traceback
import sys
import os
import functools
import enum
import logging

from GTG.core import info
from GTG.core.system_info import SystemInfo

log = logging.getLogger(__name__)


class ExceptionHandlerDialog(Gtk.MessageDialog):
    class Response(enum.IntEnum):
        EXIT = enum.auto()
        CONTINUE = enum.auto()

    def __init__(self, exception=None, main_msg=None, ignorable: bool = False, context_info: str = None):
        super().__init__(resizable=False, modal=True, destroy_with_parent=True, message_type=Gtk.MessageType.ERROR)
        self.ignorable = ignorable

        formatting = {
            'url': info.REPORT_BUG_URL,
        }

        if ignorable:
            title = _("Internal error — GTG")
            desc = _("""GTG encountered an internal error, but can continue running. Unexpected behavior may occur, so be careful.""")
        else:
            title = _("Fatal internal error — GTG")
            desc = _("""GTG encountered an internal fatal error and needs to exit.""")

        title = title.format(**formatting)
        desc = desc.format(**formatting)

        # Yes, this line looks weirdly unindented. Leave it like that, or you'll mess up the translatable string:
        desc2 = _("""Recently unsaved changes (from the last few seconds) may be lost, so make sure to check your recent changes when launching GTG again afterwards.

Please report the bug in <a href="{url}">our issue tracker</a>, with steps to trigger the problem and the error's details below.""")
        desc2 = desc2.format(**formatting)

        # You may think that GtkWindow:title is the property you need,
        # however GtkWindow:title is awkwardly styled on GtkMessageDialog,
        # and GtkMessageDialog:text is styled like a title.
        self.props.text = title
        self.set_markup(desc)
        self.props.secondary_text = desc2
        self.props.secondary_use_markup = True
        self.get_style_context().add_class("errorhandler")

        exit_button = self.add_button(_("Exit"), self.Response.EXIT)
        exit_button.get_style_context().add_class("destructive-action")
        if ignorable:
            self.add_button(_("Continue"), self.Response.CONTINUE)

        self._additional_info = Gtk.TextView()
        self._additional_info.set_buffer(Gtk.TextBuffer())
        self._additional_info.set_editable(False)
        self._additional_info.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        expander_content = Gtk.ScrolledWindow(vexpand=True, min_content_height=90)
        expander_content.set_child(self._additional_info)
        self._expander = Gtk.Expander(vexpand=True)
        self._expander.set_label(_("Details to report"))
        self._expander.set_child(expander_content)
        self.get_content_area().append(self._expander)
        self._expander.bind_property("expanded", self, "resizable",
                                     GObject.BindingFlags.SYNC_CREATE)

        # Prevent the window from becoming too tall, or having a weird aspect ratio:
        expander_content.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        expander_content.props.height_request = 200
        self.props.width_request = 450

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
            text = text + "**Context:** " + self._context_info + "\n\n"
        text = text + "```python-traceback\n" + body + "```\n\n"
        text = text + SystemInfo().get_system_info(report=True)

        self._additional_info.get_buffer().set_text(text)


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
    dialog.show()
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
