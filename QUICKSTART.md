# Quick Start: Intraday Gamma Monitoring

## TL;DR

### Step 1: Test (No API Key Needed)
```bash
source venv/bin/activate
python example_unified_monitoring.py
```
✅ Shows 4 checks with gamma regime shift and real signals

---

### Step 2: Run Live (Requires API Key)
```bash
export FLASHALPHA_API_KEY="your-key"
python unified_gamma_vol_monitor.py SPY,QQQ --interval 1800 --checks 12
```
Runs 9:30 AM – 4:00 PM ET with 30-min checks

---

### Step 3: Analyze Next Morning (After OI Updates)
```bash
python post_market_analysis.py unified_gamma_vol_monitor_YYYYMMDD_HHMMSS.json \
    --today-volume 47200000 \
    --oi-today 58950000 \
    --oi-yesterday 55200000
```
Classifies dealer activity type

---

## Key Signals

| Signal | Severity | When It Fires | What It Means |
|--------|----------|---------------|--------------|
| SHORT_GAMMA_IV_EXPANSION | 🔴 CRITICAL | GEX < -300k + IV expanding | Dealers short gamma; acceleration risk |
| SHORT_GAMMA_REGIME | 🔴 CRITICAL | GEX flips negative | Regime shift; market stickiness gone |
| CALL_WALL_SHORT_SKEW | 🟠 HIGH | Price near call wall + low call IV | Dealer supply; price rejection likely |
| PUT_WALL_LONG_SKEW | 🟠 HIGH | Price near put wall + high put IV | Dealer floor; protection expensive |
| GAMMA_FLIP_MATERIAL_MOVE | 🟡 MEDIUM | Flip moves ±0.3%+ of spot | Major dealer repositioning |
| GEX_SIGN_FLIP | 🟡 MEDIUM | Net GEX changes sign | Major positioning shift |
| POSITIVE_VRP_HIGH_ATM | 🟡 MEDIUM | IV > RV + ATM vol elevated | Vol likely to crush; sell vol candidate |

---

## What to Track

### Opening (9:30 AM)
```
 Gamma flip + walls + GEX + regime
 → Baseline dealer positioning
```

### Every 30–60 min
```
 Same metrics → Compare to prior check
 → Flag if flip moves ±0.25-0.50%, walls shift ±1 strike, regime flips
```

### Major moves
```
 If price gaps or volatility spikes:
 → Check immediately (don't wait for next interval)
 → IV may be expanding (dealer short gamma signal)
```

### Close (4:00 PM)
```
 Final snapshot → Save JSON
 → Ready for post-market analysis
```

---

## Example: Reading a Signal

**Output**:
```
🔴 [CRITICAL] SHORT_GAMMA_IV_EXPANSION
   Regime: short-gamma-bearish | IV $0.22 >> RV $0.15
   • Dealers are SHORT gamma (pro-cyclical hedging)
   • IV expanding means dealers are losing on convexity
   • Each price move accelerates vol increase = dealer pain
```

**Translation**:
- Dealers flipped to **short gamma** (they're NET SHORT; hedging amplifies moves)
- **IV is expanding** (implied vol $0.22 > realized vol $0.15)
- This means dealers are **losing money** on the convexity they're short
- **Each price move** that happens next will **accelerate the move further** (their hedging is pro-cyclical)
- **Action**: Expect sharp moves, potential spikes, momentum trading

---

## Material Change Thresholds

Use these to know when a change is "worth noticing":

| Metric | Material Move |
|--------|----------------|
| Gamma flip | ±0.25–0.50% of spot (e.g., ±$1.41 for SPY at $562) |
| Call/put wall | ±1 strike increment (e.g., $565 → $566 or $564) |
| GEX regime | Sign flip (long ↔ short gamma) |
| Check frequency | 30–60 min during market hours |

---

## Post-Market Analysis: What to Compare

**Next morning** (after 8:30 AM ET OCC settlement):

```
Volume TODAY   vs   OI TODAY     →  Classification
──────────────────────────────────────────────────
↑ (up 5%+)          ↑ (up 2%+)   →  OPENING (dealers added exposure)
↑ (up 5%+)          ↓ (down 2%+) →  CLOSING (dealers reduced exposure)
↑ (up 5%+)          → (flat ±2%) →  INTRADAY (spreads, rolls, transfers)
```

**Meaning**:
- **OPENING**: Yesterday's gamma map likely persists today; rehedging expected
- **CLOSING**: Dealers unwound yesterday; map effect fading
- **INTRADAY**: Positioning unchanged; yesterday's dealer flows internal only

---

## Getting API Keys

### FlashAlpha
1. Go to https://flashalpha.com
2. Sign up (free tier available)
3. Dashboard → API keys
4. Copy key and set: `export FLASHALPHA_API_KEY="key"`

**Tiers**:
- Free: Previous-day cached snapshots (good for demos)
- Paid: Real-time data during market hours

### QuantWheel
- Optional for pilot; structure ready
- Set when available: `export QUANTWHEEL_API_KEY="key"`

---

## Running Options

```bash
# Default: SPY + QQQ, 30-min checks, 12 total (≈6 hours)
python unified_gamma_vol_monitor.py

# Custom symbols & interval
python unified_gamma_vol_monitor.py SPY,QQQ,IWM --interval 3600 --checks 7

# 15-min checks (more frequent monitoring)
python unified_gamma_vol_monitor.py SPY --interval 900 --checks 24

# Synthetic test (no API key)
python example_unified_monitoring.py
```

---

## Files in the System

| File | Use |
|------|-----|
| `unified_gamma_vol_monitor.py` | **Live market-hours monitoring** |
| `example_unified_monitoring.py` | **Test without API key** |
| `post_market_analysis.py` | **Next-day OI classification** |
| `intraday_gamma_monitor.py` | Gamma-only (original; still works) |
| `UNIFIED_MONITORING_GUIDE.md` | Full documentation |

---

## Troubleshooting

**"Error capturing snapshot"**
→ API key invalid or tier too low. Test key with:
```bash
python3 -c "from flashalpha import FlashAlpha; client = FlashAlpha('KEY'); print(client.exposure_summary('SPY'))"
```

**"Tier restricted"**
→ Free tier doesn't support `exposure_summary()`. Upgrade at https://flashalpha.com

**Feeds showing null**
→ Normal; node hydrating. Continue running; will populate.

**No IV data (QuantWheel fields empty)**
→ QuantWheel integration placeholder; not yet active. Add your key when available.

---

## Data Freshness: What's Current?

After each check, look at `data_as_of`:

```python
"data_as_of": {
  "equity_feed": "2024-09-24T14:23:15Z",     # ← Should be minutes old (during market hours)
  "equity_options_feed": "2024-09-24T14:22:45Z",  # ← Should be minutes old
  "flow_feed": "2024-09-24T14:23:00Z",       # ← Should be minutes old
  "oi_feed": "2024-09-24T16:00:00Z",        # ← Settled at prior close (normal if 1+ days old)
}
```

✅ **OK**: intraday feeds within 2–5 min, OI at prior close  
❌ **Stale**: intraday feeds > 30 min old  
🤔 **Unknown**: feed is `null` (node hasn't seen it yet; not stale, just waiting)

---

## Key Takeaway

**The workflow**:
1. Snap gamma + vol every 30–60 min
2. Flag moves ≥ material thresholds
3. Each signal tells you how dealers are positioned
4. Next morning: compare volume/OI to classify dealer intent
5. Iterate: track which signals predicted price action

**You're building a real-time map of dealer Greeks** and using vol surface to confirm the signals. This is how prop traders detect gamma-driven moves and anticipate acceleration.

---

**Ready?** Start with:
```bash
python example_unified_monitoring.py
```
