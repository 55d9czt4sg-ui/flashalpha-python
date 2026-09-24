#!/usr/bin/env python3
"""
Intraday Gamma/Wall Monitor for SPY & QQQ

Records opening gamma flip, call/put walls, GEX during market hours.
Flags material changes (flip ±0.25-0.50% of spot, walls ≥1 strike, regime flips).
Correlates price behavior with walls and GEX.
Prepares volume/OI classification for next-day analysis.

Usage:
    python intraday_gamma_monitor.py [--symbols SPY,QQQ] [--interval 1800] [--api-key YOUR_KEY]

Requires: pip install flashalpha
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from flashalpha import FlashAlpha, TierRestrictedError
except ImportError:
    print("ERROR: flashalpha not installed. Run: pip install flashalpha")
    sys.exit(1)


class GammaMonitor:
    def __init__(self, api_key: str, symbols: list, check_interval: int = 1800):
        """
        Args:
            api_key: FlashAlpha API key
            symbols: List of symbols to monitor (e.g., ["SPY", "QQQ"])
            check_interval: Seconds between checks (default 30 min)
        """
        self.client = FlashAlpha(api_key)
        self.symbols = symbols
        self.check_interval = check_interval
        self.session_data = {}
        self.output_file = Path(f"gamma_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    def capture_snapshot(self, symbol: str, label: str) -> Optional[dict]:
        """Capture current gamma exposure snapshot."""
        try:
            exp = self.client.exposure_summary(symbol)
            
            # Handle gamma_flip null/unavailable
            flip_value = exp.get("gamma_flip")
            flip_status = exp.get("gamma_flip_status", "unknown")
            if flip_status != "available":
                flip_value = None
            
            return {
                "timestamp": datetime.now().isoformat(),
                "label": label,
                "symbol": symbol,
                "data_as_of": exp.get("data_as_of"),  # Feed freshness
                "spot": exp.get("spot"),
                "gamma_flip": flip_value,
                "gamma_flip_status": flip_status,
                "call_wall": exp.get("call_wall"),
                "put_wall": exp.get("put_wall"),
                "net_gex": exp.get("net_gex"),
                "dex": exp.get("dex"),
                "regime": exp.get("regime"),
                "hedging_estimate": exp.get("hedging_estimate", {}),
            }
        except TierRestrictedError:
            print(f"⚠️  {symbol}: Tier restricted. Upgrade your FlashAlpha plan for exposure_summary().")
            return None
        except Exception as e:
            print(f"❌ {symbol}: Error capturing snapshot: {e}")
            return None

    def check_material_change(self, prev: dict, curr: dict, threshold_pct: float = 0.35) -> tuple:
        """
        Detect meaningful changes in gamma map.
        
        Returns: (list of changes, spot_move_pct)
        """
        if not prev or not curr:
            return [], 0.0

        spot_move_pct = abs(curr["spot"] - prev["spot"]) / prev["spot"] * 100 if prev["spot"] else 0
        changes = []

        # Flip movement: 0.25-0.50% of spot
        if prev["gamma_flip"] and curr["gamma_flip"]:
            flip_move_pct = abs(curr["gamma_flip"] - prev["gamma_flip"]) / prev["spot"] * 100
            if flip_move_pct >= threshold_pct:
                direction = "↑" if curr["gamma_flip"] > prev["gamma_flip"] else "↓"
                changes.append(
                    f"🎯 FLIP: {prev['gamma_flip']:.2f} → {curr['gamma_flip']:.2f} "
                    f"({flip_move_pct:.2f}% of spot) {direction}"
                )

        # Call wall movement (≥1 strike increment)
        if prev["call_wall"] and curr["call_wall"]:
            wall_move = abs(curr["call_wall"] - prev["call_wall"])
            if wall_move >= 1.0:
                direction = "↑" if curr["call_wall"] > prev["call_wall"] else "↓"
                changes.append(f"📍 CALL_WALL: {prev['call_wall']:.2f} → {curr['call_wall']:.2f} {direction}")

        # Put wall movement
        if prev["put_wall"] and curr["put_wall"]:
            wall_move = abs(curr["put_wall"] - prev["put_wall"])
            if wall_move >= 1.0:
                direction = "↑" if curr["put_wall"] > prev["put_wall"] else "↓"
                changes.append(f"📍 PUT_WALL: {prev['put_wall']:.2f} → {curr['put_wall']:.2f} {direction}")

        # Regime flip
        if prev["regime"] and curr["regime"] and prev["regime"] != curr["regime"]:
            changes.append(f"⚡ REGIME: {prev['regime']} → {curr['regime']}")

        # GEX sign flip
        prev_gex_sign = 1 if (prev.get("net_gex") or 0) > 0 else -1
        curr_gex_sign = 1 if (curr.get("net_gex") or 0) > 0 else -1
        if prev_gex_sign != curr_gex_sign:
            changes.append(
                f"💥 NET_GEX SIGN FLIP: {prev['net_gex']:.0f} → {curr['net_gex']:.0f}"
            )

        return changes, spot_move_pct

    def correlate_price_action(self, prev: dict, curr: dict) -> list:
        """Flag price behavior at walls."""
        alerts = []

        if not prev or not curr:
            return alerts

        spot_moved_up = curr["spot"] > prev["spot"]
        spot_moved_down = curr["spot"] < prev["spot"]

        # Price touching/above call wall (resistance test)
        if spot_moved_up and prev["call_wall"] and curr["spot"] >= prev["call_wall"] * 0.995:
            alerts.append(
                f"🚧 CALL_WALL TEST: Price {curr['spot']:.2f} at/near wall {prev['call_wall']:.2f} "
                f"(dealer supply/resistance?)"
            )

        # Price breaking below put wall (support failure)
        if spot_moved_down and prev["put_wall"] and curr["spot"] <= prev["put_wall"] * 1.005:
            gex_status = "SHORT-GAMMA" if (curr.get("net_gex") or 0) < 0 else "LONG-GAMMA"
            alerts.append(
                f"⚠️  PUT_WALL BREAK: Price {curr['spot']:.2f} below wall {prev['put_wall']:.2f} "
                f"({gex_status} regime) → Watch IV expansion"
            )

        return alerts

    def save_session(self):
        """Save session data to JSON for post-market analysis."""
        with open(self.output_file, "w") as f:
            json.dump(self.session_data, f, indent=2)
        print(f"\n📊 Session data saved to {self.output_file}")

    def run(self, max_checks: int = 12):
        """
        Run monitoring loop.
        
        Args:
            max_checks: Maximum checks before stopping (default 12 ≈ 6 hours)
        """
        print(f"🎯 Starting Gamma Monitor ({', '.join(self.symbols)})")
        print(f"📍 Check interval: {self.check_interval}s ({self.check_interval//60}m)")
        print(f"💾 Output: {self.output_file}\n")

        # Initialize session
        for symbol in self.symbols:
            self.session_data[symbol] = {
                "snapshots": [],
                "material_changes": [],
                "price_action_alerts": [],
            }

        # OPENING SNAPSHOT
        print("=" * 70)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 OPENING SNAPSHOT")
        print("=" * 70)

        for symbol in self.symbols:
            snap = self.capture_snapshot(symbol, "open")
            if snap:
                self.session_data[symbol]["snapshots"].append(snap)
                print(
                    f"\n{symbol}:\n"
                    f"  Spot: {snap['spot']:.2f}\n"
                    f"  Flip: {snap['gamma_flip']:.2f if snap['gamma_flip'] else 'N/A'}\n"
                    f"  Walls: Call {snap['call_wall']:.2f} / Put {snap['put_wall']:.2f}\n"
                    f"  GEX: {snap['net_gex']:.0f}  DEX: {snap['dex']:.0f}\n"
                    f"  Regime: {snap['regime']}\n"
                    f"  Data as of: {snap['data_as_of']}"
                )

        self.save_session()

        # PERIODIC CHECKS
        for check_num in range(1, max_checks + 1):
            print("\n" + "=" * 70)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CHECK {check_num} (Interval {check_num * self.check_interval // 60}m)")
            print("=" * 70)

            for symbol in self.symbols:
                prev = self.session_data[symbol]["snapshots"][-1] if self.session_data[symbol]["snapshots"] else None
                curr = self.capture_snapshot(symbol, f"check_{check_num}")

                if not curr:
                    continue

                self.session_data[symbol]["snapshots"].append(curr)

                # Material changes
                changes, spot_move = self.check_material_change(prev, curr)
                if changes:
                    print(f"\n{symbol} — MATERIAL CHANGES:")
                    print(f"  Spot moved: {spot_move:.2f}%")
                    for change in changes:
                        print(f"  {change}")
                        self.session_data[symbol]["material_changes"].append({
                            "timestamp": curr["timestamp"],
                            "change": change,
                            "spot_move_pct": spot_move,
                        })
                else:
                    print(f"\n{symbol}: No material changes. (Spot: {curr['spot']:.2f}, Regime: {curr['regime']})")

                # Price action
                alerts = self.correlate_price_action(prev, curr)
                if alerts:
                    for alert in alerts:
                        print(f"  {alert}")
                        self.session_data[symbol]["price_action_alerts"].append({
                            "timestamp": curr["timestamp"],
                            "alert": alert,
                        })

            self.save_session()

        print("\n" + "=" * 70)
        print("✅ Monitoring complete. Session saved.")
        print(f"📝 Next step: Compare today's volume with tomorrow's OI (after 8:00 AM ET)")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Intraday Gamma/Wall Monitor for options flow analysis"
    )
    parser.add_argument(
        "--symbols",
        default="SPY,QQQ",
        help="Comma-separated symbols to monitor (default: SPY,QQQ)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1800,
        help="Seconds between checks (default: 1800 = 30 min)",
    )
    parser.add_argument(
        "--api-key",
        help="FlashAlpha API key (or set FLASHALPHA_API_KEY env var)",
    )
    parser.add_argument(
        "--checks",
        type=int,
        default=12,
        help="Max number of checks before stopping (default: 12)",
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.getenv("FLASHALPHA_API_KEY")
        if not api_key:
            print("ERROR: No API key provided. Set --api-key or FLASHALPHA_API_KEY env var")
            sys.exit(1)

    # Parse symbols
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    # Run monitor
    monitor = GammaMonitor(api_key, symbols, check_interval=args.interval)
    monitor.run(max_checks=args.checks)


if __name__ == "__main__":
    main()
