// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title  IGNIS (IGN)
 * @notice Self-consuming deflationary token — the serpent that devours its own tail.
 *
 *  Phase     Circulating Supply   Burn/tx   Treasury/tx
 *  -------------------------------------------------------
 *  SPARK     > 50 M IGN           3 %       3 %
 *  BLAZE     10 M – 50 M IGN      5 %       3 %
 *  INFERNO   1 M  – 10 M IGN      8 %       3 %
 *  EMBER     < 1 M IGN            0 %       3 %  (stable)
 *
 * Every transfer automatically:
 *   1. Burns a phase-dependent % of the amount (reducing totalSupply).
 *   2. Routes 3 % to the treasury address.
 *   3. Delivers the remainder to the recipient.
 *
 * As supply shrinks the burn rate escalates, accelerating deflation until
 * the EMBER phase where burning stops and the token stabilises.
 */
contract IGNIS is ERC20, Ownable {

    // ── Supply ────────────────────────────────────────────────────────────────

    uint256 public constant INITIAL_SUPPLY = 100_000_000 * 10 ** 18; // 100 M IGN

    // ── Phase thresholds (in wei) ─────────────────────────────────────────────

    uint256 public constant EMBER_THRESHOLD   =  1_000_000 * 10 ** 18;
    uint256 public constant INFERNO_THRESHOLD = 10_000_000 * 10 ** 18;
    uint256 public constant BLAZE_THRESHOLD   = 50_000_000 * 10 ** 18;

    // ── Rates (integer percent, e.g. 3 = 3%) ─────────────────────────────────

    uint256 public constant SPARK_BURN_RATE   = 3;
    uint256 public constant BLAZE_BURN_RATE   = 5;
    uint256 public constant INFERNO_BURN_RATE = 8;
    uint256 public constant EMBER_BURN_RATE   = 0;
    uint256 public constant TREASURY_RATE     = 3; // constant across all phases

    // ── State ─────────────────────────────────────────────────────────────────

    address public treasury;

    // ── Events ────────────────────────────────────────────────────────────────

    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    event PhaseEntered(Phase phase, uint256 supply);

    // ── Enums ─────────────────────────────────────────────────────────────────

    enum Phase { SPARK, BLAZE, INFERNO, EMBER }

    Phase private _lastPhase;

    // ── Constructor ───────────────────────────────────────────────────────────

    /**
     * @param _treasury Address that receives the 3 % treasury fee on every transfer.
     *                  Can be a multisig, DAO contract, or EOA.
     */
    constructor(address _treasury) ERC20("IGNIS", "IGN") Ownable(msg.sender) {
        require(_treasury != address(0), "IGNIS: zero treasury address");
        treasury   = _treasury;
        _lastPhase = Phase.SPARK;
        _mint(msg.sender, INITIAL_SUPPLY);
    }

    // ── Phase view helpers ────────────────────────────────────────────────────

    /// @notice Returns the current burn phase based on circulating supply.
    function currentPhase() public view returns (Phase) {
        uint256 supply = totalSupply();
        if (supply <= EMBER_THRESHOLD)   return Phase.EMBER;
        if (supply <= INFERNO_THRESHOLD) return Phase.INFERNO;
        if (supply <= BLAZE_THRESHOLD)   return Phase.BLAZE;
        return Phase.SPARK;
    }

    /// @notice Returns the burn rate (%) for the current phase.
    function currentBurnRate() public view returns (uint256) {
        Phase phase = currentPhase();
        if (phase == Phase.EMBER)   return EMBER_BURN_RATE;
        if (phase == Phase.INFERNO) return INFERNO_BURN_RATE;
        if (phase == Phase.BLAZE)   return BLAZE_BURN_RATE;
        return SPARK_BURN_RATE;
    }

    /// @notice Human-readable name of the current phase.
    function currentPhaseName() external view returns (string memory) {
        Phase phase = currentPhase();
        if (phase == Phase.EMBER)   return "EMBER";
        if (phase == Phase.INFERNO) return "INFERNO";
        if (phase == Phase.BLAZE)   return "BLAZE";
        return "SPARK";
    }

    // ── Transfer hook ─────────────────────────────────────────────────────────

    /**
     * @dev Overrides ERC-20 internal _update to inject burn + treasury logic.
     *      Mint (from == 0) and direct burns (to == 0) bypass fee logic.
     */
    function _update(address from, address to, uint256 value) internal override {
        // Mint and direct burn operations bypass fee logic
        if (from == address(0) || to == address(0)) {
            super._update(from, to, value);
            _emitPhaseChangeIfNeeded();
            return;
        }

        uint256 burnRate_     = currentBurnRate();
        uint256 burnAmount    = (value * burnRate_)    / 100;
        uint256 treasuryAmount = (value * TREASURY_RATE) / 100;
        uint256 netAmount     = value - burnAmount - treasuryAmount;

        require(netAmount > 0, "IGNIS: amount too small after fees");

        // 1. Net amount to recipient
        super._update(from, to, netAmount);

        // 2. Burn — reduces totalSupply, may trigger a phase transition
        if (burnAmount > 0) {
            super._update(from, address(0), burnAmount);
            _emitPhaseChangeIfNeeded();
        }

        // 3. Treasury fee
        if (treasuryAmount > 0) {
            super._update(from, treasury, treasuryAmount);
        }
    }

    /// @dev Emits PhaseEntered if the phase changed after a burn.
    function _emitPhaseChangeIfNeeded() internal {
        Phase newPhase = currentPhase();
        if (newPhase != _lastPhase) {
            _lastPhase = newPhase;
            emit PhaseEntered(newPhase, totalSupply());
        }
    }

    // ── Admin ─────────────────────────────────────────────────────────────────

    /// @notice Update the treasury address. Only callable by owner.
    function setTreasury(address _treasury) external onlyOwner {
        require(_treasury != address(0), "IGNIS: zero treasury address");
        emit TreasuryUpdated(treasury, _treasury);
        treasury = _treasury;
    }
}
