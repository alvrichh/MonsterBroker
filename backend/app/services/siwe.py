"""Sign-In with Ethereum (EIP-4361): the backend issues a nonce inside a
human-readable message, the wallet signs it, we recover the address. No
password, no email needed."""

from __future__ import annotations

import re
import secrets
import time
from datetime import UTC, datetime

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import is_address, to_checksum_address

NONCE_TTL = 300  # seconds a message stays valid
STATEMENT = "Entra en MonsterBroker con tu wallet. Esta firma no cuesta gas ni mueve fondos."

_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$", re.MULTILINE)
_NONCE = re.compile(r"^Nonce: (\S+)$", re.MULTILINE)
_DOMAIN = re.compile(r"^(\S+) wants you to sign in with your Ethereum account:$", re.MULTILINE)


class SiweError(Exception):
    pass


class SiweService:
    def __init__(self, domain: str, uri: str, chain_id: int) -> None:
        self.domain, self.uri, self.chain_id = domain, uri, chain_id
        self._nonces: dict[str, tuple[str, float]] = {}  # address → (nonce, expires)

    def build_message(self, address: str, nonce: str) -> str:
        issued = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return (
            f"{self.domain} wants you to sign in with your Ethereum account:\n{address}\n\n"
            f"{STATEMENT}\n\n"
            f"URI: {self.uri}\nVersion: 1\nChain ID: {self.chain_id}\nNonce: {nonce}\nIssued At: {issued}"
        )

    def issue(self, address: str) -> str:
        if not is_address(address):
            raise SiweError("invalid address")
        address = to_checksum_address(address)
        nonce = secrets.token_urlsafe(12)
        self._nonces[address.lower()] = (nonce, time.time() + NONCE_TTL)
        self._sweep()
        return self.build_message(address, nonce)

    def verify(self, message: str, signature: str) -> str:
        """Returns the checksummed address that signed `message`, consuming its nonce."""
        domain = _DOMAIN.search(message)
        address = _ADDRESS.search(message)
        nonce = _NONCE.search(message)
        if not (domain and address and nonce):
            raise SiweError("malformed message")
        if domain.group(1) != self.domain:
            raise SiweError("wrong domain")
        expected = self._nonces.get(address.group(0).lower())
        if not expected or expected[0] != nonce.group(1):
            raise SiweError("unknown or reused nonce")
        if expected[1] < time.time():
            raise SiweError("message expired")
        try:
            signer = Account.recover_message(encode_defunct(text=message), signature=signature)
        except Exception as error:  # eth_account raises several concrete types
            raise SiweError("bad signature") from error
        if signer.lower() != address.group(0).lower():
            raise SiweError("signature does not match the address")
        del self._nonces[address.group(0).lower()]
        return to_checksum_address(signer)

    def _sweep(self) -> None:
        now = time.time()
        for key in [k for k, (_, exp) in self._nonces.items() if exp < now]:
            del self._nonces[key]
