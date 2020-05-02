# netsuite

[![Travis CI build status (Linux)](https://travis-ci.org/jmagnusson/netsuite.svg?branch=master)](https://travis-ci.org/jmagnusson/netsuite)
[![PyPI version](https://img.shields.io/pypi/v/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![License](https://img.shields.io/pypi/l/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![Available as wheel](https://img.shields.io/pypi/wheel/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)
[![PyPI status (alpha/beta/stable)](https://img.shields.io/pypi/status/netsuite.svg)](https://pypi.python.org/pypi/netsuite/)

Make requests to NetSuite SuiteTalk SOAP/REST Web Services and Restlets

## Installation

Programmatic use only:

    pip install netsuite

With CLI support:

    pip install netsuite[cli]

With NetSuite SuiteTalk REST Web Services API support:

    pip install netsuite[rest_api]

With all features:

    pip install netsuite[all]


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

### `rest-api` - Make requests to NetSuite REST API

See the NetSuite help center for info on how to use the REST API. The `netsuite rest-api openapi-serve` command is also a big help.

#### `netsuite rest-api get`

List endpoint examples:

```
$ netsuite rest-api get /record/v1/customer
```

```
$ netsuite rest-api get /record/v1/invoice --limit 10 --offset 30
```

```
$ netsuite rest-api get /record/v1/salesOrder --query 'email IS "john.doe@example.com"'
```

Detail endpoint examples:

```
$ netsuite rest-api get /record/v1/salesOrder/1337
```

```
$ netsuite rest-api get /record/v1/invoice/123 --expandSubResources
```

#### `netsuite rest-api post`

Examples:
```
$ cat ~/customer-no-1-data.json | netsuite rest-api post /record/v1/customer -
```

#### `netsuite rest-api put`

Examples:
```
$ cat ~/customer-no-1-data.json | netsuite rest-api put /record/v1/customer/123 -
```

#### `netsuite rest-api patch`

Examples:
```
$ cat ~/changed-customer-data.json | netsuite rest-api patch /record/v1/customer/123 -
```

#### `netsuite rest-api delete`

Examples:
```
$ netsuite rest-api delete /record/v1/customer/123
```

#### `netsuite rest-api jsonschema`

Examples:
```
$ netsuite rest-api jsonschema salesOrder
{"type":"object","properties":...
```

#### `netsuite rest-api openapi`

Examples:
```
$ netsuite rest-api openapi salesOrder customer invoice
{"openapi":"3.0.1","info":{"title":"NetSuite REST Record API"...
```


#### `netsuite rest-api openapi-serve`

Start a server that fetches and lists the OpenAPI spec for the given record types, using [Swagger UI](https://swagger.io/tools/swagger-ui/). Defaults to port 8000.

Examples:

```
$ netsuite rest-api openapi-serve customer salesOrder
INFO:netsuite:Fetching OpenAPI spec for record types customer, salesOrder...
INFO:netsuite:NetSuite REST API docs available at http://127.0.0.1:8001
```

It's also possible to fetch the OpenAPI spec for all known record types. This will however take a long time (60+ seconds).
```
$ netsuite rest-api openapi-serve
WARNING:netsuite:Fetching OpenAPI spec for ALL known record types... This will take a long time! (Consider providing only the record types of interest by passing their names to this command as positional arguments)
INFO:netsuite:NetSuite REST API docs available at http://127.0.0.1:8001
```


### `interact` - Interact with SOAP/REST web services and restlets

Starts an IPython REPL where you can interact with the client.

```
$ netsuite interact
Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client

Example usage:
    ws_results = ns.getList('customer', internalIds=[1337])
    restlet_results = ns.restlet.request(987)
    rest_api_results = await ns.rest_api.get("/record/v1/salesOrder")

In [1]: rest_api_results = await ns.rest_api.get("
```


### `restlet` - Make requests to restlets

```
$ echo '{"savedSearchId": 987}' | netsuite restlet 123 -
```
