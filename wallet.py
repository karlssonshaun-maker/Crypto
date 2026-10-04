"""ECDSA wallet: key generation, signing, verification, addresses."""

import hashlib
import binascii
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError


def generate_keypair():
    """Return (private_key_hex, public_key_hex)."""
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()
    return sk.to_string().hex(), vk.to_string().hex()


def public_key_to_address(public_key_hex: str) -> str:
    """Derive a wallet address from a public key (like Bitcoin's approach)."""
    pub_bytes = bytes.fromhex(public_key_hex)
    sha256 = hashlib.sha256(pub_bytes).digest()
    ripemd = hashlib.new("ripemd160", sha256).digest()
    # Add version byte and encode
    versioned = b"\x00" + ripemd
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    return _b58encode(versioned + checksum)


def sign_transaction(private_key_hex: str, tx_data: dict) -> str:
    """Sign a transaction dict and return the signature hex."""
    import json
    sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    message = json.dumps(tx_data, sort_keys=True).encode()
    signature = sk.sign(message)
    return signature.hex()


def verify_signature(public_key_hex: str, tx_data: dict, signature_hex: str) -> bool:
    """Verify a transaction signature. Returns True if valid."""
    import json
    try:
        vk = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
        message = json.dumps(tx_data, sort_keys=True).encode()
        return vk.verify(bytes.fromhex(signature_hex), message)
    except (BadSignatureError, Exception):
        return False


# ── Base58 encoding ───────────────────────────────────────────────────

_BASE58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def _b58encode(data: bytes) -> str:
    count = 0
    for byte in data:
        if byte == 0:
            count += 1
        else:
            break
    num = int.from_bytes(data, "big")
    result = []
    while num > 0:
        num, rem = divmod(num, 58)
        result.append(_BASE58_ALPHABET[rem:rem + 1])
    result.extend([_BASE58_ALPHABET[0:1]] * count)
    return b"".join(reversed(result)).decode("ascii")


class Wallet:
    def __init__(self, private_key_hex: str = None):
        if private_key_hex:
            sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.private_key = private_key_hex
            self.public_key = sk.get_verifying_key().to_string().hex()
        else:
            self.private_key, self.public_key = generate_keypair()
        self.address = public_key_to_address(self.public_key)

    def sign(self, tx_data: dict) -> str:
        return sign_transaction(self.private_key, tx_data)

    def __repr__(self):
        return f"Wallet(address={self.address})"
