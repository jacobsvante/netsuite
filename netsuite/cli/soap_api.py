from .. import json
from ..client import NetSuite
from ..config import Config
from ..soap_api import helpers

__all__ = ()


def add_parser(parser, subparser):
    soap_api_parser = subparser.add_parser(
        "soap-api", description="Make NetSuite SuiteTalk Web Services SOAP requests"
    )
    soap_api_subparser = soap_api_parser.add_subparsers()
    _add_get_parser(soap_api_parser, soap_api_subparser)
    _add_get_list_parser(soap_api_parser, soap_api_subparser)

    return (soap_api_parser, soap_api_subparser)


def _add_get_list_parser(parser, subparser):
    async def getList(config, args) -> str:
        soap_api = _get_soap_api_or_error(parser, config)
        resp = await soap_api.getList(
            args.record_type, externalIds=args.externalId, internalIds=args.internalId
        )
        return _dump_response(resp)

    p = subparser.add_parser("getList", description="Call the getList method")
    p.add_argument("record_type", help="The record type to get")
    p.add_argument(
        "-e",
        "--externalId",
        action="append",
        help="External IDs to get",
    )
    p.add_argument(
        "-i",
        "--internalId",
        action="append",
        help="Internal IDs to get",
    )
    p.set_defaults(func=getList)


def _add_get_parser(parser, subparser):
    async def get(config, args) -> str:
        soap_api = _get_soap_api_or_error(parser, config)
        resp = await soap_api.get(
            args.record_type, externalId=args.externalId, internalId=args.internalId
        )
        return _dump_response(resp)

    p = subparser.add_parser("get", description="Call the `get` method")
    p.add_argument("record_type", help="The record type to get")
    p.add_argument(
        "-e",
        "--externalId",
        help="External ID to get",
    )
    p.add_argument(
        "-i",
        "--internalId",
        help="Internal ID to get",
    )
    p.set_defaults(func=get)


def _get_soap_api_or_error(parser, config: Config):
    ns = NetSuite(config)

    try:
        return ns.soap_api  # Cached property that initializes NetSuiteRestApi
    except RuntimeError as ex:
        parser.error(str(ex))


def _dump_response(resp) -> str:
    return json.dumps(helpers.to_builtin(resp))
