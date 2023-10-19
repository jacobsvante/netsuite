import argparse
import functools
import http.server
import logging
import logging.config
import pathlib
import tempfile
from typing import Dict, List, Optional, Union

from .. import json
from ..client import NetSuite
from ..config import Config

logger = logging.getLogger("netsuite")

ParsedHeaders = Dict[str, Union[List[str], str]]

__all__ = ()


def add_parser(parser, subparser):
    rest_api_parser = subparser.add_parser("rest-api")
    rest_api_subparser = rest_api_parser.add_subparsers()
    _add_rest_api_get_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_post_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_put_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_patch_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_delete_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_suiteql_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_jsonschema_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_openapi_parser(rest_api_parser, rest_api_subparser)
    _add_rest_api_openapi_serve_parser(rest_api_parser, rest_api_subparser)

    return (rest_api_parser, rest_api_subparser)


def _add_rest_api_get_parser(parser, subparser):
    async def rest_api_get(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)
        params = {}
        if args.expandSubResources is True:
            params["expandSubResources"] = "true"
        if args.limit is not None:
            params["limit"] = args.limit
        if args.offset is not None:
            params["offset"] = args.offset
        if args.fields is not None:
            params["fields"] = ",".join(args.fields)
        if args.expand is not None:
            params["expand"] = ",".join(args.expand)
        if args.query is not None:
            params["q"] = args.query
        resp = await rest_api.get(
            args.subpath, params=params, headers=_parse_headers_arg(parser, args.header)
        )
        return json.dumps(resp)

    p = subparser.add_parser(
        "get", description="Make a GET request to NetSuite REST web services"
    )
    p.set_defaults(func=rest_api_get)
    p.add_argument(
        "subpath",
        help="The subpath to GET, e.g. `/record/v1/salesOrder`",
    )
    p.add_argument(
        "-q",
        "--query",
        help="Search query used to filter results. See NetSuite help center for syntax information. Only works for list endpoints e.g. /record/v1/customer",
    )
    p.add_argument(
        "-e",
        "--expandSubResources",
        action="store_true",
        help="Automatically expand all sublists, sublist lines and subrecords on this record. Only works for detail endpoints e.g. /record/v1/invoice/123.",
    )
    p.add_argument("-l", "--limit", type=int)
    p.add_argument("-o", "--offset", type=int)
    p.add_argument(
        "-f",
        "--fields",
        metavar="field",
        nargs="*",
        help="Only include the given fields in response",
    )
    p.add_argument(
        "-E",
        "--expand",
        nargs="*",
        help="Expand the given sublist lines and subrecords on this record. Only works for detail endpoints e.g. /record/v1/invoice/123.",
    )
    _add_rest_api_headers_arg(p)


def _add_rest_api_post_parser(parser, subparser):
    async def rest_api_post(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)
        with args.payload_file as fh:
            payload_str = fh.read()

        payload = json.loads(payload_str)

        resp = await rest_api.post(
            args.subpath, json=payload, headers=_parse_headers_arg(parser, args.header)
        )
        return json.dumps(resp)

    p = subparser.add_parser(
        "post", description="Make a POST request to NetSuite REST web services"
    )
    p.set_defaults(func=rest_api_post)
    p.add_argument(
        "subpath",
        help="The subpath to POST to, e.g. `/record/v1/salesOrder`",
    )
    p.add_argument("payload_file", type=argparse.FileType("r"))
    _add_rest_api_headers_arg(p)


def _add_rest_api_put_parser(parser, subparser):
    async def rest_api_put(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)
        with args.payload_file as fh:
            payload_str = fh.read()

        payload = json.loads(payload_str)

        resp = await rest_api.put(
            args.subpath, json=payload, headers=_parse_headers_arg(parser, args.header)
        )
        return json.dumps(resp)

    p = subparser.add_parser(
        "put", description="Make a PUT request to NetSuite REST web services"
    )
    p.set_defaults(func=rest_api_put)
    p.add_argument(
        "subpath",
        help="The subpath to PUT to, e.g. `/record/v1/salesOrder/eid:abc123`",
    )
    p.add_argument("payload_file", type=argparse.FileType("r"))
    _add_rest_api_headers_arg(p)


def _add_rest_api_patch_parser(parser, subparser):
    async def rest_api_patch(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)
        with args.payload_file as fh:
            payload_str = fh.read()

        payload = json.loads(payload_str)

        resp = await rest_api.patch(
            args.subpath, json=payload, headers=_parse_headers_arg(parser, args.header)
        )
        return json.dumps(resp)

    p = subparser.add_parser(
        "patch", description="Make a PATCH request to NetSuite REST web services"
    )
    p.set_defaults(func=rest_api_patch)
    p.add_argument(
        "subpath",
        help="The subpath to PATCH to, e.g. `/record/v1/salesOrder/eid:abc123`",
    )
    p.add_argument("payload_file", type=argparse.FileType("r"))
    _add_rest_api_headers_arg(p)


def _add_rest_api_delete_parser(parser, subparser):
    async def rest_api_delete(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)
        resp = await rest_api.delete(
            args.subpath, headers=_parse_headers_arg(parser, args.header)
        )
        return json.dumps(resp)

    p = subparser.add_parser(
        "delete", description="Make a DELETE request to NetSuite REST web services"
    )
    p.set_defaults(func=rest_api_delete)
    p.add_argument(
        "subpath",
        help="The subpath for the DELETE request, e.g. `/record/v1/salesOrder/eid:abc123`",
    )
    _add_rest_api_headers_arg(p)


def _add_rest_api_suiteql_parser(parser, subparser):
    async def rest_api_suiteql(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)

        with args.q_file as fh:
            q = fh.read()

        resp = await rest_api.suiteql(
            q=q,
            limit=args.limit,
            offset=args.offset,
            headers=_parse_headers_arg(parser, args.header),
        )

        return json.dumps(resp)

    p = subparser.add_parser(
        "suiteql", description="Make a SuiteQL request to NetSuite REST web services"
    )
    p.set_defaults(func=rest_api_suiteql)
    p.add_argument(
        "q_file", type=argparse.FileType("r"), help="File containing a SuiteQL query"
    )
    p.add_argument("-l", "--limit", type=int, default=10)
    p.add_argument("-o", "--offset", type=int, default=0)
    _add_rest_api_headers_arg(p)


def _add_rest_api_jsonschema_parser(parser, subparser):
    async def rest_api_jsonschema(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)
        resp = await rest_api.jsonschema(args.record_type)
        return json.dumps(resp)

    p = subparser.add_parser(
        "jsonschema", description="Retrieve JSON Schema for the given record type"
    )
    p.set_defaults(func=rest_api_jsonschema)
    p.add_argument("record_type", help="The record type to get JSONSchema spec for")
    _add_rest_api_headers_arg(p)


def _add_rest_api_openapi_parser(parser, subparser):
    async def rest_api_openapi(config, args) -> str:
        rest_api = _get_rest_api_or_error(parser, config)
        resp = await rest_api.openapi(args.record_types)
        return json.dumps(resp)

    p = subparser.add_parser(
        "openapi",
        description="Retrieve OpenAPI spec for the given record types",
    )
    p.set_defaults(func=rest_api_openapi)
    p.add_argument(
        "record_types",
        metavar="record_type",
        nargs="+",
        help="The record type(s) to get OpenAPI spec for",
    )
    _add_rest_api_headers_arg(p)


def _add_rest_api_openapi_serve_parser(parser, subparser):
    async def rest_api_openapi_serve(config, args):
        rest_api = _get_rest_api_or_error(parser, config)
        if len(args.record_types) == 0:
            logger.warning(
                "Fetching OpenAPI spec for ALL known record types... This will take a long "
                "time! (Consider providing only the record types of interest by passing "
                "their names to this command as positional arguments)"
            )
        else:
            rt_str = ", ".join(args.record_types)
            logger.info(f"Fetching OpenAPI spec for record types {rt_str}...")
        spec = await rest_api.openapi(args.record_types)
        tempdir = pathlib.Path(tempfile.mkdtemp())
        openapi_file = tempdir / "openapi.json"
        html_file = tempdir / "index.html"
        openapi_file.write_bytes(json.dumps(spec).encode("utf-8"))
        html = """<!DOCTYPE html>
    <html>
        <head>
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <title>NetSuite REST Record API</title>
        </head>
        <body>
        <div id="swagger-ui">
        </div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <!-- `SwaggerUIBundle` is now available on the page -->
        <script>
        const ui = SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            layout: "BaseLayout",
            deepLinking: true
        })
        </script>
        </body>
    </html>"""
        html_file.write_text(html)
        handler_class = functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=str(tempdir),
        )
        logger.info(
            f"NetSuite REST Record API docs available at http://{args.bind}:{args.port}"
        )
        try:
            http.server.test(
                HandlerClass=handler_class,
                ServerClass=http.server.ThreadingHTTPServer,
                port=args.port,
                bind=args.bind,
            )
        finally:
            html_file.unlink()
            openapi_file.unlink()
            tempdir.rmdir()

    p = subparser.add_parser(
        "openapi-serve",
        description="Start a HTTP server on localhost serving the OpenAPI spec via Swagger UI",
    )
    p.set_defaults(func=rest_api_openapi_serve)
    p.add_argument(
        "record_types",
        metavar="record_type",
        nargs="*",
        help="The record type(s) to get OpenAPI spec for. If not provided the OpenAPI spec for all known record types will be retrieved.",
    )
    p.add_argument("-p", "--port", default=8000, type=int, help="The port to listen to")
    p.add_argument("-b", "--bind", default="127.0.0.1", help="The host to bind to")


def _get_rest_api_or_error(parser, config: Config):
    ns = NetSuite(config)

    try:
        return ns.rest_api  # Cached property that initializes NetSuiteRestApi
    except RuntimeError as ex:
        parser.error(str(ex))


def _parse_headers_arg(
    parser,
    headers: Optional[List[str]],
) -> ParsedHeaders:
    out: ParsedHeaders = {}

    if headers is None:
        headers = []

    for raw_header in headers:
        err = False
        try:
            k, v = raw_header.split(":", maxsplit=1)
        except ValueError:
            err = True
        else:
            k, v = (k.strip(), v.strip())
            if not k or not v:
                err = True
        if err:
            parser.error(
                f"Invalid header: `{raw_header}``. Should have format: `NAME: VALUE`"
            )
        else:
            existing = out.get(k)
            if existing:
                if isinstance(existing, list):
                    existing.append(v)
                else:
                    out[k] = [existing, v]
            else:
                out[k] = v
    return out


def _add_rest_api_headers_arg(parser):
    parser.add_argument(
        "-H",
        "--header",
        action="append",
        help="Headers to append. Can be specified multiple time and the format for each is `KEY: VALUE`",
    )
