# netsuite

[![Continuous Integration Status](https://github.com/jacobsvante/netsuite/actions/workflows/ci.yml/badge.svg)](https://github.com/jacobsvante/netsuite/actions/workflows/ci.yml)
[![Continuous Delivery Status](https://github.com/jacobsvante/netsuite/actions/workflows/cd.yml/badge.svg)](https://github.com/jacobsvante/netsuite/actions/workflows/cd.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/jacobsvante/netsuite?color=%2334D058)](https://codecov.io/gh/jacobsvante/netsuite)
[![PyPI version](https://img.shields.io/pypi/v/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![License](https://img.shields.io/pypi/l/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![Python Versions](https://img.shields.io/pypi/pyversions/netsuite.svg)](https://pypi.org/project/netsuite/)
[![PyPI status (alpha/beta/stable)](https://img.shields.io/pypi/status/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![Slack Status](https://netsuite-slackin.fly.dev/badge.svg)](https://netsuite-slackin.fly.dev)

Make async requests to NetSuite SuiteTalk SOAP, REST Web Services, and Restlets. [Detailed documentation available here.](https://jacobsvante.github.io/netsuite/)

# Help & Support

Join the [Slack channel](https://netsuite-slackin.fly.dev) for help with NetSuite issues. Please do not post usage questions as issues in GitHub.

There are some additional helpful resources for NetSuite development [listed here](https://dashboard.suitesync.io/docs/resources#netsuite).

## Installation

With default features (REST API + Restlet support):

    pip install netsuite

With Web Services SOAP API support:

    pip install netsuite[soap_api]

With CLI support:

    pip install netsuite[cli]

With `orjson` package (faster JSON handling):

    pip install netsuite[orjson]

With all features:

    pip install netsuite[all]

## Documentation

Is found here: https://jacobsvante.github.io/netsuite/
