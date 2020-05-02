import argparse
import asyncio
import functools
import http.server
import inspect
import logging
import logging.config
import pathlib
import sys
import tempfile

import IPython
import pkg_resources
import traitlets

import netsuite
from netsuite import config, json
from netsuite.constants import DEFAULT_INI_PATH, DEFAULT_INI_SECTION

logger = logging.getLogger("netsuite")


def main():
    try:
        args = parser.parse_args()
    except Exception:
        parser.print_help()
        return

    subparser_name = sys.argv[-1]

    if subparser_name == "rest-api":
        rest_api_parser.print_help()
        return

    config = _load_config_or_error(args.config_path, args.config_section)

    log_level = getattr(logging, args.log_level)
    logging.basicConfig(level=log_level)

    ret = args.func(config, args)

    if inspect.iscoroutinefunction(args.func):
        ret = asyncio.run(ret)

    if ret is not None:
        print(ret)


def version(config, args) -> str:
    return pkg_resources.get_distribution("netsuite").version


def interact(config, args):
    ns = netsuite.NetSuite(config)

    user_ns = {"ns": ns}

    banner1 = """Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client

Example usage:
    ws_results = ns.getList('customer', internalIds=[1337])
    restlet_results = ns.restlet.request(987)
    rest_api_results = await ns.rest_api.get("/record/v1/salesOrder")
"""

    IPython.embed(
        user_ns=user_ns,
        banner1=banner1,
        config=traitlets.config.Config(colors="LightBG"),
        # To fix no colored input we pass in `using=False`
        # See: https://github.com/ipython/ipython/issues/11523
        # TODO: Remove once this is fixed upstream
        using=False,
    )


def restlet(config, args) -> str:
    ns = netsuite.NetSuite(config)

    if not args.payload:
        payload = None
    elif args.payload == "-":
        with sys.stdin as fh:
            payload = json.loads(fh.read())
    else:
        payload = json.loads(args.payload)

    resp = ns.restlet.raw_request(
        script_id=args.script_id,
        deploy=args.deploy,
        payload=payload,
        raise_on_bad_status=False,
    )
    return resp.text


async def rest_api_get(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)
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
    resp = await rest_api.get(args.subpath, params=params)
    return json.dumps_str(resp)


async def rest_api_post(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)
    with args.payload_file as fh:
        payload_str = fh.read()

    payload = json.loads(payload_str)

    resp = await rest_api.post(args.subpath, json=payload)
    return json.dumps_str(resp)


async def rest_api_put(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)
    with args.payload_file as fh:
        payload_str = fh.read()

    payload = json.loads(payload_str)

    resp = await rest_api.put(args.subpath, json=payload)
    return json.dumps_str(resp)


async def rest_api_patch(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)
    with args.payload_file as fh:
        payload_str = fh.read()

    payload = json.loads(payload_str)

    resp = await rest_api.patch(args.subpath, json=payload)
    return json.dumps_str(resp)


async def rest_api_delete(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)

    resp = await rest_api.delete(args.subpath)
    return json.dumps_str(resp)


async def rest_api_suiteql(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)

    with args.q_file as fh:
        q = fh.read()

    resp = await rest_api.suiteql(q=q, limit=args.limit, offset=args.offset)

    return json.dumps_str(resp)


async def rest_api_jsonschema(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)
    resp = await rest_api.jsonschema(args.record_type)
    return json.dumps_str(resp)


async def rest_api_openapi(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)
    resp = await rest_api.openapi(args.record_types)
    return json.dumps_str(resp)


async def rest_api_openapi_serve(config, args) -> str:
    rest_api = _get_rest_api_or_error(config)
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
    openapi_file.write_bytes(json.dumps(spec))
    html = """<!DOCTYPE html>
<html>
    <head>
    <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
    <title>NetSuite REST Record API</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
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
        http.server.SimpleHTTPRequestHandler, directory=str(tempdir),
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


def _load_config_or_error(path: str, section: str) -> config.Config:
    try:
        return config.from_ini(path=path, section=section)
    except FileNotFoundError:
        parser.error(f"Config file {path} not found")
    except KeyError as ex:
        if ex.args == (section,):
            parser.error(f"No config section `{section}` in file {path}")
        else:
            raise ex


def _get_rest_api_or_error(config: config.Config):
    ns = netsuite.NetSuite(config)

    try:
        return ns.rest_api  # Cached property that initializes NetSuiteRestApi
    except RuntimeError as ex:
        parser.error(str(ex))


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    "-l",
    "--log-level",
    help="The log level to use",
    default="INFO",
    choices=("DEBUG", "INFO", "WARNING", "ERROR"),
)
parser.add_argument(
    "-p",
    "--config-path",
    help="The config file to get settings from",
    default=DEFAULT_INI_PATH,
)
parser.add_argument(
    "-c",
    "--config-section",
    help="The config section to get settings from",
    default=DEFAULT_INI_SECTION,
)

subparsers = parser.add_subparsers(help="App CLI", required=True)

version_parser = subparsers.add_parser("version")
version_parser.set_defaults(func=version)

interact_parser = subparsers.add_parser(
    "interact",
    aliases=["i"],
    description="Starts a REPL to enable live interaction with NetSuite webservices",
)
interact_parser.set_defaults(func=interact)

restlet_parser = subparsers.add_parser(
    "restlet", description="Make request to a restlet"
)
restlet_parser.set_defaults(func=restlet)
restlet_parser.add_argument("script_id", type=int)
restlet_parser.add_argument("payload")
restlet_parser.add_argument("-d", "--deploy", type=int, default=1)

rest_api_parser = subparsers.add_parser("rest-api", aliases=["r"])
rest_api_subparser = rest_api_parser.add_subparsers()

rest_api_get_parser = rest_api_subparser.add_parser(
    "get", description="Make a GET request to NetSuite REST web services"
)
rest_api_get_parser.set_defaults(func=rest_api_get)
rest_api_get_parser.add_argument(
    "subpath", help="The subpath to GET, e.g. `/record/v1/salesOrder`",
)
rest_api_get_parser.add_argument(
    "-q",
    "--query",
    help="Search query used to filter results. See NetSuite help center for syntax information. Only works for list endpoints e.g. /record/v1/customer",
)
rest_api_get_parser.add_argument(
    "-e",
    "--expandSubResources",
    action="store_true",
    help="Automatically expand all sublists, sublist lines and subrecords on this record. Only works for detail endpoints e.g. /record/v1/invoice/123.",
)
rest_api_get_parser.add_argument("-l", "--limit", type=int)
rest_api_get_parser.add_argument("-o", "--offset", type=int)
rest_api_get_parser.add_argument(
    "-f",
    "--fields",
    metavar="field",
    nargs="*",
    help="Only include the given fields in response",
)
rest_api_get_parser.add_argument(
    "-E",
    "--expand",
    nargs="*",
    help="Expand the given sublist lines and subrecords on this record. Only works for detail endpoints e.g. /record/v1/invoice/123.",
)

rest_api_post_parser = rest_api_subparser.add_parser(
    "post", description="Make a POST request to NetSuite REST web services"
)
rest_api_post_parser.set_defaults(func=rest_api_post)
rest_api_post_parser.add_argument(
    "subpath", help="The subpath to POST to, e.g. `/record/v1/salesOrder`",
)
rest_api_post_parser.add_argument("payload_file", type=argparse.FileType("r"))

rest_api_put_parser = rest_api_subparser.add_parser(
    "put", description="Make a PUT request to NetSuite REST web services"
)
rest_api_put_parser.set_defaults(func=rest_api_put)
rest_api_put_parser.add_argument(
    "subpath", help="The subpath to PUT to, e.g. `/record/v1/salesOrder/eid:abc123`",
)
rest_api_put_parser.add_argument("payload_file", type=argparse.FileType("r"))

rest_api_patch_parser = rest_api_subparser.add_parser(
    "patch", description="Make a PATCH request to NetSuite REST web services"
)
rest_api_patch_parser.set_defaults(func=rest_api_patch)
rest_api_patch_parser.add_argument(
    "subpath", help="The subpath to PATCH to, e.g. `/record/v1/salesOrder/eid:abc123`",
)
rest_api_patch_parser.add_argument("payload_file", type=argparse.FileType("r"))

rest_api_delete_parser = rest_api_subparser.add_parser(
    "delete", description="Make a delete request to NetSuite REST web services"
)
rest_api_delete_parser.set_defaults(func=rest_api_delete)
rest_api_delete_parser.add_argument(
    "subpath",
    help="The subpath for the DELETE request, e.g. `/record/v1/salesOrder/eid:abc123`",
)

rest_api_suiteql_parser = rest_api_subparser.add_parser(
    "suiteql", description="Make a SuiteQL request to NetSuite REST web services"
)
rest_api_suiteql_parser.set_defaults(func=rest_api_suiteql)
rest_api_suiteql_parser.add_argument(
    "q_file", type=argparse.FileType("r"), help="File containing a SuiteQL query"
)
rest_api_suiteql_parser.add_argument("-l", "--limit", type=int, default=10)
rest_api_suiteql_parser.add_argument("-o", "--offset", type=int, default=0)

rest_api_jsonschema_parser = rest_api_subparser.add_parser(
    "jsonschema", description="Retrieve JSON Schema for the given record type"
)
rest_api_jsonschema_parser.set_defaults(func=rest_api_jsonschema)
rest_api_jsonschema_parser.add_argument(
    "record_type", help="The record type to get JSONSchema spec for"
)

rest_api_openapi_parser = rest_api_subparser.add_parser(
    "openapi",
    aliases=["oas"],
    description="Retrieve OpenAPI spec for the given record types",
)
rest_api_openapi_parser.set_defaults(func=rest_api_openapi)
rest_api_openapi_parser.add_argument(
    "record_types",
    metavar="record_type",
    nargs="+",
    help="The record type(s) to get OpenAPI spec for",
)


rest_api_openapi_parser = rest_api_subparser.add_parser(
    "openapi-serve",
    aliases=["oas-serve"],
    description="Start a HTTP server on localhost serving the OpenAPI spec via Swagger UI",
)
rest_api_openapi_parser.set_defaults(func=rest_api_openapi_serve)
rest_api_openapi_parser.add_argument(
    "record_types",
    metavar="record_type",
    nargs="*",
    help="The record type(s) to get OpenAPI spec for. If not provided the OpenAPI spec for all known record types will be retrieved.",
)
rest_api_openapi_parser.add_argument(
    "-p", "--port", default=8000, type=int, help="The port to listen to"
)
rest_api_openapi_parser.add_argument(
    "-b", "--bind", default="127.0.0.1", help="The host to bind to"
)
