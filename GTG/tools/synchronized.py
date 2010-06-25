from __future__ import with_statement
from threading import Lock

def synchronized(fun):
    the_lock = Lock()

    def fwrap(function):
        def newFunction(*args, **kw):
            with the_lock:
                return function(*args, **kw)

        return newFunction

    return fwrap(fun)
