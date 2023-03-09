import argparse

from ..config import Config

__all__ = ()


def load_config_or_error(parser: argparse.ArgumentParser, path: str, section: str) -> Config:  # type: ignore[return]
    try:
        conf = Config.from_ini(path=path, section=section)
    except FileNotFoundError:
        parser.error(f"Config file {path} not found")
    except KeyError as ex:
        if ex.args == (section,):
            parser.error(f"No config section `{section}` in file {path}")
        else:
            raise ex
    else:
        return conf
