# QuantWheel + FlashAlpha Integration Guide

**Why pair them?** QuantWheel's IV surface analytics + FlashAlpha's dealer gamma positioning create a **complete options market picture**. Gamma shows dealer hedging; vol surface shows what's priced in. Together they reveal **actionable convergence signals**.

## Key Integration Points

### 1. **IV Surface vs. Gamma Regime**

| FlashAlpha Signal | QuantWheel Confirmation | Interpretation |
|---|---|---|
| **Long-gamma** (positive GEX) | IV stuck/compressing | Market "sticky"; dealers profit on containment; range trade setup |
| **Short-gamma** (negative GEX) | IV expanding or elevated | Dealers short gamma; acceleration risk; vol expands on moves |
| Regime flip | Term structure inversion | Major dealer hedge shift; gamma map changes sharply |

**Trade signal:** Dealers long gamma + short skew = vol premium is already short; sell spreads into walls.

---

### 2. **Call Wall + Skew = Vol Premium Priceable**

**Scenario:**
- FlashAlpha: Price $565 approaching call wall at $566
- QuantWheel: Upside skew is SHORT (calls are cheap relative to ATM)
- GEX: Positive (dealers long gamma)

**Interpretation:**
> Dealers have short calls baked in (the call wall). They're long gamma overall (bullish for dealers). The short upside skew means call premium is not expensive. Price testing the wall is normal market behavior. Dealers will defend the wall with hedging.

**Action:** Don't fight the wall; expect rejection. If short skew compresses (calls get expensive), dealers have repriced risk higher.

---

### 3. **Put Wall + Skew = Risk Premium Location**

**Scenario:**
- FlashAlpha: Put wall at $560; price $561; negative GEX (dealers short gamma)
- QuantWheel: Long downside skew (puts expensive relative to ATM)
- Regime: Short-gamma-bearish

**Interpretation:**
> Risk premium is concentrated in puts. Dealers are SHORT gamma (accelerator, pro-cyclical). If price breaks the put wall and vol expands, dealers lose and accelerate selling. The high put IV already reflects this risk but vol can expand further.

**Action:** Put wall break below $560 + IV expansion = high acceleration potential. Downside skew provides cushion for Put buyers.

---

### 4. **Gamma Flip Movement vs. Term Structure**

**Scenario:**
- FlashAlpha: Gamma flip moves from $561 to $563 (0.35% of $562)
- QuantWheel: Front-month IV drops 1 vol point while back-month stable

**Interpretation:**
> Dealers are repositioning (flipping their gamma hedge level). Front-month volatility is compressing (likely dealer closing short straddles). This is opening activity: they're adjusting net short positions, not closing them.

**Action:** Flip movement + front-month vol crush = dealers are rehedging directionally. Expect the new flip level to hold; trade near it.

---

### 5. **Price Action Correlation (Gamma + Skew)**

| Price Movement | Gamma Regime | Skew Response | Implication |
|---|---|---|---|
| Test call wall | Long gamma | Skew compresses / ATM IV up | Dealers selling premium; holding wall |
| Break put wall | Short gamma | Downside IV spikes | Dealers losing; escalation likely |
| Hold near flip | Long gamma | Vol stable, skew flat | Equilibrium; dealers anchored |
| Reverse at wall | Any | Skew widens | Dealers adding position; repricing risk |

**QuantWheel metrics to monitor:**
- **Skew slope:** Is it steepening (risk repricing) or flattening (risk being digested)?
- **Put-call vol ratio:** Directional beta of volatility
- **Realized vs. implied:** Are dealers far from the future realized path?

---

## Convergence Signals (Gamma + Vol)

### 🔴 HIGH PRIORITY

**1. Regime Flip + Term Structure Inversion**
```
Event: Gamma regime changes from long to short-gamma
       + Front-month IV inverts (front month > back month)
Meaning: Dealers now short gamma AND front month is nervous
Risk: Major acceleration risk; vol will likely spike
Action: Reduce long-gamma hedges; prepare for escalation
```

**2. Short Gamma + IV Expanding (Live)**
```
Event: Negative GEX + upward vol movement detected
Meaning: Dealers are getting hurt in real time
Risk: Escalation likely to continue (pro-cyclical)
Action: Stay defensive; don't add longs near walls
```

**3. Price at Call Wall + Short Skew Compressing**
```
Event: Price at call wall + upside skew tightens (calls getting expensive)
Meaning: Dealers are being forced to add to short calls (hedge pressure)
Risk: If wall breaks, dealers will fight hard to reclaim
Action: Strong resistance; expect sharp reversal or heavy volume to break it
```

### 🟡 MEDIUM PRIORITY

**4. Put Wall + Long Downside Skew Expanding**
```
Event: Put wall + downside skew gets steeper (puts expensive)
Meaning: Put buyers are paying up for protection
Risk: Indicates elevated tail risk in market view
Action: Put wall support holds until tail event happens; don't be short into it
```

**5. Gamma Flip Moving but Walls Stable**
```
Event: Flip shifts 0.25%+ but call/put walls don't move
Meaning: Dealers are trimming hedges on the flip, but range boundaries hold
Risk: Low; market is consolidating
Action: Range-play opportunity; trade mean-reversion into walls
```

---

## Real-World Example Walkthrough

### Morning: 9:30 AM ET

**FlashAlpha snapshot:**
```
SPY: $567
Flip: $566
Call wall: $570
Put wall: $565
GEX: +2.1M (long gamma)
Regime: long-gamma
```

**QuantWheel snapshot:**
```
ATM IV: 14.5%
Skew: Short (call IV 13.2%, put IV 16.1%)
Term: Front month = Back month (flat)
RV: 11.2% (implied > realized by 3.3%)
```

**Interpretation:**
- Dealers are long gamma (range-play bias). Vol premium is NOT being paid (realized is cheap).
- Upside skew is SHORT (calls cheap; puts expensive). Dealers have short calls (the wall at $570).
- Front-month volatility is flat with back month (no term stress).

**Expectation:** SPY should oscillate between $565–$570 today. Call wall at $570 is strong resistance. Put wall at $565 is support.

---

### Intraday: 11:00 AM ET (Check)

**FlashAlpha update:**
```
SPY: $568.50 (+0.25%)
Flip: $566.40 (moved +0.07%)
Call wall: $570 (unchanged)
Put wall: $565 (unchanged)
GEX: +2.3M (stable)
Regime: long-gamma ✓
```

**QuantWheel update:**
```
ATM IV: 14.2% (-0.3 vol)
Skew: Short (call IV 13.0%, put IV 16.3%)
RV: 11.4% (still cheap vs implied)
```

**Convergence check:**
- Price inched up but GEX remained positive → Market is "sticky" (long-gamma working)
- IV compressed slightly → Dealers are selling (premium harvesting)
- Skew widened slightly (puts more expensive) → Dealers are adding to short calls

**Signal:** Market is consolidating. Continue monitoring for wall breaks.

---

### Intraday: 2:30 PM ET (Check)

**FlashAlpha update:**
```
SPY: $571.20 (+0.76% from open)
Flip: $568.80 (moved +0.50% ⚠️ MATERIAL)
Call wall: $571 (moved up by $1 ⚠️ MATERIAL)
Put wall: $565.50 (moved down by -$0.50, minor)
GEX: -456K (SIGN FLIP ⚠️ SHORT GAMMA)
Regime: short-gamma-bullish ⚠️ FLIPPED
```

**QuantWheel update:**
```
ATM IV: 15.1% (+0.9 vol, expanding ⚠️)
Skew: Long (call IV 14.8%, put IV 15.9%, flattening)
Term: Front month > Back month (inversion starting ⚠️)
RV: 12.1% (implied still expensive but gap narrowing)
```

**Convergence alert:**
> 🚨 **MAJOR REGIME SHIFT DETECTED**
> - Gamma flipped from Long → Short (dealers now SHORT gamma, pro-cyclical)
> - Call wall moved up $1 (dealers repositioned higher)
> - IV is EXPANDING (dealers losing on short positions)
> - Term structure inverting (front-month stress)
> - Skew flattening (puts getting cheaper, upside getting more expensive)

**Interpretation:**
Dealers have lost control. They were long gamma, defending the $570 wall. Price broke it. Now they're short gamma, the IV is expanding, and the wall has moved up to $571. This is an **acceleration regime**. If price breaks $571 decisively, expect further escalation.

**Action (per trader):**
- Exit any long-gamma hedges (they're working against you now)
- Watch $571 call wall; if it's broken, look for next resistance
- Put skew is flattening → Put premium is cheap relative to calls now
- Be cautious of scalp longs; bias is upside but volatility is rising

---

### Post-Close: 4:15 PM ET

**Session summary:**
- **Volume:** 165M shares (up 15% vs 5-day avg)
- **OI change (today vs yesterday):** +1.8% (opening activity, not closing)
- **Gamma regime flips:** 1 (Long → Short at 2:30 PM)
- **Wall migrations:** Call wall +$1, put wall -$0.50
- **IV impact:** +0.6 vol (from 14.5% to 15.1%)

**Tomorrow's calibration:**
Since OI increased (dealers opened), the new gamma map (short-gamma, $571 call wall, $565.50 put wall) is likely **persistent**. Expect dealers to defend the $571 call wall and respect the $565.50 put wall support. Monitor for continuation gaps or mean-reversion back into the wall range.

---

## Integration Checklist

- [ ] Deploy FlashAlpha monitor for gamma snapshots (30 min intervals)
- [ ] Add QuantWheel IV surface polling (same 30 min rhythm)
- [ ] Implement convergence detection (code provided in `quantwheel_gamma_integration.py`)
- [ ] Save combined snapshots to JSON (gamma + vol + signals)
- [ ] Post-market: Compare volume with OI (FlashAlpha) + check term structure shift (QuantWheel)
- [ ] Repeat daily; build regime persistence patterns (dealers rarely flip twice in one day)

## Quick Command Reference

```bash
# Run unified monitor
python quantwheel_gamma_integration.py SPY \
    --api-key-fa $FLASHALPHA_API_KEY \
    --api-key-qw $QUANTWHEEL_API_KEY \
    --interval 1800 \
    --checks 12

# Or standalone FlashAlpha
python intraday_gamma_monitor.py --symbols SPY,QQQ --interval 1800 --checks 12

# Post-market analysis
python post_market_analysis.py gamma_monitor_*.json \
    --today-volume 165000000 \
    --oi-today 45500000 \
    --oi-yesterday 44700000
```

---

**Questions?** The FlashAlpha API docs: https://lab.flashalpha.com/swagger  
QuantWheel dashboard: https://quantwheel.com

Happy trading! 📊
