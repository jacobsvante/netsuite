---
hide:
- navigation
---

# netsuite python library

Make async requests to NetSuite SuiteTalk SOAP/REST Web Services and Restlets

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


## Programmatic use - Basic Example

```python
import asyncio

from netsuite import NetSuite, Config, TokenAuth

config = Config(
    account="12345",
    auth=TokenAuth(consumer_key="abc", consumer_secret="123", token_id="xyz", token_secret="456"),
)

ns = NetSuite(config)


async def async_main():
    rest_api_results = await ns.rest_api.get("/record/v1/salesOrder")

    restlet_results = await ns.restlet.get(987, deploy=2)

    # NOTE: SOAP needs `pip install netsuite[soap_api]`
    soap_api_results = await ns.soap_api.getList('customer', internalIds=[1337])

    # Multiple requests, using the same underlying connection
    async with ns.soap_api:
        customers = await ns.soap_api.getList('customer', internalIds=[1, 2, 3])
        sales_orders = await ns.soap_api.getList('salesOrder', internalIds=[1, 2])

if __name__ == "__main__":
    asyncio.run(async_main())

```

## Programmatic use - Search Object by Custom Field Value

```python
import asyncio
import zeep.helpers

from netsuite import NetSuite, Config, TokenAuth

config = Config(
    account="12345",
    auth=TokenAuth(consumer_key="abc", consumer_secret="123", token_id="xyz", token_secret="456"),
)

ns = NetSuite(config)


async def async_main() -> dict:
    SearchStringCustomField = ns.soap_api.Core.SearchStringCustomField
    search_string_custom_field = SearchStringCustomField(
        scriptId='**CUSTOM_FIELD_ID**',  # Replace with a custom field ID
        operator='is',
        searchValue='**TEST_VALUE**'  # Replace with any string value
    )
    SearchCustomFieldList = ns.soap_api.Core.SearchCustomFieldList
    search_custom_field_list = SearchCustomFieldList(customField=[search_string_custom_field])
    SearchBasic = ns.soap_api.Common.TransactionSearchBasic  # Performing a Transaction Object Search
    Search = ns.soap_api.Sales.TransactionSearch  # Performing a Transaction Object Search
    search_basic = SearchBasic(customFieldList=search_custom_field_list)
    record = Search(basic=search_basic)
    response = await ns.soap_api.search(record=record)
    return zeep.helpers.serialize_object(response)  # Return the data as a dict

if __name__ == "__main__":
    asyncio.run(async_main())
```

## Programmatic use - Search Object by Custom Field Value - REST API

```python
import asyncio

from netsuite import NetSuite, Config, TokenAuth

config = Config(
    account="12345",
    auth=TokenAuth(consumer_key="abc", consumer_secret="123", token_id="xyz", token_secret="456"),
)

ns = NetSuite(config)

async def async_main() -> dict:
    customer_keyword = 'Test Customer'
    query_params = {'q':f'Name CONTAIN "{customer_keyword}"'}
    rest_api_results = await ns.rest_api.get("/record/v1/customer", params=query_params)

    if __name__ == "__main__":
        asyncio.run(async_main())
```

## Programmatic use - Download Large Files Using SOAP API
When working with large files, you might find that responses are truncated if they exceed 10MB. This limitation stems from the default settings in Zeep. To overcome this, enable the `xml_huge_tree` option in the Zeep client settings.

```python
ns = NetSuite(config)
# Enable handling of large XML trees
ns.soap_api.client.settings.xml_huge_tree = True
```
## Programmatic use - Adjusting Cache Settings
When deploying applications with strict permissions, you might encounter issues related to caching and more specifically to the location where Zeep library is trying to write its cache SQLite database. You can adjust the cache settings by passing a custom cache parameter via `soap_api_options` when initializing the `NetSuite` or `NetSuiteSoapApi` class.

### Option 1 - Change SQLite path
```python
from netsuite import NetSuite, Config, TokenAuth
from zeep.cache import SqliteCache

config = Config(
    account="12345",
    auth=TokenAuth(consumer_key="abc", consumer_secret="123", token_id="xyz", token_secret="456"),
)

# Specify SQLite path in soap_api_options
soap_api_options = {"cache": SqliteCache(path='/tmp/sqlite.db', timeout=60)}

ns = NetSuite(config, soap_api_options=soap_api_options)

```

### Option-2 Use InMemoryCache
```python
from netsuite import NetSuite, Config, TokenAuth
from zeep.cache import InMemoryCache

config = Config(
    account="12345",
    auth=TokenAuth(consumer_key="abc", consumer_secret="123", token_id="xyz", token_secret="456"),
)

# Specify InMemoryCache in soap_api_options
soap_api_options = {"cache": InMemoryCache()}

ns = NetSuite(config, soap_api_options=soap_api_options)
```

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

Alternatively, you can source configuration from your environment variables instead (pairs well with [direnv](https://direnv.net)):

```shell
export NETSUITE_ACCOUNT=DIGITS_SB1
export NETSUITE_CONSUMER_KEY=LONGALPHANUMERIC
export NETSUITE_CONSUMER_SECRET=LONGALPHANUMERIC
export NETSUITE_TOKEN_ID=LONGALPHANUMERIC
export NETSUITE_TOKEN_SECRET=LONGALPHANUMERIC
```

And using the `--config-environment` flag when loading the CLI.

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

You can also pull configuration from your environment:

```shell
netsuite --config-environment rest-api openapi-serve
```

### `interact` - Interact with SOAP/REST web services and restlets

Starts an IPython REPL where you can interact with the client.

```
$ netsuite interact
Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client

Example usage:
    soap_api_results = ns.soap_api.getList('customer', internalIds=[1337])
    rest_api_results = await ns.rest_api.get("/record/v1/salesOrder")
    restlet_results = await ns.restlet.get(987, deploy=2)

In [1]: rest_api_results = await ns.rest_api.get("
```


### `restlet` - Make requests to restlets

```
$ echo '{"savedSearchId": 987}' | netsuite restlet 123 -
```

### suiteanalytics

```
brew install unixodbc
```

## Developers

To run the tests, do:

1. Install Poetry (https://python-poetry.org/docs/)
1. Install dependencies `poetry install --extras all`
1. Run tests: `poetry run pytest`

Before committing and publishing a pull request, do:

1. Install pre-commit globally: `pip install pre-commit`
1. Run `pre-commit install` to install the Git hook

[pre-commit](https://pre-commit.com/) will ensure that all code is formatted per our conventions. Failing to run this will probably make the CI tests fail in the PR instead.
