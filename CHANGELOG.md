# Changelog

## [0.12.0](https://github.com/jacobsvante/netsuite/compare/v0.11.0...v0.12.0) (2024-03-01)


### Features

* add more account helpers ([a66bf39](https://github.com/jacobsvante/netsuite/commit/a66bf3931f50f602122523ae2e4cd33866de8e55))
* **odbc:** add username and password auth ([e01f601](https://github.com/jacobsvante/netsuite/commit/e01f60145df0a168841fbafa1ccb9881d3184fa2))
* **odbc:** adding odbc data source to config ([b5a6a38](https://github.com/jacobsvante/netsuite/commit/b5a6a38c0c7b7a7417608dfaca2a7ce75894f406))
* source username and password from env ([38b1788](https://github.com/jacobsvante/netsuite/commit/38b178856be2bf7bdc3cd1d6de430d6227e44470))


### Bug Fixes

* sourcing username + password from env ([78063b5](https://github.com/jacobsvante/netsuite/commit/78063b536cef0896a10ccba84dda28642d56647f))
* union typing fix for old py ([a73540e](https://github.com/jacobsvante/netsuite/commit/a73540e99c92996fb4e08e4dd9729ef3fe4bff50))


### Documentation

* adding slack link ([4ba6cf9](https://github.com/jacobsvante/netsuite/commit/4ba6cf9bca21df0e88e67cf586d77716ef301a32))

## [0.11.0](https://github.com/jacobsvante/netsuite/compare/v0.10.1...v0.11.0) (2024-01-25)


### Features

* adding token_info restapi command ([dbeaf0a](https://github.com/jacobsvante/netsuite/commit/dbeaf0a34a5c78328a89763ae8cae3853e834f37))

## [0.10.1](https://github.com/jacobsvante/netsuite/compare/v0.10.0...v0.10.1) (2024-01-24)


### Bug Fixes

* add `query` helper to interact and use a standard ipython shell ([896be6f](https://github.com/jacobsvante/netsuite/commit/896be6fa6d6cfee3474c13d6a01047b1c73f7193))


### Documentation

* additional rest api documentation ([81b629c](https://github.com/jacobsvante/netsuite/commit/81b629cb4ffa10823b76764d7780c5b8fae3b2e6))
* removing beta quality disclaimer ([c09b230](https://github.com/jacobsvante/netsuite/commit/c09b2306ac59193075646e57f0b65a1506f776ab))

## [0.10.0](https://github.com/jacobsvante/netsuite/compare/v0.9.0...v0.10.0) (2023-10-29)


### Features

* import pretty_traceback if it exists ([93e6246](https://github.com/jacobsvante/netsuite/commit/93e6246dbc44a51017143fa985dec3c65c6e8f4a))
* support ENV-based configuration ([3ba4150](https://github.com/jacobsvante/netsuite/commit/3ba4150df29b8a2942604fd77b4f772185e8653a))
* upgrade swagger openai viewer 3 =&gt; 5 ([bc52155](https://github.com/jacobsvante/netsuite/commit/bc52155989fc0d5256eaa106f97e7e32bbecccbd))


### Bug Fixes

* make log level optional ([5110138](https://github.com/jacobsvante/netsuite/commit/51101387a621c8cfd8ccdbfa7fa8e2b3ab0eaa10))
* missing cached_property usage ([b6eef1a](https://github.com/jacobsvante/netsuite/commit/b6eef1aeb3bdffdf37581a1944d6b7249954fcb1))
* mypy 1.x ignore ([c80b03f](https://github.com/jacobsvante/netsuite/commit/c80b03f7694a7e44adace97e4a295ce2216f094d))
* mypy dict typing error ([890c3a5](https://github.com/jacobsvante/netsuite/commit/890c3a53e0240d64436d8409671defa9d6c9a63d))
* mypy fixes ([33314b4](https://github.com/jacobsvante/netsuite/commit/33314b45218faefe6a38f9fcffd24aa3fb1aa057))
* optional log_level for real ([f4b9a92](https://github.com/jacobsvante/netsuite/commit/f4b9a92fd9a4f283ad918bf8c4013a1411592451))
* use old-school dict typing assignment for py 8 ([8168726](https://github.com/jacobsvante/netsuite/commit/8168726c597c10b7b878a7e39d625a8cf12db90d))


### Documentation

* add config-environment note ([378f8e5](https://github.com/jacobsvante/netsuite/commit/378f8e54524b90b9c482a99936026211afa0004b))
* add docs link to headline ([3fa13ad](https://github.com/jacobsvante/netsuite/commit/3fa13adb6c180ee3edfc2fec2be7e97c2f137fe7))
* add gh link ([4368c65](https://github.com/jacobsvante/netsuite/commit/4368c659ba7378168c882a1ec58eb728f32498dd))
* add myself to authors ([6095fb3](https://github.com/jacobsvante/netsuite/commit/6095fb32b08ec73a970a8d780d377973f4b3f5c3))
* add repo url ([69b0e79](https://github.com/jacobsvante/netsuite/commit/69b0e799cbc0ee5c8149441e6cdec39c2c12588c))

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
