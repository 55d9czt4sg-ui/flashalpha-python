# Unified Intraday Gamma + QuantWheel Vol Monitoring

Complete system for real-time dealer positioning + volatility surface tracking during market hours.

## System Architecture

```
FlashAlpha API (Gamma/Dealer Flow)  +  QuantWheel API (IV Surface/Skew)
              ↓                                      ↓
    [Gamma Snapshot]                    [Vol Surface Snapshot]
    • Gamma flip ±0.25-0.50%          • ATM IV, skew, term structure
    • Call/put walls                   • Put/call vol ratio
    • Net GEX (regime)                 • Realized vs implied
    • DEX (dealer GEX)                 • Vol risk premium
              ↓                                      ↓
              └──────────[Convergence Engine]───────┘
                              ↓
                      [Signal Detection]
                      • Wall + skew combos
                      • Short gamma + IV expansion
                      • GEX regime flips
                      • Positive VRP + high vol
                              ↓
                   [JSON Session File]
                   → Next: Post-market OI analysis
```

## Installation

```bash
cd /path/to/flashalpha-python
python -m venv venv
source venv/bin/activate
pip install -e .
```

## API Keys

Obtain free tier keys:
- **FlashAlpha**: https://flashalpha.com (free tier returns previous-day snapshot; paid tiers get real-time)
- **QuantWheel**: Not yet integrated; placeholder structure ready for when API is available

Set environment:
```bash
export FLASHALPHA_API_KEY="your-flashalpha-key"
export QUANTWHEEL_API_KEY="your-quantwheel-key"  # Optional
```

## Quick Start

### 1. Test with Synthetic Data (No API Key Required)

```bash
python example_unified_monitoring.py
```

**Output**: 4 checks showing gamma flip transitions and real-time vol surface dynamics
- Check 1–2: Long-gamma regime; dealers providing support
- Check 3: **Regime flip to SHORT gamma**; vol expanding; critical signals
- Check 4: Sustained short-gamma; acceleration risk

This demonstrates the complete workflow and signal types.

### 2. Run Live During Market Hours

```bash
python unified_gamma_vol_monitor.py SPY,QQQ \
    --interval 1800 \
    --checks 12
```

**Parameters**:
- `symbols`: Comma-separated (default: `SPY,QQQ`)
- `--interval`: Seconds between checks (default: 1800 = 30 min)
- `--checks`: Total checks to run (default: 12 ≈ 6 hours for 30-min intervals)

**Typical schedule** (9:30 AM – 4:00 PM ET):
```bash
# 30-min checks: 12 total = 6 hours
python unified_gamma_vol_monitor.py SPY,QQQ --interval 1800 --checks 12

# Or hourly: 7 checks
python unified_gamma_vol_monitor.py SPY,QQQ --interval 3600 --checks 7

# Custom symbols
python unified_gamma_vol_monitor.py SPY,QQQ,IWM --interval 1800 --checks 12
```

### 3. Post-Market Analysis (Next Morning)

After OCC publishes settlement OI (typically 8:00–8:30 AM ET):

```bash
python post_market_analysis.py \
    unified_gamma_vol_monitor_YYYYMMDD_HHMMSS.json \
    --today-volume 45000000 \
    --oi-today 55000000 \
    --oi-yesterday 52000000
```

Classifies dealer activity:
- **Opening**: Volume ↑↑, OI ↑↑ → Gamma map persists into next session
- **Closing**: Volume ↑↑, OI ↓↓ → Dealers unwinding; map effect fades
- **Intraday**: Volume ↑, OI ~flat → Spreads/rolls; positioning unchanged

## Signal Types & Interpretations

### 🟠 CALL_WALL_SHORT_SKEW
**Pattern**: Price near call wall + call IV lower than ATM

**Interpretation**:
- Dealer supply concentrated at call wall (high call OI)
- Call IV is cheap = upside risk already priced
- Dealers are protecting sellers (seller hedging demand)

**Trade Setup**: Watch for price rejection at wall; dealer defense likely

---

### 🟠 PUT_WALL_LONG_SKEW
**Pattern**: Price near put wall + put IV elevated vs ATM

**Interpretation**:
- Dealer floor at put wall (high put OI)
- Put IV premium elevated = protection demand high
- Risk premium concentrated in downside

**Trade Setup**: If price breaks below wall, watch for put skew collapse + vol expansion

---

### 🔴 SHORT_GAMMA_IV_EXPANSION
**Pattern**: Regime shows "short-gamma-bearish" + IV expanding vs realized vol

**Interpretation**:
- Dealers are **NET SHORT gamma** (pro-cyclical hedging)
- IV expansion = dealers losing on convexity
- Each price move accelerates vol increase
- Dealer hedging amplifies market moves

**Trade Setup**: Anticipate sharp moves, vol spikes, and potential acceleration

---

### 🔴 SHORT_GAMMA_REGIME
**Pattern**: Net GEX < -300k + regime flips to short-gamma

**Interpretation**:
- Dealers flipped from long to short gamma (or vice versa)
- Market stickiness disappeared; moves accelerate
- Gamma pinning less likely at expiry
- Dealer hedging is pro-cyclical (amplifies moves)

**Trade Setup**: Trade momentum; expect directional runs into expiry

---

### 🟡 POSITIVE_VRP_HIGH_ATM
**Pattern**: Volatility risk premium > 0 + ATM IV elevated

**Interpretation**:
- Implied vol > Realized vol = selling vol is rewarded
- Mean reversion candidate (vol likely to crush)
- If driven by put demand: short vol is directional hedge

**Trade Setup**: Short vol strategies gain; monitor for crush into lower realized

---

### 🟡 GAMMA_FLIP_MATERIAL_MOVE
**Pattern**: Flip moved ±0.3% or more from previous check

**Interpretation**:
- Dealers adjusted hedge exposure significantly
- New flip level is long-gamma boundary
- If price approaches flip: watch for support/resistance
- Indicates major repositioning event

**Trade Setup**: Mark new flip on chart; compare to term structure for edge

---

### 🟡 GEX_SIGN_FLIP
**Pattern**: Net GEX changed sign (long ↔ short)

**Interpretation**:
- **Critical regime shift** in dealer positioning
- Stickiness disappeared; market became acceleratory
- Wall effectiveness decreased (dealer no longer defending)
- Major flow/gamma event likely triggered flip

**Trade Setup**: Major positioning change; anticipate vol/flow changes

---

## Convergence Logic: Gamma + Vol Working Together

### Setup 1: Price at Call Wall + Short Call Skew

```
GAMMA:          VOL:              RESULT:
Call wall       Call IV < ATM      Dealers protecting sellers
High call OI    Low upside vol      Risk premium priced out
                                    → Price rejection likely
                                    → Low edge for buyers
```

**Action**: Expect price to reject at wall or pullback before breaking

---

### Setup 2: Price at Put Wall + Long Put Skew

```
GAMMA:          VOL:              RESULT:
Put wall        Put IV >> ATM      Dealers providing floor
High put OI     Elevated downside  But protection expensive
                vol premium        → Breakout carries upside squeeze
                                    → Vol crush on hold
```

**Action**: If break below wall: watch for put IV collapse + short-vol dislocation

---

### Setup 3: Short-Gamma Regime + IV Expanding

```
GAMMA:          VOL:              RESULT:
GEX << 0        IV ↑ vs RV        Dealers losing on convexity
Short gamma     Vol expanding      Each move amplifies next move
Dealers short   Market accelerates Hedging is PRO-cyclical
                                   → Spikes and sharp moves
```

**Action**: Trade momentum; expect vol acceleration on directional moves

---

### Setup 4: Long-Gamma Regime + IV Contracting

```
GAMMA:          VOL:              RESULT:
GEX >> 0        IV ↓ vs RV        Dealers profiting on convexity
Long gamma      Vol crushing       Market mean-reverts
Dealers long    Moves get dampened Hedging is ANTI-cyclical
                                   → Sticky, rangebound
```

**Action**: Fade extremes; expect pullbacks and mean reversion

---

## Data Freshness & Feed Status

Every response includes `data_as_of` per feed:

```python
{
  "data_as_of": {
    "equity_feed": "2024-09-24T14:23:15Z",
    "equity_options_feed": "2024-09-24T14:22:45Z",
    "flow_feed": "2024-09-24T14:23:00Z",
    "oi_feed": "2024-09-24T16:00:00Z",  # Settled at prior close
  }
}
```

**Interpretation**:
- **During market hours**: equity/options/flow should be minutes old
- **OI feed**: Settled once per session at prior close (normal if 1+ days behind)
- **Null feed**: That node hasn't seen the feed yet; don't assume stale
- **Compare timestamps directly**: Don't parse for semantic meaning; just check recency

## Workflow: Full Day Example

### 9:30 AM ET (Market Open)

```bash
python unified_gamma_vol_monitor.py SPY,QQQ --interval 1800 --checks 12
```

**Console output**:
```
🎯 UNIFIED GAMMA + VOL MONITOR
📊 Symbols: SPY, QQQ
📍 Interval: 1800s (30m)
🔁 Checks: 12
💾 Output: unified_gamma_vol_monitor_20240924_093000.json

[09:30:15] OPENING
================================================================
📊 SPY:
  Spot: $565.23 | Flip: $562.75
  Walls: Call $567.50 / Put $562.75
  GEX:    +850,000 | Regime: long-gamma-bullish
  
  ✨ No signals (normal start)
```

### 10:00 AM ET (First Check)

```
[10:00:22] CHECK 2
================================================================
📊 SPY:
  Spot: $565.89 | Flip: $563.10
  Walls: Call $568.00 / Put $563.00
  GEX:    +720,000 | Regime: long-gamma-bullish
  
  ✨ No signals (stable long gamma)
```

### 11:00 AM ET (Unexpected Move)

```
[11:01:45] CHECK 4
================================================================
📊 SPY:
  Spot: $563.50 | Flip: $560.85
  Walls: Call $567.00 / Put $560.85
  GEX:   -120,000 | Regime: MIXED
  
  🚨 SIGNALS (2):
    🟡 [MEDIUM] GAMMA_FLIP_MATERIAL_MOVE
       Flip moved $562.75 → $560.85 (-0.32%)
       • Dealers adjusted hedge exposure significantly
       • New flip at $560.85: dealers' long-gamma boundary
       • If price approaches: watch for gamma support/resistance
    
    🟡 [MEDIUM] SHORT_GAMMA_REGIME
       GEX: -120,000 | Dealer positioning shifted short
       • Market stickiness degrading
       • Acceleration risk on next move
```

### 12:30 PM ET (Continued Weakness)

```
[12:32:10] CHECK 6
================================================================
📊 SPY:
  Spot: $561.75 | Flip: $559.20
  Walls: Call $565.50 / Put $559.20
  GEX:   -380,000 | Regime: short-gamma-bearish
  
  🚨 SIGNALS (3):
    🔴 [CRITICAL] SHORT_GAMMA_IV_EXPANSION
       Regime: short-gamma-bearish | IV $0.22 >> RV $0.15
       • Dealers are SHORT gamma (pro-cyclical hedging)
       • IV expanding means dealers are losing on convexity
       • Each price move accelerates vol increase = dealer pain
    
    🔴 [CRITICAL] SHORT_GAMMA_REGIME
       GEX: -380,000 | Regime: SHORT GAMMA
       • Dealers are NET short gamma
       • Market stickiness gone; moves accelerate
       • Gamma pin at expiry less likely
    
    🟠 [HIGH] PUT_WALL_LONG_SKEW
       Price $561.75 near put wall $559.20; puts premium elevated
       • Dealer floor at $559.20 (OI concentration)
       • Put IV elevated vs ATM = protection demand high
       • Break below wall = vol crush risk on expiry day
```

### 4:00 PM ET (Market Close)

Monitor completes. JSON session saved with all snapshots + signals.

### Next Morning (8:30 AM ET, After OI Update)

```bash
# Get volumes from broker/market data
python post_market_analysis.py unified_gamma_vol_monitor_20240924_093000.json \
    --today-volume 47200000 \
    --oi-today 58950000 \
    --oi-yesterday 55200000

# Output:
# CLASSIFICATION: OPENING ACTIVITY
# Volume up 4.5% | OI up 6.8%
# → Gamma map changes will likely persist into today (Thursday)
# → New dealer positioning from Wednesday; rehedging expected today
```

## Troubleshooting

### No output / "Error capturing snapshot"

**Cause**: API key invalid or tier restricted

**Fix**:
```bash
# Test API key directly
python3 << 'EOF'
from flashalpha import FlashAlpha
client = FlashAlpha("YOUR_API_KEY")
exp = client.exposure_summary("SPY")
print(exp)
EOF
```

If error: key is invalid or account tier too low. Upgrade at https://flashalpha.com

---

### "Tier restricted" message

**Cause**: `exposure_summary()` requires paid tier

**Fix**: Upgrade FlashAlpha account to access real-time data

Free tier only provides previous-day cached snapshot via `stock_summary()`.

---

### Feeds showing as null

**Cause**: That node hasn't received the feed yet; not stale

**Fix**: Continue running; node will hydrate feeds over time. Or use `--checks 1` to see one snapshot, then re-run if needed.

---

### IV data not appearing

**Cause**: QuantWheel integration not yet active

**Status**: Placeholder structure ready; will populate when QuantWheel API is available

**Workaround**: Use gamma data + external vol surface (e.g., VolSurface, OptionMetrics) for now

---

## Files in This System

| File | Purpose |
|------|---------|
| `unified_gamma_vol_monitor.py` | Production live monitoring script; runs 9:30 AM – 4:00 PM ET |
| `example_unified_monitoring.py` | Synthetic data demo; tests without API key |
| `post_market_analysis.py` | Next-morning OI/volume classification (existing) |
| `intraday_gamma_monitor.py` | Original gamma-only monitor (still works standalone) |
| `quantwheel_gamma_integration.py` | Early QuantWheel stub (merged into unified script) |

---

## Next Steps

1. **Get API keys**:
   - FlashAlpha: https://flashalpha.com (free or paid)
   - QuantWheel: Register for beta (optional; placeholder ready)

2. **Test with example**:
   ```bash
   python example_unified_monitoring.py
   ```

3. **Run live during market hours**:
   ```bash
   export FLASHALPHA_API_KEY="your-key"
   python unified_gamma_vol_monitor.py SPY,QQQ
   ```

4. **Analyze post-market**:
   ```bash
   python post_market_analysis.py unified_gamma_vol_monitor_YYYYMMDD_HHMMSS.json \
       --today-volume <vol> --oi-today <oi> --oi-yesterday <prev_oi>
   ```

5. **Iterate**:
   - Track which signals predict price action
   - Refine thresholds (flip move %, wall proximity %)
   - Log entry/exit results against signals

---

## Reference: Signal Severity Levels

- 🔴 **CRITICAL** (immediate attention):
  - Short-gamma regime flip
  - GEX sign flip
  - Major regime shifts
  
- 🟠 **HIGH** (material change):
  - Call/put wall proximity + skew patterns
  - Significant gamma flip move
  
- 🟡 **MEDIUM** (watch closely):
  - Positive VRP + high ATM vol
  - Regime gradient changes
  
- ⚪ **LOW** (informational):
  - Minor moves
  - Confirmations

---

## Support & Further Resources

- **FlashAlpha Playground**: https://lab.flashalpha.com/swagger (try endpoints live)
- **Custom Instructions**: See `AGENTS.md` for SDK usage guidelines
- **Historical Data**: Use `flashalpha-historical` package for backtesting on dates like 2020-03-16 (gamma regime flips)

---

**Last Updated**: 2024-09-24  
**Version**: Unified Gamma + QuantWheel v1.0  
**Status**: Production-ready (QuantWheel integration placeholder)
