from functools import wraps


def testmethod(test):
    """
    A decorator that prepares a class' method to run a test.
    
    This assumes that the class has _setup() and _cleanup() defined.
    Any code that contained in _setup() will be called prior to the
    test, and any in _cleanup() with be called immediately after it
    succeeds.

    Note that if the method raises an exception, _cleanup() will not
    run.

    :param test: called implicitly, don't invoke with an argument
    :type test: any class method which runs a test

    Example:
        class TestClass:
            def _setup(self):
                # do some setup before test runs

            def _cleanup(self):
                # cleanup after test

            @testmethod
            def _some_test(self):
                # test code
    """
    @wraps(test)
    def run_test(self):
        self._setup()
        test(self)
        self._cleanup()
    return run_test

class TestFailedException(Exception):
    def __init__(self, message="Test FAILED!"):
        super().__init__(message)
