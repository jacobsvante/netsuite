import os

NOT_SET: object = object()
DEFAULT_INI_PATH: str = os.environ.get(
    'NETSUITE_CONFIG',
    os.path.expanduser('~/.config/netsuite.ini'),
)
DEFAULT_INI_SECTION: str = 'netsuite'
