import typing
from functools import cached_property

import pyodbc

from .config import Config


class NetSuiteODBC:
    def __init__(self, config: Config):
        if not config.is_password_auth:
            raise RuntimeError(
                "Only username/password auth is supported for ODBC connections."
            )

        self._config = config

    @cached_property
    def hostname(self) -> str:
        return f"{self._config.account_slugified}.connect.api.netsuite.com"

    @cached_property
    def _connection_string(self) -> str:
        return (
            f"DRIVER={self._config.odbc_driver};"
            f"Host={self.hostname};"
            "Port=1708;"
            "Encrypted=1;"
            "AllowSinglePacketLogout=1;"
            "Truststore=system;"
            f"ServerDataSource={self._config.odbc_data_source};"
            f"UID={self._config.auth.username};"
            f"PWD={self._config.auth.password};"
            "CustomProperties="
            f"AccountID={self._config.account};"
            f"RoleID={self._config.auth.role}"
        )

    def connect(self) -> pyodbc.Connection:
        """
        Connects to the ODBC database and returns the connection object

        :return: pyodbc.Connection
        """
        return pyodbc.connect(self._connection_string)

    def execute(self, sql: str) -> pyodbc.Cursor:
        """
        Executes the SQL statement and returns the pyodbc cursor object

        :param sql:
        :return: pyodbc.Cursor
        """
        with self.connect() as connection:
            cursor = connection.cursor()
            return cursor.execute(sql)

    def query(self, sql: str) -> list[dict[str, typing.Any]]:
        """
        Executes the SQL statement and returns the results as a list of dicts
        :param sql:
        :return: list[dict[str, any]]
        """
        with self.connect() as connection:
            cursor = connection.cursor()
            response = cursor.execute(sql)
            headers = [col[0] for col in response.description]
            results = [
                dict(zip(headers, row)) for i, row in enumerate(response.fetchall())
            ]
            return results
