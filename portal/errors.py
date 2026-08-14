"""Classes for error handling."""


class ConnectApiError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Message from Connect API: {self.message}"


class InvalidParameter(Exception):
    def __init__(self, param):
        self.param = param

    def __str__(self):
        return f"Invalid parameter: {self.param}"


class MissingParameter(Exception):
    def __init__(self, param):
        self.param = param

    def __str__(self):
        return f"Missing parameter: {self.param}"


class InvalidFormError(Exception):
    pass
