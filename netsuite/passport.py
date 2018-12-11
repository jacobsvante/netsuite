import base64
import hmac
import random
from datetime import datetime
from typing import Dict, TypeVar

from zeep.xsd.valueobjects import CompoundValue

from .config import Config

NetSuite = TypeVar('NetSuite')


class Passport:

    def get_element(self) -> str:
        raise NotImplementedError


class UserCredentialsPassport(Passport):

    def __init__(
        self,
        ns: NetSuite,
        *,
        account: str,
        email: str,
        password: str
    ) -> None:
        self.ns = ns
        self.account = account
        self.email = email
        self.password = password

    def get_element(self) -> CompoundValue:
        return self.ns.Core.Passport(
            account=self.account,
            email=self.email,
            password=self.password,
        )


class TokenPassport(Passport):

    def __init__(
        self,
        ns: NetSuite,
        *,
        account: str,
        consumer_key: str,
        consumer_secret: str,
        token_id: str,
        token_secret: str
    ) -> None:
        self.ns = ns
        self.account = account
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.token_id = token_id
        self.token_secret = token_secret

    def _generate_timestamp(self) -> str:
        """Generate timestamp

        Returns:
            str: A seconds precision timestamp
        """
        return str(int(datetime.now().timestamp()))

    def _generate_nonce(self, length: int = 20) -> str:
        """Generate pseudorandom number"""
        return ''.join([str(random.randint(0, 9)) for i in range(length)])

    def _get_signature_message(self, nonce: str, timestamp: str) -> str:
        return '&'.join((
            self.account,
            self.consumer_key,
            self.token_id,
            nonce,
            timestamp,
        ))

    def _get_signature_key(self) -> str:
        return '&'.join((self.consumer_secret, self.token_secret))

    def _get_signature_value(self, nonce: str, timestamp: str) -> str:
        key = self._get_signature_key()
        message = self._get_signature_message(nonce, timestamp)
        hashed = hmac.new(
            key=key.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod='sha256'
        ).digest()
        return base64.b64encode(hashed).decode()

    def _get_signature(self, nonce: str, timestamp: str) -> CompoundValue:
        return self.ns.Core.TokenPassportSignature(
            self._get_signature_value(nonce, timestamp),
            algorithm='HMAC-SHA256',
        )

    def get_element(self) -> CompoundValue:
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()
        signature = self._get_signature(nonce, timestamp)
        return self.ns.Core.TokenPassport(
            account=self.account,
            consumerKey=self.consumer_key,
            token=self.token_id,
            nonce=nonce,
            timestamp=timestamp,
            signature=signature,
        )


def make(ns: NetSuite, config: Config) -> Dict:
    if config.auth_type == 'token':
        token_passport = TokenPassport(
            ns,
            account=config.account,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            token_id=config.token_id,
            token_secret=config.token_secret,
        )
        return {'tokenPassport': token_passport.get_element()}
    elif config.auth_type == 'credentials':
        passport = UserCredentialsPassport(
            ns,
            account=config.account,
            email=config.email,
            password=config.password,
        )
        return {
            'applicationInfo': {
                'applicationId': config.application_id,
            },
            'passport': passport.get_element(),
        }
    else:
        raise NotImplementedError(f'config.auth_type={config.auth_type}')
