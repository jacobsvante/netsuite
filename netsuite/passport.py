import base64
import hmac
import random
from datetime import datetime
from typing import Dict

import zeep

from .config import Config


class Passport:

    def get_element(self) -> str:
        raise NotImplementedError


class TokenPassport(Passport):

    def __init__(
        self,
        client: zeep.Client,
        *,
        account: str,
        consumer_key: str,
        consumer_secret: str,
        token_id: str,
        token_secret: str,
    ) -> None:
        self.client = client
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

    def _get_signature(self, nonce: str, timestamp: str) -> zeep.xsd.Element:
        TokenPassportSignature = self.client.get_type('{urn:core_2017_2.platform.webservices.netsuite.com}TokenPassportSignature')
        return TokenPassportSignature(
            self._get_signature_value(nonce, timestamp),
            algorithm='HMAC-SHA256',
        )

    def get_element(self) -> zeep.xsd.Element:
        TokenPassport = self.client.get_element('{urn:messages_2017_2.platform.webservices.netsuite.com}tokenPassport')
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()
        signature = self._get_signature(nonce, timestamp)
        return TokenPassport(
            account=self.account,
            consumerKey=self.consumer_key,
            token=self.token_id,
            nonce=nonce,
            timestamp=timestamp,
            signature=signature,
        )


def make(client: zeep.Client, config: Config) -> Dict[str, zeep.xsd.Element]:
    if 'password' in config:
        raise NotImplementedError
        # return {
        #     'passport': UsernamePassport(..),
        # }
    else:
        token_passport = TokenPassport(
            client,
            account=config.account,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            token_id=config.token_id,
            token_secret=config.token_secret,
        )
        return {'tokenPassport': token_passport.get_element()}
