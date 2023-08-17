from typing import Any
"""TDXAPI Exceptions."""


class ObjectNotFoundException(Exception):
    """Object was not found in remote TDx instance."""

class NotAuthorizedException(Exception):
    """Current user is not authorized in remote TDx instance."""


class RequestFailedException(Exception):
    """Generic error when sending request to remote TDx instance."""


class NoDefaultAppException(Exception):
    """No app was provided and no default is set."""


class InvalidHTTPMethodException(Exception):
    """Not a supported HTTP Method."""


class NoSuchAttributeException(Exception):
    """The attribute could not be found in the object."""


class PropertyNotSetException(Exception):
    """The property has not been set."""


class InvalidParameterException(Exception):
    """Provided parameter is not valid."""


class PersonDoesNotExistException(Exception):
    """Matching person does not exist in TDx."""

    def __init__(
        self,
        criteria: dict[str, Any],
        message: str = "Matching person does not exist in TDx"
    ) -> None:
        self.criteria: dict[str, Any] = criteria
        self.message: str = message
        super().__init__(self.message)


class MultipleMatchesException(Exception):
    """More than one match for search."""

    def __init__(
            self,
            type: str,
            message: str = "Multiple matches detected"
    ) -> None:
        self.message: str = message
        self.type: str = type
        super().__init__(self.message)


class InvalidUniqnameException(Exception):
    """Uniqname is not 3-8 alpha characters."""


class TDXCommunicationException(Exception):
    """Error communicating with TDx."""

    def __init__(
            self,
            message: str = "Could not connect to TDx"
    ):
        self.message: str = message
        super().__init__(self.message)


class UnableToAttachAssetException(Exception):
    """Asset could not be attached to ticket, likely already attached."""

    def __init__(
            self,
            ticket: str,
            asset: str,
            message: str = "Could not attach asset to ticket"
    ):
        self.message: str = message
        self.ticket: str = ticket
        self.asset: str = asset
        super().__init__(self.message)