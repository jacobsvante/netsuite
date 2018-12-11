# Changelog

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
