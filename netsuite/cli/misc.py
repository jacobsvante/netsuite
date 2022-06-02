import pkg_resources

__all__ = ()


def add_parser(parser, subparser):
    version_parser = subparser.add_parser("version")
    version_parser.set_defaults(func=version)
    return (version_parser, None)


def version() -> str:
    return pkg_resources.get_distribution("netsuite").version
