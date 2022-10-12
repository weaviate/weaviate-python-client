from functools import wraps


def testmethod(test):
    @wraps(test)
    def run_test(self):
        self._setup()
        test(self)
        self._cleanup()
    return run_test

class TestFailedException(Exception):
    def __init__(self, message="Test FAILED!"):
        super().__init__(message)
