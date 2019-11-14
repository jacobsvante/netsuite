# Changelog

## 0.5.0 (2019-11-14)
 
* Breaking: `upsertList` response returns `[]WriteResponse{status, baseRef}` instance instead of `BaseRef` instance. This allows inspection or unexpected write statuses.
* Fix: `get` method no longer raise error on when return when using an externalId
* Feature: Add support for `delete` method
* Feature: Add implementation of `deleteList` method, which sometimes behaves unexpectedly (according to SuiteTalk response), use at own peril
* Feature: Add API discovery methods (outlined in README)
* Info: Update README with getting-started examples
* Info: Add doc-strings with examples for the following methods: `add`, `update`, `upsert`, `delete`
    

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
