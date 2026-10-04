"""
IGNIS (IGN) — self-consuming deflationary token node CLI.

Usage:
    python node.py
"""

from blockchain import (Blockchain, PHASES, INITIAL_SUPPLY,
                        BURN_ADDRESS, TREASURY_ADDRESS, VALIDATOR_REWARD)
from wallet import Wallet
from transaction import create_transaction, verify_transaction

W = 62  # banner/separator width


def print_banner():
    print("=" * W)
    print("  ██╗ ██████╗ ███╗   ██╗██╗███████╗")
    print("  ██║██╔════╝ ████╗  ██║██║██╔════╝")
    print("  ██║██║  ███╗██╔██╗ ██║██║███████╗")
    print("  ██║██║   ██║██║╚██╗██║██║╚════██║")
    print("  ██║╚██████╔╝██║ ╚████║██║███████║")
    print("  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚══════╝")
    print()
    print("       The Serpent Token  |  IGN")
    print("  The serpent that devours its own tail.")
    print("=" * W)


def sep(char="-"):
    print(char * W)


def fmt(amount: float) -> str:
    return f"{amount:>18,.4f} IGN"


def show_phase_status(chain: Blockchain):
    phase  = chain.get_phase()
    supply = chain.get_circulating_supply()
    burned = INITIAL_SUPPLY - supply
    bar_pct = max(0.0, min(1.0, supply / INITIAL_SUPPLY))
    filled  = int(bar_pct * 30)
    bar     = "[" + "#" * filled + "." * (30 - filled) + "]"
    print(f"  {bar}  {supply/1_000_000:.2f}M IGN")
    print(f"  Phase    : {phase['num']}. {phase['name']}"
          f"  |  Burn/tx: {phase['burn_rate']*100:.0f}%"
          f"  |  Treasury/tx: 3%")
    print(f"  Burned   : {burned:,.4f} IGN total")


def main():
    print_banner()
    chain   = Blockchain()
    wallets = {}

    print("\nCommands:")
    print("  new_wallet  genesis   wallets   send   mine")
    print("  balance     phase     supply    chain  validate  quit\n")

    while True:
        try:
            cmd = input("ignis> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if cmd == "quit":
            print("Bye!")
            break

        # ── new_wallet ──────────────────────────────────────────────────────
        elif cmd == "new_wallet":
            name = input("  Wallet name: ").strip()
            if name in wallets:
                print(f"  Wallet '{name}' already exists.")
            else:
                w = Wallet()
                wallets[name] = w
                print(f"  Created  : {name}")
                print(f"  Address  : {w.address}")
                print(f"  Pub key  : {w.public_key[:32]}...")

        # ── genesis ─────────────────────────────────────────────────────────
        elif cmd == "genesis":
            if chain.genesis_minted:
                print("  Genesis supply already minted.")
            elif not wallets:
                print("  Create a wallet first to receive the genesis supply.")
            else:
                names = ", ".join(wallets.keys())
                name  = input(f"  Send {INITIAL_SUPPLY:,} IGN to ({names}): ").strip()
                if name not in wallets:
                    print(f"  Unknown wallet '{name}'.")
                else:
                    chain.mint_genesis(wallets[name].address)
                    print(f"  {INITIAL_SUPPLY:,} IGN queued for '{name}'.")
                    print("  Run 'mine' to confirm the genesis block.")

        # ── wallets ─────────────────────────────────────────────────────────
        elif cmd == "wallets":
            if not wallets:
                print("  No wallets yet. Use 'new_wallet'.")
            else:
                sep()
                for name, w in wallets.items():
                    bal = chain.get_balance(w.address)
                    print(f"  {name:12s}  {w.address}  {fmt(bal)}")
                sep()

        # ── send ────────────────────────────────────────────────────────────
        elif cmd == "send":
            sender_name = input("  From wallet: ").strip()
            if sender_name not in wallets:
                print(f"  Unknown wallet '{sender_name}'.")
                continue

            recipient_name = input("  To wallet (name or address): ").strip()
            recipient_addr = (wallets[recipient_name].address
                              if recipient_name in wallets else recipient_name)

            try:
                amount = float(input("  Amount (IGN): "))
            except ValueError:
                print("  Invalid amount.")
                continue

            phase      = chain.get_phase()
            burn_amt   = round(amount * phase["burn_rate"], 4)
            tsy_amt    = round(amount * 0.03, 4)
            net_amt    = round(amount - burn_amt - tsy_amt, 4)

            sep()
            print(f"  Phase     : {phase['num']}. {phase['name']}")
            print(f"  Sending   :{fmt(amount)}")
            print(f"  Recipient :{fmt(net_amt)}")
            print(f"  Burned    :{fmt(burn_amt)}  ({phase['burn_rate']*100:.0f}%)")
            print(f"  Treasury  :{fmt(tsy_amt)}  (3%)")
            sep()

            tx = create_transaction(wallets[sender_name], recipient_addr, amount)
            if not verify_transaction(tx):
                print("  ERROR: Signature verification failed.")
                continue
            if chain.add_transaction(tx):
                print("  Transaction queued. Run 'mine' to confirm.")
            else:
                print("  Transaction rejected (check balance).")

        # ── mine ────────────────────────────────────────────────────────────
        elif cmd == "mine":
            if not wallets:
                print("  Create a wallet first.")
                continue
            names      = ", ".join(wallets.keys())
            miner_name = input(f"  Validator wallet ({names}): ").strip()
            if miner_name not in wallets:
                print(f"  Unknown wallet '{miner_name}'.")
                continue

            pending = len(chain.pending_transactions)
            print(f"  Confirming {pending} pending transaction(s)... ",
                  end="", flush=True)
            block = chain.mine(wallets[miner_name].address)
            print("done!")
            print(f"  {block}")
            sep()
            show_phase_status(chain)
            sep()

        # ── balance ─────────────────────────────────────────────────────────
        elif cmd == "balance":
            name = input("  Wallet name: ").strip()
            if name not in wallets:
                print(f"  Unknown wallet '{name}'.")
            else:
                bal = chain.get_balance(wallets[name].address)
                print(f"  {name}:{fmt(bal)}")

        # ── phase ───────────────────────────────────────────────────────────
        elif cmd == "phase":
            current = chain.get_phase()
            sep()
            show_phase_status(chain)
            sep()
            print("  All phases:")
            for p in PHASES:
                tag    = " <-- current" if p["name"] == current["name"] else ""
                supply_label = (f"<{p['max_supply']//1_000_000}M"
                                if p["max_supply"] != float("inf")
                                else ">50M")
                print(f"    {p['num']}. {p['name']:8s}  "
                      f"supply {supply_label:8s}  "
                      f"burn {p['burn_rate']*100:.0f}%{tag}")
            sep()

        # ── supply ──────────────────────────────────────────────────────────
        elif cmd == "supply":
            supply = chain.get_circulating_supply()
            burned = INITIAL_SUPPLY - supply
            tsy    = chain.get_treasury_balance()
            sep()
            print(f"  Initial supply  :{fmt(INITIAL_SUPPLY)}")
            print(f"  Total burned    :{fmt(burned)}")
            print(f"  Treasury held   :{fmt(tsy)}")
            print(f"  Circulating     :{fmt(supply)}")
            sep()
            show_phase_status(chain)
            sep()

        # ── chain ───────────────────────────────────────────────────────────
        elif cmd == "chain":
            print(f"  Chain length: {len(chain.chain)} blocks")
            sep()
            for block in chain.chain:
                print(f"  {block}")
                for tx in block.transactions:
                    s = tx["sender"]
                    r = tx["recipient"]
                    s_lbl = s[:16] if len(s) > 16 else s
                    r_lbl = r[:16] if len(r) > 16 else r
                    note = ""
                    if r == BURN_ADDRESS:
                        note = "  [BURN]"
                    elif r == TREASURY_ADDRESS:
                        note = "  [TREASURY]"
                    print(f"    {s_lbl:16s} -> {r_lbl:16s}  "
                          f"{tx['amount']:>16,.4f} IGN{note}")
                sep()

        # ── validate ────────────────────────────────────────────────────────
        elif cmd == "validate":
            if chain.is_valid():
                print("  Chain is VALID.")
            else:
                print("  Chain is INVALID — tampering detected!")

        else:
            print("  Unknown command. Try: new_wallet | genesis | wallets |")
            print("  send | mine | balance | phase | supply | chain | validate | quit")


if __name__ == "__main__":
    main()
