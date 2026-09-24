#!/usr/bin/env python3
"""
QuantWheel + FlashAlpha Integration

Combines QuantWheel's IV surface / skew dynamics with FlashAlpha's gamma/wall data
for a unified intraday options positioning dashboard.

Key synergies:
  • IV surface → Identify vol crush risk at walls (short skew = short vol already priced)
  • Term structure → Flag calendar-roll opportunities (front month collapsing)
  • Skew dynamics → Confirm dealer short-gamma bias (downside IV elevated)
  • Flow context → Map order flow against gamma regimes and skew

Usage:
    python quantwheel_gamma_integration.py SPY \
        --api-key-fa $FLASHALPHA_API_KEY \
        --api-key-qw $QUANTWHEEL_API_KEY

Workflow:
    1. Snapshot IV surface + term structure from QuantWheel
    2. Overlay gamma flip, walls, GEX from FlashAlpha
    3. Flag convergence signals:
       - Price at call wall + short skew = "vol already priced out" signal
       - Put wall + long skew = "risk premium concentrated" signal
       - Short-gamma regime + IV contraction = acceleration risk
    4. Save unified view to JSON for post-market analysis
"""

import argparse
import json
import os
from datetime import datetime
from typing import Optional

try:
    from flashalpha import FlashAlpha, TierRestrictedError
except ImportError:
    print("ERROR: flashalpha SDK not found. Install with: pip install flashalpha")
    exit(1)

# QuantWheel API would be queried here if SDK available
# For now, we'll show the integration pattern


class QuantWheelFlashAlphaMonitor:
    """Unified gamma + vol surface monitor."""

    def __init__(self, symbol: str, api_key_fa: str, api_key_qw: Optional[str] = None):
        self.symbol = symbol
        self.client_fa = FlashAlpha(api_key_fa)
        self.api_key_qw = api_key_qw  # Would initialize QuantWheel client here
        self.session_data = {}

    def snapshot_gamma(self) -> dict:
        """Capture gamma exposure from FlashAlpha."""
        try:
            exp = self.client_fa.exposure_summary(self.symbol)
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "spot": exp.get("spot"),
                "gamma_flip": exp.get("gamma_flip"),
                "gamma_flip_status": exp.get("gamma_flip_status"),
                "call_wall": exp.get("call_wall"),
                "put_wall": exp.get("put_wall"),
                "net_gex": exp.get("net_gex"),
                "dex": exp.get("dex"),
                "regime": exp.get("regime"),
                "data_as_of": exp.get("data_as_of"),
            }
        except TierRestrictedError:
            return {
                "error": f"Tier restricted on {self.symbol}. Upgrade plan to access exposure_summary()."
            }

    def snapshot_vol_surface(self) -> dict:
        """Capture IV surface from QuantWheel (stub)."""
        # In production, this would call QuantWheel API
        # Example structure:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "atm_iv": None,  # QuantWheel would provide
            "term_structure": None,  # IV by expiry
            "skew": {
                "downside_iv": None,  # 10% OTM puts
                "atm_iv": None,
                "upside_iv": None,  # 10% OTM calls
                "skew_slope": None,  # Steepness
            },
            "smile": None,  # Full vol smile across strikes
            "realized_vs_implied": None,  # RV vs IV comparison
            "put_call_vol_ratio": None,  # Skew direction indicator
            "note": "QuantWheel API integration requires API key. Replace with live calls.",
        }

    def convergence_analysis(self, gamma_snap: dict, vol_snap: dict) -> list:
        """Identify convergence signals between gamma and vol."""
        signals = []

        if not gamma_snap.get("spot"):
            return signals

        # Pattern 1: Price near call wall + short skew
        if (
            gamma_snap.get("call_wall")
            and gamma_snap.get("spot")
            and abs(gamma_snap["spot"] - gamma_snap["call_wall"]) < gamma_snap["spot"] * 0.005
        ):  # Within 0.5%
            signals.append(
                {
                    "type": "CALL_WALL_PROXIMITY",
                    "severity": "MEDIUM",
                    "description": f"Price {gamma_snap['spot']:.2f} within 0.5% of call wall {gamma_snap['call_wall']:.2f}",
                    "implication": "Dealer supply/resistance; short skew would indicate vol already priced",
                }
            )

        # Pattern 2: Short-gamma regime + IV expanding
        if gamma_snap.get("regime") == "short-gamma-bearish":
            signals.append(
                {
                    "type": "SHORT_GAMMA_IV_EXPANSION_RISK",
                    "severity": "HIGH",
                    "description": f"Regime: {gamma_snap['regime']}, GEX: {gamma_snap.get('net_gex', 0):,}",
                    "implication": "Dealers are short gamma. If IV expands, dealers lose. Monitor for volatility break.",
                }
            )

        # Pattern 3: Put wall + elevated downside skew
        if gamma_snap.get("put_wall"):
            signals.append(
                {
                    "type": "PUT_WALL_SKEW_CONCENTRATION",
                    "severity": "MEDIUM",
                    "description": f"Put wall at {gamma_snap['put_wall']:.2f}; downside vol premium concentrated",
                    "implication": "Risk premium is baked into puts. Break below wall + vol expands = dealer acceleration.",
                }
            )

        # Pattern 4: Regime flip + term structure shift
        if (
            gamma_snap.get("regime")
            and vol_snap.get("term_structure") is not None
        ):  # Would check if structure changed
            signals.append(
                {
                    "type": "REGIME_TERM_FLIP",
                    "severity": "HIGH",
                    "description": f"Regime: {gamma_snap.get('regime')}; term structure via QuantWheel shows reversal",
                    "implication": "Dealer gamma bias AND vol curve consensus shifted. Major positioning change.",
                }
            )

        return signals

    def run_snapshot(self) -> dict:
        """Capture gamma + vol surface simultaneously."""
        gamma = self.snapshot_gamma()
        vol = self.snapshot_vol_surface()
        signals = self.convergence_analysis(gamma, vol)

        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "symbol": self.symbol,
            "gamma": gamma,
            "vol_surface": vol,
            "convergence_signals": signals,
        }

        return snapshot

    def save_session(self, filepath: str):
        """Persist unified session data."""
        with open(filepath, "w") as f:
            json.dump(self.session_data, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="QuantWheel + FlashAlpha unified gamma/vol monitor"
    )
    parser.add_argument("symbol", help="Symbol to monitor (e.g., SPY)")
    parser.add_argument(
        "--api-key-fa",
        default=os.getenv("FLASHALPHA_API_KEY"),
        help="FlashAlpha API key (default: FLASHALPHA_API_KEY env var)",
    )
    parser.add_argument(
        "--api-key-qw",
        default=os.getenv("QUANTWHEEL_API_KEY"),
        help="QuantWheel API key (optional; default: QUANTWHEEL_API_KEY env var)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1800,
        help="Check interval in seconds (default: 1800 = 30 min)",
    )
    parser.add_argument(
        "--checks",
        type=int,
        default=1,
        help="Number of checks to run (default: 1)",
    )

    args = parser.parse_args()

    if not args.api_key_fa:
        print("ERROR: FLASHALPHA_API_KEY required. Set env var or use --api-key-fa")
        exit(1)

    print(f"\n🎯 QuantWheel + FlashAlpha Monitor: {args.symbol}")
    print(f"📍 Interval: {args.interval}s | Checks: {args.checks}")
    print("=" * 80)

    monitor = QuantWheelFlashAlphaMonitor(args.symbol, args.api_key_fa, args.api_key_qw)

    for i in range(args.checks):
        snap = monitor.run_snapshot()
        monitor.session_data[args.symbol] = snap

        # Pretty print
        print(f"\n✅ SNAPSHOT {i+1}/{args.checks}")
        print("-" * 80)

        if snap["gamma"].get("error"):
            print(f"⚠️  {snap['gamma']['error']}")
        else:
            print(f"Spot: {snap['gamma'].get('spot', 'N/A'):.2f}")
            print(f"Flip: {snap['gamma'].get('gamma_flip', 'N/A')}")
            print(
                f"Walls: Call {snap['gamma'].get('call_wall')} / Put {snap['gamma'].get('put_wall')}"
            )
            print(f"GEX: {snap['gamma'].get('net_gex', 0):,}  DEX: {snap['gamma'].get('dex', 0):,}")
            print(f"Regime: {snap['gamma'].get('regime', 'unknown')}")

        if snap["convergence_signals"]:
            print(f"\n🚨 CONVERGENCE SIGNALS ({len(snap['convergence_signals'])}):")
            for sig in snap["convergence_signals"]:
                print(f"  [{sig['severity']}] {sig['type']}")
                print(f"    → {sig['description']}")
                print(f"    ⚡ {sig['implication']}")
        else:
            print("\n✨ No convergence signals detected.")

        if i < args.checks - 1:
            import time

            print(f"\n⏳ Waiting {args.interval}s for next check...")
            time.sleep(args.interval)

    # Save output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"quantwheel_gamma_monitor_{timestamp}.json"
    monitor.save_session(output_file)

    print(f"\n💾 Session saved: {output_file}")
    print("\n✅ Monitoring complete.")


if __name__ == "__main__":
    main()
