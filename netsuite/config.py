import configparser
from typing import Dict, Union

from pydantic import BaseModel

from .constants import DEFAULT_INI_PATH, DEFAULT_INI_SECTION

__all__ = ("Config", "TokenAuth")


class TokenAuth(BaseModel):
    consumer_key: str
    consumer_secret: str
    token_id: str
    token_secret: str


class Config(BaseModel):
    account: str
    auth: TokenAuth
    # TODO: Support OAuth2
    # auth: Union[OAuth2, TokenAuth]

    @property
    def account_slugified(self) -> str:
        # https://followingnetsuite.wordpress.com/2018/10/18/suitetalk-sandbox-urls-addendum/
        return self.account.lower().replace("_", "-")

    @classmethod
    def from_ini(
        cls, path: str = DEFAULT_INI_PATH, section: str = DEFAULT_INI_SECTION
    ) -> "Config":
        iniconf = configparser.ConfigParser()
        with open(path) as fp:
            iniconf.read_file(fp)

        d: Dict[str, Union[str, Dict[str, str]]] = {"auth": {}}

        auth_type = iniconf[section].get("auth_type", "token")

        if auth_type != "token":
            raise RuntimeError(f"Only token auth is supported, not `{auth_type}`")

        for key, val in iniconf[section].items():
            if auth_type == "token" and key in TokenAuth.__fields__:
                d["auth"][key] = val  # type: ignore[index]
            else:
                d[key] = val

        return cls(**d)
