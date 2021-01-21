class TestFailedException(Exception):
    def __init__(self, message="Test FAILED!"):
        super().__init__(message)
