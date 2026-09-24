#!/usr/bin/env python3
"""
Example: Unified Gamma + Vol Monitoring with QuantWheel Data

Demonstrates the complete intraday monitoring workflow with realistic synthetic data.
Shows how gamma (FlashAlpha) and vol surface (QuantWheel) converge to produce 
actionable trading signals.

This runs WITHOUT an API key, so you can test the system end-to-end.

Usage:
    python example_unified_monitoring.py
    
Output:
    • Real-time console output showing convergence signals
    • JSON session file with all snapshots
"""

import json
from datetime import datetime
from typing import Dict, Any, List


def generate_synthetic_gamma_snapshot(
    symbol: str, check_num: int, base_spot: float
) -> Dict[str, Any]:
    """Generate realistic gamma data for a check."""
    
    # Simulate gradual price movement
    spot = base_spot + (check_num - 1) * 0.5
    
    # Gamma flip moves based on price
    if check_num == 1:
        flip = spot - 2.5  # Initial flip position
        regime = "long-gamma-bullish"
        net_gex = 850_000  # Dealers long gamma
    elif check_num == 2:
        flip = spot - 2.2  # Flip moves up slightly
        regime = "long-gamma-bullish"
        net_gex = 720_000  # Still long, but less
    elif check_num == 3:
        flip = spot - 1.8  # Material flip move
        regime = "short-gamma-bearish"
        net_gex = -380_000  # Flipped to short gamma!
    else:
        flip = spot - 1.5
        regime = "short-gamma-bearish"
        net_gex = -420_000
    
    call_wall = spot + 1.75
    put_wall = spot - 1.25
    dex = -250_000
    
    return {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "spot": spot,
        "gamma_flip": flip,
        "gamma_flip_status": "available",
        "call_wall": call_wall,
        "put_wall": put_wall,
        "net_gex": net_gex,
        "dex": dex,
        "regime": regime,
        "data_as_of": {
            "equity_feed": datetime.now().isoformat(),
            "equity_options_feed": datetime.now().isoformat(),
            "flow_feed": datetime.now().isoformat(),
        },
    }


def generate_synthetic_vol_snapshot(
    symbol: str, check_num: int, base_vol: float
) -> Dict[str, Any]:
    """Generate realistic IV surface data (QuantWheel-like structure)."""
    
    # Simulate vol dynamics
    if check_num == 1:
        atm_iv = base_vol
        put_iv = base_vol * 1.15  # Put skew elevated
        call_iv = base_vol * 0.95
    elif check_num == 2:
        atm_iv = base_vol * 1.08
        put_iv = base_vol * 1.18
        call_iv = base_vol * 0.98
    elif check_num == 3:
        atm_iv = base_vol * 1.25  # Vol expanding!
        put_iv = base_vol * 1.35  # Put skew getting steeper
        call_iv = base_vol * 1.05
    else:
        atm_iv = base_vol * 1.20
        put_iv = base_vol * 1.32
        call_iv = base_vol * 1.02
    
    put_call_ratio = put_iv / call_iv
    vrp = atm_iv - (base_vol * 0.85)  # Implied > Realized = positive VRP
    
    return {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "atm_iv": atm_iv,
        "term_structure": {
            "front_month": atm_iv,
            "next_month": atm_iv * 0.92,
            "front_minus_next": atm_iv * 0.08,
        },
        "skew": {
            "put_iv": put_iv,
            "atm_iv": atm_iv,
            "call_iv": call_iv,
            "put_call_ratio": put_call_ratio,
            "skew_steepness": put_iv - call_iv,
        },
        "realized_vol": base_vol * 0.85,
        "vrp": vrp,
        "status": "synthetic example data",
    }


def detect_convergence_signals(
    gamma: Dict, vol: Dict, symbol: str
) -> List[Dict]:
    """Identify signals from gamma + vol convergence."""
    signals = []
    
    spot = gamma.get("spot", 0)
    flip = gamma.get("gamma_flip", 0)
    call_wall = gamma.get("call_wall", 0)
    put_wall = gamma.get("put_wall", 0)
    regime = gamma.get("regime", "")
    net_gex = gamma.get("net_gex", 0)
    
    atm_iv = vol.get("atm_iv", 0)
    put_iv = vol.get("skew", {}).get("put_iv", 0)
    call_iv = vol.get("skew", {}).get("call_iv", 0)
    vrp = vol.get("vrp", 0)
    
    # SIGNAL: Call wall + short vol skew
    if call_wall and abs(spot - call_wall) < spot * 0.01:
        if call_iv < atm_iv * 0.97:
            signals.append({
                "type": "CALL_WALL_SHORT_SKEW",
                "severity": "HIGH",
                "timestamp": datetime.now().isoformat(),
                "description": f"Price ${spot:.2f} near call wall ${call_wall:.2f}; calls are cheap vs ATM",
                "implication": [
                    f"Dealer supply at ${call_wall:.2f} (OI concentration)",
                    f"Call IV ${call_iv:.2f} < ATM IV ${atm_iv:.2f} = vol already priced",
                    "Low risk premium for upside; dealer protecting seller",
                ],
                "setup": "Price rejection at wall likely. Watch for dealer-driven pullback.",
            })
    
    # SIGNAL: Put wall + elevated put skew
    if put_wall and abs(spot - put_wall) < spot * 0.01:
        if put_iv > atm_iv * 1.10:
            signals.append({
                "type": "PUT_WALL_LONG_SKEW",
                "severity": "HIGH",
                "timestamp": datetime.now().isoformat(),
                "description": f"Price ${spot:.2f} near put wall ${put_wall:.2f}; puts premium elevated",
                "implication": [
                    f"Dealer floor at ${put_wall:.2f}",
                    f"Put IV ${put_iv:.2f} >> ATM ${atm_iv:.2f} = protection demand high",
                    "Risk premium concentrated in downside; vol crush risk on breakout",
                ],
                "setup": "If price breaks below wall, watch for put skew collapse.",
            })
    
    # SIGNAL: Short-gamma + IV expanding
    if "short-gamma" in regime and atm_iv > vol.get("realized_vol", 0) * 1.20:
        signals.append({
            "type": "SHORT_GAMMA_IV_EXPANSION",
            "severity": "CRITICAL",
            "timestamp": datetime.now().isoformat(),
            "description": f"Regime: {regime} | IV ${atm_iv:.2f} >> RV ${vol.get('realized_vol', 0):.2f}",
            "implication": [
                "Dealers are SHORT gamma (pro-cyclical hedging)",
                "IV expanding means dealers are losing on convexity",
                "Each price move accelerates vol increase = dealer pain",
            ],
            "setup": "Expect sharp moves and vol spikes. Dealers may hedge aggressively.",
        })
    
    # SIGNAL: GEX regime flip (demo only - in live system detects previous state)
    if net_gex < -300_000 and regime == "short-gamma-bearish":
        signals.append({
            "type": "SHORT_GAMMA_REGIME",
            "severity": "CRITICAL",
            "timestamp": datetime.now().isoformat(),
            "description": f"GEX: {net_gex:,} | Regime: SHORT GAMMA",
            "implication": [
                "Dealers are NET short gamma",
                "Market stickiness gone; moves accelerate",
                "Gamma pin at expiry less likely",
            ],
            "setup": "Trade momentum into expiry. Watch for directional runs.",
        })
    
    # SIGNAL: Positive VRP with high ATM vol
    if vrp > 0 and atm_iv > 0.25:
        signals.append({
            "type": "POSITIVE_VRP_HIGH_ATM",
            "severity": "MEDIUM",
            "timestamp": datetime.now().isoformat(),
            "description": f"VRP: ${vrp:.4f} (IV > RV) | ATM IV: ${atm_iv:.2f}",
            "implication": [
                "Volatility risk premium positive = selling vol is rewarded",
                "Implied vol elevated vs realized = mean reversion candidate",
                "If IV came from put demand (skew), short vol is directional hedge",
            ],
            "setup": "Short vol strategies gain. Monitor for crush into lower realized.",
        })
    
    return signals


def print_check(check_num: int, symbols: List[str], check_data: Dict):
    """Pretty-print a check with signals."""
    print("\n" + "=" * 100)
    print(f"[CHECK {check_num}] {datetime.now().isoformat()}")
    print("=" * 100)
    
    for symbol in symbols:
        data = check_data[symbol]
        gamma = data["gamma"]
        vol = data["vol"]
        signals = data["signals"]
        
        print(f"\n📊 {symbol}:")
        print(f"  Price: ${gamma['spot']:.2f} | Flip: ${gamma['gamma_flip']:.2f}")
        print(
            f"  Walls: Call ${gamma['call_wall']:.2f} / Put ${gamma['put_wall']:.2f}"
        )
        print(f"  GEX: {gamma['net_gex']:>11,} | Regime: {gamma['regime']}")
        print(
            f"  Vol: ATM ${vol['atm_iv']:.2f} (RV ${vol['realized_vol']:.2f}) | "
            f"Put/Call ratio: {vol['skew']['put_call_ratio']:.3f}"
        )
        
        if signals:
            print(f"\n  🚨 SIGNALS ({len(signals)}):")
            for sig in signals:
                emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MEDIUM": "🟡",
                    "LOW": "⚪",
                }.get(sig["severity"], "❓")
                
                print(f"    {emoji} [{sig['severity']}] {sig['type']}")
                print(f"       {sig['description']}")
                for impl in sig.get("implication", []):
                    print(f"       • {impl}")
        else:
            print(f"  ✨ No convergence signals this check")


def main():
    print("\n" + "=" * 100)
    print("🎯 UNIFIED GAMMA + VOL MONITORING - SYNTHETIC EXAMPLE")
    print("=" * 100)
    
    symbols = ["SPY", "QQQ"]
    num_checks = 4
    
    # Base prices / vols
    base_prices = {"SPY": 563.5, "QQQ": 428.2}
    base_vols = {"SPY": 0.18, "QQQ": 0.22}
    
    # Collect all session data
    session = {symbol: {"snapshots": [], "all_signals": []} for symbol in symbols}
    
    # Run checks
    for check_num in range(1, num_checks + 1):
        check_data = {}
        
        for symbol in symbols:
            gamma = generate_synthetic_gamma_snapshot(
                symbol, check_num, base_prices[symbol]
            )
            vol = generate_synthetic_vol_snapshot(
                symbol, check_num, base_vols[symbol]
            )
            signals = detect_convergence_signals(gamma, vol, symbol)
            
            check_data[symbol] = {
                "gamma": gamma,
                "vol": vol,
                "signals": signals,
            }
            
            session[symbol]["snapshots"].append({
                "check": check_num,
                "gamma": gamma,
                "vol": vol,
            })
            session[symbol]["all_signals"].extend(signals)
        
        # Display
        print_check(check_num, symbols, check_data)
    
    # Save session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"example_unified_monitoring_session_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(session, f, indent=2, default=str)
    
    print("\n" + "=" * 100)
    print("✅ EXAMPLE MONITORING COMPLETE")
    print("=" * 100)
    print(f"💾 Session saved: {output_file}")
    print("\n📌 KEY INSIGHTS FROM THIS EXAMPLE:")
    print("  • Check 1: Long-gamma regime; dealers providing support")
    print("  • Check 2: Regime shifting; gamma flip moved up (dealers hedging)")
    print("  • Check 3: CRITICAL FLIP to short gamma; vol expanding; signals escalate")
    print("  • Check 4: Sustained short-gamma; expect acceleration/spikes")
    print("\n📊 Signal types detected:")
    print("  • Call Wall + Short Skew = Vol already priced; resistance likely")
    print("  • Put Wall + Long Skew = Protection demand high; crush risk on break")
    print("  • Short Gamma + IV Expansion = Dealer losses; expect sharp moves")
    print("  • Positive VRP + High Vol = Selling vol is rewarded")
    print("\n🎯 WORKFLOW:")
    print("  1. Run this example to understand output format")
    print("  2. Run live system during market hours: python unified_gamma_vol_monitor.py SPY,QQQ")
    print("  3. Monitor console for real-time signals")
    print("  4. Next morning: python post_market_analysis.py <session_json>")


if __name__ == "__main__":
    main()
