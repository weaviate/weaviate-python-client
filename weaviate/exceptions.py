class ThingAlreadyExistsException(Exception):
    pass


class UnexpectedStatusCodeException(Exception):
    pass


class AuthenticationFailedException(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ForbiddenRequest403Exception(Exception):
    pass


class UnauthorizedRequest401Exception(Exception):
    pass


class SemanticError422Exception(Exception):
    pass


class ServerError500Exception(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
