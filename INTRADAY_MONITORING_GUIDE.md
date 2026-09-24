# Intraday Gamma & Dealer Positioning Monitor

Complete workflow for tracking dealer gamma exposure, call/put walls, and options-driven price action during market hours.

## Overview

This toolset implements the full intraday monitoring workflow:

1. **Record opening** gamma flip, walls, GEX, DEX at 9:30 AM ET
2. **Poll every 30–60 minutes** and flag material changes
3. **Correlate with price** rejection at walls or breaks below support
4. **Post-market** volume/OI comparison to classify activity type and predict map persistence

## Prerequisites

```bash
# Install FlashAlpha SDK
pip install flashalpha

# Set API key
export FLASHALPHA_API_KEY="your-api-key-here"
```

Get your API key at https://flashalpha.com/dashboard

## Quick Start

### 1. Run Intraday Monitor (9:30 AM – 4:00 PM ET)

```bash
# Monitor SPY & QQQ with 30-minute intervals
python intraday_gamma_monitor.py \
    --symbols SPY,QQQ \
    --interval 1800 \
    --api-key $FLASHALPHA_API_KEY \
    --checks 12

# Or: Monitor single symbol with 1-hour intervals
python intraday_gamma_monitor.py \
    --symbols SPY \
    --interval 3600 \
    --checks 6
```

**Output:**
- Console: Real-time snapshots, material changes, price-action alerts
- JSON file: `gamma_monitor_YYYYMMDD_HHMMSS.json` with full session data

### 2. Post-Market Analysis (After 8 AM ET, next day)

After OCC publishes OI updates (~8:00 AM ET), run:

```bash
python post_market_analysis.py gamma_monitor_20240924_093000.json \
    --today-volume 150000000 \
    --oi-today 45123456 \
    --oi-yesterday 44987654
```

**Output:**
- Activity classification (Opening / Closing / Intraday Trading)
- Recommendation for next trading day
- Summary of material changes and price-action alerts

## What Gets Monitored

### Gamma Flip
- Strike where dealer gamma changes from **Long** → **Short** (or vice versa)
- Flag when it moves ±0.25–0.50% of spot price
- Movement → dealers adjusting directional hedging

### Call Wall & Put Wall
- Call wall: Strike with abnormally high call OI (dealer short call exposure)
  - Typically acts as **resistance**; price tends to reject
- Put wall: Strike with abnormally high put OI (dealer short put exposure)
  - Typically acts as **support**; breaks can signal acceleration
- Flag when walls shift ≥1 full strike increment

### Net Gamma Exposure (GEX)
- **Positive GEX** (Long gamma): Dealers are net long gamma
  - Price action is bullish for dealers (they profit on moves either direction)
  - Market tends to "stick" near current levels
- **Negative GEX** (Short gamma): Dealers are short gamma
  - Price action is pro-cyclical (they're short down, long up)
  - Market accelerates, volatility expands on moves
  - Sign flip = regime shift

### Dealer Delta (DEX)
- Dealers' directional positioning (positive = net long)
- Combined with GEX tells whether dealers are hedging against or amplifying

### Regime
- Market gamma regime label (e.g., "long-gamma", "short-gamma-bullish")
- Flips when dealer positioning materially changes

## Example Workflow

### 9:30 AM ET – Opening Snapshot

```
🎯 Starting Gamma Monitor (SPY, QQQ)
📍 Check interval: 1800s (30m)
💾 Output: gamma_monitor_20240924_093000.json

[09:30:15] 📈 OPENING SNAPSHOT
===========================================================================
SPY:
  Spot: 562.45
  Flip: 561.80
  Walls: Call 566.00 / Put 560.00
  GEX: +1,234,567  DEX: +89,000
  Regime: long-gamma
  Data as of: 2024-09-24T09:30:05Z

QQQ:
  Spot: 489.12
  Flip: 488.50
  Walls: Call 492.00 / Put 487.00
  GEX: -456,789  DEX: -12,000
  Regime: short-gamma-bearish
  Data as of: 2024-09-24T09:30:06Z
```

**Interpretation:**
- **SPY**: Dealers long gamma (bullish for dealers). Call wall at 566 is likely resistance.
- **QQQ**: Dealers short gamma (short-term bullish, vol-positive). Put wall at 487 is support.

### 10:00 AM ET – First Check (30 min later)

```
[10:00:42] CHECK 1 (Interval 30m)
===========================================================================

SPY — MATERIAL CHANGES:
  Spot moved: +0.18%
  🎯 FLIP: 561.80 → 562.15 (0.31% of spot) ↑

QQQ: No material changes. (Spot: 489.08, Regime: short-gamma-bearish)
```

**Interpretation:**
- SPY flip moved up 0.31% → Material change (threshold 0.25%). Dealers hedged higher.
- QQQ stable → No regime shift yet.

### 11:30 AM ET – Second Check

```
[11:30:18] CHECK 2 (Interval 60m)
===========================================================================

SPY — MATERIAL CHANGES:
  Spot moved: +0.51%
  📍 CALL_WALL: 566.00 → 567.00 ↑
  💥 NET_GEX SIGN FLIP: +1,234,567 → -89,456

  🚧 CALL_WALL TEST: Price 566.85 at/near wall 566.00 (dealer supply/resistance?)

QQQ — MATERIAL CHANGES:
  Spot moved: -0.34%
  ⚠️  PUT_WALL BREAK: Price 486.90 below wall 487.00 (SHORT-GAMMA regime) → Watch IV expansion
```

**Interpretation:**
- **SPY**: Call wall moved up; GEX flipped negative (dealers now short gamma). Price tested wall and reversed slightly.
- **QQQ**: Price broke below put wall while in short-gamma regime → Expect vol expansion if move continues.

### 4:00 PM ET – Close

```
✅ Monitoring complete. Session saved.
📝 Next step: Compare today's volume with tomorrow's OI (after 8:00 AM ET)
```

### 8:30 AM ET Next Day – Post-Market Analysis

```bash
$ python post_market_analysis.py gamma_monitor_20240924_093000.json \
    --today-volume 150000000 \
    --oi-today 45123456 \
    --oi-yesterday 44987654

📊 VOLUME & OI:
  Today's volume:  150,000,000
  OI today:        45,123,456
  OI yesterday:    44,987,654
  OI change:       +0.30%

🎯 CLASSIFICATION: INTRADAY_TRADING
   → Volume ↑ but OI ~flat +0.30% → Spreads/rolls/transfers; not reliable dealer repo

✅ GUIDANCE FOR TOMORROW:
  • Activity was likely spreads, rolls, or customer transfers
  • Dealer net positioning may not have changed materially
  • Recheck the gamma map at tomorrow's open; prior day's walls less reliable
```

## Material Change Thresholds

| Signal | Threshold | Interpretation |
|--------|-----------|---|
| **Gamma Flip** | ±0.25–0.50% of spot | Dealer hedge adjustment; directional positioning shift |
| **Call Wall** | ≥1.0 strike increment | Supply migration; resistance level may shift |
| **Put Wall** | ≥1.0 strike increment | Support migration; floor level may shift |
| **Regime** | Change detected | Major shift in dealer gamma bias; volat. regime change |
| **GEX Sign Flip** | Positive ↔ Negative | Dealers switch from long-gamma to short-gamma (or vice versa) |

## Price Action Correlations

### Call Wall Resistance
```
If SPY price approaches call wall while it's high call OI:
  ✓ Repeated rejection → Dealers likely defending resistance
  ✓ Breakout above → Dealers add to short position; vol may spike
  ✓ Reversal → Dealer hedging pressure working
```

### Put Wall Support
```
If price approaches put wall in short-gamma regime:
  ✓ Rejection off wall → Dealer buying support
  ✓ Break below wall → Expect acceleration + vol expansion
  ✓ Quick bounce → Market gamma is helping price recovery
```

## Post-Market Classification

### Opening Activity (OI ↑, Volume ↑)
- Dealers **opened new positions** to control risk
- Gamma map is **likely persistent**
- **Tomorrow's strategy:** Trade off the wall levels; expect them to hold

### Closing Activity (OI ↓, Volume ↑)
- Dealers **closed positions**; OI contracts
- Gamma map effect may **fade as hedges unwind**
- **Tomorrow's strategy:** Recheck opening; walls may shift lower

### Intraday Trading (OI ~flat, Volume ↑)
- Spreads, rolls, or customer-to-customer transfers
- Dealer net positioning **unchanged**
- **Tomorrow's strategy:** Don't assume today's walls persist; recalibrate at open

## Feed Freshness

Every snapshot includes `data_as_of` per feed:

```json
{
  "data_as_of": "2024-09-24T10:00:05.123Z",
  "equity_feed": "2024-09-24T10:00:05.123Z",
  "equity_options_feed": "2024-09-24T10:00:04.891Z",
  "oi_feed": "2024-09-23T16:00:00.000Z",  # Prior session OI (published at close)
  "flow_feed": "2024-09-24T10:00:03.456Z"
}
```

- **Equity/options/flow feeds** within a few minutes of real time during market hours = good
- **OI feed** at prior close = normal (settled OI published once per session)
- **Null feed** = that node hasn't seen that data since startup; don't assume stale

## Advanced: Spread Premium vs Flow

⚠️ **Common pitfall:** Large put flow at the ask doesn't automatically mean bearish.

```
Example: Large put bought at ask
  ├─ Could be: Directional short (bearish) → Use GEX regime to cross-check
  ├─ Could be: Hedge on long stock (bullish intent)
  ├─ Could be: One leg of collar or spread
  └─ Could be: Directional long (risk reversal buyer)
```

**Solution:** Pair flow labels with:
- Gamma regime (dealers short-gamma → flow likely accelerates)
- Wall levels (flow at wall strikes ≠ flow off-wall)
- OI change next day (volume up + OI flat → spreads, not directional)

## Troubleshooting

### `TierRestrictedError`

```
⚠️  SPY: Tier restricted. Upgrade your FlashAlpha plan for exposure_summary().
```

You're on a free or limited plan. Upgrade at https://flashalpha.com/pricing.

### No material changes detected all day

- Market is range-bound and dealer positioning is stable
- This is valid data! Flat gamma regimes don't usually move walls or flips
- Use for **reversal trades** (range support/resistance testing)

### `data_as_of` is very old

- Market may be slow/illiquid (early/late session)
- Check if it's outside regular hours (9:30 AM – 4:00 PM ET)
- If during hours, network/API latency; retry snapshot

## Files

- **`intraday_gamma_monitor.py`** — Main monitoring loop; run 9:30 AM – 4:00 PM ET
- **`post_market_analysis.py`** — Volume/OI classification; run after 8:00 AM ET next day
- **`gamma_monitor_*.json`** — Session output with all snapshots, changes, alerts
- **`INTRADAY_MONITORING_GUIDE.md`** — This file

## Next Steps

1. Set `FLASHALPHA_API_KEY` environment variable
2. Run `python intraday_gamma_monitor.py` at market open tomorrow
3. Let it run through the day (checks every 30 min)
4. After OCC updates OI next morning, run `post_market_analysis.py`
5. Use guidance to calibrate tomorrow's opening strategy

Happy monitoring! 📊
