__all__ = ("NetsuiteResponseError",)


class NetsuiteResponseError(Exception):
    """Raised when a Netsuite result was marked as unsuccessful"""
