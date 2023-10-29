import configparser
import os
import typing as t

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
    log_level: t.Optional[str] = None

    # TODO: Support OAuth2
    # auth: Union[OAuth2, TokenAuth]

    @property
    def account_slugified(self) -> str:
        # https://followingnetsuite.wordpress.com/2018/10/18/suitetalk-sandbox-urls-addendum/
        return self.account.lower().replace("_", "-")

    @staticmethod
    def _reorganize_auth_keys(raw: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        # we intentionally do not type `reorganized` here, mypy does not like union types with dict key assignment
        # https://stackoverflow.com/questions/69824126/mypy-invalid-index-type-str-for-unionstr-dictstr-str-expected-type-u

        reorganized: t.Dict[t.Any, t.Any] = {"auth": {}}

        for key, val in raw.items():
            if key in TokenAuth.model_fields:
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
