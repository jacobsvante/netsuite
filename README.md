# netsuite

[![Continuous Integration Status](https://github.com/vlouvet/netsuite/actions/workflows/ci.yml/badge.svg)](https://github.com/vlouvet/netsuite/actions/workflows/ci.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/vlouvet/netsuite?color=%2334D058)](https://codecov.io/gh/vlouvet/netsuite)
[![License](https://img.shields.io/github/license/vlouvet/netsuite.svg)](LICENSE)

Make async requests to NetSuite SuiteTalk SOAP, REST Web Services, and Restlets.

This is an unofficial fork. It is not published to PyPI; install directly from this repository.

## Installation

Default features (REST API + Restlet support):

    pip install git+https://github.com/vlouvet/netsuite.git

Pin to a specific commit or tag:

    pip install git+https://github.com/vlouvet/netsuite.git@<commit-sha-or-tag>

With Web Services SOAP API support (deprecated by NetSuite as of the 2027.1 release — prefer REST + OAuth 2.0 for new integrations):

    pip install "netsuite[soap_api] @ git+https://github.com/vlouvet/netsuite.git"

With CLI support:

    pip install "netsuite[cli] @ git+https://github.com/vlouvet/netsuite.git"

With `orjson` package (faster JSON handling):

    pip install "netsuite[orjson] @ git+https://github.com/vlouvet/netsuite.git"

With all features:

    pip install "netsuite[all] @ git+https://github.com/vlouvet/netsuite.git"

## Documentation

In-repo documentation lives in [`docs/index.md`](docs/index.md).
