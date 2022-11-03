''' Classes for error handling. '''


class ConnectApiError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'Message from Connect API: %s' % self.message


class InvalidParameter(Exception):
    def __init__(self, param):
        self.param = param

    def __str__(self):
        return 'Invalid parameter: %s' % self.param


class MissingParameter(Exception):
    def __init__(self, param):
        self.param = param

    def __str__(self):
        return 'Missing parameter: %s' % self.param


class InvalidFormError(Exception):
    pass
