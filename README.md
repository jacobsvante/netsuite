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


## NetSuite Configuration

It is recommended that you use token based authentication when allow 3rd party applications (such as this) to access your
NetSuite instance. You can follow this [guide](http://mikebian.co/using-netsuites-token-based-authentication-with-suitetalk/)
([archived here](https://web.archive.org/web/20180829235439/http://mikebian.co/using-netsuites-token-based-authentication-with-suitetalk/), just in case)
to enable token based authentication. Remember to copy the relevant tokens and keys
from various points in the guide to your `netsuite.ini` file! It will look something like this:

```ini
[netsuite]
auth_type = token
# found in NetSuite at Setup > Company > Company Information > ACCOUNT ID
account = 123456
consumer_key = 789123
consumer_secret = 456789
token_id = 012345
token_secret = 678901
```

## CLI

### Configuration

To use the command line utilities you must add a config file with a `[netsuite]` section as shown in the 
[NetSuite Configuration Section](#netsuite-configuration) above.


You can add multiple sections like this if you have several different configurations. 
The `[netsuite]` section will be read by default, but can be overridden using the `-c` flag.

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

## Programmatic Usage

### Getting Started
To use this library in python scripts, you must either create a config file in `$HOME/.config/config.ini`. If you
prefer to use a different location (or if you are a Windows user), you can alternatively set the `NETSUITE_CONFIG` 
environment variable to the location of your configuration file. 


Bash:
```bash
export NETSUITE_CONFIG=/full/path/to/config.ini
```

Python:
```
import os

os.environ['NETSUITE_CONFIG'] = '/full/path/to/config.ini'

```

To test that this configuration will load properly, you may want to check the output of:

```
import netsuite
# optional: netsuite.config.from_int(config_path, config_region)
print(netsuite.config.from_ini().__dict__)

#{'auth_type': 'token',
# 'account': '123456',
# 'consumer_key': '789123',
# 'consumer_secret': '456789',
# 'token_id': '012345',
# 'token_secret': '678901',
# 'application_id': None,
# 'email': None,
# 'password': None,
# 'preferences': {}}
```

### Basic Usage
#### Fetch Records by ID
```
import os

os.environ['NETSUITE_CONFIG'] = '/path/to/netsuite.ini'

import netsuite

config = netsuite.config.from_ini()
client = netsuite.NetSuite(config=config)

# list of vendor records
client.getList("vendor", internalIds=[1337], externalIds=['MY_CORPORATE_IDENTIFIER1'])

# list of customer records
client.getList("customer", internalIds=[1337], externalIds=['MY_CORPORATE_IDENTIFIER1'])
```
#### Search

```
SearchStringField = client.Core.SearchStringField
CustomerSearchBasic = client.Common.CustomerSearchBasic
CustomerSearch = client.Relationships.CustomerSearch

search_string = SearchStringField(**{
            'operator': 'contains',
            'searchValue': 'a'
        })
customer_search_basic = CustomerSearchBasic(companyName=search_string)
record = CustomerSearch(basic=customer_search_basic)
response = client.request('search', record)
```

### Advanced Usage and Discovery
Before you can really use the API, you have to have an idea of what you're looking for. The client has a few
helper methods to facilitate the process of discovering types and functionality defined in the service.

* [`get_type`](#get_type)
* [`get_type_factory_name`](#get_type_factory_name)
* [`get_type_class`](#get_type_class)
* [`search_types`](#search_types)
* [`search_type_args`](#search_type_args)
* [`types_dump`](#types_dump)

Let's say that we want to do a search for Vendor, but we know nothing about the types or service calls required to make 
that happen. All we know is how to do a customer search. Based on what we know about doing a customer search,
it stands to reason that there is probably a `VendorSearchBasic` and a `VendorSearch` 
type, but we don't know what namespace they are in or how to construct them. 


#### `get_type`
```
print(client.get_type('VendorSearch'))
print(client.get_type('VendorSearchBasic'))
```
 
First, we can see that `VendorSearch` requires `VendorSearchBasic`.

`ns13:VendorSearch(basic: ns5:VendorSearchBasic, **)`

And the output of `VendorSearchBasic` shows me that there are all kinds of searches we could conduct on vendors.

A small subset:

* `accountNumber: ns0:SearchStringField` 
* `dateCreated: ns0:SearchDateField` 
* `firstName: ns0:SearchStringField`
* `lastName: ns0:SearchStringField`
* `lastModifiedDate: ns0:SearchDateField`

Suppose we want to find all of the recently modified vendors. In the customer search snippet above, we already knew what 
factories we should be using to generate the Customer types. Let's just say for now we don't know what factories
we will be using for our Vendor search functionality. 

Instead of searching through the WSDL, we can use `get_type_factory_name` and/or `get_type_class`.


#### `get_type_factory_name`
```
print(client.get_type_factory_name('VendorSearch'))
# `Relationships`
```
Now we know in the future that we can generate an instance of that type using
```
client.Relationships.VendorSearch()
```

Alternatively, 

#### `get_type_class`
```
VendorSearch = client.get_type_class('VendorSearch')
```

Now, using all of that to figure out how to search vendors:

```
SearchDateField = client.get_type_class('SearchDateField')
VendorSearchBasic = client.get_type_class('VendorSearchBasic')
VendorSearch = client.get_type_class('VendorSearch')

search_date = SearchDateField('ninetyDaysAgo', operator='after')
vendor_search_basic = VendorSearchBasic(lastModifiedDate=search_date)
record = VendorSearch(basic=vendor_search_basic)
response = client.request('search', record)
```

**Note: valid arguments for `SearchDateField` can be found [here](http://www.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2018_1/schema/enum/searchdate.html?mode=package) and
for `SearchDateFieldOperator` [here](http://www.netsuite.com/help/helpcenter/en_US/srbrowser/Browser2018_1/schema/enum/searchdatefieldoperator.html?mode=package). 
These pages are indexed so a simple web search should help you find things like this.**


#### `search_types`

If you only have a vague idea of what you are looking for, you can use `search_types` to discover new type names. 
For example, if you wanted to know what type definitions have "Vendor" in the name:

```
type_definitions_containing_substring_vendor = client.search_types('Vendor')

#[
#    'ns17:ItemVendor(vendor: ns0:RecordRef, vendorCode: xsd:string, **)',
#    'ns17:ItemVendorList(itemVendor: ns17:ItemVendor[], replaceAll: xsd:boolean)',
#    . . . 
#]
```
Or if you want to see which types have an argument matching the substring

#### `search_type_args`

```
type_definitions_with_vendor_in_arg_names = client.search_type_args('Vendor')

[
    . . .
    'ns17:ServicePurchaseItem(nullFieldList: ns0:NullField, . . ., vendorName: xsd:string, . . .)'
    . . . 
]



```




If all of that fails, you can always try perusing the output of 

#### `types_dump`
```
print(client.types_dump)
``` 
The output is very large, so be mindful of that.

