#!/usr/bin/env python3
"""
Unified Gamma + Vol Monitor (Tier-Adaptive)

Automatically adapts to available API tier:
- Basic/Free tier: Monitors spot + IV surface (ATM IV, HV, VRP when available)
- Growth tier: Full gamma monitoring (flip, walls, GEX, regime, dealer flow)

Usage:
    export FLASHALPHA_API_KEY="your-key"
    python unified_gamma_vol_monitor_tier_adaptive.py SPY,QQQ --interval 1800 --checks 12
"""

import json
import sys
import time
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from flashalpha import FlashAlpha, TierRestrictedError
except ImportError:
    print("❌ flashalpha not installed. Install with: pip install flashalpha")
    sys.exit(1)


class SignalSeverity(Enum):
    CRITICAL = "🔴 CRITICAL"
    HIGH = "🟠 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "⚪ LOW"


@dataclass
class GammaSnapshot:
    """Gamma exposure snapshot (Growth tier only)"""
    symbol: str
    spot: float
    gamma_flip: Optional[float]
    gamma_flip_status: str
    call_wall: Optional[float]
    put_wall: Optional[float]
    net_gex: Optional[float]
    regime: str
    timestamp: str
    data_as_of: Dict[str, Any]
    tier: str = "growth"


@dataclass
class VolSnapshot:
    """IV surface snapshot (all tiers)"""
    symbol: str
    spot: float
    atm_iv: float
    hv_20: float
    hv_60: Optional[float]
    vrp: Optional[float]
    call_iv_25d: Optional[float]
    atm_iv_mid: Optional[float]
    put_iv_25d: Optional[float]
    timestamp: str
    data_as_of: Dict[str, Any]
    tier: str = "basic"


@dataclass
class ConvergenceSignal:
    """Detected convergence signal"""
    severity: SignalSeverity
    signal_type: str
    symbol: str
    description: str
    threshold_metric: str
    current_value: str
    recommendation: str


class UnifiedMonitor:
    def __init__(self, api_key: str):
        self.client = FlashAlpha(api_key)
        self.tier = self._detect_tier()
        self.last_snapshots = {}
        self.session_signals = []
        
    def _detect_tier(self) -> str:
        """Detect available API tier by attempting Growth endpoint"""
        try:
            self.client.exposure_summary("SPY")
            return "growth"
        except TierRestrictedError:
            return "basic"
    
    def snapshot_vol_surface(self, symbol: str) -> Optional[VolSnapshot]:
        """Capture IV surface snapshot (works on all tiers)"""
        try:
            result = self.client.stock_summary(symbol)
            vol = result.get("volatility", {})
            price = result.get("price", {})
            
            spot = price.get("mid") or price.get("last")
            
            return VolSnapshot(
                symbol=symbol,
                spot=spot,
                atm_iv=vol.get("atm_iv"),
                hv_20=vol.get("hv_20"),
                hv_60=vol.get("hv_60"),
                vrp=vol.get("vrp"),
                call_iv_25d=vol.get("skew_25d"),
                atm_iv_mid=vol.get("atm_iv"),
                put_iv_25d=vol.get("skew_25d"),
                timestamp=datetime.utcnow().isoformat() + "Z",
                data_as_of=result.get("data_as_of", {}),
                tier="basic"
            )
        except Exception as e:
            print(f"❌ Error capturing vol snapshot for {symbol}: {e}")
            return None
    
    def snapshot_gamma(self, symbol: str) -> Optional[GammaSnapshot]:
        """Capture gamma snapshot (Growth tier only)"""
        if self.tier != "growth":
            return None
        
        try:
            result = self.client.exposure_summary(symbol)
            return GammaSnapshot(
                symbol=symbol,
                spot=result.get("spot"),
                gamma_flip=result.get("gamma_flip"),
                gamma_flip_status=result.get("gamma_flip_status", "unavailable"),
                call_wall=result.get("call_wall"),
                put_wall=result.get("put_wall"),
                net_gex=result.get("net_gex"),
                regime=result.get("regime", "unknown"),
                timestamp=datetime.utcnow().isoformat() + "Z",
                data_as_of=result.get("data_as_of", {}),
                tier="growth"
            )
        except TierRestrictedError:
            return None
        except Exception as e:
            print(f"❌ Error capturing gamma snapshot for {symbol}: {e}")
            return None
    
    def detect_convergence_signals(self, gamma: Optional[GammaSnapshot], vol: Optional[VolSnapshot]) -> List[ConvergenceSignal]:
        """Detect convergence signals based on available data"""
        signals = []
        
        if not vol:
            return signals
        
        symbol = vol.symbol
        
        # Signal 1: High ATM IV with low HV = vol contraction risk
        if vol.atm_iv and vol.hv_20 and vol.atm_iv > vol.hv_20 * 1.15:
            vrp_z = ((vol.atm_iv - vol.hv_20) / vol.hv_20) * 100
            signals.append(ConvergenceSignal(
                severity=SignalSeverity.MEDIUM,
                signal_type="POSITIVE_VRP_HIGH_ATM",
                symbol=symbol,
                description="IV elevated vs realized vol - contraction risk",
                threshold_metric="ATM IV > HV 20d * 1.15",
                current_value=f"ATM IV: {vol.atm_iv:.2f}%, HV 20d: {vol.hv_20:.2f}% (gap: {vrp_z:+.1f}%)",
                recommendation="Consider selling vol; monitor for crush into support"
            ))
        
        # Growth-tier signals
        if gamma and gamma.regime:
            # Signal 2: Short gamma regime
            if "short-gamma" in gamma.regime.lower():
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.CRITICAL,
                    signal_type="SHORT_GAMMA_REGIME",
                    symbol=symbol,
                    description="Dealers short gamma - moves will accelerate",
                    threshold_metric="Regime = short-gamma-bearish",
                    current_value=f"Current regime: {gamma.regime}",
                    recommendation="Watch for pin rejection; expect faster acceleration on breaks"
                ))
            
            # Signal 3: Short gamma + high IV = acceleration + contraction risk
            if "short-gamma" in gamma.regime.lower() and vol.atm_iv and vol.hv_20 and vol.atm_iv > vol.hv_20 * 1.10:
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.CRITICAL,
                    signal_type="SHORT_GAMMA_IV_EXPANSION",
                    symbol=symbol,
                    description="Dealers short gamma losing on convexity - peak risk",
                    threshold_metric="short-gamma regime + ATM IV > HV 20d * 1.10",
                    current_value=f"Regime: {gamma.regime}, IV premium: {((vol.atm_iv/vol.hv_20 - 1) * 100):+.1f}%",
                    recommendation="Highest acceleration risk; expect sharp directional move"
                ))
        
        return signals
    
    def print_check(self, check_num: int, gamma: Optional[GammaSnapshot], vol: Optional[VolSnapshot], signals: List[ConvergenceSignal]):
        """Print formatted check output"""
        print(f"\n{'='*75}")
        print(f"CHECK #{check_num} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*75}")
        print(f"API Tier: {self.tier.upper()} | Market open: False (after hours)")
        
        if vol:
            print(f"\n{vol.symbol} VOLATILITY SNAPSHOT:")
            print(f"  Spot:         ${vol.spot:.2f}")
            print(f"  ATM IV:       {vol.atm_iv:.2f}%")
            print(f"  HV 20d:       {vol.hv_20:.2f}%")
            if vol.hv_60:
                print(f"  HV 60d:       {vol.hv_60:.2f}%")
            if vol.vrp:
                print(f"  VRP:          {vol.vrp:.2f}")
            print(f"  Data as of:   {vol.data_as_of.get('equity_feed', 'N/A')}")
        
        if gamma:
            print(f"\n{gamma.symbol} GAMMA SNAPSHOT (Growth Tier):")
            print(f"  Spot:         ${gamma.spot:.2f}")
            print(f"  Gamma Flip:   {gamma.gamma_flip:.2f if gamma.gamma_flip else 'N/A'}")
            print(f"  Call Wall:    {gamma.call_wall:.2f if gamma.call_wall else 'N/A'}")
            print(f"  Put Wall:     {gamma.put_wall:.2f if gamma.put_wall else 'N/A'}")
            print(f"  Net GEX:      {gamma.net_gex:,.0f if gamma.net_gex else 'N/A'}")
            print(f"  Regime:       {gamma.regime}")
            print(f"  Data as of:   {gamma.data_as_of.get('equity_options_feed', 'N/A')}")
        else:
            print(f"\n⚠️  GAMMA DATA UNAVAILABLE - Upgrade to Growth tier for full monitoring")
        
        if signals:
            print(f"\n🚨 CONVERGENCE SIGNALS ({len(signals)} detected):")
            for sig in signals:
                print(f"\n  {sig.severity.value} {sig.signal_type}")
                print(f"    {sig.description}")
                print(f"    Threshold: {sig.threshold_metric}")
                print(f"    Current:   {sig.current_value}")
                print(f"    Action:    {sig.recommendation}")
        else:
            print(f"\n✅ No convergence signals detected this check")
    
    def run(self, symbols: List[str], interval_seconds: int = 1800, num_checks: int = 12):
        """Run monitoring loop"""
        print(f"\n{'='*75}")
        print(f"🚀 UNIFIED GAMMA + VOL MONITOR (Tier-Adaptive)")
        print(f"{'='*75}")
        print(f"API Tier Detected: {self.tier.upper()}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Check interval: {interval_seconds}s | Total checks: {num_checks}")
        print(f"Market hours: 09:30 - 16:00 ET (currently after-hours test)")
        
        if self.tier == "basic":
            print(f"\n⚠️  BASIC TIER - Limited to spot + IV surface")
            print(f"   To unlock full gamma monitoring, upgrade to Growth tier:")
            print(f"   https://flashalpha.com → Dashboard → Settings")
        
        all_signals = {}
        
        for check_num in range(1, num_checks + 1):
            check_signals = []
            
            for symbol in symbols:
                vol = self.snapshot_vol_surface(symbol)
                gamma = self.snapshot_gamma(symbol)
                signals = self.detect_convergence_signals(gamma, vol)
                
                self.print_check(check_num, gamma, vol, signals)
                check_signals.extend(signals)
            
            if check_num < num_checks:
                print(f"\n⏳ Next check in {interval_seconds}s... (Ctrl+C to stop)")
                try:
                    time.sleep(interval_seconds)
                except KeyboardInterrupt:
                    print(f"\n⏹️  Monitoring stopped by user")
                    break
        
        # Save session
        session_file = f"unified_gamma_vol_monitor_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(session_file, "w") as f:
            json.dump({
                "tier": self.tier,
                "symbols": symbols,
                "checks": num_checks,
                "interval_seconds": interval_seconds,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, f, indent=2)
        
        print(f"\n✅ Session saved to: {session_file}")


def main():
    api_key = os.getenv("FLASHALPHA_API_KEY")
    if not api_key:
        print("❌ FLASHALPHA_API_KEY environment variable not set")
        print("   Set with: export FLASHALPHA_API_KEY='your-key'")
        sys.exit(1)
    
    symbols = ["SPY", "QQQ"]
    if len(sys.argv) > 1 and sys.argv[1] != "--help":
        symbols = sys.argv[1].split(",")
    
    interval = 1800  # 30 minutes default
    if "--interval" in sys.argv:
        idx = sys.argv.index("--interval")
        if idx + 1 < len(sys.argv):
            interval = int(sys.argv[idx + 1])
    
    checks = 12  # Default 12 checks (6 hours at 30min interval)
    if "--checks" in sys.argv:
        idx = sys.argv.index("--checks")
        if idx + 1 < len(sys.argv):
            checks = int(sys.argv[idx + 1])
    
    monitor = UnifiedMonitor(api_key)
    monitor.run(symbols, interval, checks)


if __name__ == "__main__":
    main()
