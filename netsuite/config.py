import configparser
from typing import Dict

from .constants import DEFAULT_INI_PATH, DEFAULT_INI_SECTION, NOT_SET

TOKEN = 'token'
CREDENTIALS = 'credentials'


class Config:
    """
    Takes dictionary keys/values that will be set as attribute names/values
    on the config object if they exist as attributes

    Args:
        **opts:
            Dictionary keys/values that will be set as attribute names/values
    """

    auth_type = TOKEN
    """The authentication type to use, either 'token' or 'credentials'"""

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

    application_id = None
    """Application ID, used with auth_type=credentials"""

    email = None
    """Account e-mail, used with auth_type=credentials"""

    password = None
    """Account password, used with auth_type=credentials"""

    preferences = None
    """Additional preferences"""

    _settings_mapping = (
        (
            'account',
            {'type': str, 'required': True},
        ),
        (
            'consumer_key',
            {'type': str, 'required_for_auth_type': TOKEN},
        ),
        (
            'consumer_secret',
            {'type': str, 'required_for_auth_type': TOKEN},
        ),
        (
            'token_id',
            {'type': str, 'required_for_auth_type': TOKEN},
        ),
        (
            'token_secret',
            {'type': str, 'required_for_auth_type': TOKEN},
        ),
        (
            'application_id',
            {'type': str, 'required_for_auth_type': CREDENTIALS},
        ),
        (
            'email',
            {'type': str, 'required_for_auth_type': CREDENTIALS},
        ),
        (
            'password',
            {'type': str, 'required_for_auth_type': CREDENTIALS},
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

    def _set_auth_type(self, value: str) -> None:
        self._validate_attr('auth_type', value, str, True, {})
        self.auth_type = value
        assert self.auth_type in (TOKEN, CREDENTIALS)

    def _set(self, dct: Dict[str, object]) -> None:
        # As other setting validations depend on auth_type we set it first
        auth_type = dct.get('auth_type', self.auth_type)
        self._set_auth_type(auth_type)

        for attr, opts in self._settings_mapping:
            value = dct.get(attr, NOT_SET)
            type_ = opts['type']

            required = opts.get(
                'required',
                opts.get('required_for_auth_type') == auth_type
            )

            self._validate_attr(attr, value, type_, required, opts)

            if value is NOT_SET and 'default' in opts:
                value = opts['default']()

            setattr(self, attr, (None if value is NOT_SET else value))

    def _validate_attr(
        self,
        attr: str,
        value: object,
        type_: object,
        required: bool,
        opts: dict
    ) -> None:
        if required and value is NOT_SET:
            required_for_auth_type = opts.get('required_for_auth_type')
            if required_for_auth_type:
                raise ValueError(
                    f'Attribute {attr} is required for auth_type='
                    f'`{required_for_auth_type}`'
                )
            else:
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
