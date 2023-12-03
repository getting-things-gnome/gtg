from unittest.mock import Mock


class MockThread(Mock):

    def __init__(self, *args, target=None, **kwargs):
        super().__init__()
        self._target = target

    def start(self):
        return self._target()


class MockTimer(MockThread):

    def __init__(self, *args, **kwargs):
        if 'function' in kwargs:
            super().__init__(target=kwargs['function'])
        elif len(args) >= 2:
            super().__init__(target=args[1])
        else:
            raise AssertionError("%s couldn't find delayed function call"
                                 % self.__class__.__name__)
