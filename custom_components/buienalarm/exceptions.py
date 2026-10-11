"""Buienalarm exceptions."""
# exceptions.py


class BuienalarmError(Exception):
    """Base class for Buienalarm errors."""

    def __init__(self, message: str) -> None:
        """Initialize the BuienalarmError."""
        super().__init__(message)
        self.message = message


class ApiError(BuienalarmError):
    """Raised when a Buienalarm API request ends in an error."""


class InvalidCoordinatesError(BuienalarmError):
    """Raised when the coordinates are invalid."""


class RequestsExceededError(BuienalarmError):
    """Raised when the allowed number of requests has been exceeded."""


class BuienalarmApiException(BuienalarmError):
    """Raised when there is an exception with the Buienalarm API."""


class BuienalarmApiClientCommunicationError(BuienalarmError):
    """Raised when there is a Communication error with the Buienalarm Api Client."""


class BuienalarmApiRateLimitError(BuienalarmError):
    """Raised when the allowed number of requests has been exceeded."""
