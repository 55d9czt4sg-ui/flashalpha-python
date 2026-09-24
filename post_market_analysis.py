#!/usr/bin/env python3
"""
Post-Market OI/Volume Analysis

After market close and OCC open-interest update (∼8 AM ET next day):
  1. Load intraday session JSON
  2. Compare today's volume with OI change (today vs yesterday)
  3. Classify activity (opening vs closing vs intraday)
  4. Predict map persistence

Usage:
    python post_market_analysis.py gamma_monitor_20240924_093000.json \
        --today-volume 150000000 \
        --oi-today 45123456 \
        --oi-yesterday 44987654
"""

import argparse
import json
import sys
from pathlib import Path


def classify_activity(volume: float, oi_change_pct: float) -> str:
    """
    Classify intraday activity based on volume and OI change.

    Returns classification label and interpretation.
    """
    if volume < 0 or oi_change_pct is None:
        return "INSUFFICIENT_DATA", "Cannot classify without volume and OI"

    # Thresholds
    significant_vol = 1e7  # 10M+ share volume
    significant_oi_change = 2.0  # 2% OI change

    if volume < significant_vol:
        return "LOW_VOLUME", "Volume too low for reliable dealer repositioning signal"

    if oi_change_pct > significant_oi_change:
        return (
            "OPENING_ACTIVITY",
            f"Volume ↑ + OI ↑{oi_change_pct:.1f}% → Opening activity; gamma map likely PERSISTENT",
        )
    elif oi_change_pct < -significant_oi_change:
        return (
            "CLOSING_ACTIVITY",
            f"Volume ↑ + OI ↓{abs(oi_change_pct):.1f}% → Closing activity; gamma map effect may FADE",
        )
    else:
        return (
            "INTRADAY_TRADING",
            f"Volume ↑ but OI ~flat {oi_change_pct:+.1f}% → Spreads/rolls/transfers; not reliable dealer repo",
        )


def load_session_data(filepath: Path) -> dict:
    """Load intraday monitoring JSON."""
    with open(filepath) as f:
        return json.load(f)


def summarize_session(data: dict) -> dict:
    """Extract key stats from session."""
    summary = {}

    for symbol, session in data.items():
        snapshots = session.get("snapshots", [])
        if not snapshots:
            continue

        open_snap = snapshots[0]
        close_snap = snapshots[-1]

        summary[symbol] = {
            "spot_open": open_snap.get("spot"),
            "spot_close": close_snap.get("spot"),
            "spot_move_pct": (
                (close_snap.get("spot") - open_snap.get("spot")) / open_snap.get("spot") * 100
                if open_snap.get("spot")
                else 0
            ),
            "flip_open": open_snap.get("gamma_flip"),
            "flip_close": close_snap.get("gamma_flip"),
            "regime_open": open_snap.get("regime"),
            "regime_close": close_snap.get("regime"),
            "regime_flipped": open_snap.get("regime") != close_snap.get("regime"),
            "material_changes_count": len(session.get("material_changes", [])),
            "price_action_alerts_count": len(session.get("price_action_alerts", [])),
            "material_changes": session.get("material_changes", []),
            "price_action_alerts": session.get("price_action_alerts", []),
        }

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Post-market OI/volume analysis for gamma map persistence"
    )
    parser.add_argument(
        "session_file",
        type=Path,
        help="Path to gamma_monitor JSON output",
    )
    parser.add_argument(
        "--today-volume",
        type=float,
        required=True,
        help="Total volume for symbol today (e.g., 150000000)",
    )
    parser.add_argument(
        "--oi-today",
        type=float,
        required=True,
        help="Open interest as of close today",
    )
    parser.add_argument(
        "--oi-yesterday",
        type=float,
        required=True,
        help="Open interest from yesterday (prior close)",
    )

    args = parser.parse_args()

    if not args.session_file.exists():
        print(f"ERROR: Session file not found: {args.session_file}")
        sys.exit(1)

    # Load and summarize
    data = load_session_data(args.session_file)
    summary = summarize_session(data)

    # Classify activity
    oi_change_pct = (args.oi_today - args.oi_yesterday) / args.oi_yesterday * 100
    classification, interpretation = classify_activity(args.today_volume, oi_change_pct)

    # Report
    print("\n" + "=" * 80)
    print("POST-MARKET ANALYSIS")
    print("=" * 80)

    print(f"\n📊 VOLUME & OI:")
    print(f"  Today's volume: {args.today_volume:,.0f}")
    print(f"  OI today:      {args.oi_today:,.0f}")
    print(f"  OI yesterday:  {args.oi_yesterday:,.0f}")
    print(f"  OI change:     {oi_change_pct:+.2f}%")

    print(f"\n🎯 CLASSIFICATION: {classification}")
    print(f"   → {interpretation}\n")

    print("INTRADAY SUMMARY:")
    print("-" * 80)

    for symbol, stats in summary.items():
        print(f"\n{symbol}:")
        print(f"  Spot:   {stats['spot_open']:.2f} → {stats['spot_close']:.2f} ({stats['spot_move_pct']:+.2f}%)")
        print(
            f"  Regime: {stats['regime_open']} → {stats['regime_close']} "
            f"{'⚡ FLIPPED' if stats['regime_flipped'] else '(stable)'}"
        )
        print(f"  Flip:   {stats['flip_open']:.2f} → {stats['flip_close']:.2f if stats['flip_close'] else 'N/A'}")
        print(f"  Material changes: {stats['material_changes_count']}")
        print(f"  Price action alerts: {stats['price_action_alerts_count']}")

        if stats["material_changes"]:
            print(f"\n  🔍 Material Changes:")
            for chg in stats["material_changes"][:3]:  # Show first 3
                print(f"    [{chg['timestamp']}] {chg['change']}")
            if len(stats["material_changes"]) > 3:
                print(f"    ... and {len(stats['material_changes']) - 3} more")

        if stats["price_action_alerts"]:
            print(f"\n  🚨 Price Action Alerts:")
            for alert in stats["price_action_alerts"][:3]:  # Show first 3
                print(f"    [{alert['timestamp']}] {alert['alert']}")
            if len(stats["price_action_alerts"]) > 3:
                print(f"    ... and {len(stats['price_action_alerts']) - 3} more")

    print("\n" + "=" * 80)
    print("✅ GUIDANCE FOR TOMORROW:")
    print("-" * 80)

    if classification == "OPENING_ACTIVITY":
        print(
            "  • Gamma map from today is likely PERSISTENT into tomorrow\n"
            "  • Call wall remains likely resistance; put wall remains likely support\n"
            "  • Monitor for extension or reversal near the overnight levels\n"
        )
    elif classification == "CLOSING_ACTIVITY":
        print(
            "  • Gamma map from today may FADE as dealers close positions\n"
            "  • Call wall/put wall may shift lower into tomorrow open\n"
            "  • Look for new wall formation in first hour of trading\n"
        )
    elif classification == "INTRADAY_TRADING":
        print(
            "  • Activity was likely spreads, rolls, or customer transfers\n"
            "  • Dealer net positioning may not have changed materially\n"
            "  • Recheck the gamma map at tomorrow's open; prior day's walls less reliable\n"
        )

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
