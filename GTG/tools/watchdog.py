import threading

class Watchdog(object):
    '''
    a simple thread-safe watchdog.
    usage:
    with Watchdod(timeout, error_function):
        #do something
    '''

    def __init__(self, timeout, error_function):
        self.timeout = timeout
        self.error_function = error_function

    def __enter__(self):
        self.timer = threading.Timer(self.timeout, self.error_function)
        self.timer.start()

    def __exit__(self, type, value, traceback):
        try:
            self.timer.cancel()
        except:
            pass
        if value == None:
            return True
        return False
