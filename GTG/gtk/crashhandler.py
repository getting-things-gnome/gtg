#!/usr/bin/env python2
# Copyright 2010 David D. Lowe
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

"""GTK except hook for your applications.
To use, simply import this module and call gtkcrashhandler.initialize().
Import this module before calling gtk.main().

If gtkcrashhandler cannot import gtk, pygtk, pango or gobject,
gtkcrashhandler will print a warning and use the default excepthook.

If you're using multiple threads, use gtkcrashhandler_thread decorator."""

import sys
import os
import time
import signal
from contextlib import contextmanager

from GTG import info


try:
    import pygtk
    pygtk.require("2.0")  # not tested on earlier versions
    import gtk
    import pango
    import gobject
    _gtk_initialized = True
except Exception:
    print >> sys.stderr, "gtkcrashhandler could not load GTK 2.0"
    _gtk_initialized = False
import traceback
from gettext import gettext as _
import threading

APP_NAME = None
MESSAGE = _("We're terribly sorry. Could you help us fix the problem by "
            "reporting the crash?")
USE_APPORT = False

_old_sys_excepthook = None  # None means that initialize() has not been called
                           # yet.

dialog = None


def initialize(app_name=None, message=None, use_apport=False):
    """Initialize the except hook built on GTK.

    @param app_name: The current application's name to be read by humans,
        untranslated.
    @param message: A message that will be displayed in the error dialog,
        replacing the default message string. Untranslated.
        If you don't want a message, pass "".
    @param use_apport: If set to True, gtkcrashhandler will override
        the settings in /etc/default/apport and call apport if possible,
        silently failing if not. If set to False, the normal behaviour will
        be executed, which may mean Apport kicking in anyway.
    """
    global APP_NAME, MESSAGE, USE_APPORT, _gtk_initialized, _old_sys_excepthook
    if app_name:
        APP_NAME = _(app_name)
    if not message is None:
        MESSAGE = _(message)
    if use_apport:
        USE_APPORT = use_apport
    if _gtk_initialized is True and _old_sys_excepthook is None:
        # save sys.excepthook first, as it may not be sys.__excepthook__
        # (for example, it might be Apport's python hook)
        _old_sys_excepthook = sys.excepthook
        # replace sys.excepthook with our own
        sys.excepthook = _replacement_excepthook


def _replacement_excepthook(type, value, tracebk, thread=None):
    """This function will replace sys.excepthook."""
    # create traceback string and print it
    tb = "".join(traceback.format_exception(type, value, tracebk))
    if thread:
        if not isinstance(thread, threading._MainThread):
            tb = "Exception in thread %s:\n%s" % (thread.getName(), tb)
    print >> sys.stderr, tb

    # determine whether to add a "Report problem..." button
    add_apport_button = False
    global USE_APPORT
    if USE_APPORT:
        # see if this file is from a properly installed distribution package
        try:
            from apport.fileutils import likely_packaged
            try:
                filename = os.path.realpath(os.path.join(os.getcwdu(),
                                                         sys.argv[0]))
            except:
                filename = os.path.realpath("/proc/%i/exe" % os.getpid())
            if not os.path.isfile(filename) or \
                    not os.access(filename, os.X_OK):
                raise Exception()
            add_apport_button = likely_packaged(filename)
        except:
            add_apport_button = False

    res = show_error_window(tb, add_apport_button=add_apport_button)

    if res == 3:  # report button clicked
        # enable apport, overriding preferences
        try:
            # create new temporary configuration file, where enabled=1
            import re
            from apport.packaging_impl import impl as apport_packaging
            newconfiguration = "# temporary apport configuration file " \
                               "by gtkcrashhandler.py\n\n"
            try:
                for line in open(apport_packaging.configuration):
                    if re.search('^\s*enabled\s*=\s*0\s*$', line) is None:
                        newconfiguration += line
            finally:
                newconfiguration += "enabled=1"
            import tempfile
            tempfile, tempfilename = tempfile.mkstemp()
            os.write(tempfile, newconfiguration)
            os.close(tempfile)

            # set apport to use this configuration file, temporarily
            apport_packaging.configuration = tempfilename
            # override Apport's ignore settings for this app
            from apport.report import Report
            Report.check_ignored = lambda self: False
        except:
            pass

    if res in (2, 3):  # quit
        sys.stderr = os.tmpfile()
        global _old_sys_excepthook
        _old_sys_excepthook(type, value, tracebk)
        sys.stderr = sys.__stderr__
        os._exit(1)


def show_error_window(error_string, add_apport_button=False):
    """Displays an error dialog, and returns the response ID.

    error_string       -- the error's output (usually a traceback)
    add_apport_button  -- whether to add a 'report with apport' button

    Returns the response ID of the dialog, 1 for ignore, 2 for close and
    3 for apport.
    """
    # initialize dialog
    title = _("An error has occurred")
    global APP_NAME
    if APP_NAME:
        title = APP_NAME
    global dialog
    # Do not allow more than one error window
    if dialog is not None:
        return 1

    dialog = gtk.Dialog(title)

    # title Label
    label = gtk.Label()
    label.set_markup("<b>%s</b>" % _("It looks like an error has occurred."))
    label.set_alignment(0, 0.5)
    dialog.get_content_area().pack_start(label, False)

    # message Label
    global MESSAGE
    text_label = gtk.Label()
    text_label.set_markup(MESSAGE)
    text_label.set_alignment(0, 0.5)
    text_label.set_line_wrap(True)

    def text_label_size_allocate(widget, rect):
        """Lets label resize correctly while wrapping text."""
        widget.set_size_request(rect.width, -1)

    text_label.connect("size-allocate", text_label_size_allocate)
    if not MESSAGE == "":
        dialog.get_content_area().pack_start(text_label, False)

    # TextView with error_string
    buffer = gtk.TextBuffer()
    buffer.set_text(error_string)
    textview = gtk.TextView()
    textview.set_buffer(buffer)
    textview.set_editable(False)
    try:
        textview.modify_font(pango.FontDescription("monospace 8"))
    except Exception:
        print >> sys.stderr, "gtkcrashhandler: modify_font raised an exception"

    # allow scrolling of textview
    scrolled = gtk.ScrolledWindow()
    scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled.add_with_viewport(textview)

    # hide the textview in an Expander widget
    expander = gtk.expander_new_with_mnemonic(_("_Details"))
    expander.add(scrolled)
    expander.connect('activate', on_expanded)
    dialog.get_content_area().pack_start(expander, True)

    # add buttons
    if add_apport_button:
        dialog.add_button(_("_Report this problem..."), 3)
    # If we're have multiple threads, or if we're in a GTK callback,
    # execution can continue normally in other threads, so add button
    if gtk.main_level() > 0 or threading.activeCount() > 1:
        dialog.add_button(_("_Ignore the error"), 1)
    dialog.add_button(("_Close the program"), 2)
    dialog.set_default_response(2)

    # set dialog aesthetic preferences
    dialog.set_border_width(12)
    dialog.get_content_area().set_spacing(4)
    dialog.set_resizable(False)

    # show the dialog and act on it
    dialog.show_all()
    res = dialog.run()
    dialog.destroy()
    if res < 0:
        res = 2
    return res


def on_expanded(widget):
    global dialog
    dialog.set_size_request(600, 600)


def gtkcrashhandler_thread(run):
    """gtkcrashhandler_thread is a decorator for the run() method of
    threading.Thread.

    If you forget to use this decorator, exceptions in threads will be
    printed to standard error output, and GTK's main loop will continue to run.

    #Example 1::

        class ExampleThread(threading.Thread):
            E{@}gtkcrashhandler_thread
            def run(self):
                1 / 0 # this error will be caught by gtkcrashhandler

    #Example 2::

        def function(arg):
            arg / 0 # this error will be caught by gtkcrashhandler
        threading.Thread(target=gtkcrashhandler_thread(function),args=(1,))
                .start()
    """

    def gtkcrashhandler_wrapped_run(*args, **kwargs):
        try:
            run(*args, **kwargs)
        except Exception, ee:
            lock = threading.Lock()
            lock.acquire()
            tb = sys.exc_info()[2]
            if gtk.main_level() > 0:
                gobject.idle_add(
                    lambda ee=ee, tb=tb, thread=threading.currentThread():
                    _replacement_excepthook(ee.__class__, ee, tb,
                                            thread=thread))
            else:
                time.sleep(0.1)  # ugly hack, seems like threads that are
                                # started before running gtk.main() cause
                                # this one to crash.
                                # This delay allows gtk.main() to initialize
                                # properly.
                                # My advice: run gtk.main() before starting
                                # any threads or don't run gtk.main() at all
                _replacement_excepthook(ee.__class__, ee, tb,
                                        thread=threading.currentThread())
            lock.release()

    # return wrapped run if gtkcrashhandler has been initialized
    global _gtk_initialized, _old_sys_excepthook
    if _gtk_initialized and _old_sys_excepthook:
        return gtkcrashhandler_wrapped_run
    else:
        return run

if __name__ == "__main__":
    # throw test exception
    initialize(app_name="gtkcrashhandler", message="Don't worry, though. This "
               "is just a test. To use the code properly, call "
               "gtkcrashhandler.initialize() in your PyGTK app to "
               "automatically catch any Python exceptions like this.")

    class DoNotRunException(Exception):

        def __str__(self):
            return "gtkcrashhandler.py should imported, not run"

    raise DoNotRunException()


## We handle initialization directly here, since this module will be used as a
#  singleton
# we listen for signals from the system in order to save our configuration
# if GTG is forcefully terminated (e.g.: on shutdown).

@contextmanager
def signal_catcher(callback):
    # if TERM or ABORT are caught, we execute the callback function
    for s in [signal.SIGABRT, signal.SIGTERM]:
        signal.signal(s, lambda a, b: callback())
    yield

initialize(app_name="Getting Things GNOME!",
           message="GTG" + info.VERSION +
           _(" has crashed. Please report the bug on <a href=\""
           "http://bugs.edge.launchpad.net/gtg\">our Launchpad page</a>."
             " If you have Apport installed, it will be started for you."),
           use_apport=True)
