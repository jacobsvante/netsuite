from importlib.metadata import version as _package_version

__all__ = ()


def add_parser(parser, subparser):
    version_parser = subparser.add_parser("version")
    version_parser.set_defaults(func=version)
    return (version_parser, None)


def version() -> str:
    return _package_version("netsuite")
