# Changelog

## [0.9.0](https://github.com/jacobsvante/netsuite/compare/v0.8.0...v0.9.0) (2022-06-02)


### Bug Fixes

* Async connections sessions were being closed ([28e2b8e](https://github.com/jacobsvante/netsuite/commit/28e2b8e387ae4d30d65540901714f69a0b6248ab))
* Don't require existing config to check version ([b9982bf](https://github.com/jacobsvante/netsuite/commit/b9982bf23ebf051ba994c0c1f8b0ba3f88b31cbc))
* Regression in `openapi serve` CLI command ([c0074a0](https://github.com/jacobsvante/netsuite/commit/c0074a08edbef352b8b707ae1a6a7a21a25ce3d1))
* Update dependencies ([1956b4d](https://github.com/jacobsvante/netsuite/commit/1956b4db748dd321fe310c3542f3e29c0f2161eb)), closes [#39](https://github.com/jacobsvante/netsuite/issues/39) [#40](https://github.com/jacobsvante/netsuite/issues/40)


### Documentation

* Add example project for soap requests ([352bdd6](https://github.com/jacobsvante/netsuite/commit/352bdd6c9c63d1d2f9b0107921d35ca690dad82d))


### Continuous Integration

* Fix yaml miss ([9180897](https://github.com/jacobsvante/netsuite/commit/91808971e3ab737ab0cd5bde8eda6a5b04bdd2e3))

## [0.8.0](https://github.com/jacobsvante/netsuite/compare/v0.7.0...v0.8.0) - 2021-04-28

### Changed
- Default signing method is now HMAC-SHA256 for REST API and Restlet. The old default of HMAC-SHA1 can be set via the `signature_method` keyword argument. (Thanks to @zerodarkzone, issue #27)

### Added
- HMAC-SHA256 signing method when making requests to REST API and Restlets
- Dependency `oauthlib`

## [0.7.0](https://github.com/jacobsvante/netsuite/compare/v0.6.3...v0.7.0) - 2021-04-27

This release breaks a lot of things. Please read carefully.

### Changed
- SOAP and Restlet APIs are now async (i.e. this library is no longer useable in a non-async environment)
- The `netsuite.client.NetSuite` class is now just a thin layer around each of the different API types (SOAP, REST, Restlets)
- SOAP Web Services support is no longer included in the default install, please use `netsuite[soap_api]` (unfortunately `zeep` pulls in a lot of other dependencies, so I decided to remove it by default)
- `netsuite.restlet.NetsuiteRestlet` has been renamed to `netsuite.restlet.NetSuiteRestlet`
- Move NetSuite version to 2021.1
- Upgrade to httpx ~0.18

### Added
- `netsuite.restlet.NetSuiteRestlet` now support all four HTTP verbs GET, POST, PUT & DELETE via dedicated functions `.get`, `.post`, `.put` & `.delete`
- REST API and Restlet are now supported with the default install
- CLI now has a new sub-command `soap-api`, which currently only support `get` and `getList`
- Dependency [pydantic](https://pydantic-docs.helpmanual.io/) has been added to help with config validation

### Removed
- Authentication via User credentials has been removed (will no longer work from NetSuite 2021.2 release anyway)
- `netsuite.restlet.NetSuiteRestApi.request` and `netsuite.restlet.NetSuiteRestlet.request` no longer exists - use each dedicated "verb method" instead
- Removed dead code for setting SOAP preferences
- CLI sub-command aliases `i` (interact) and `r` (rest-api) have been removed to avoid confusion

## [0.6.3](https://github.com/jacobsvante/netsuite/compare/v0.6.2...v0.6.3) - 2021-04-26

### Added
- Ability to supply custom headers to REST API requests made from CLI via "-H/--header" flag
- Support custom payload, headers and params in suiteql REST API method

## [0.6.2](https://github.com/jacobsvante/netsuite/compare/v0.6.1...v0.6.2) - 2021-04-25

### Fixed
- `NetSuiteRestApi` no longer requires a running asyncio loop to be instantiated

## [0.6.1](https://github.com/jacobsvante/netsuite/compare/v0.6.0...v0.6.1) - 2021-04-25

### Fixed
- Fix "local variable 'record_ref' referenced before assignment" error in `NetSuite.get` method - Thanks @VeNoMouS! (#25)

## [0.6.0] - 2021-04-25

### Fixed
- Release 2021.1 wouldn't accept non-GET requests to the REST API without body being part of the signing. Thanks to @mmangione for the PR! (#26)

### Added
- Documentation site

### Removed
- Python 3.6 support

### Changed
- Upgrade to httpx ~0.17
- Use poetry for package management
- Move to Github Actions

## [0.5.3] - 2020-05-26

### Fixed
- Couldn't import `netsuite` unless `httpx` was installed. Fixes #18

## [0.5.2] - 2020-05-02

### Fixed
- Only forward explicitly passed in parameters for `netsuite rest-api get` command. Fixes error `Invalid query parameter name: limit. Allowed query parameters are: fields, expand, expandSubResources.`

### Added
- Ability to have `netsuite rest-api get` only return a given list of fields via `--fields`
- Ability for `netsuite rest-api get` to only expand a given set of sublist and subrecord types via `--expand`

## [0.5.1] - 2020-05-02

### Changed
- HTML title in OpenAPI Swagger docs

## [0.5.0] - 2020-05-02

### Added
- Support for SuiteTalk REST Web Services, including standard GET, POST, PATCH, PUT, DELETE requests as well as making SuiteQL queries. For now it's an optional dependency (install with `pip install netsuite[rest_api]`)
- Start a HTTP server via command line to browse REST API OpenAPI spec docs for a given set of records (utilizes Swagger UI)

### Changed
- `--log-level`, `--config-path` and `--config-section` must now be passed directly to the `netsuite` command, and not its sub-commands.

## [0.4.1] - 2020-03-09

### Changed
- Extend Zeep Transport GET and POST HTTP methods to apply the account-specific dynamic domain as the remote host
- Update the NetSuite WSDL compatibility to 2019.2

## [0.4.0] - 2019-04-29

### Added
- Support for specifying operation/request timeouts

### Changed
- Changed: Throw an exception if Suitetalk returns a response error

## [0.3.2] - 2019-04-11

### Added
- Support for `update` and `search` operations

## [0.3.1] - 2019-04-11

### Changed
- Decrease restlet request time on subsequent requests by half by re-using the OAuth session

## [0.3.0] - 2019-04-10

### Added
- Support for making requests to restlets
- New command to utilize the new restlet request capability
- Added: Document usage of CLI utils
### Removed
- `requests-ntlm` dependency which was never used

### Changed
- Don't specify `lxml` as a dependency. Implicitly take dependency from `zeep` instead.

## [0.2.2] - 2018-12-11

### Added
- `get`, `getAll`, `add`, `upsert` and `upsertList` methods. Big thanks go out to @matmunn for the original PR. (#6)

## [0.2.1] - 2018-12-11

### Added
- Helper `NetSuite.to_builtin` to convert zeep objects to python builtins
- `lastQtyAvailableChange` filter

## [0.2.0] - 2018-12-11

### Changed
- Sandbox is now configured through account ID, `sandbox` flag is now a no-op
- New default version is 2018.1.0
- Account specific domains are now used when `wsdl_url` is left unspecified

### Added
- Support regular credentials Passport
- Listing Python 3.7 as a supported version

## [0.1.1] - 2018-04-02

### Fixed
- `getItemAvailability` only read first passed in external/internal ID

### Added
- Allow overriding global NS preferences through SOAP headers

## [0.1.0] - 2018-03-29

- Initial version. Support for `getList` and `getItemAvailability`
- Please note that there is currently no handling for error responses from the API
