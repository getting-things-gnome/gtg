import sys
from optparse import OptionParser


def X_is_running():
    from gtk.gdk import Screen
    try:
        if Screen().get_display():
            return True
    except RuntimeError:
        pass
    return False


try:
    parser = OptionParser()
    parser.add_option('-b', '--boot-test', action='store_true', dest='boot_test',
      help="Exit immediately after completing boot-up actions", default=False)
    parser.add_option('-c', '--no-crash-handler', action='store_true', dest='no_crash_handler',
      help="Disable the automatic crash handler", default=False)
    parser.add_option('-d', '--debug', action='store_true', dest='debug',
      help="Enable debug output", default=False)
    parser.add_option('-v', '--version', action='store_true', dest='version_and_exit',
      help="Print GTG's version number", default=False)
    (options, args) = parser.parse_args()

    if options.version_and_exit:
        from GTG import info
        print "gtg (Getting Things Gnome!) %s" %(info.VERSION)
        print
        print "For more information: %s" %(info.URL)
        sys.exit(0)

    elif not X_is_running():
        print "Could not open X display"
        sys.exit(1)

    else:
        import GTG.gtg
        sys.exit(GTG.gtg.main(options, args))

except KeyboardInterrupt:
    sys.exit(1)
