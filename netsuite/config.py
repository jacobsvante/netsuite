import configparser
import os
import typing as t
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
    log_level: str
    # TODO: Support OAuth2
    # auth: Union[OAuth2, TokenAuth]

    @property
    def account_slugified(self) -> str:
        # https://followingnetsuite.wordpress.com/2018/10/18/suitetalk-sandbox-urls-addendum/
        return self.account.lower().replace("_", "-")

    @staticmethod
    def _reorganize_auth_keys(raw: Dict[str, t.Any]) -> Dict[str, t.Any]:
        reorganized: Dict[str, Union[str, Dict[str, str]]] = {"auth": {}}

        for key, val in raw.items():
            if key in TokenAuth.__fields__:
                reorganized["auth"][key] = val
            else:
                reorganized[key] = val
        return reorganized

    @classmethod
    def from_env(cls):
        """
        Initialize config from environment variables.

        - `NETSUITE_AUTH_TYPE`: Specifies the type of authentication, defaults to `token`
        - `NETSUITE_ACCOUNT`: The Netsuite account number.
        - `NETSUITE_CONSUMER_KEY`: The consumer key for OAuth.
        - `NETSUITE_CONSUMER_SECRET`: The consumer secret for OAuth.
        - `NETSUITE_TOKEN_ID`: The token ID for OAuth.
        - `NETSUITE_TOKEN_SECRET`: The token secret for OAuth.
        - `NETSUITE_LOG_LEVEL`: log level for NetSuite debugging

        Returns a dictionary of available config options.
        """

        keys = [
            "auth_type",
            "account",
            "consumer_key",
            "consumer_secret",
            "token_id",
            "token_secret",
            "log_level",
        ]
        prefix = "NETSUITE_"
        raw = {
            k: os.environ[prefix + k.upper()]
            for k in keys
            if prefix + k.upper() in os.environ
        }

        reorganized = cls._reorganize_auth_keys(raw)
        return cls(**reorganized)

    @classmethod
    def from_ini(
        cls, path: str = DEFAULT_INI_PATH, section: str = DEFAULT_INI_SECTION
    ) -> "Config":
        iniconf = configparser.ConfigParser()
        with open(path) as fp:
            iniconf.read_file(fp)

        selected_configuration = iniconf[section]

        auth_type = selected_configuration.get("auth_type", "token")
        if auth_type != "token":
            raise RuntimeError(f"Only token auth is supported, not `{auth_type}`")

        raw = {key: val for key, val in selected_configuration.items()}
        reorganized = cls._reorganize_auth_keys(raw)
        return cls(**reorganized)  # type: ignore
