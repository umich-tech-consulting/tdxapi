"""TDXAPI Exceptions."""


class ObjectNotFoundException(Exception):
    """Object was not found in remote TDx instance."""


class AssetAttachFailedException(Exception):
    """Attaching asset to ticket failed."""


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


class UniqnameDoesNotExistException(Exception):
    """Uniqname does not exist in TDx."""

    def __init__(
        self,
        uniqname: str,
        message: str = "Uniqname does not exist in TDx"
    ) -> None:
        self.uniqname: str = uniqname
        self.message: str = message
        super().__init__(self.message)


class MultipleMatchesException(Exception):
    """More than one match for search."""


class InvalidUniqnameException(Exception):
    """Uniqname is not 3-8 alpha characters."""
