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


@argh.arg('-c', '--config-section')
@argh.arg('-p', '--config-path')
def interact(
    log_level: 'The log level to use' = None,
    config_path: 'The config file to get settings from.' = DEFAULT_INI_PATH,
    config_section: 'The config section to get settings from.' = DEFAULT_INI_SECTION,
):
    """Starts a REPL to enable live interaction with NetSuite webservices"""
    _set_log_level(log_level)

    conf = config.from_ini(path=config_path, section=config_section)
    ns = netsuite.NetSuite(conf, sandbox=True)
    # print(ns.getList('customer', internalIds=['11397']))

    user_ns = {'ns': ns}

    banner1 = """Welcome to Netsuite WS client interactive mode
Available vars:
    `ns` - NetSuite client

Example usage:
    results = ns.getList('customer', internalIds=[1337])
"""

    IPython.embed(
        user_ns=user_ns,
        banner1=banner1,
        config=traitlets.config.Config(colors='LightBG')
    )


command_parser = argh.ArghParser()
command_parser.add_commands([interact])
main = command_parser.dispatch
