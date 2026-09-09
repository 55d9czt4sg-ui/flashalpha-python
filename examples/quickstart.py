"""FlashAlpha SDK quick start — get running in 3 minutes."""

from flashalpha import FlashAlpha


def flip(payload):
    """Format ``gamma_flip``, which is ``None`` for most chains.

    When no level is published the API returns ``gamma_flip: null`` and a
    ``gamma_flip_status`` reason code (e.g. ``"no_boundary"``). Anything
    other than ``"available"`` means there is no flip to show.
    """
    level = payload.get("gamma_flip")
    if level is None:
        return f"n/a ({payload.get('gamma_flip_status') or 'unavailable'})"
    return f"{level:.2f}"


# 1. Initialize with your API key
fa = FlashAlpha("YOUR_API_KEY")

# 2. Get gamma exposure for SPY
gex = fa.gex("SPY")
print(f"SPY Net GEX: ${gex['net_gex']:,.0f}")
print(f"Gamma flip: {flip(gex)}")
print(f"Regime: {gex['net_gex_label']}")
print()

# 3. Key support/resistance levels
levels = fa.exposure_levels("SPY")["levels"]
print(f"Call wall (resistance): {levels['call_wall']}")
print(f"Put wall (support):     {levels['put_wall']}")
print(f"Gamma flip:             {flip(levels)}")
print(f"0DTE magnet:            {levels['zero_dte_magnet']}")
print()

# 4. Stock quote
quote = fa.stock_quote("SPY")
print(f"SPY: ${quote['mid']:.2f} (bid {quote['bid']:.2f} / ask {quote['ask']:.2f})")
print()

# 5. BSM greeks calculator
greeks = fa.greeks(spot=580, strike=580, dte=30, sigma=0.18)
print("BSM Greeks (580C, 30 DTE, 18% vol):")
print(f"  Price:  ${greeks['theoretical_price']:.2f}")
print(f"  Delta:  {greeks['first_order']['delta']:.4f}")
print(f"  Gamma:  {greeks['first_order']['gamma']:.6f}")
print(f"  Theta:  {greeks['first_order']['theta']:.4f}")
print(f"  Vega:   {greeks['first_order']['vega']:.4f}")
print(f"  Vanna:  {greeks['second_order']['vanna']:.6f}")
print()

# 6. Implied volatility solver
iv_result = fa.iv(spot=580, strike=580, dte=30, price=12.69)
print(f"IV from $12.69 premium: {iv_result['implied_volatility_pct']:.1f}%")
print()

# 7. Account info
account = fa.account()
print(f"Plan: {account['plan']} | Remaining: {account['remaining']}")
