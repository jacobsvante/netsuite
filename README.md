# netsuite

[![Travis CI build status (Linux)](https://travis-ci.org/jmagnusson/netsuite.svg?branch=master)](https://travis-ci.org/jmagnusson/netsuite)
[![PyPI version](https://img.shields.io/pypi/v/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![License](https://img.shields.io/pypi/l/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![Available as wheel](https://img.shields.io/pypi/wheel/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![PyPI status (alpha/beta/stable)](https://img.shields.io/pypi/status/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)

Make requests to NetSuite Web Services and Restlets

## Installation

Programmatic use only:

    pip install netsuite

With CLI support:

    pip install netsuite[cli]


## CLI

### Configuration

To use the command line utilities you must add a config file with a section in this format:

```ini
[netsuite]
auth_type = token
account = 123456
consumer_key = 789123
consumer_secret = 456789
token_id = 012345
token_secret = 678901
```

You can add multiple sections like this. The `netsuite` section will be read by default, but can be overridden using the `-c` flag.

The default location that will be read is `~/.config/netsuite.ini`. This can overriden with the `-p` flag.

Append `--help` to the commands to see full documentation.

### `restlet` - Make requests to restlets

```
$ echo '{"savedSearchId": 987}' | netsuite restlet 123 -
```


### `interact` - Interact with web services and/or restlets

```
$ netsuite interact
Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client

Example usage:
    results = ns.getList('customer', internalIds=[1337])

In [1]:
```
