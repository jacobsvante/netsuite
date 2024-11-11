# Compatibility module - in case SOAP isn't enabled in library
try:
    import zeep as __zeep  # noqa
except ImportError:
    ZEEP_INSTALLED = False
else:
    ZEEP_INSTALLED = True

if ZEEP_INSTALLED:
    import requests
    from zeep import *  # noqa
    from zeep import cache, client, helpers, transports, xsd
else:

    class _Transport: ...

    class _BaseCache: ...

    class _SqliteCache: ...

    class _CompoundValue: ...

    class _Client: ...

    class _ServiceProxy: ...

    class _Factory: ...

    class _valueobjects:
        CompoundValue = _CompoundValue

    class cache:  # type: ignore[no-redef]
        Base = _BaseCache
        SqliteCache = _SqliteCache

    class client:  # type: ignore[no-redef]
        Client = _Client
        AsyncClient = _Client
        ServiceProxy = _ServiceProxy
        Factory = _Factory

    class transports:  # type: ignore[no-redef]
        Transport = _Transport
        AsyncTransport = _Transport

    class xsd:  # type: ignore[no-redef]
        CompoundValue = _CompoundValue
        valueobjects = _valueobjects

    class helpers:  # type: ignore[no-redef]
        serialize_object = None

    class requests:  # type: ignore[no-redef]
        Session = None
