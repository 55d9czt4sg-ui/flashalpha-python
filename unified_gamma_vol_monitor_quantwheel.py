#!/usr/bin/env python3
"""
Unified Gamma + Vol Monitor (QuantWheel-Powered)

Uses QuantWheel for complete gamma + volatility analysis:
- Gamma flip tracking (dealer repositioning)
- Call/put walls (dealer supply/demand)
- Net GEX (dealer gamma exposure)
- Regime classification (long/short gamma)
- IV surface + skew + term structure
- VRP + realized vol + distribution

Usage:
    export QUANTWHEEL_API_KEY="your-key"
    python unified_gamma_vol_monitor_quantwheel.py SPY,QQQ --interval 1800 --checks 12
"""

import json
import sys
import time
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

# Try to import quantwheel SDK
QUANTWHEEL_AVAILABLE = False
try:
    from quantwheel import QuantWheel
    QUANTWHEEL_AVAILABLE = True
except ImportError:
    try:
        from quantwheel_mock import QuantWheel
        QUANTWHEEL_AVAILABLE = True
        USING_MOCK = True
        print("ℹ️  Using QuantWheel mock SDK (real SDK not yet installed)")
        print("   Once installed, will seamlessly use real API")
    except ImportError:
        USING_MOCK = False
        print("⚠️  quantwheel SDK not installed yet")
        print("   Once available, this script will use it for complete gamma analytics")


class SignalSeverity(Enum):
    CRITICAL = "🔴 CRITICAL"
    HIGH = "🟠 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "⚪ LOW"


@dataclass
class GammaSnapshot:
    """Complete gamma exposure snapshot from QuantWheel"""
    symbol: str
    spot: float
    gamma_flip: Optional[float]
    gamma_flip_status: str
    call_wall: Optional[float]
    put_wall: Optional[float]
    net_gex: Optional[float]  # Dealer's net long gamma
    regime: str  # long-gamma-bullish, short-gamma-bearish, unknown
    dealer_exposure_notional: Optional[float]
    timestamp: str
    data_as_of: Dict[str, Any]


@dataclass
class VolSnapshot:
    """Complete IV surface snapshot from QuantWheel"""
    symbol: str
    spot: float
    # ATM volatility
    atm_iv: float
    hv_20: float
    hv_60: Optional[float]
    hv_252: Optional[float]
    # Term structure
    front_month_iv: Optional[float]
    next_month_iv: Optional[float]
    term_structure_slope: Optional[float]
    # Skew
    put_iv_25d: Optional[float]
    atm_iv_level: Optional[float]
    call_iv_25d: Optional[float]
    put_call_iv_ratio: Optional[float]
    # VRP & distribution
    vrp: Optional[float]
    skew_premium: Optional[float]
    tail_risk: Optional[float]
    timestamp: str
    data_as_of: Dict[str, Any]


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


class QuantWheelMonitor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = self._init_client()
        self.last_snapshots = {}
        self.session_signals = []
        
    def _init_client(self):
        """Initialize QuantWheel client"""
        if not QUANTWHEEL_AVAILABLE:
            print("⚠️  QuantWheel SDK not yet installed")
            print("   Stub mode active - ready to accept real API when SDK available")
            return None
        
        try:
            # Initialize with your API key
            client = QuantWheel(api_key=self.api_key)
            print(f"✅ QuantWheel client initialized")
            return client
        except Exception as e:
            print(f"❌ Failed to initialize QuantWheel: {e}")
            return None
    
    def snapshot_gamma(self, symbol: str) -> Optional[GammaSnapshot]:
        """Capture gamma snapshot from QuantWheel"""
        if not self.client:
            # Stub mode: return None to signal unavailable
            return self._stub_gamma_snapshot(symbol)
        
        try:
            # QuantWheel gamma analysis
            result = self.client.gamma_analysis(
                symbol=symbol,
                expiration="current",  # Today's expiration for 0DTE analysis
                include_dealer_exposure=True,
                include_regime=True
            )
            
            gamma = result.get("gamma_exposure", {})
            dealer = result.get("dealer_position", {})
            
            return GammaSnapshot(
                symbol=symbol,
                spot=result.get("spot"),
                gamma_flip=gamma.get("flip_level"),
                gamma_flip_status=gamma.get("flip_status", "unavailable"),
                call_wall=gamma.get("call_wall_level"),
                put_wall=gamma.get("put_wall_level"),
                net_gex=dealer.get("net_long_gamma"),
                regime=result.get("regime", "unknown"),
                dealer_exposure_notional=dealer.get("notional_exposure"),
                timestamp=datetime.utcnow().isoformat() + "Z",
                data_as_of=result.get("data_as_of", {})
            )
        except Exception as e:
            print(f"❌ Error capturing gamma snapshot for {symbol}: {e}")
            return self._stub_gamma_snapshot(symbol)
    
    def snapshot_vol_surface(self, symbol: str) -> Optional[VolSnapshot]:
        """Capture complete IV surface from QuantWheel"""
        if not self.client:
            # Stub mode
            return self._stub_vol_snapshot(symbol)
        
        try:
            # QuantWheel IV surface analysis
            result = self.client.volatility_surface(
                symbol=symbol,
                include_skew=True,
                include_term=True,
                include_distribution=True,
                include_vrp=True
            )
            
            surface = result.get("surface", {})
            skew = result.get("skew", {})
            term = result.get("term", {})
            vrp = result.get("vrp", {})
            dist = result.get("distribution", {})
            
            return VolSnapshot(
                symbol=symbol,
                spot=result.get("spot"),
                atm_iv=surface.get("atm_iv"),
                hv_20=surface.get("historical_vol"),
                hv_60=None,
                hv_252=None,
                front_month_iv=term.get("front_iv"),
                next_month_iv=term.get("back_iv"),
                term_structure_slope=term.get("term_slope"),
                put_iv_25d=skew.get("put_iv"),
                atm_iv_level=skew.get("call_iv"),
                call_iv_25d=skew.get("call_iv"),
                put_call_iv_ratio=skew.get("put_call_ratio"),
                vrp=vrp.get("vrp_level"),
                skew_premium=dist.get("skew_premium"),
                tail_risk=dist.get("kurtosis"),
                timestamp=datetime.utcnow().isoformat() + "Z",
                data_as_of=result.get("data_as_of", {})
            )
        except Exception as e:
            print(f"❌ Error capturing vol snapshot for {symbol}: {e}")
            return self._stub_vol_snapshot(symbol)
    
    def _stub_gamma_snapshot(self, symbol: str) -> GammaSnapshot:
        """Stub gamma snapshot (placeholder until real API)"""
        return GammaSnapshot(
            symbol=symbol,
            spot=None,
            gamma_flip=None,
            gamma_flip_status="sdk_unavailable",
            call_wall=None,
            put_wall=None,
            net_gex=None,
            regime="unknown",
            dealer_exposure_notional=None,
            timestamp=datetime.utcnow().isoformat() + "Z",
            data_as_of={}
        )
    
    def _stub_vol_snapshot(self, symbol: str) -> VolSnapshot:
        """Stub vol snapshot (placeholder until real API)"""
        return VolSnapshot(
            symbol=symbol,
            spot=None,
            atm_iv=None,
            hv_20=None,
            hv_60=None,
            hv_252=None,
            front_month_iv=None,
            next_month_iv=None,
            term_structure_slope=None,
            put_iv_25d=None,
            atm_iv_level=None,
            call_iv_25d=None,
            put_call_iv_ratio=None,
            vrp=None,
            skew_premium=None,
            tail_risk=None,
            timestamp=datetime.utcnow().isoformat() + "Z",
            data_as_of={}
        )
    
    def detect_convergence_signals(self, gamma: Optional[GammaSnapshot], vol: Optional[VolSnapshot]) -> List[ConvergenceSignal]:
        """Detect convergence signals from gamma + vol data"""
        signals = []
        
        if not gamma or not vol:
            return signals
        
        symbol = gamma.symbol
        
        # 1️⃣ SHORT GAMMA + IV EXPANSION = Dealers losing on convexity
        if gamma.regime and "short-gamma" in gamma.regime and vol.atm_iv and vol.hv_20:
            iv_premium = (vol.atm_iv - vol.hv_20) / vol.hv_20
            if iv_premium > 0.10:  # >10% premium
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.CRITICAL,
                    signal_type="SHORT_GAMMA_IV_EXPANSION",
                    symbol=symbol,
                    description="Dealers short gamma losing on convexity - peak acceleration risk",
                    threshold_metric="short-gamma regime + ATM IV > HV 20d by >10%",
                    current_value=f"Regime: {gamma.regime}, IV premium: {iv_premium*100:+.1f}%",
                    recommendation="Highest risk of sharp directional acceleration; dealers forced to hedge pro-cyclically"
                ))
        
        # 2️⃣ SHORT GAMMA REGIME
        if gamma.regime and "short-gamma" in gamma.regime:
            signals.append(ConvergenceSignal(
                severity=SignalSeverity.CRITICAL,
                signal_type="SHORT_GAMMA_REGIME",
                symbol=symbol,
                description="Dealers short gamma - moves will accelerate without natural stickiness",
                threshold_metric="regime = short-gamma-bearish or short-gamma-bullish",
                current_value=f"Current regime: {gamma.regime}",
                recommendation="Watch for wall rejections; price moves will persist longer; expect bigger swings"
            ))
        
        # 3️⃣ CALL WALL + SHORT SKEW = Dealer supply resistance
        if gamma.call_wall and vol.put_call_iv_ratio and vol.put_call_iv_ratio > 1.05 and gamma.spot:
            pct_to_wall = abs(gamma.call_wall - gamma.spot) / gamma.spot
            if pct_to_wall < 0.01:  # Within 1% of spot
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.HIGH,
                    signal_type="CALL_WALL_SHORT_SKEW",
                    symbol=symbol,
                    description="Price near call wall with put skew elevated - dealer supply/resistance",
                    threshold_metric="spot within 1% of call_wall + put/call IV ratio > 1.05",
                    current_value=f"Spot: ${gamma.spot:.2f}, Call wall: ${gamma.call_wall:.2f}, Put/call IV: {vol.put_call_iv_ratio:.3f}",
                    recommendation="Expect price rejection at wall; dealers likely supplying calls at this level"
                ))
        
        # 4️⃣ PUT WALL + LONG SKEW = Dealer floor
        if gamma.put_wall and vol.put_call_iv_ratio and vol.put_call_iv_ratio < 0.95 and gamma.spot:
            pct_to_wall = abs(gamma.put_wall - gamma.spot) / gamma.spot
            if pct_to_wall < 0.01:  # Within 1% of spot
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.HIGH,
                    signal_type="PUT_WALL_LONG_SKEW",
                    symbol=symbol,
                    description="Price near put wall with call skew elevated - dealer support floor",
                    threshold_metric="spot within 1% of put_wall + put/call IV ratio < 0.95",
                    current_value=f"Spot: ${gamma.spot:.2f}, Put wall: ${gamma.put_wall:.2f}, Put/call IV: {vol.put_call_iv_ratio:.3f}",
                    recommendation="Dealer floor likely holding; protection is expensive; downside limited"
                ))
        
        # 5️⃣ GEX SIGN FLIP = Major dealer repositioning
        last_snapshot = self.last_snapshots.get(symbol)
        if last_snapshot and gamma.net_gex and last_snapshot.get("net_gex"):
            sign_change = (gamma.net_gex > 0) != (last_snapshot["net_gex"] > 0)
            if sign_change:
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.MEDIUM,
                    signal_type="GEX_SIGN_FLIP",
                    symbol=symbol,
                    description=f"Dealer positioning flipped from {'long' if last_snapshot['net_gex'] > 0 else 'short'} to {'short' if gamma.net_gex > 0 else 'long'} gamma",
                    threshold_metric="net_gex changed sign (positive ↔ negative)",
                    current_value=f"Previous: {last_snapshot['net_gex']:+,.0f}, Now: {gamma.net_gex:+,.0f}",
                    recommendation="Major repositioning event; wall effectiveness may degrade; expect more volatile action"
                ))
        
        # 6️⃣ GAMMA FLIP MATERIAL MOVE = Dealers repositioned ~$1-2B notional
        if last_snapshot and gamma.gamma_flip and last_snapshot.get("gamma_flip") and gamma.spot:
            flip_move = abs(gamma.gamma_flip - last_snapshot["gamma_flip"]) / gamma.spot
            if flip_move > 0.003:  # >0.3% of spot
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.MEDIUM,
                    signal_type="GAMMA_FLIP_MATERIAL_MOVE",
                    symbol=symbol,
                    description="Gamma flip moved significantly - dealers repositioned ~$1-2B notional",
                    threshold_metric="gamma_flip moved >0.3% of spot",
                    current_value=f"Previous flip: ${last_snapshot['gamma_flip']:.2f}, Now: ${gamma.gamma_flip:.2f}, Move: {flip_move*100:+.2f}%",
                    recommendation="New flip level is new dealer boundary; old dealers likely took risk off"
                ))
        
        # 7️⃣ HIGH VRP + TERM EXPANSION = Vol likely to crush
        if vol.vrp and vol.vrp > 0.15 and vol.front_month_iv and vol.next_month_iv:
            term_slope = (vol.next_month_iv - vol.front_month_iv) / vol.front_month_iv if vol.front_month_iv else None
            if term_slope and term_slope > 0.03:  # Front month cheap, back month rich
                signals.append(ConvergenceSignal(
                    severity=SignalSeverity.MEDIUM,
                    signal_type="HIGH_VRP_TERM_EXPANSION",
                    symbol=symbol,
                    description="High variance risk premium with term expansion - vol contraction likely",
                    threshold_metric="VRP > 0.15 + term_slope > 3%",
                    current_value=f"VRP: {vol.vrp:.3f}, Front/next IV: {vol.front_month_iv:.2f}% / {vol.next_month_iv:.2f}%, Term slope: {term_slope*100:.1f}%",
                    recommendation="Sell vol into strength; monitor for term compression"
                ))
        
        return signals
    
    def print_check(self, check_num: int, gamma: Optional[GammaSnapshot], vol: Optional[VolSnapshot], signals: List[ConvergenceSignal]):
        """Print formatted check output"""
        print(f"\n{'='*80}")
        print(f"CHECK #{check_num} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*80}")
        print(f"Data source: {'QuantWheel SDK Active' if self.client else 'QuantWheel SDK (Stub mode - awaiting SDK)'}")
        
        if gamma:
            print(f"\n{gamma.symbol} GAMMA SNAPSHOT:")
            if gamma.spot:
                print(f"  Spot:                     ${gamma.spot:.2f}")
            if gamma.gamma_flip:
                print(f"  Gamma Flip:               ${gamma.gamma_flip:.2f} ({gamma.gamma_flip_status})")
            if gamma.call_wall:
                print(f"  Call Wall:                ${gamma.call_wall:.2f}")
            if gamma.put_wall:
                print(f"  Put Wall:                 ${gamma.put_wall:.2f}")
            if gamma.net_gex:
                print(f"  Net GEX (Dealer):         {gamma.net_gex:+,.0f} notional")
            if gamma.dealer_exposure_notional:
                print(f"  Dealer Exposure:          ${gamma.dealer_exposure_notional:+,.0f}")
            print(f"  Gamma Regime:             {gamma.regime}")
        
        if vol:
            print(f"\n{vol.symbol} VOLATILITY SURFACE:")
            if vol.spot:
                print(f"  Spot:                     ${vol.spot:.2f}")
            if vol.atm_iv:
                print(f"  ATM IV:                   {vol.atm_iv:.2f}%")
            if vol.hv_20:
                print(f"  HV 20d:                   {vol.hv_20:.2f}%")
            if vol.hv_60:
                print(f"  HV 60d:                   {vol.hv_60:.2f}%")
            if vol.front_month_iv and vol.next_month_iv:
                term_slope = (vol.next_month_iv - vol.front_month_iv) / vol.front_month_iv
                print(f"  Term Structure:           {vol.front_month_iv:.2f}% → {vol.next_month_iv:.2f}% (slope: {term_slope*100:+.1f}%)")
            if vol.put_call_iv_ratio:
                print(f"  Put/Call IV Ratio:        {vol.put_call_iv_ratio:.3f}")
            if vol.vrp:
                print(f"  Variance Risk Premium:    {vol.vrp:.3f}")
            if vol.tail_risk:
                print(f"  Tail Risk Score:          {vol.tail_risk:.2f}")
        
        if signals:
            print(f"\n🚨 CONVERGENCE SIGNALS ({len(signals)} detected):")
            for sig in signals:
                print(f"\n  {sig.severity.value} | {sig.signal_type}")
                print(f"    └─ {sig.description}")
                print(f"    └─ Threshold: {sig.threshold_metric}")
                print(f"    └─ Current:   {sig.current_value}")
                print(f"    └─ Action:    {sig.recommendation}")
        else:
            print(f"\n✅ No convergence signals detected this check")
        
        # Store snapshot for next iteration
        if gamma:
            self.last_snapshots[gamma.symbol] = asdict(gamma)
    
    def run(self, symbols: List[str], interval_seconds: int = 1800, num_checks: int = 12):
        """Run monitoring loop"""
        print(f"\n{'='*80}")
        print(f"🚀 UNIFIED GAMMA + VOL MONITOR (QuantWheel-Powered)")
        print(f"{'='*80}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Check interval: {interval_seconds}s | Total checks: {num_checks}")
        print(f"Market hours: 09:30 - 16:00 ET (currently after-hours test)")
        
        if not self.client:
            print(f"\n⚠️  STUB MODE - QuantWheel SDK not yet installed")
            print(f"   Once installed, this script will provide:")
            print(f"   • Gamma flip tracking (dealer repositioning)")
            print(f"   • Call/put walls (dealer supply/demand)")
            print(f"   • Net GEX (dealer gamma exposure)")
            print(f"   • Regime classification (long/short gamma)")
            print(f"   • Complete IV surface + skew + term")
            print(f"   • VRP + realized vol + distribution")
        
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
        session_file = f"quantwheel_gamma_vol_monitor_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(session_file, "w") as f:
            json.dump({
                "sdk_available": QUANTWHEEL_AVAILABLE,
                "symbols": symbols,
                "checks": num_checks,
                "interval_seconds": interval_seconds,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, f, indent=2)
        
        print(f"\n✅ Session saved to: {session_file}")


def main():
    api_key = os.getenv("QUANTWHEEL_API_KEY")
    if not api_key:
        print("ℹ️  QUANTWHEEL_API_KEY environment variable not set")
        print("   Running in stub mode (SDK integration ready, awaiting API key)")
        print("   Set with: export QUANTWHEEL_API_KEY='your-key'")
        api_key = "stub-key"  # Stub mode
    
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
    
    monitor = QuantWheelMonitor(api_key)
    monitor.run(symbols, interval, checks)


if __name__ == "__main__":
    main()
