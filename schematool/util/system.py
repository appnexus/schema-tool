import sys


# A simple wrapper around 'sys' that makes things just a little easier
# to test with (since we can mock it out and what not)
class System(object):

    is_test = False

    @classmethod
    def set_test(cls, flag):
        """
        Set wether or not this utility is in test-mode. In test-mode some
        things (like exit) will not make calls to the actual 'sys' package
        but will do some other type of behavior that makes testing easier
        and stuff.
        """
        cls.is_test = flag

    @classmethod
    def exit(cls, code):
        if cls.is_test:
            raise SystemExit(code)
        else:
            sys.exit(code)

class SystemExit(Exception):
    def __init__(self, code):
        self.code = code

    def __str__(self):
        return str(self.code)
