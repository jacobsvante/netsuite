import sys
import requests

from io import StringIO

__all__ = ('cached_property', 'raise_for_status_with_body')


class cached_property:
    """ Decorator that turns an instance method into a cached property
    From https://speakerdeck.com/u/mitsuhiko/p/didntknow, slide #69
    """
    __NOT_SET = object()

    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.__module__ = func.__module__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, self.__NOT_SET)
        if value is self.__NOT_SET:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def raise_for_status_with_body(
    response,
    on_bad_status=None
):
    """Raise exception on bad HTTP status and capture response body

    Also:
        * If an exception occurs the response body will be added to the
          exception string.
        * If `on_bad_status` is provided this function will run on a request
          exception.
    """
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException as ex:
        body = response.text
        if body and len(ex.args) == 1:
            ex.args = (ex.args[0] + f'\nBody: {body}', )
        if on_bad_status is not None:
            on_bad_status()
        raise ex


class Capturing(list):
    """
    taken from https://stackoverflow.com/questions/16571150/how-to-capture-stdout-output-from-a-python-function-call

    Captures stdout

    Example:

        with Capturing() as output:
            print('hello world')

        print ('displays on screen')

        with Capturing(output) as output:  # note the constructor argument
            print ('hello world2')

        print ('done')
        print ('output:', output)

        # displays on screen
        # done
        # output: ['hello world', 'hello world2']

    """
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout
