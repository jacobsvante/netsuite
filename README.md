# netsuite

[![Continuous Integration Status](https://github.com/jmagnusson/netsuite/actions/workflows/ci.yml/badge.svg)](https://github.com/jmagnusson/netsuite/actions/workflows/ci.yml)
[![Continuous Delivery Status](https://github.com/jmagnusson/netsuite/actions/workflows/cd.yml/badge.svg)](https://github.com/jmagnusson/netsuite/actions/workflows/cd.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/jmagnusson/netsuite?color=%2334D058)](https://codecov.io/gh/jmagnusson/netsuite)
[![PyPI version](https://img.shields.io/pypi/v/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![License](https://img.shields.io/pypi/l/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![Python Versions](https://img.shields.io/pypi/pyversions/netsuite.svg)](https://pypi.org/project/netsuite/)
[![PyPI status (alpha/beta/stable)](https://img.shields.io/pypi/status/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)

Make async requests to NetSuite SuiteTalk SOAP/REST Web Services and Restlets

## Beta quality disclaimer

The project's API is still very much in fluctuation. Please consider pinning your dependency to this package to a minor version (e.g. `poetry add netsuite~0.7` or `pipenv install netsuite~=0.7.0`), which is guaranteed to have no breaking changes. From 1.0 and forward we will keep a stable API.

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

Is found here: https://jmagnusson.github.io/netsuite/
