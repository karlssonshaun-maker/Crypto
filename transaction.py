"""Build and verify signed IGN transactions."""

from wallet import Wallet, verify_signature


def create_transaction(sender_wallet: Wallet, recipient_address: str,
                       amount: float) -> dict:
    """
    Build a signed transaction ready to submit to the blockchain.
    The signature covers sender, recipient, and amount — preventing tampering.
    """
    tx_data = {
        "sender": sender_wallet.address,
        "recipient": recipient_address,
        "amount": amount,
    }
    signature = sender_wallet.sign(tx_data)
    return {
        **tx_data,
        "signature": signature,
        "public_key": sender_wallet.public_key,
    }


def verify_transaction(tx: dict) -> bool:
    """Return True if the transaction signature is valid."""
    if tx.get("sender") == "COINBASE":
        return True
    tx_data = {
        "sender": tx["sender"],
        "recipient": tx["recipient"],
        "amount": tx["amount"],
    }
    return verify_signature(tx["public_key"], tx_data, tx["signature"])
