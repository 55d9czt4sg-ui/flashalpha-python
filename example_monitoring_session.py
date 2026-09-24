#!/usr/bin/env python3
"""
example_monitoring_session.py
Demonstrates the full intraday gamma monitoring + post-market analysis workflow.

This script:
1. Creates a synthetic monitoring session (mimics real market data)
2. Simulates material changes and flags them
3. Saves JSON output that post_market_analysis.py can consume
4. Runs post-market classification on the synthetic data

Usage:
    python example_monitoring_session.py
"""

import json
import os
from datetime import datetime, timedelta

def generate_synthetic_session():
    """Create a mock monitoring session with material changes."""
    
    session = {
        "start_time": datetime.now().isoformat(),
        "symbols": ["SPY"],
        "snapshots": [
            # OPENING SNAPSHOT
            {
                "symbol": "SPY",
                "timestamp": datetime.now().isoformat(),
                "spot": 562.45,
                "gamma_flip": 561.80,
                "gamma_flip_status": "available",
                "call_wall": 566.00,
                "put_wall": 560.00,
                "net_gex": 1234567,
                "dex": 89000,
                "regime": "long-gamma",
                "data_as_of": datetime.now().isoformat(),
                "phase": "open",
            },
            # CHECK 1: 30 MIN LATER - Minor move, no material change
            {
                "symbol": "SPY",
                "timestamp": (datetime.now() + timedelta(minutes=30)).isoformat(),
                "spot": 562.60,
                "gamma_flip": 561.82,  # +0.01 move
                "gamma_flip_status": "available",
                "call_wall": 566.00,
                "put_wall": 560.00,
                "net_gex": 1250000,
                "dex": 91000,
                "regime": "long-gamma",
                "data_as_of": (datetime.now() + timedelta(minutes=30)).isoformat(),
                "phase": "check_1",
            },
            # CHECK 2: 60 MIN LATER - Material flip move (↓0.48 = -0.085%)
            {
                "symbol": "SPY",
                "timestamp": (datetime.now() + timedelta(minutes=60)).isoformat(),
                "spot": 562.70,
                "gamma_flip": 561.32,  # -0.48 move — MATERIAL!
                "gamma_flip_status": "available",
                "call_wall": 566.00,
                "put_wall": 560.00,
                "net_gex": 1100000,
                "dex": 75000,
                "regime": "long-gamma",
                "data_as_of": (datetime.now() + timedelta(minutes=60)).isoformat(),
                "phase": "check_2",
                "material_change": {
                    "type": "gamma_flip_move",
                    "from": 561.80,
                    "to": 561.32,
                    "pct_change": -0.085,
                    "reason": "Flip moved 0.48 points (-0.085% of spot). Dealers adjusting hedge exposure.",
                }
            },
            # CHECK 3: 90 MIN LATER - Call wall moves up +1 strike (material)
            {
                "symbol": "SPY",
                "timestamp": (datetime.now() + timedelta(minutes=90)).isoformat(),
                "spot": 563.00,
                "gamma_flip": 561.30,
                "gamma_flip_status": "available",
                "call_wall": 567.00,  # +1 strike — MATERIAL!
                "put_wall": 560.00,
                "net_gex": 950000,
                "dex": 60000,
                "regime": "long-gamma",
                "data_as_of": (datetime.now() + timedelta(minutes=90)).isoformat(),
                "phase": "check_3",
                "material_change": {
                    "type": "wall_move",
                    "wall": "call_wall",
                    "from": 566.00,
                    "to": 567.00,
                    "strike_increment": 1,
                    "reason": "Call wall moved +1.00 to 567. Dealers pushing supply resistance higher.",
                }
            },
        ],
        "material_changes": [
            {
                "check": 2,
                "timestamp": (datetime.now() + timedelta(minutes=60)).isoformat(),
                "type": "gamma_flip_move",
                "description": "Flip dropped from 561.80 to 561.32 (-0.085%)",
            },
            {
                "check": 3,
                "timestamp": (datetime.now() + timedelta(minutes=90)).isoformat(),
                "type": "wall_move",
                "description": "Call wall moved +1 strike to 567.00",
            },
        ],
        "price_action_alerts": [
            {
                "check": 3,
                "timestamp": (datetime.now() + timedelta(minutes=90)).isoformat(),
                "alert": "Price approaching new call wall at 567.00 — watch for rejection or breakout",
            },
        ],
    }
    
    return session

def save_session(session, filename="example_gamma_session.json"):
    """Write synthetic session to JSON file."""
    with open(filename, "w") as f:
        json.dump(session, f, indent=2)
    print(f"✅ Saved synthetic session: {filename}\n")
    return filename

def run_post_market_analysis(filename):
    """Run post-market classification on the session."""
    print("📊 POST-MARKET ANALYSIS\n")
    
    with open(filename) as f:
        data = json.load(f)
    
    print("Opening Snapshot:")
    opening = data["snapshots"][0]
    print(f"  Spot: ${opening['spot']:.2f}")
    print(f"  Flip: ${opening['gamma_flip']:.2f}")
    print(f"  Call Wall: ${opening['call_wall']:.2f}")
    print(f"  Put Wall: ${opening['put_wall']:.2f}")
    print(f"  Regime: {opening['regime']}\n")
    
    closing = data["snapshots"][-1]
    print("Final Snapshot (after all checks):")
    print(f"  Spot: ${closing['spot']:.2f} (↑${closing['spot'] - opening['spot']:.2f})")
    print(f"  Flip: ${closing['gamma_flip']:.2f} (↓${closing['gamma_flip'] - opening['gamma_flip']:.2f})")
    print(f"  Call Wall: ${closing['call_wall']:.2f}")
    print(f"  Regime: {closing['regime']}\n")
    
    print("Material Changes Detected:")
    for i, change in enumerate(data["material_changes"], 1):
        print(f"  {i}. [{change['check']}] {change['type']}: {change['description']}")
    
    print("\nPrice Action Alerts:")
    for alert in data["price_action_alerts"]:
        print(f"  • {alert['alert']}")
    
    print("\n" + "="*70)
    print("CLASSIFICATION (Next Day, After OCC OI Update)")
    print("="*70)
    
    # Simulate volume/OI comparison
    today_volume = 180_000_000  # SPY typical: 80-100M
    today_oi = 46_500_000       # Synthetic
    yesterday_oi = 45_500_000   # Synthetic
    
    oi_change_pct = ((today_oi - yesterday_oi) / yesterday_oi) * 100
    volume_vs_avg = "above average" if today_volume > 100_000_000 else "normal"
    
    print(f"\nToday's Volume: {today_volume:,}")
    print(f"OI Change: {yesterday_oi:,} → {today_oi:,} ({oi_change_pct:+.1f}%)")
    print(f"Volume was: {volume_vs_avg}\n")
    
    if oi_change_pct > 2:
        activity_type = "OPENING ACTIVITY"
        outlook = "✅ Dealer positions likely persist into next session. Gamma map should hold."
    elif oi_change_pct < -2:
        activity_type = "CLOSING ACTIVITY"
        outlook = "⚠️ Dealers unwound positions. Gamma map effect may fade or reverse."
    else:
        activity_type = "INTRADAY TRADING"
        outlook = "⏸️ Likely spreads/rolls/hedges. Dealer net positioning unchanged."
    
    print(f"Classification: {activity_type}")
    print(f"Outlook: {outlook}")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Plot opening vs closing gamma map (flip, walls, regime)")
    print("2. Overlay price action on gamma flip — watch for rejection/support/resistance")
    print("3. Compare dealer GEX flip (today → tomorrow) to confirm positioning change")
    print("4. If opening activity: monitor next day for gamma-driven price dynamics")
    print("5. If closing activity: reassess gamma support/resistance levels at market open")

def main():
    print("🎯 INTRADAY GAMMA MONITORING EXAMPLE\n")
    print("="*70)
    
    # Step 1: Generate synthetic data
    session = generate_synthetic_session()
    
    # Step 2: Save to JSON
    filename = save_session(session)
    
    # Step 3: Run post-market analysis
    run_post_market_analysis(filename)
    
    print("\n✅ Example workflow complete!")
    print(f"\nYou can inspect the session JSON:")
    print(f"  cat {filename}")
    print(f"\nOr use the real post_market_analysis.py script:")
    print(f"  python post_market_analysis.py {filename} --today-volume 180000000 --oi-today 46500000 --oi-yesterday 45500000")

if __name__ == "__main__":
    main()
