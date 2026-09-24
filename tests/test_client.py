"""Unit tests for the FlashAlpha client — all API calls are mocked."""

import pytest
import responses

from flashalpha import (
    FlashAlpha,
    AuthenticationError,
    FlashAlphaError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TierRestrictedError,
)

BASE = "https://lab.flashalpha.com"


@pytest.fixture
def fa():
    return FlashAlpha("test-key")


# ── Error handling ──────────────────────────────────────────────────


@responses.activate
def test_401_raises_authentication_error(fa):
    responses.get(f"{BASE}/v1/account", json={"title": "Unauthorized", "status": 401, "detail": "Invalid API key."}, status=401)
    with pytest.raises(AuthenticationError) as exc_info:
        fa.account()
    assert exc_info.value.status_code == 401


@responses.activate
def test_403_raises_tier_restricted_error(fa):
    responses.get(
        f"{BASE}/v1/exposure/summary/SPY",
        json={"status": "ERROR", "error": "tier_restricted", "message": "Requires Growth plan.", "current_plan": "Free", "required_plan": "Growth"},
        status=403,
    )
    with pytest.raises(TierRestrictedError) as exc_info:
        fa.exposure_summary("SPY")
    assert exc_info.value.current_plan == "Free"
    assert exc_info.value.required_plan == "Growth"


@responses.activate
def test_404_raises_not_found_error(fa):
    responses.get(f"{BASE}/stockquote/ZZZZZ", json={"error": "symbol_not_found", "message": "No data for ZZZZZ."}, status=404)
    with pytest.raises(NotFoundError):
        fa.stock_quote("ZZZZZ")


@responses.activate
def test_429_raises_rate_limit_error(fa):
    responses.get(
        f"{BASE}/stockquote/SPY",
        json={"status": "ERROR", "error": "Quota exceeded", "message": "Quota exceeded."},
        status=429,
        headers={"Retry-After": "60"},
    )
    with pytest.raises(RateLimitError) as exc_info:
        fa.stock_quote("SPY")
    assert exc_info.value.retry_after == 60


@responses.activate
def test_500_raises_server_error(fa):
    responses.get(f"{BASE}/health", json={"detail": "Internal server error"}, status=500)
    with pytest.raises(ServerError) as exc_info:
        fa.health()
    assert exc_info.value.status_code == 500


@responses.activate
def test_unknown_error_raises_base(fa):
    responses.get(f"{BASE}/health", json={"detail": "Teapot"}, status=418)
    with pytest.raises(FlashAlphaError) as exc_info:
        fa.health()
    assert exc_info.value.status_code == 418


# ── Market Data ─────────────────────────────────────────────────────


@responses.activate
def test_stock_quote(fa):
    payload = {"ticker": "SPY", "bid": 600.0, "ask": 600.02, "mid": 600.01, "lastPrice": 600.01, "lastUpdate": "2026-03-01T16:00:00Z"}
    responses.get(f"{BASE}/stockquote/SPY", json=payload)
    result = fa.stock_quote("SPY")
    assert result["ticker"] == "SPY"
    assert result["bid"] == 600.0


@responses.activate
def test_option_quote_with_filters(fa):
    payload = {"underlying": "SPY", "type": "C", "expiry": "2026-03-20", "strike": 590.0, "delta": 0.65}
    responses.get(f"{BASE}/optionquote/SPY", json=payload)
    result = fa.option_quote("SPY", expiry="2026-03-20", strike=590, type="C")
    assert result["delta"] == 0.65


@responses.activate
def test_surface(fa):
    responses.get(f"{BASE}/v1/surface/SPY", json={"symbol": "SPY", "data": []})
    result = fa.surface("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_stock_summary(fa):
    responses.get(f"{BASE}/v1/stock/SPY/summary", json={"symbol": "SPY", "market_open": True})
    result = fa.stock_summary("SPY")
    assert result["symbol"] == "SPY"


# ── Historical ──────────────────────────────────────────────────────


@responses.activate
def test_historical_stock_quote(fa):
    payload = {"ticker": "SPY", "date": "2026-03-05", "count": 1, "rows": []}
    responses.get(f"{BASE}/historical/stockquote/SPY", json=payload)
    result = fa.historical_stock_quote("SPY", date="2026-03-05", time="10:30")
    assert result["date"] == "2026-03-05"
    # Verify query params were sent
    assert "date=2026-03-05" in responses.calls[0].request.url
    assert "time=10%3A30" in responses.calls[0].request.url


@responses.activate
def test_historical_option_quote(fa):
    payload = {"ticker": "SPY", "date": "2026-03-05", "count": 1, "rows": []}
    responses.get(f"{BASE}/historical/optionquote/SPY", json=payload)
    result = fa.historical_option_quote("SPY", date="2026-03-05", expiry="2026-03-20", strike=580, type="C")
    assert result["count"] == 1


# ── Exposure Analytics ──────────────────────────────────────────────


@responses.activate
def test_gex(fa):
    payload = {"symbol": "SPY", "net_gex": 2850000000, "gamma_flip": 595.25, "strikes": []}
    responses.get(f"{BASE}/v1/exposure/gex/SPY", json=payload)
    result = fa.gex("SPY")
    assert result["net_gex"] == 2850000000


@responses.activate
def test_gex_with_filters(fa):
    payload = {"symbol": "SPY", "strikes": []}
    responses.get(f"{BASE}/v1/exposure/gex/SPY", json=payload)
    fa.gex("SPY", expiration="2026-03-20", min_oi=100)
    assert "expiration=2026-03-20" in responses.calls[0].request.url
    assert "min_oi=100" in responses.calls[0].request.url


@responses.activate
def test_dex(fa):
    payload = {"symbol": "SPY", "net_dex": -450000000, "strikes": []}
    responses.get(f"{BASE}/v1/exposure/dex/SPY", json=payload)
    result = fa.dex("SPY")
    assert result["net_dex"] == -450000000


@responses.activate
def test_vex(fa):
    payload = {"symbol": "SPY", "net_vex": 1200000000, "strikes": []}
    responses.get(f"{BASE}/v1/exposure/vex/SPY", json=payload)
    result = fa.vex("SPY")
    assert result["net_vex"] == 1200000000


@responses.activate
def test_chex(fa):
    payload = {"symbol": "SPY", "net_chex": 850000000, "strikes": []}
    responses.get(f"{BASE}/v1/exposure/chex/SPY", json=payload)
    result = fa.chex("SPY")
    assert result["net_chex"] == 850000000


@responses.activate
def test_exposure_summary(fa):
    payload = {"symbol": "SPY", "regime": "positive_gamma", "exposures": {}}
    responses.get(f"{BASE}/v1/exposure/summary/SPY", json=payload)
    result = fa.exposure_summary("SPY")
    assert result["regime"] == "positive_gamma"


@responses.activate
def test_exposure_levels(fa):
    payload = {"symbol": "SPY", "levels": {"gamma_flip": 595.25, "call_wall": 600, "put_wall": 590}}
    responses.get(f"{BASE}/v1/exposure/levels/SPY", json=payload)
    result = fa.exposure_levels("SPY")
    assert result["levels"]["call_wall"] == 600


@responses.activate
def test_narrative(fa):
    payload = {"symbol": "SPY", "narrative": {"regime": "Dealers long gamma.", "outlook": "Range-bound."}}
    responses.get(f"{BASE}/v1/exposure/narrative/SPY", json=payload)
    result = fa.narrative("SPY")
    assert "regime" in result["narrative"]


@responses.activate
def test_zero_dte(fa):
    payload = {"symbol": "SPY", "regime": {"label": "positive_gamma"}, "pin_risk": {"pin_score": 82}, "decay": {"gamma_acceleration": 2.4}}
    responses.get(f"{BASE}/v1/exposure/zero-dte/SPY", json=payload)
    result = fa.zero_dte("SPY")
    assert result["pin_risk"]["pin_score"] == 82


@responses.activate
def test_zero_dte_with_strike_range(fa):
    payload = {"symbol": "SPY", "strikes": []}
    responses.get(f"{BASE}/v1/exposure/zero-dte/SPY", json=payload)
    fa.zero_dte("SPY", strike_range=0.05)
    assert "strike_range=0.05" in responses.calls[0].request.url


# ── Zero-DTE Flow ───────────────────────────────────────────────────


@responses.activate
def test_flow_zero_dte_snapshot(fa):
    payload = {"symbol": "SPY", "flow_direction": {"bias": "long_gamma"}}
    responses.get(f"{BASE}/v1/flow/zero-dte/snapshot/SPY", json=payload)
    result = fa.flow_zero_dte_snapshot("SPY")
    assert result["flow_direction"]["bias"] == "long_gamma"


@responses.activate
def test_flow_zero_dte_snapshot_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/snapshot/SPY", json={"symbol": "SPY"})
    fa.flow_zero_dte_snapshot("SPY", expiry="2026-06-09")
    assert "expiry=2026-06-09" in responses.calls[0].request.url


@responses.activate
def test_flow_zero_dte_leaderboard(fa):
    payload = {
        "metric": "heat",
        "n": 2,
        "as_of": "2026-06-14T15:00:00Z",
        "market_open": True,
        "entries": [
            {"rank": 1, "symbol": "SPY", "value": 9.4},
            {"rank": 2, "symbol": "QQQ", "value": 7.1},
        ],
    }
    responses.get(f"{BASE}/v1/flow/zero-dte/leaderboard", json=payload)
    result = fa.flow_zero_dte_leaderboard()
    assert result["entries"][0]["symbol"] == "SPY"


@responses.activate
def test_flow_zero_dte_leaderboard_with_params(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/leaderboard", json={"metric": "pin_risk", "entries": []})
    fa.flow_zero_dte_leaderboard(metric="pin_risk", n=10)
    url = responses.calls[0].request.url
    assert "metric=pin_risk" in url
    assert "n=10" in url


# ── Pricing ─────────────────────────────────────────────────────────


@responses.activate
def test_greeks(fa):
    payload = {"theoretical_price": 12.687, "first_order": {"delta": 0.53, "gamma": 0.013}}
    responses.get(f"{BASE}/v1/pricing/greeks", json=payload)
    result = fa.greeks(spot=580, strike=580, dte=30, sigma=0.18)
    assert result["first_order"]["delta"] == 0.53


@responses.activate
def test_iv(fa):
    payload = {"implied_volatility": 0.18, "implied_volatility_pct": 18.0}
    responses.get(f"{BASE}/v1/pricing/iv", json=payload)
    result = fa.iv(spot=580, strike=580, dte=30, price=12.69)
    assert result["implied_volatility_pct"] == 18.0


@responses.activate
def test_kelly(fa):
    payload = {"sizing": {"kelly_fraction": 0.077, "half_kelly": 0.038}, "recommendation": "Risk 3.8%"}
    responses.get(f"{BASE}/v1/pricing/kelly", json=payload)
    result = fa.kelly(spot=580, strike=580, dte=30, sigma=0.18, premium=12.69, mu=0.12)
    assert result["sizing"]["kelly_fraction"] == 0.077


# ── Volatility ──────────────────────────────────────────────────────


@responses.activate
def test_volatility(fa):
    payload = {"symbol": "TSLA", "atm_iv": 48.5, "realized_vol": {"rv_20d": 45.8}}
    responses.get(f"{BASE}/v1/volatility/TSLA", json=payload)
    result = fa.volatility("TSLA")
    assert result["atm_iv"] == 48.5


@responses.activate
def test_adv_volatility(fa):
    payload = {"symbol": "SPY", "svi_parameters": [{"expiry": "2026-04-04", "a": 0.0045}], "arbitrage_flags": []}
    responses.get(f"{BASE}/v1/adv_volatility/SPY", json=payload)
    result = fa.adv_volatility("SPY")
    assert result["svi_parameters"][0]["a"] == 0.0045


# ── Reference Data ──────────────────────────────────────────────────


@responses.activate
def test_tickers(fa):
    payload = {"tickers": ["AAPL", "SPY"], "count": 2}
    responses.get(f"{BASE}/v1/tickers", json=payload)
    result = fa.tickers()
    assert result["count"] == 2


@responses.activate
def test_options(fa):
    payload = {"symbol": "SPY", "expirations": [], "expiration_count": 0}
    responses.get(f"{BASE}/v1/options/SPY", json=payload)
    result = fa.options("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_symbols(fa):
    payload = {"symbols": ["SPY", "QQQ"], "count": 2}
    responses.get(f"{BASE}/v1/symbols", json=payload)
    result = fa.symbols()
    assert result["count"] == 2


# ── Account & System ────────────────────────────────────────────────


@responses.activate
def test_account(fa):
    payload = {"plan": "pro", "daily_limit": "unlimited", "usage_today": 0}
    responses.get(f"{BASE}/v1/account", json=payload)
    result = fa.account()
    assert result["plan"] == "pro"


@responses.activate
def test_health(fa):
    payload = {"status": "Healthy"}
    responses.get(f"{BASE}/health", json=payload)
    result = fa.health()
    assert result["status"] == "Healthy"


# ── Max Pain ────────────────────────────────────────────────────────


@responses.activate
def test_max_pain(fa):
    payload = {"symbol": "SPY", "max_pain_strike": 545, "pin_probability": 68}
    responses.get(f"{BASE}/v1/maxpain/SPY", json=payload)
    result = fa.max_pain("SPY")
    assert result["max_pain_strike"] == 545
    assert result["pin_probability"] == 68


@responses.activate
def test_max_pain_calls_correct_path(fa):
    responses.get(f"{BASE}/v1/maxpain/AAPL", json={})
    fa.max_pain("AAPL")
    assert "/v1/maxpain/AAPL" in responses.calls[0].request.url


@responses.activate
def test_max_pain_with_expiration(fa):
    responses.get(f"{BASE}/v1/maxpain/SPY", json={})
    fa.max_pain("SPY", expiration="2026-04-17")
    assert "expiration=2026-04-17" in responses.calls[0].request.url


@responses.activate
def test_max_pain_without_expiration(fa):
    responses.get(f"{BASE}/v1/maxpain/SPY", json={"max_pain_by_expiration": [{"expiration": "2026-04-17"}]})
    result = fa.max_pain("SPY")
    assert "max_pain_by_expiration" in result


@responses.activate
def test_max_pain_full_response(fa):
    payload = {
        "symbol": "SPY",
        "underlying_price": 548.32,
        "max_pain_strike": 545,
        "distance": {"absolute": 3.32, "percent": 0.61, "direction": "above"},
        "signal": "neutral",
        "put_call_oi_ratio": 1.284,
        "pain_curve": [{"strike": 545, "total_pain": 3700000}],
        "oi_by_strike": [{"strike": 545, "call_oi": 35000, "put_oi": 42000}],
        "dealer_alignment": {"alignment": "converging", "gamma_flip": 546},
        "regime": "positive_gamma",
        "expected_move": {"max_pain_within_expected_range": True},
        "pin_probability": 68,
    }
    responses.get(f"{BASE}/v1/maxpain/SPY", json=payload)
    result = fa.max_pain("SPY")
    assert result["distance"]["direction"] == "above"
    assert result["dealer_alignment"]["alignment"] == "converging"
    assert result["signal"] == "neutral"
    assert result["regime"] == "positive_gamma"


@responses.activate
def test_max_pain_403_tier_restricted(fa):
    responses.get(
        f"{BASE}/v1/maxpain/SPY",
        json={"status": "ERROR", "error": "tier_restricted", "message": "Requires Growth plan.", "current_plan": "Free", "required_plan": "Growth"},
        status=403,
    )
    with pytest.raises(TierRestrictedError) as exc:
        fa.max_pain("SPY")
    assert exc.value.current_plan == "Free"


# ── Screener ───────────────────────────────────────────────────────

import json as _json


def _screener_body(call):
    return _json.loads(call.request.body)


@responses.activate
def test_screener_empty(fa):
    payload = {
        "meta": {"total_count": 10, "returned_count": 10, "tier": "growth"},
        "data": [{"symbol": "SPY", "price": 656.01}],
    }
    responses.post(f"{BASE}/v1/screener", json=payload)
    result = fa.screener()
    assert result["meta"]["tier"] == "growth"
    assert result["data"][0]["symbol"] == "SPY"
    # Empty body
    assert _screener_body(responses.calls[0]) == {}


@responses.activate
def test_screener_sends_post_with_json_content_type(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(limit=5)
    req = responses.calls[0].request
    assert req.method == "POST"
    assert req.url == f"{BASE}/v1/screener"
    assert req.headers.get("Content-Type") == "application/json"
    assert req.headers.get("X-Api-Key") == "test-key"


@responses.activate
def test_screener_leaf_filter(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(filters={"field": "regime", "operator": "eq", "value": "positive_gamma"})
    body = _screener_body(responses.calls[0])
    assert body["filters"]["field"] == "regime"
    assert body["filters"]["operator"] == "eq"
    assert body["filters"]["value"] == "positive_gamma"


@responses.activate
def test_screener_and_group(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        filters={
            "op": "and",
            "conditions": [
                {"field": "regime", "operator": "eq", "value": "positive_gamma"},
                {"field": "harvest_score", "operator": "gte", "value": 65},
            ],
        },
        sort=[{"field": "harvest_score", "direction": "desc"}],
        select=["symbol", "price", "harvest_score"],
        limit=20,
    )
    body = _screener_body(responses.calls[0])
    assert body["filters"]["op"] == "and"
    assert len(body["filters"]["conditions"]) == 2
    assert body["limit"] == 20
    assert body["select"] == ["symbol", "price", "harvest_score"]
    assert body["sort"] == [{"field": "harvest_score", "direction": "desc"}]


@responses.activate
def test_screener_or_group(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        filters={
            "op": "or",
            "conditions": [
                {"field": "vrp_regime", "operator": "eq", "value": "toxic_short_vol"},
                {"field": "vrp_regime", "operator": "eq", "value": "event_only"},
            ],
        },
    )
    body = _screener_body(responses.calls[0])
    assert body["filters"]["op"] == "or"


@responses.activate
def test_screener_nested_and_inside_or(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        filters={
            "op": "or",
            "conditions": [
                {
                    "op": "and",
                    "conditions": [
                        {"field": "regime", "operator": "eq", "value": "positive_gamma"},
                        {"field": "harvest_score", "operator": "gte", "value": 70},
                    ],
                },
                {
                    "op": "and",
                    "conditions": [
                        {"field": "regime", "operator": "eq", "value": "negative_gamma"},
                        {"field": "atm_iv", "operator": "gte", "value": 50},
                    ],
                },
            ],
        },
    )
    body = _screener_body(responses.calls[0])
    assert body["filters"]["op"] == "or"
    assert body["filters"]["conditions"][0]["op"] == "and"
    assert body["filters"]["conditions"][1]["op"] == "and"


@responses.activate
def test_screener_between_operator(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(filters={"field": "atm_iv", "operator": "between", "value": [15, 25]})
    body = _screener_body(responses.calls[0])
    assert body["filters"]["operator"] == "between"
    assert body["filters"]["value"] == [15, 25]


@responses.activate
def test_screener_in_operator(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(filters={"field": "term_state", "operator": "in", "value": ["contango", "mixed"]})
    body = _screener_body(responses.calls[0])
    assert body["filters"]["operator"] == "in"
    assert body["filters"]["value"] == ["contango", "mixed"]


@responses.activate
def test_screener_null_operators(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(filters={"field": "vrp_regime", "operator": "is_not_null"})
    body = _screener_body(responses.calls[0])
    assert body["filters"]["operator"] == "is_not_null"
    assert "value" not in body["filters"]


@responses.activate
def test_screener_cascading_filters(fa):
    """Cascading filters on expiries/strikes/contracts levels."""
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        filters={
            "op": "and",
            "conditions": [
                {"field": "regime", "operator": "eq", "value": "positive_gamma"},
                {"field": "expiries.days_to_expiry", "operator": "lte", "value": 14},
                {"field": "strikes.call_oi", "operator": "gte", "value": 2000},
                {"field": "contracts.type", "operator": "eq", "value": "C"},
                {"field": "contracts.delta", "operator": "gte", "value": 0.3},
            ],
        },
        select=["*"],
    )
    body = _screener_body(responses.calls[0])
    fields = [c["field"] for c in body["filters"]["conditions"]]
    assert "expiries.days_to_expiry" in fields
    assert "strikes.call_oi" in fields
    assert "contracts.type" in fields
    assert "contracts.delta" in fields
    assert body["select"] == ["*"]


@responses.activate
def test_screener_with_formulas(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        formulas=[{"alias": "vrp_ratio", "expression": "atm_iv / rv_20d"}],
        filters={"formula": "vrp_ratio", "operator": "gte", "value": 1.2},
        sort=[{"formula": "vrp_ratio", "direction": "desc"}],
    )
    body = _screener_body(responses.calls[0])
    assert body["formulas"][0]["alias"] == "vrp_ratio"
    assert body["formulas"][0]["expression"] == "atm_iv / rv_20d"
    assert body["filters"]["formula"] == "vrp_ratio"
    assert body["sort"][0]["formula"] == "vrp_ratio"


@responses.activate
def test_screener_inline_formula(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        filters={"formula": "atm_iv - rv_20d", "operator": "gt", "value": 6},
    )
    body = _screener_body(responses.calls[0])
    assert body["filters"]["formula"] == "atm_iv - rv_20d"


@responses.activate
def test_screener_multi_sort(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        sort=[
            {"field": "dealer_flow_risk", "direction": "asc"},
            {"field": "harvest_score", "direction": "desc"},
        ],
        select=["symbol", "dealer_flow_risk", "harvest_score"],
    )
    body = _screener_body(responses.calls[0])
    assert len(body["sort"]) == 2
    assert body["sort"][0]["direction"] == "asc"
    assert body["sort"][1]["direction"] == "desc"


@responses.activate
def test_screener_pagination(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(limit=10, offset=10)
    body = _screener_body(responses.calls[0])
    assert body["limit"] == 10
    assert body["offset"] == 10


@responses.activate
def test_screener_negative_number(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(filters={"field": "net_gex", "operator": "lt", "value": -500000})
    body = _screener_body(responses.calls[0])
    assert body["filters"]["value"] == -500000


@responses.activate
def test_screener_select_star(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(select=["*"])
    body = _screener_body(responses.calls[0])
    assert body["select"] == ["*"]


@responses.activate
def test_screener_select_star_with_formula(fa):
    responses.post(f"{BASE}/v1/screener", json={"meta": {}, "data": []})
    fa.screener(
        formulas=[{"alias": "ratio", "expression": "call_wall / (put_wall + 30)"}],
        select=["*", "ratio"],
    )
    body = _screener_body(responses.calls[0])
    assert body["select"] == ["*", "ratio"]


@responses.activate
def test_screener_returns_response_structure(fa):
    payload = {
        "meta": {
            "total_count": 7,
            "returned_count": 7,
            "universe_size": 250,
            "offset": 0,
            "limit": 50,
            "tier": "alpha",
            "as_of": "2026-04-05T10:30:00Z",
        },
        "data": [
            {"symbol": "SPY", "price": 656.01, "regime": "positive_gamma", "atm_iv": 20.7}
        ],
    }
    responses.post(f"{BASE}/v1/screener", json=payload)
    result = fa.screener()
    assert result["meta"]["tier"] == "alpha"
    assert result["meta"]["universe_size"] == 250
    assert result["data"][0]["price"] == 656.01


@responses.activate
def test_screener_tier_restricted_alpha_field(fa):
    err_body = {
        "status": "ERROR",
        "error": "validation_error",
        "message": "Field 'harvest_score' requires the Alpha plan or higher.",
    }
    responses.post(f"{BASE}/v1/screener", json=err_body, status=400)
    with pytest.raises(FlashAlphaError) as exc:
        fa.screener(filters={"field": "harvest_score", "operator": "gte", "value": 65})
    assert exc.value.status_code == 400
    assert "Alpha" in str(exc.value)


@responses.activate
def test_screener_formula_error(fa):
    err_body = {
        "status": "ERROR",
        "error": "formula_error",
        "message": "Unexpected token '+' at position 5",
    }
    responses.post(f"{BASE}/v1/screener", json=err_body, status=400)
    with pytest.raises(FlashAlphaError):
        fa.screener(formulas=[{"alias": "bad", "expression": "+ atm_iv"}])


@responses.activate
def test_screener_tier_restricted_403(fa):
    err_body = {
        "status": "ERROR",
        "error": "tier_restricted",
        "message": "Screener requires Growth plan or higher.",
        "current_plan": "Free",
        "required_plan": "Growth",
    }
    responses.post(f"{BASE}/v1/screener", json=err_body, status=403)
    with pytest.raises(TierRestrictedError) as exc:
        fa.screener()
    assert exc.value.current_plan == "Free"
    assert exc.value.required_plan == "Growth"


# ── New endpoint families (1.1.0) ───────────────────────────────────


@responses.activate
def test_surface_svi(fa):
    payload = {"symbol": "SPY", "slices": [{"expiry": "2026-07-17", "a": 0.0045}]}
    responses.get(f"{BASE}/v1/surface/svi/SPY", json=payload)
    result = fa.surface_svi("SPY")
    assert "/v1/surface/svi/SPY" in responses.calls[0].request.url
    assert result["symbol"] == "SPY"


@responses.activate
def test_dispersion(fa):
    payload = {"index": "SPX", "implied_correlation": 0.412, "correlation_premium": 0.027}
    responses.get(f"{BASE}/v1/dispersion", json=payload)
    result = fa.dispersion(index="SPX", symbols=["AAPL", "MSFT", "NVDA"], weights=[0.5, 0.3, 0.2], horizon_days=20)
    url = responses.calls[0].request.url
    assert "index=SPX" in url
    assert "symbols=AAPL%2CMSFT%2CNVDA" in url
    assert "weights=0.5%2C0.3%2C0.2" in url
    assert "horizon_days=20" in url
    assert result["implied_correlation"] == 0.412


@responses.activate
def test_universe(fa):
    payload = {"symbols": [{"symbol": "SPY", "tier": 1}], "count": 1}
    responses.get(f"{BASE}/v1/universe", json=payload)
    result = fa.universe(sort="symbol", limit=20)
    url = responses.calls[0].request.url
    assert "/v1/universe" in url
    assert "sort=symbol" in url
    assert "limit=20" in url
    assert result["count"] == 1


@responses.activate
def test_expected_move(fa):
    payload = {"symbol": "SPY", "expected_moves": [{"expiry": "2026-06-20", "move_pct": 1.2}]}
    responses.get(f"{BASE}/v1/expected-move/SPY", json=payload)
    result = fa.expected_move("SPY", expiry="2026-06-20")
    assert "/v1/expected-move/SPY" in responses.calls[0].request.url
    assert "expiry=2026-06-20" in responses.calls[0].request.url
    assert result["symbol"] == "SPY"


@responses.activate
def test_realized_volatility(fa):
    payload = {
        "symbol": "AAPL",
        "underlying_price": 201.50,
        "estimators": {"yang_zhang": {"rv10": 17.0, "rv20": 19.7, "rv30": 20.3}},
    }
    responses.get(f"{BASE}/v1/volatility/realized/AAPL", json=payload)
    result = fa.realized_volatility("AAPL")
    assert "/v1/volatility/realized/AAPL" in responses.calls[0].request.url
    assert result["estimators"]["yang_zhang"]["rv20"] == 19.7


@responses.activate
def test_volatility_forecast(fa):
    payload = {
        "symbol": "AAPL",
        "ewma": {"lambda": 0.94, "vol_annualized": 19.6, "next_day_forecast": 19.6},
        "garch": {"model": "garch_1_1", "distribution": "student_t", "converged": True},
    }
    responses.get(f"{BASE}/v1/volatility/forecast/AAPL", json=payload)
    result = fa.volatility_forecast("AAPL", dist="student_t")
    assert "/v1/volatility/forecast/AAPL" in responses.calls[0].request.url
    assert "dist=student_t" in responses.calls[0].request.url
    assert result["garch"]["model"] == "garch_1_1"


@responses.activate
def test_vrp_history(fa):
    payload = {"symbol": "SPY", "days": 30, "history": []}
    responses.get(f"{BASE}/v1/vrp/SPY/history", json=payload)
    result = fa.vrp_history("SPY", days=30)
    assert "/v1/vrp/SPY/history" in responses.calls[0].request.url
    assert "days=30" in responses.calls[0].request.url
    assert result["days"] == 30


@responses.activate
def test_flow_stock_bars(fa):
    payload = {"symbol": "SPY", "resolution": "5m", "bars": []}
    responses.get(f"{BASE}/v1/flow/stocks/SPY/bars", json=payload)
    result = fa.flow_stock_bars("SPY", resolution="5m", minutes=120)
    url = responses.calls[0].request.url
    assert "/v1/flow/stocks/SPY/bars" in url
    assert "resolution=5m" in url
    assert "minutes=120" in url
    assert result["resolution"] == "5m"


@responses.activate
def test_strategy_flow_anomaly(fa):
    payload = {"strategy": "flow_anomaly", "symbol": "SPY", "decision": "candidate", "score": 72}
    responses.get(f"{BASE}/v1/strategies/flow-anomaly/SPY", json=payload)
    result = fa.strategy_flow_anomaly("SPY", expiry="2026-06-19")
    url = responses.calls[0].request.url
    assert "/v1/strategies/flow-anomaly/SPY" in url
    assert "expiry=2026-06-19" in url
    assert result["decision"] == "candidate"


@responses.activate
def test_strategy_vol_carry_params(fa):
    responses.get(f"{BASE}/v1/strategies/vol-carry/SPY", json={"strategy": "vol_carry", "score": 60})
    fa.strategy_vol_carry("SPY", target_short_delta=0.20, max_width=10, min_credit=0.15, min_open_interest=250)
    url = responses.calls[0].request.url
    assert "targetShortDelta=0.2" in url
    assert "maxWidth=10" in url
    assert "minCredit=0.15" in url
    assert "minOpenInterest=250" in url


@responses.activate
def test_strategy_term_structure_no_params(fa):
    responses.get(f"{BASE}/v1/strategies/term-structure/SPY", json={"strategy": "term_structure", "score": 50})
    fa.strategy_term_structure("SPY")
    assert responses.calls[0].request.url == f"{BASE}/v1/strategies/term-structure/SPY"


@responses.activate
def test_earnings_calendar(fa):
    payload = {"events": [{"symbol": "AAPL", "earnings_date": "2026-06-09"}], "count": 1}
    responses.get(f"{BASE}/v1/earnings/calendar", json=payload)
    result = fa.earnings_calendar(days=14, symbols=["AAPL", "MSFT"], importance=3)
    url = responses.calls[0].request.url
    assert "/v1/earnings/calendar" in url
    assert "days=14" in url
    assert "symbols=AAPL%2CMSFT" in url
    assert "importance=3" in url
    assert result["count"] == 1


@responses.activate
def test_earnings_screener(fa):
    responses.get(f"{BASE}/v1/earnings/screener", json={"events": [], "count": 0})
    fa.earnings_screener(sort="vrp_richest", limit=20, days=14, min_importance=3)
    url = responses.calls[0].request.url
    assert "sort=vrp_richest" in url
    assert "min_importance=3" in url


@responses.activate
def test_structure_pnl_post_body(fa):
    payload = {"breakevens": [102.1], "max_profit": 7.9, "max_loss": -2.1, "pnl_curve": []}
    responses.post(f"{BASE}/v1/structures/pnl", json=payload)
    legs = [
        {"action": "buy", "type": "call", "strike": 100, "premium": 3.20, "quantity": 1},
        {"action": "sell", "type": "call", "strike": 110, "premium": 1.10, "quantity": 1},
    ]
    result = fa.structure_pnl(legs, min_underlying=80, max_underlying=130, points=81)
    req = responses.calls[0].request
    assert req.method == "POST"
    assert req.url == f"{BASE}/v1/structures/pnl"
    body = _json.loads(req.body)
    assert body["legs"] == legs
    assert body["minUnderlying"] == 80
    assert body["maxUnderlying"] == 130
    assert body["points"] == 81
    assert result["max_profit"] == 7.9


@responses.activate
def test_structure_greeks_post_body(fa):
    responses.post(f"{BASE}/v1/structures/greeks", json={"spot": 102.5, "position_greeks": {}})
    legs = [{"action": "buy", "type": "call", "strike": 100, "expiry": "2026-07-17", "impliedVol": 0.28, "quantity": 1}]
    fa.structure_greeks(legs, spot=102.5, today="2026-06-05", rate=0.045, dividend_yield=0.013)
    body = _json.loads(responses.calls[0].request.body)
    assert body["legs"] == legs
    assert body["spot"] == 102.5
    assert body["today"] == "2026-06-05"
    assert body["rate"] == 0.045
    assert body["dividendYield"] == 0.013


@responses.activate
def test_zero_dte_with_expiry(fa):
    responses.get(f"{BASE}/v1/exposure/zero-dte/SPY", json={"symbol": "SPY", "strikes": []})
    fa.zero_dte("SPY", expiry="2026-06-09")
    assert "expiry=2026-06-09" in responses.calls[0].request.url


@responses.activate
def test_vrp_with_date(fa):
    responses.get(f"{BASE}/v1/vrp/SPY", json={"symbol": "SPY"})
    fa.vrp("SPY", date="2026-06-05")
    assert "date=2026-06-05" in responses.calls[0].request.url


# ── Client config ──────────────────────────────────────────────────


def test_api_key_in_header():
    fa = FlashAlpha("my-secret-key")
    assert fa._session.headers["X-Api-Key"] == "my-secret-key"


def test_custom_base_url():
    fa = FlashAlpha("key", base_url="https://custom.api.com/")
    assert fa.base_url == "https://custom.api.com"


def test_custom_timeout():
    fa = FlashAlpha("key", timeout=10)
    assert fa.timeout == 10


# ── Additional endpoint coverage (Growth+ / Alpha+) ──────────────────


@responses.activate
def test_exposure_sheet(fa):
    responses.get(f"{BASE}/v1/exposure/sheet/SPY", json={"symbol": "SPY", "exposure": {}})
    result = fa.exposure_sheet("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_exposure_sheet_with_filters(fa):
    responses.get(f"{BASE}/v1/exposure/sheet/SPY", json={"symbol": "SPY"})
    fa.exposure_sheet("SPY", expiration="2026-07-17", min_oi=100)
    url = responses.calls[0].request.url
    assert "expiration=2026-07-17" in url
    assert "min_oi=100" in url


@responses.activate
def test_exposure_term_structure(fa):
    responses.get(f"{BASE}/v1/exposure/term-structure/SPY", json={"symbol": "SPY", "dte_buckets": []})
    result = fa.exposure_term_structure("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_exposure_basket_list(fa):
    responses.get(f"{BASE}/v1/exposure/basket", json={"symbols": ["SPY", "QQQ"], "aggregate": {}})
    result = fa.exposure_basket(["SPY", "QQQ"])
    url = responses.calls[0].request.url
    assert "symbols=SPY%2CQQQ" in url or "symbols=SPY,QQQ" in url


@responses.activate
def test_exposure_basket_with_weights(fa):
    responses.get(f"{BASE}/v1/exposure/basket", json={"symbols": ["SPY", "QQQ"], "weights": [0.6, 0.4]})
    result = fa.exposure_basket(["SPY", "QQQ"], weights=[0.6, 0.4])
    url = responses.calls[0].request.url
    assert "weights=" in url


@responses.activate
def test_exposure_oi_diff(fa):
    responses.get(f"{BASE}/v1/exposure/oi-diff/SPY", json={"symbol": "SPY", "changes": []})
    result = fa.exposure_oi_diff("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_exposure_oi_diff_with_top_n(fa):
    responses.get(f"{BASE}/v1/exposure/oi-diff/SPY", json={"symbol": "SPY", "top_n": 10})
    fa.exposure_oi_diff("SPY", top_n=10)
    assert "topN=10" in responses.calls[0].request.url


@responses.activate
def test_liquidity(fa):
    responses.get(f"{BASE}/v1/liquidity/SPY", json={"symbol": "SPY", "bid_ask_spread": 0.01})
    result = fa.liquidity("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_skew_term(fa):
    responses.get(f"{BASE}/v1/volatility/skew-term/SPY", json={"symbol": "SPY", "term": []})
    result = fa.skew_term("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_spot_vol_correlation(fa):
    responses.get(f"{BASE}/v1/volatility/spot-vol-correlation/SPY", json={"symbol": "SPY", "correlation": 0.0})
    result = fa.spot_vol_correlation("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_dispersion_alt(fa):
    responses.get(f"{BASE}/v1/dispersion", json={"index": "SPX", "constituents": []})
    result = fa.dispersion(index="SPX", symbols=["AAPL", "MSFT", "GOOGL"])
    assert "index" in result


@responses.activate
def test_dispersion_with_weights(fa):
    responses.get(f"{BASE}/v1/dispersion", json={"index": "SPX"})
    fa.dispersion(index="SPX", symbols="AAPL,MSFT", weights=[0.6, 0.4])
    url = responses.calls[0].request.url
    assert "weights=" in url


@responses.activate
def test_vix_state(fa):
    responses.get(f"{BASE}/v1/macro/vix-state", json={"vix": 20.0, "regime": "normal"})
    result = fa.vix_state()
    assert "vix" in result


@responses.activate
def test_universe_alt(fa):
    responses.get(f"{BASE}/v1/universe", json={"symbols": ["SPY", "QQQ"], "count": 2})
    result = fa.universe()
    assert "symbols" in result


@responses.activate
def test_universe_with_sort_and_limit(fa):
    responses.get(f"{BASE}/v1/universe", json={"symbols": ["SPY"], "count": 1})
    fa.universe(sort="gex_exposure", limit=1)
    url = responses.calls[0].request.url
    assert "sort=gex_exposure" in url
    assert "limit=1" in url


@responses.activate
def test_flow_levels(fa):
    responses.get(f"{BASE}/v1/flow/levels/SPY", json={"symbol": "SPY", "levels": []})
    result = fa.flow_levels("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_levels_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/levels/SPY", json={"symbol": "SPY"})
    fa.flow_levels("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_pin_risk(fa):
    responses.get(f"{BASE}/v1/flow/pin-risk/SPY", json={"symbol": "SPY", "strikes": []})
    result = fa.flow_pin_risk("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_pin_risk_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/pin-risk/SPY", json={"symbol": "SPY"})
    fa.flow_pin_risk("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_summary(fa):
    responses.get(f"{BASE}/v1/flow/summary/SPY", json={"symbol": "SPY", "summary": {}})
    result = fa.flow_summary("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_summary_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/summary/SPY", json={"symbol": "SPY"})
    fa.flow_summary("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_oi(fa):
    responses.get(f"{BASE}/v1/flow/oi/SPY", json={"symbol": "SPY", "oi_flow": {}})
    result = fa.flow_oi("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_oi_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/oi/SPY", json={"symbol": "SPY"})
    fa.flow_oi("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_gex(fa):
    responses.get(f"{BASE}/v1/flow/gex/SPY", json={"symbol": "SPY", "gex": {}})
    result = fa.flow_gex("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_gex_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/gex/SPY", json={"symbol": "SPY"})
    fa.flow_gex("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_dex(fa):
    responses.get(f"{BASE}/v1/flow/dex/SPY", json={"symbol": "SPY", "dex": {}})
    result = fa.flow_dex("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_dex_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/dex/SPY", json={"symbol": "SPY"})
    fa.flow_dex("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_dealer_risk(fa):
    responses.get(f"{BASE}/v1/flow/dealer-risk/SPY", json={"symbol": "SPY", "risk": {}})
    result = fa.flow_dealer_risk("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_dealer_risk_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/dealer-risk/SPY", json={"symbol": "SPY"})
    fa.flow_dealer_risk("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_live(fa):
    responses.get(f"{BASE}/v1/flow/live/SPY", json={"symbol": "SPY", "live": {}})
    result = fa.flow_live("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_live_with_expiry(fa):
    responses.get(f"{BASE}/v1/flow/live/SPY", json={"symbol": "SPY"})
    fa.flow_live("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_flow_zero_dte_heatmap(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/heatmap/SPY", json={"symbol": "SPY", "heatmap": []})
    result = fa.flow_zero_dte_heatmap("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_zero_dte_heatmap_with_metric(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/heatmap/SPY", json={"symbol": "SPY"})
    fa.flow_zero_dte_heatmap("SPY", metric="gex", mode="raw")
    url = responses.calls[0].request.url
    assert "metric=gex" in url
    assert "mode=raw" in url


@responses.activate
def test_flow_zero_dte_series(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/series/SPY", json={"symbol": "SPY", "series": []})
    result = fa.flow_zero_dte_series("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_zero_dte_series_with_bar(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/series/SPY", json={"symbol": "SPY"})
    fa.flow_zero_dte_series("SPY", bar="5m")
    assert "bar=5m" in responses.calls[0].request.url


@responses.activate
def test_flow_zero_dte_strike_flow(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/strike-flow/SPY", json={"symbol": "SPY", "strikes": []})
    result = fa.flow_zero_dte_strike_flow("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_zero_dte_strike_flow_with_bar(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/strike-flow/SPY", json={"symbol": "SPY"})
    fa.flow_zero_dte_strike_flow("SPY", bar="1m")
    assert "bar=1m" in responses.calls[0].request.url


@responses.activate
def test_flow_zero_dte_hedge_flow(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/hedge-flow/SPY", json={"symbol": "SPY", "flows": []})
    result = fa.flow_zero_dte_hedge_flow("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_flow_zero_dte_hedge_flow_with_side(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/hedge-flow/SPY", json={"symbol": "SPY"})
    fa.flow_zero_dte_hedge_flow("SPY", side="calls", bar="1m")
    url = responses.calls[0].request.url
    assert "side=calls" in url
    assert "bar=1m" in url


@responses.activate
def test_flow_zero_dte_leaderboard_alt(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/leaderboard", json={"symbols": []})
    result = fa.flow_zero_dte_leaderboard()
    assert "symbols" in result


@responses.activate
def test_flow_zero_dte_leaderboard_with_params_alt(fa):
    responses.get(f"{BASE}/v1/flow/zero-dte/leaderboard", json={"symbols": []})
    fa.flow_zero_dte_leaderboard(metric="heat", n=20)
    url = responses.calls[0].request.url
    assert "metric=heat" in url
    assert "n=20" in url


@responses.activate
def test_expected_move_alt(fa):
    responses.get(f"{BASE}/v1/expected-move/SPY", json={"symbol": "SPY", "move": {}})
    result = fa.expected_move("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_expected_move_with_expiry(fa):
    responses.get(f"{BASE}/v1/expected-move/SPY", json={"symbol": "SPY"})
    fa.expected_move("SPY", expiry="2026-06-19")
    assert "expiry=2026-06-19" in responses.calls[0].request.url


@responses.activate
def test_realized_volatility_alt(fa):
    responses.get(f"{BASE}/v1/volatility/realized/SPY", json={"symbol": "SPY", "hv": 0.25})
    result = fa.realized_volatility("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_volatility_forecast_alt(fa):
    responses.get(f"{BASE}/v1/volatility/forecast/SPY", json={"symbol": "SPY", "forecast": {}})
    result = fa.volatility_forecast("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_volatility_forecast_with_dist(fa):
    responses.get(f"{BASE}/v1/volatility/forecast/SPY", json={"symbol": "SPY"})
    fa.volatility_forecast("SPY", dist="gaussian")
    assert "dist=gaussian" in responses.calls[0].request.url


@responses.activate
def test_vrp_history_alt(fa):
    responses.get(f"{BASE}/v1/vrp/SPY/history", json={"symbol": "SPY", "history": []})
    result = fa.vrp_history("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_vrp_history_with_days(fa):
    responses.get(f"{BASE}/v1/vrp/SPY/history", json={"symbol": "SPY"})
    fa.vrp_history("SPY", days=30)
    assert "days=30" in responses.calls[0].request.url


@responses.activate
def test_earnings_calendar_alt(fa):
    responses.get(f"{BASE}/v1/earnings/calendar", json={"events": []})
    result = fa.earnings_calendar()
    assert "events" in result


@responses.activate
def test_earnings_calendar_with_filters(fa):
    responses.get(f"{BASE}/v1/earnings/calendar", json={"events": []})
    fa.earnings_calendar(days=7, importance=2)
    url = responses.calls[0].request.url
    assert "days=7" in url
    assert "importance=2" in url


@responses.activate
def test_earnings_expected_move(fa):
    responses.get(f"{BASE}/v1/earnings/expected-move/SPY", json={"symbol": "SPY", "move": {}})
    result = fa.earnings_expected_move("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_earnings_history(fa):
    responses.get(f"{BASE}/v1/earnings/history/SPY", json={"symbol": "SPY", "history": []})
    result = fa.earnings_history("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_earnings_history_with_limit(fa):
    responses.get(f"{BASE}/v1/earnings/history/SPY", json={"symbol": "SPY"})
    fa.earnings_history("SPY", limit=10)
    assert "limit=10" in responses.calls[0].request.url


@responses.activate
def test_earnings_iv_crush(fa):
    responses.get(f"{BASE}/v1/earnings/iv-crush/SPY", json={"symbol": "SPY", "crush": {}})
    result = fa.earnings_iv_crush("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_earnings_vrp(fa):
    responses.get(f"{BASE}/v1/earnings/vrp/SPY", json={"symbol": "SPY", "vrp": {}})
    result = fa.earnings_vrp("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_earnings_dealer_positioning(fa):
    responses.get(f"{BASE}/v1/earnings/dealer-positioning/SPY", json={"symbol": "SPY", "positioning": {}})
    result = fa.earnings_dealer_positioning("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_earnings_strategies(fa):
    responses.get(f"{BASE}/v1/earnings/strategies/SPY", json={"symbol": "SPY", "strategies": []})
    result = fa.earnings_strategies("SPY")
    assert result["symbol"] == "SPY"


@responses.activate
def test_strategy_flow_anomaly_alt(fa):
    responses.get(f"{BASE}/v1/strategies/flow-anomaly/SPY", json={"score": 72, "decision": "candidate"})
    result = fa.strategy_flow_anomaly("SPY")
    assert result["score"] == 72


@responses.activate
def test_strategy_expiry_positioning(fa):
    responses.get(f"{BASE}/v1/strategies/expiry-positioning/SPY", json={"score": 65, "decision": "neutral"})
    result = fa.strategy_expiry_positioning("SPY")
    assert result["score"] == 65


@responses.activate
def test_strategy_zero_dte(fa):
    responses.get(f"{BASE}/v1/strategies/zero-dte/SPY", json={"score": 58, "decision": "avoid"})
    result = fa.strategy_zero_dte("SPY")
    assert result["score"] == 58


@responses.activate
def test_strategy_dealer_regime(fa):
    responses.get(f"{BASE}/v1/strategies/dealer-regime/SPY", json={"score": 60, "decision": "candidate"})
    result = fa.strategy_dealer_regime("SPY")
    assert result["score"] == 60


@responses.activate
def test_strategy_vol_carry(fa):
    responses.get(f"{BASE}/v1/strategies/vol-carry/SPY", json={"score": 55, "decision": "neutral"})
    result = fa.strategy_vol_carry("SPY")
    assert result["score"] == 55


@responses.activate
def test_strategy_yield_enhancement(fa):
    responses.get(f"{BASE}/v1/strategies/yield-enhancement/SPY", json={"score": 62, "decision": "candidate"})
    result = fa.strategy_yield_enhancement("SPY")
    assert result["score"] == 62


@responses.activate
def test_strategy_surface_anomaly(fa):
    responses.get(f"{BASE}/v1/strategies/surface-anomaly/SPY", json={"score": 70, "decision": "candidate"})
    result = fa.strategy_surface_anomaly("SPY")
    assert result["score"] == 70


@responses.activate
def test_strategy_skew(fa):
    responses.get(f"{BASE}/v1/strategies/skew/SPY", json={"score": 45, "decision": "avoid"})
    result = fa.strategy_skew("SPY")
    assert result["score"] == 45


@responses.activate
def test_strategy_term_structure(fa):
    responses.get(f"{BASE}/v1/strategies/term-structure/SPY", json={"score": 50, "decision": "neutral"})
    result = fa.strategy_term_structure("SPY")
    assert result["score"] == 50


@responses.activate
def test_strategy_tail_pricing(fa):
    responses.get(f"{BASE}/v1/strategies/tail-pricing/SPY", json={"score": 48, "decision": "avoid"})
    result = fa.strategy_tail_pricing("SPY")
    assert result["score"] == 48
