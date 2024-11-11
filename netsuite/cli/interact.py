import asyncio

import IPython

from ..client import NetSuite

__all__ = ()


def add_parser(parser, subparser):
    interact_parser = subparser.add_parser(
        "interact",
        description="Starts a REPL to enable live interaction with NetSuite webservices",
    )
    interact_parser.set_defaults(func=interact)
    return (interact_parser, None)


def interact(config, args):
    ns = NetSuite(config)

    user_ns = {
        "ns": ns,
        "query": lambda **kwargs: asyncio.run(ns.rest_api.suiteql(**kwargs)),
    }

    banner1 = """Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client
    `query` - run SuiteQL sync

Example usage:
    soap_results = await ns.soap_api.getList('customer', internalIds=[1337])

    restlet_results = await ns.restlet.get(987, deploy=2)

    rest_api_results = await ns.rest_api.get("/record/v1/salesOrder")
    ns.rest_api._default_timeout = 60 * 5
    catalog = await ns.rest_api.openapi()

    query_results = await ns.rest_api.suiteql("SELECT * FROM salesOrder")
    query_results = query("SELECT * FROM salesOrder")
"""

    print(banner1)
    IPython.start_ipython(argv=[], user_ns=user_ns)
