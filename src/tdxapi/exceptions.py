class ObjectNotFoundException(Exception):
    """Object was not found in remote TDx instance"""

class AssetAttachFailedException(Exception):
    """Attaching asset to ticket failed"""

class NotAuthorizedException(Exception):
    """Current user is not authorized in remote TDx instance"""

class RequestFailedException(Exception):
    """Generic error when sending request to remote TDx instance"""

class NoDefaultAppException(Exception):
    """No app was provided and no default is set"""