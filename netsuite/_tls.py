"""A process-wide TLS context shared by every outgoing request.

`RestApiBase` opens a fresh `httpx.AsyncClient` per request. Without an
explicit `verify=`, httpx builds a new `ssl.SSLContext` for each client and
re-parses the ~250 KB certifi CA bundle every time. Over a long run of
requests that cert loading dominates wall-clock time (it is where a
batch job's timeout traceback usually lands: `load_verify_locations`).

Building the context once and passing it as `verify=` makes httpx use it
as-is. The trust store matches httpx's own default: `SSL_CERT_FILE` /
`SSL_CERT_DIR` when set, otherwise certifi.
"""

import os
import ssl
import threading
from typing import Optional

import certifi

__all__ = ("shared_ssl_context",)

_lock = threading.Lock()
_context: Optional[ssl.SSLContext] = None


def _build_ssl_context() -> ssl.SSLContext:
    cert_file = os.environ.get("SSL_CERT_FILE")
    if cert_file and os.path.isfile(cert_file):
        return ssl.create_default_context(cafile=cert_file)
    cert_dir = os.environ.get("SSL_CERT_DIR")
    if cert_dir and os.path.isdir(cert_dir):
        return ssl.create_default_context(capath=cert_dir)
    return ssl.create_default_context(cafile=certifi.where())


def shared_ssl_context() -> ssl.SSLContext:
    """Return the process-wide `ssl.SSLContext`, building it on first use."""
    global _context
    if _context is None:
        with _lock:
            if _context is None:
                _context = _build_ssl_context()
    return _context
