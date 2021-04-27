import argparse

from .. import json
from ..client import NetSuite
from ..config import Config

__all__ = ()


def add_parser(parser, subparser):
    restlet_parser = subparser.add_parser(
        "restlet", description="Make NetSuite Restlet requests"
    )
    restlet_subparser = restlet_parser.add_subparsers()
    _add_restlet_get_parser(restlet_parser, restlet_subparser)
    _add_restlet_post_parser(restlet_parser, restlet_subparser)
    _add_restlet_put_parser(restlet_parser, restlet_subparser)
    _add_restlet_delete_parser(restlet_parser, restlet_subparser)

    return (restlet_parser, restlet_subparser)


def _add_restlet_get_parser(parser, subparser):
    async def restlet_get(config, args) -> str:
        restlet = _get_restlet_or_error(parser, config)

        resp = await restlet.get(script_id=args.script_id, deploy=args.deploy)
        return json.dumps(resp)

    p = subparser.add_parser(
        "get", description="Make a GET request to NetSuite Restlet"
    )
    _add_default_restlet_args(p)
    p.set_defaults(func=restlet_get)


def _add_restlet_post_parser(parser, subparser):
    async def restlet_post(config, args) -> str:
        restlet = _get_restlet_or_error(parser, config)

        with args.payload_file as fh:
            payload_str = fh.read()

        payload = json.loads(payload_str)

        resp = await restlet.post(
            script_id=args.script_id, deploy=args.deploy, json=payload
        )
        return json.dumps(resp)

    p = subparser.add_parser(
        "post", description="Make a POST request to NetSuite Restlet"
    )
    p.set_defaults(func=restlet_post)
    _add_default_restlet_args(p)
    p.add_argument("payload_file", type=argparse.FileType("r"))


def _add_restlet_put_parser(parser, subparser):
    async def restlet_put(config, args) -> str:
        restlet = _get_restlet_or_error(parser, config)

        with args.payload_file as fh:
            payload_str = fh.read()

        payload = json.loads(payload_str)

        resp = await restlet.put(
            script_id=args.script_id, deploy=args.deploy, json=payload
        )
        return json.dumps(resp)

    p = subparser.add_parser(
        "put", description="Make a PUT request to NetSuite Restlet"
    )
    p.set_defaults(func=restlet_put)
    _add_default_restlet_args(p)
    p.add_argument("payload_file", type=argparse.FileType("r"))


def _add_restlet_delete_parser(parser, subparser):
    async def restlet_delete(config, args) -> str:
        restlet = _get_restlet_or_error(parser, config)

        resp = await restlet.put(script_id=args.script_id, deploy=args.deploy)
        return json.dumps(resp)

    p = subparser.add_parser(
        "delete", description="Make a DELETE request to a NetSuite Restlet"
    )
    p.set_defaults(func=restlet_delete)
    _add_default_restlet_args(p)


def _get_restlet_or_error(parser, config: Config):
    ns = NetSuite(config)

    try:
        return ns.restlet  # Cached property that initializes NetSuiteRestlet
    except RuntimeError as ex:
        parser.error(str(ex))


def _add_default_restlet_args(parser_: argparse.ArgumentParser):
    parser_.add_argument("script_id", type=int, help="The script to run")
    parser_.add_argument(
        "-d", "--deploy", type=int, default=1, help="The deployment version"
    )
