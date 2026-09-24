# INTRADAY GAMMA MONITORING — SETUP & EXECUTION GUIDE

This guide walks you through setting up and running the complete intraday gamma monitoring system for SPY and QQQ.

---

## Prerequisites

- **Python 3.9+**
- **FlashAlpha API key** (free at https://flashalpha.com)
- **FlashAlpha SDK** (already installed: `pip list | grep flashalpha`)

---

## SETUP (One-time)

### 1. Activate Virtual Environment

```bash
cd /Users/billy/copilot-worktrees/flashalpha-python/55d9czt4sg-ui-silver-giggle
source venv/bin/activate
```

### 2. Set API Key (One of these methods)

**Option A: Environment Variable (Recommended)**
```bash
export FLASHALPHA_API_KEY="your-key-from-flashalpha.com"
```

**Option B: Pass to Script**
```bash
python intraday_gamma_monitor.py --api-key "your-key"
```

**Option C: Create .env file**
```bash
echo 'FLASHALPHA_API_KEY="your-key"' > .env
```

---

## EXECUTION

### During Market Hours (9:30 AM – 4:00 PM ET)

#### **Default: SPY + QQQ, 30-min checks for 6 hours**

```bash
python intraday_gamma_monitor.py
```

**What happens:**
- Captures opening gamma map (flip, walls, GEX, regime)
- Polls every 30 minutes for material changes
- Runs 12 checks total (covers ~9:30 AM to 3:30 PM ET)
- Saves JSON to `gamma_monitor_YYYYMMDD_HHMMSS.json`
- Real-time output shows:
  ```
  🎯 Starting Gamma Monitor (SPY, QQQ)
  📍 Check interval: 1800s (30m)
  💾 Output: gamma_monitor_20240924_093000.json
  
  [09:30:15] 📈 OPENING SNAPSHOT
  SPY:
    Spot: 562.45
    Flip: 561.80
    Walls: Call 566.00 / Put 560.00
    GEX: +1,234,567  DEX: +89,000
    Regime: long-gamma
  ```

#### **Custom: Different Symbols/Intervals**

```bash
# SPY only, 1-hour checks
python intraday_gamma_monitor.py --symbols SPY --interval 3600 --checks 6

# SPY, QQQ, IWM with 15-min polls
python intraday_gamma_monitor.py --symbols SPY,QQQ,IWM --interval 900 --checks 24

# Full market hours: 9:30 AM to 4:00 PM (27 x 10-min checks)
python intraday_gamma_monitor.py --interval 600 --checks 27
```

#### **Monitor in Background**

```bash
# Run in terminal multiplexer (recommended)
tmux new-session -d -s gamma "cd /Users/billy/.../55d9czt4sg-ui-silver-giggle && source venv/bin/activate && python intraday_gamma_monitor.py"

# Or nohup
nohup python intraday_gamma_monitor.py > gamma_monitor.log 2>&1 &
```

**Watch logs:**
```bash
tail -f gamma_monitor.log
```

---

### After Market Close (Next Morning, After 8:00 AM ET)

Once OCC publishes open interest updates (typically 8:00–8:30 AM ET next day):

#### **Step 1: Get OI Data**

Check your broker or data provider for:
- **Today's volume** (e.g., 182,500,000 shares for SPY)
- **Today's close OI** (e.g., 46,523,456)
- **Yesterday's close OI** (e.g., 45,123,456)

#### **Step 2: Run Post-Market Analysis**

```bash
python post_market_analysis.py gamma_monitor_20240924_093000.json \
    --today-volume 182500000 \
    --oi-today 46523456 \
    --oi-yesterday 45123456
```

**Output:**
```
Session Summary
Opening Snapshot: Spot 562.45 | Flip 561.80 | Call Wall 566.00
Final Snapshot:   Spot 564.20 | Flip 562.10 | Call Wall 567.00
Material Changes: 2 detected (flip moved, wall shifted)

Volume vs Average: +22.3% (opening activity)
OI Change: +45,123,456 → +46,523,456 (+3.1%)

Classification: 🟢 OPENING ACTIVITY
├─ Volume elevated + OI up >2%
├─ Dealer positions likely persist
└─ Gamma map should hold into tomorrow
```

---

## EXAMPLE: DRY-RUN WITH SYNTHETIC DATA

To test the full workflow **without** using API credits:

```bash
python example_monitoring_session.py
```

This will:
1. Generate synthetic market data with realistic material changes
2. Save to `example_gamma_session.json`
3. Run post-market classification on the data
4. Show you exactly what a real session output looks like

**Output:**
```
Opening Snapshot: Spot 562.45 | Flip 561.80 | Call 566.00 | Put 560.00
Final Snapshot:   Spot 563.00 | Flip 561.30 | Call 567.00 | Put 560.00

Material Changes Detected:
  1. [Check 2] Flip moved from 561.80 to 561.32 (-0.085%)
  2. [Check 3] Call wall moved +1 strike to 567.00

Classification: OPENING ACTIVITY ✅
OI up +2.2% | Volume above average
Outlook: Dealer positions likely persist
```

---

## KEY METRICS EXPLAINED

| Metric | What It Shows | Red Flag 🚨 |
|--------|---|---|
| **Gamma Flip** | Strike where dealer gamma flips long→short | Moves ±0.25–0.50% of spot = material repositioning |
| **Call Wall** | High call OI strike | Usually resistance; move ≥1 strike = dealer supply shifting |
| **Put Wall** | High put OI strike | Usually support; move ≥1 strike = dealer protection shifting |
| **Net GEX** | Positive = long gamma (sticky). Negative = short gamma (pro-cyclical) | GEX sign flip = major regime change |
| **Regime** | `long-gamma` vs `short-gamma` | Flips flag material change in dealer hedging mode |

---

## MATERIAL CHANGE THRESHOLDS

The monitor flags changes only when **substantial**:

| Type | Threshold | Why |
|------|-----------|-----|
| **Gamma Flip Move** | ±0.25–0.50% of spot | Dealers adjusting $1–2B+ hedge exposure |
| **Wall Shift** | ≥1 strike increment | Supply/support re-positioned meaningfully |
| **Regime Flip** | `long-gamma` ↔ `short-gamma` | Pro-cyclical behavior changes |

Minor noise (0.05% flip moves, $0.10 wall jitter) is **ignored** automatically.

---

## INTERPRETING RESULTS

### Price Action After Gamma Map Changes

**Call wall moved higher (+1 strike) = Dealer supply resistance pushed up**
```
→ Price tests new wall repeatedly
→ If price breaks through: dealers may be overwhelmed; acceleration expected
→ If price rejects wall: dealers defending effectively; consolidation expected
```

**Put wall lowered (-1 strike) = Dealer floor support removed**
```
→ Price tests old put wall
→ If price breaks below: short-gamma environment; vol expansion likely
→ If price holds: old support still functioning; dealers may re-defend below
```

**Gamma Flip moved down (closer to spot) = Dealers more short-gamma at spot**
```
→ Means: If market rallies, dealers become LONGER gamma (good for rallies)
→ Means: If market sells off, dealers become SHORTER gamma (accelerates down)
```

---

## NEXT-DAY FLOW CLASSIFICATION

After OCC updates OI at market open next day:

### **Opening Activity** (OI ↑ >2%, Volume ↑)
```
✅ Dealers OPENED new positions
→ Gamma map likely PERSISTS into next session
→ Watch for same walls/flip to function as S/R again
→ Use today's regime to frame next-day bias
```

### **Closing Activity** (OI ↓ >2%, Volume ↑)
```
⚠️ Dealers CLOSED positions
→ Gamma map effect may FADE or REVERSE
→ Previous walls lose power; find new structural levels
→ Regime may flip if dealer hedge intensity drops
```

### **Intraday Trading** (OI ~flat, Volume ↑)
```
⏸️ Likely spreads/rolls/hedges NOT dealer repositioning
→ Gamma map snapshot still valid as S/R
→ No material new dealer positioning to expect
→ Use for tactical mean-reversion setups
```

---

## TROUBLESHOOTING

### Script Won't Run: `ModuleNotFoundError: No module named 'flashalpha'`
```bash
# Reactivate venv and install
source venv/bin/activate
pip install flashalpha
python intraday_gamma_monitor.py
```

### API Error: `TierRestrictedError` (403)
```
Your API tier doesn't include the endpoint.
→ Upgrade plan at https://flashalpha.com
→ Free tier: stock_summary only (previous-day cached data)
```

### Missing Data: `data_as_of` is too old
```
→ Feed lag during off-hours (expected)
→ During market hours: check internet connection
→ If persistent: data feed may be down; try again in 5 min
```

### JSON File Not Saving
```bash
# Check permissions on current directory
ls -la gamma_monitor*.json
# If missing: ensure script ran full 12 checks before interrupting
```

---

## EXAMPLE: LIVE WORKFLOW

```bash
# 9:30 AM: Start monitoring
$ python intraday_gamma_monitor.py
🎯 Starting Gamma Monitor (SPY, QQQ)
📍 Check interval: 1800s (30m)
💾 Output: gamma_monitor_20240924_093000.json
[09:30:15] 📈 OPENING SNAPSHOT
SPY:
  Spot: 562.45
  Flip: 561.80
  Walls: Call 566.00 / Put 560.00
  GEX: +1,234,567
  Regime: long-gamma
QQQ:
  Spot: 476.30
  Flip: 475.80
  Walls: Call 480.00 / Put 475.00
  GEX: +892,345
  Regime: long-gamma

# 10:00 AM: (no output = no material changes detected)

# 11:00 AM: 🚨 MATERIAL CHANGE DETECTED
[11:00:42] CHECK 2 (Interval 30m)
SPY:
  🚨 Gamma Flip moved from 561.80 → 561.32 (-0.048, -0.085%)
  ← Dealers adjusting hedge. More gamma short at spot now.
  → If we rally, dealers flip LONG (supportive)
  → If we sell off, dealers flip SHORT (accelerative)

# 1:30 PM: Another check, more flags
QQQ:
  🚨 Call Wall moved from 480.00 → 481.00 (+1 strike)
  ← Dealer supply resistance higher. Bullish adjustment.
  → Watch for rejection or breakout at 481

# 3:30 PM: Monitor exits after 12 checks
✅ Session saved to: gamma_monitor_20240924_093000.json
```

**Next morning (8:30 AM ET):**
```bash
$ python post_market_analysis.py gamma_monitor_20240924_093000.json \
    --today-volume 182500000 --oi-today 46523456 --oi-yesterday 45123456

Classification: 🟢 OPENING ACTIVITY
├─ Volume +22% vs avg | OI +3.1%
├─ Dealer positions PERSISTED overnight
└─ Gamma map should still function as support/resistance today
```

---

## NEXT STEPS

1. **Run the example first** to see what output looks like without using API credits
   ```bash
   python example_monitoring_session.py
   ```

2. **Set up your API key** and run a real session tomorrow at market open

3. **Compare opening snapshot vs closing snapshot** (after all 12 checks)

4. **Next morning: run post-market analysis** to classify dealer activity

5. **Track the gamma map across multiple days** to build intuition for S/R patterns

---

## Files in This Repo

| File | Purpose |
|------|---------|
| `intraday_gamma_monitor.py` | Main monitoring loop (run during market hours) |
| `post_market_analysis.py` | OI/volume classification (run next morning) |
| `example_monitoring_session.py` | Dry-run demo with synthetic data (test without API key) |
| `INTRADAY_MONITORING_GUIDE.md` | Conceptual guide (what to look for, how to interpret) |
| `INTRADAY_MONITORING_SETUP.md` | This file |

---

## Support

**API Key Issues?**
- Sign up at https://flashalpha.com
- Check your tier includes the endpoints you need
- Playground to test endpoints: https://lab.flashalpha.com/swagger

**Script Issues?**
- Check Python version: `python3 --version` (need 3.9+)
- Verify venv: `which python` (should show `.../venv/bin/python`)
- Syntax check: `python3 -m py_compile intraday_gamma_monitor.py`

---

**Ready?** Start with the example, then run live at market open tomorrow! 🎯
