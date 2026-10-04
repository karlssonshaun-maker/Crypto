"""IGNIS (IGN) — A self-consuming deflationary token with 4 burn phases."""

import hashlib
import json
import time
from typing import List

# ── Phase table (checked smallest-first; first match wins) ───────────────────
PHASES = [
    {"num": 4, "name": "EMBER",   "max_supply": 1_000_000,    "burn_rate": 0.00},
    {"num": 3, "name": "INFERNO", "max_supply": 10_000_000,   "burn_rate": 0.08},
    {"num": 2, "name": "BLAZE",   "max_supply": 50_000_000,   "burn_rate": 0.05},
    {"num": 1, "name": "SPARK",   "max_supply": float("inf"), "burn_rate": 0.03},
]

INITIAL_SUPPLY   = 100_000_000   # 100 M IGN minted at genesis
TREASURY_RATE    = 0.03          # 3 % of every tx goes to treasury
BURN_ADDRESS     = "IGN_BURN"
TREASURY_ADDRESS = "IGN_TREASURY"
GENESIS_SENDER   = "IGNIS_GENESIS"
VALIDATOR_REWARD = 0             # Fixed supply — no new tokens from mining


class Block:
    def __init__(self, index, transactions, previous_hash,
                 timestamp=None, nonce=0):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self):
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    def __repr__(self):
        return (f"Block(#{self.index} hash={self.hash[:10]}... "
                f"txns={len(self.transactions)} nonce={self.nonce})")


class Blockchain:
    DIFFICULTY = 4

    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(0, [], "0" * 64, timestamp=0.0)
        self.chain.append(genesis)

    @property
    def last_block(self):
        return self.chain[-1]

    # ── Genesis mint ─────────────────────────────────────────────────────────

    @property
    def genesis_minted(self) -> bool:
        """True if the initial 100M IGN supply has been issued."""
        for block in self.chain:
            for tx in block.transactions:
                if tx["sender"] == GENESIS_SENDER:
                    return True
        for tx in self.pending_transactions:
            if tx["sender"] == GENESIS_SENDER:
                return True
        return False

    def mint_genesis(self, founder_address: str) -> bool:
        """Mint the full initial supply to founder_address. One-time only."""
        if self.genesis_minted:
            return False
        self.pending_transactions.append({
            "sender":     GENESIS_SENDER,
            "recipient":  founder_address,
            "amount":     INITIAL_SUPPLY,
            "signature":  "GENESIS",
            "public_key": "",
        })
        return True

    # ── Supply & Phase ────────────────────────────────────────────────────────

    def get_circulating_supply(self) -> float:
        """INITIAL_SUPPLY minus all tokens sent to the burn address."""
        burned = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx["recipient"] == BURN_ADDRESS:
                    burned += tx["amount"]
        for tx in self.pending_transactions:
            if tx["recipient"] == BURN_ADDRESS:
                burned += tx["amount"]
        return INITIAL_SUPPLY - burned

    def get_phase(self) -> dict:
        supply = self.get_circulating_supply()
        for phase in PHASES:
            if supply <= phase["max_supply"]:
                return phase
        return PHASES[-1]  # SPARK (>50M)

    def get_treasury_balance(self) -> float:
        return self.get_balance(TREASURY_ADDRESS)

    # ── Mining / Validation ───────────────────────────────────────────────────

    def proof_of_work(self, block: Block) -> Block:
        target = "0" * self.DIFFICULTY
        block.nonce = 0
        block.hash = block.compute_hash()
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.compute_hash()
        return block

    def mine(self, validator_address: str) -> Block:
        """Confirm all pending transactions into a new block."""
        txns = list(self.pending_transactions)
        if VALIDATOR_REWARD > 0:
            txns.append({
                "sender":     "COINBASE",
                "recipient":  validator_address,
                "amount":     VALIDATOR_REWARD,
                "signature":  "COINBASE",
                "public_key": "",
            })
        block = Block(len(self.chain), txns, self.last_block.hash)
        block = self.proof_of_work(block)
        self.chain.append(block)
        self.pending_transactions.clear()
        return block

    # ── Transactions ──────────────────────────────────────────────────────────

    def add_transaction(self, tx: dict) -> bool:
        required = {"sender", "recipient", "amount", "signature", "public_key"}
        if not required.issubset(tx):
            return False
        if tx["amount"] <= 0:
            return False

        sender = tx["sender"]
        amount = tx["amount"]

        # Protocol senders bypass burn/treasury logic
        if sender in (GENESIS_SENDER, "COINBASE", BURN_ADDRESS, TREASURY_ADDRESS):
            self.pending_transactions.append(tx)
            return True

        # Balance check: sender must cover the full original amount
        if self.get_balance(sender) < amount:
            print(f"  Insufficient balance for {sender[:16]}...")
            return False

        phase           = self.get_phase()
        burn_amount     = round(amount * phase["burn_rate"], 8)
        treasury_amount = round(amount * TREASURY_RATE, 8)
        net_amount      = round(amount - burn_amount - treasury_amount, 8)

        if net_amount <= 0:
            print("  Transaction rejected: amount too small after fees.")
            return False

        # 1. Net transfer to recipient (annotated with fee breakdown)
        self.pending_transactions.append({
            **tx,
            "amount":    net_amount,
            "_burn":     burn_amount,
            "_treasury": treasury_amount,
            "_phase":    phase["name"],
        })

        # 2. Burn leg — removed from circulating supply
        if burn_amount > 0:
            self.pending_transactions.append({
                "sender":     sender,
                "recipient":  BURN_ADDRESS,
                "amount":     burn_amount,
                "signature":  "BURN",
                "public_key": "",
            })

        # 3. Treasury leg
        if treasury_amount > 0:
            self.pending_transactions.append({
                "sender":     sender,
                "recipient":  TREASURY_ADDRESS,
                "amount":     treasury_amount,
                "signature":  "TREASURY",
                "public_key": "",
            })

        return True

    # ── Balances ──────────────────────────────────────────────────────────────

    def get_balance(self, address: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx["recipient"] == address:
                    balance += tx["amount"]
                if tx["sender"] == address:
                    balance -= tx["amount"]
        for tx in self.pending_transactions:
            if tx["sender"] == address:
                balance -= tx["amount"]
        return balance

    # ── Validation ────────────────────────────────────────────────────────────

    def is_valid(self) -> bool:
        target = "0" * self.DIFFICULTY
        for i in range(1, len(self.chain)):
            cur, prev = self.chain[i], self.chain[i - 1]
            if cur.hash != cur.compute_hash():
                return False
            if cur.previous_hash != prev.hash:
                return False
            if not cur.hash.startswith(target):
                return False
        return True
