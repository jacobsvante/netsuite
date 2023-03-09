import IPython
import traitlets

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

    user_ns = {"ns": ns}

    banner1 = """Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client

Example usage:
    soap_results = await ns.soap_api.getList('customer', internalIds=[1337])
    restlet_results = await ns.restlet.get(987, deploy=2)
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
