# Changelog

## 0.5.2 (2020-05-02)

* Fix: Only forward explicitly passed in parameters for `netsuite rest-api get` command. Fixes error `Invalid query parameter name: limit. Allowed query parameters are: fields, expand, expandSubResources.`
* Feature: Add ability to have `netsuite rest-api get` only return a given list of fields via `--fields`
* Feature: Add ability for `netsuite rest-api get` to only expand a given set of sublist and subrecord types via `--expand`

## 0.5.1 (2020-05-02)

* Fix HTML title in OpenAPI Swagger docs

## 0.5.0 (2020-05-02)

* Feature: Support for SuiteTalk REST Web Services, including standard GET, POST, PATCH, PUT, DELETE requests as well as making SuiteQL queries. For now it's an optional dependency (install with `pip install netsuite[rest_api]`)
* Feature: Start a HTTP server via command line to browse REST API OpenAPI spec docs for a given set of records (utilizes Swagger UI)
* Breaking change: `--log-level`, `--config-path` and `--config-section` must now be passed directly to the `netsuite` command, and not its sub-commands.

## 0.4.1 (2020-03-09)

* Extend Zeep Transport GET and POST HTTP methods to apply the account-specific dynamic domain as the remote host
* Update the NetSuite WSDL compatibility to 2019.2

## 0.4.0 (2019-04-29)

* Enhancement: Add support for specifying operation/request timeouts
* Enhancement: Throw an exception if Suitetalk returns a response error

## 0.3.2 (2019-04-11)

* Feature: Add support for `update` and `search` operations

## 0.3.1 (2019-04-11)

* Enhancement: Decrease restlet request time on subsequent requests by half by re-using the OAuth session

## 0.3.0 (2019-04-10)

* Feature: Added support for making requests to restlets
* Feature: New command to utilize the new restlet request capability
* Info: Removed `requests-ntlm` dependency which was never used
* Info: Don't specify `lxml` as a dependency. Implicitly take dependency from `zeep` instead.
* Info: Document usage of CLI utils

## 0.2.2 (2018-12-11)

* Feature: Added `get`, `getAll`, `add`, `upsert` and `upsertList` methods. Big thanks go out to @matmunn for the original PR. (#6)

## 0.2.1 (2018-12-11)

* Feature: Helper `NetSuite.to_builtin` to convert zeep objects to python builtins
* Feature: Add `lastQtyAvailableChange` filter

## 0.2.0 (2018-12-11)

* Breaking change: Sandbox is now configured through account ID, `sandbox` flag is now a no-op
* Breaking change: New default version is 2018.1.0
* Breaking change: Account specific domains are now used when `wsdl_url` is left unspecified
* Feature: Support regular credentials Passport
* Info: Listing Python 3.7 as a supported version

## 0.1.1 (2018-04-02)

* Fix: `getItemAvailability` only read first passed in external/internal ID
* Feature: Allow overriding global NS preferences through SOAP headers

## 0.1.0 (2018-03-29)

* Initial version. Support for `getList` and `getItemAvailability`
* Please note that there is currently no handling for error responses from the API. TODO!
