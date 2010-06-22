from GTG.tools.borg import Borg



class TestingMode(Borg):


    def set_testing_mode(self, value):
        self._testing_mode = value

    def get_testing_mode(self):
        try:
            return self._testing_mode
        except:
            return False

