from functools import wraps
from typing import Any, Callable, Optional

from .. import constants
from . import zeep
from .exceptions import NetsuiteResponseError

__all__ = ("WebServiceCall",)


def WebServiceCall(
    path: Optional[str] = None,
    extract: Optional[Callable] = None,
    *,
    default: Any = constants.NOT_SET,
) -> Callable:
    """
    Decorator for NetSuite methods returning SOAP responses

    Args:
        path:
            A dot-separated path for specifying where relevant data resides (where the `status` attribute is set)
        extract:
            A function to extract data from response before returning it.
        default:
            If the existing path does not exist in response, return this
            instead.

    Returns:
        Decorator to use on `NetSuite` web service methods
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kw):
            response = fn(self, *args, **kw)
            if not isinstance(response, zeep.xsd.ComplexType):
                return response

            if path is not None:
                for part in path.split("."):
                    try:
                        response = getattr(response, part)
                    except AttributeError:
                        if default is constants.NOT_SET:
                            raise
                        else:
                            return default

            try:
                response_status = response["status"]
            except TypeError:
                response_status = None
                for record in response:
                    # NOTE: Status is set on each returned record for lists,
                    #       really strange...
                    response_status = record["status"]
                    break

            is_success = response_status["isSuccess"]

            if not is_success:
                response_detail = response_status["statusDetail"]
                raise NetsuiteResponseError(response_detail)

            if extract is not None:
                response = extract(response)

            return response

        return wrapper

    return decorator
