import json
import sys
import logging
import logging.config

import IPython
import argh
import traitlets

import netsuite
from netsuite import config
from netsuite.constants import DEFAULT_INI_PATH, DEFAULT_INI_SECTION


def _set_log_level(log_level):
    if log_level is not None:
        level = getattr(logging, log_level.upper())
        logging.basicConfig()
        logging.getLogger('zeep').setLevel(level)
        netsuite.logger.setLevel(level)


@argh.arg('-l', '--log-level', help='The log level to use')
@argh.arg('-p', '--config-path', help='The config file to get settings from')
@argh.arg('-c', '--config-section', help='The config section to get settings from')
def interact(
    log_level=None,
    config_path=DEFAULT_INI_PATH,
    config_section=DEFAULT_INI_SECTION
):
    """Starts a REPL to enable live interaction with NetSuite webservices"""
    _set_log_level(log_level)

    conf = config.from_ini(path=config_path, section=config_section)

    ns = netsuite.NetSuite(conf)

    user_ns = {'ns': ns}

    banner1 = """Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client

Example usage:
    ws_results = ns.getList('customer', internalIds=[1337])
    restlet_results = ns.restlet.request(987)
"""

    IPython.embed(
        user_ns=user_ns,
        banner1=banner1,
        config=traitlets.config.Config(colors='LightBG'),
        # To fix no colored input we pass in `using=False`
        # See: https://github.com/ipython/ipython/issues/11523
        # TODO: Remove once this is fixed upstream
        using=False,
    )


@argh.arg('-l', '--log-level', help='The log level to use')
@argh.arg('-p', '--config-path', help='The config file to get settings from')
@argh.arg('-c', '--config-section', help='The config section to get settings from')
def restlet(
    script_id,
    payload,
    deploy=1,
    log_level=None,
    config_path=DEFAULT_INI_PATH,
    config_section=DEFAULT_INI_SECTION
):
    """Make requests to restlets"""

    _set_log_level(log_level)
    conf = config.from_ini(path=config_path, section=config_section)
    ns = netsuite.NetSuite(conf)

    if not payload:
        payload = None
    elif payload == '-':
        payload = json.load(sys.stdin)
    else:
        payload = json.loads(payload)

    resp = ns.restlet.raw_request(
        script_id=script_id,
        deploy=deploy,
        payload=payload,
        raise_on_bad_status=False,
    )
    return resp.text


command_parser = argh.ArghParser()
command_parser.add_commands([interact, restlet])
main = command_parser.dispatch
