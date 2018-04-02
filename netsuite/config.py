import configparser
from typing import Any, Dict, Tuple

from .constants import DEFAULT_INI_PATH, DEFAULT_INI_SECTION, NOT_SET


class Config:
    """
    Takes dictionary keys/values that will be set as attribute names/values
    on the config object if they exist as attributes

    Args:
        **opts:
            Dictionary keys/values that will be set as attribute names/values
    """

    account = None
    """The NetSuite account ID"""

    consumer_key = None
    """The OAuth 1.0 consumer key"""

    consumer_secret = None
    """The OAuth 1.0 consumer secret"""

    token_id = None
    """The OAuth 1.0 token ID"""

    token_secret = None
    """The OAuth 1.0 token secret"""

    preferences = None
    """Additional preferences"""

    _settings_mapping: Tuple[
        Tuple[
            str,
            Dict[str, Any]
        ],
        ...
    ] = (
        (
            'account',
            {'type': str, 'required': True},
        ),
        (
            'consumer_key',
            {'type': str, 'required': True},
        ),
        (
            'consumer_secret',
            {'type': str, 'required': True},
        ),
        (
            'token_id',
            {'type': str, 'required': True},
        ),
        (
            'token_secret',
            {'type': str, 'required': True},
        ),
        (
            'preferences',
            {'type': dict, 'required': False, 'default': lambda: {}},
        ),
    )

    def __init__(self, **opts) -> None:
        self._set(opts)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def _set(self, dct: Dict[str, object]) -> None:
        for attr, opts in self._settings_mapping:
            value = dct.get(attr, NOT_SET)
            type_ = opts['type']
            required = opts['required']
            self._validate_attr(attr, value, type_, required)

            if value is NOT_SET and 'default' in opts:
                value = opts['default']()

            setattr(self, attr, (None if value is NOT_SET else value))

    def _validate_attr(
        self,
        attr: str,
        value: object,
        type_: object,
        required: bool,
    ) -> None:
        if required and value is NOT_SET:
            raise ValueError(f'Attribute {attr} is required')
        if value is not NOT_SET and not isinstance(value, type_):
            raise ValueError(f'Attribute {attr} is not of type `{type_}`')


def from_ini(
    path: str = DEFAULT_INI_PATH,
    section: str = DEFAULT_INI_SECTION
) -> Config:
    iniconf = configparser.ConfigParser()
    with open(path) as fp:
        iniconf.read_file(fp)

    config_dict = {'preferences': {}}

    for key, val in iniconf[section].items():
        if key.startswith('preferences_'):
            _, key = key.split('_', 1)
            config_dict['preferences'][key] = val
        else:
            config_dict[key] = val

    return Config(**config_dict)
