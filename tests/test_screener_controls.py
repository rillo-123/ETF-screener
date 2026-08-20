import json
from pathlib import Path

import pandas as pd

from ETF_screener.screener_controls import (
    _ema_cross_event_mask,
    _ema_flatten_mask,
    _ha_ema_volume_mask,
    _heikin_ashi_ohlc,
    _validate_ha_ema_volume_conditions,
    _latest_event_age_days,
    _macd_cross_mask,
    _price_ema_cross_mask,
    _required_screen_history_days,
    RsiEvent,
    RsiEventSequence,
    _rsi_cross_mask,
    _rsi_event_sequence_ages,
    _stoch_cross_mask,
    _supertrend_cross_mask,
    _volume_spike_mask,
)


def test_screen_history_includes_ema_200_warmup_and_lookback():
    assert _required_screen_history_days({"lookback_days": 30}) == 830


def test_screen_history_expands_for_long_active_ema():
    filters = {
        "lookback_days": 10,
        "ema_slope_period_1": 20,
        "ema_slope_period_2": 50,
        "ema_slope_period_3": 250,
        "price_ema_event_enabled": True,
        "price_ema_period": 300,
    }
    assert _required_screen_history_days(filters) == 1210


def _dates(length=8):
    return pd.Series(pd.date_range("2026-01-01", periods=length, freq="D"))


def test_rsi_cross_mask_detects_both_directions():
    rsi = pd.Series([50.0, 42.0, 39.0, 45.0, 51.0])

    down = _rsi_cross_mask(rsi, level=40, mode="cross_down")
    up = _rsi_cross_mask(rsi, level=50, mode="cross_up")

    assert down[2]
    assert up[4]
    assert not down.iloc[[0, 1, 3, 4]].any()


def test_rsi_event_sequence_requires_distinct_consecutive_crossings():
    dates = pd.Series(pd.date_range("2026-01-01", periods=12, freq="D"))
    rsi = pd.Series(
        [50.0, 39.0, 45.0, 55.0, 61.0, 49.0, 42.0, 55.0, 65.0, 35.0, 45.0, 50.0]
    )
    events = [
        {"rsi_cross_value": 50.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 8},
        {"rsi_cross_value": 40.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 3},
    ]

    ages = _rsi_event_sequence_ages(rsi, dates, events, lookback_days=10)

    assert ages == [6, 2]


def test_rsi_event_sequence_accepts_each_window_boundary():
    dates = pd.Series(pd.date_range("2026-01-01", periods=12, freq="D"))
    rsi = pd.Series(
        [50.0, 39.0, 45.0, 55.0, 61.0, 49.0, 42.0, 55.0, 65.0, 35.0, 45.0, 50.0]
    )
    events = [
        {"rsi_cross_value": 50.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 6},
        {"rsi_cross_value": 40.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 2},
    ]

    assert _rsi_event_sequence_ages(rsi, dates, events, lookback_days=10) == [6, 2]
    events[1]["rsi_event_age"] = 1
    assert _rsi_event_sequence_ages(rsi, dates, events, lookback_days=10) is None


def test_rsi_event_sequence_traces_three_chronological_crossdowns():
    dates = pd.Series(pd.date_range("2026-01-01", periods=10, freq="D"))
    rsi = pd.Series([60.0, 49.0, 45.0, 39.0, 35.0, 29.0, 32.0, 35.0, 40.0, 45.0])
    events = [
        {"rsi_cross_value": 50.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 8},
        {"rsi_cross_value": 40.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 6},
        {"rsi_cross_value": 30.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 4},
    ]

    assert _rsi_event_sequence_ages(rsi, dates, events, lookback_days=10) == [8, 6, 4]


def test_rsi_event_sequence_normalization_preserves_two_steps():
    from ETF_screener.screener_controls import normalize_screen_filters

    filters = normalize_screen_filters(
        {
            "lookback_days": 30,
            "rsi_event_enabled": True,
            "rsi_events": [
                {"cross_value": 40, "cross_mode": "cross_down", "event_age": 5},
                {"cross_value": 50, "cross_mode": "cross_up", "event_age": 12},
            ],
        }
    )

    assert filters["rsi_events"] == [
        {"rsi_cross_value": 40.0, "rsi_cross_mode": "cross_down", "rsi_event_age": 5},
        {"rsi_cross_value": 50.0, "rsi_cross_mode": "cross_up", "rsi_event_age": 12},
    ]


def test_rsi_filter_normalization_supports_optional_minimum():
    from ETF_screener.screener_controls import normalize_screen_filters

    defaults = normalize_screen_filters({})
    enabled = normalize_screen_filters(
        {"rsi_filter_enabled": True, "rsi_filter_min": 62}
    )

    assert defaults["rsi_filter_enabled"] is False
    assert defaults["rsi_filter_min"] == 50.0
    assert enabled["rsi_filter_enabled"] is True
    assert enabled["rsi_filter_min"] == 62.0


def test_price_ema_normalization_supports_multiple_price_sources():
    from ETF_screener.screener_controls import normalize_screen_filters

    filters = normalize_screen_filters(
        {
            "price_ema_event_enabled": True,
            "price_ema_sources": ["high", "low", "high"],
        }
    )

    assert filters["price_ema_sources"] == ["high", "low"]
    assert [event["price_ema_source"] for event in filters["price_ema_events"]] == [
        "high",
        "low",
    ]


def test_rsi_events_are_instantiable_and_serialize_at_the_api_boundary():
    event = RsiEvent(level=50.0, mode="cross_down", max_age_days=8, event_id="rsi")
    sequence = RsiEventSequence((event,))

    assert sequence.events[0] is event
    assert event.to_dict() == {
        "rsi_cross_value": 50.0,
        "rsi_cross_mode": "cross_down",
        "rsi_event_age": 8,
        "rsi_event_id": "rsi",
    }


def test_macd_cross_mask_applies_mode_region_constraints():
    macd = pd.Series([-1.0, -0.5, -0.4, -0.1, 1.0])
    signal = pd.Series([-0.8, -0.6, -0.3, -0.2, 0.8])

    assert _macd_cross_mask(macd, signal, mode="bullish_cross").iloc[3]
    assert _macd_cross_mask(macd, signal, mode="low_cross_buy").iloc[3]
    assert not _macd_cross_mask(macd, signal, mode="high_cross_sell").any()

    bearish_macd = macd.iloc[::-1].reset_index(drop=True)
    bearish_signal = signal.iloc[::-1].reset_index(drop=True)
    assert _macd_cross_mask(bearish_macd, bearish_signal, mode="bearish_cross").any()


def test_stoch_cross_mask_requires_the_selected_region():
    k = pd.Series([10.0, 12.0, 25.0, 20.0, 8.0])
    d = pd.Series([12.0, 10.0, 20.0, 15.0, 10.0])

    up_below = _stoch_cross_mask(k, d, level=20, mode="cross_up", region="below")
    down_below = _stoch_cross_mask(k, d, level=20, mode="cross_down", region="below")
    down_any = _stoch_cross_mask(k, d, level=20, mode="cross_down", region="any")

    assert up_below.iloc[1]
    assert not up_below.iloc[2]  # The cross occurs above the trigger.
    assert down_below.iloc[4]
    assert down_any.iloc[4]


def test_supertrend_cross_mask_detects_both_regime_changes():
    green = pd.Series([False, False, True, True, False, False, True])

    red_to_green = _supertrend_cross_mask(green, mode="red_to_green")
    green_to_red = _supertrend_cross_mask(green, mode="green_to_red")

    assert red_to_green.iloc[[2, 6]].all()
    assert green_to_red.iloc[4]
    assert not red_to_green.iloc[4]


def test_ema_cross_mask_detects_requested_direction_without_hidden_slope_filter():
    close = pd.Series([100.0] * 30 + [80.0] * 8 + [130.0] * 12)

    cross_up, _states, _fast_slope, _slow_slope = _ema_cross_event_mask(
        close,
        fast_period=3,
        slow_period=10,
        fast_slope_direction="any",
        slow_slope_direction="any",
        cross_mode="cross_up",
    )
    cross_down, *_ = _ema_cross_event_mask(
        close,
        fast_period=3,
        slow_period=10,
        fast_slope_direction="any",
        slow_slope_direction="any",
        cross_mode="cross_down",
    )

    assert cross_down.any()
    assert cross_up.any()


def test_price_ema_cross_mask_detects_both_directions():
    close = pd.Series([100.0, 90.0, 95.0, 110.0])

    cross_down = _price_ema_cross_mask(close, period=3, mode="cross_down")
    cross_up = _price_ema_cross_mask(close, period=3, mode="cross_up")

    assert cross_down.iloc[1]
    assert cross_up.iloc[3]
    assert not cross_down.iloc[[0, 2, 3]].any()


def test_ema_flatten_mask_classifies_top_and_bottom():
    close = pd.Series([100.0, 120.0, 120.0, 120.0, 100.0])

    top, top_states = _ema_flatten_mask(
        close, period=2, lookback=1, tolerance=5.0, mode="top"
    )
    bottom, bottom_states = _ema_flatten_mask(
        close, period=2, lookback=1, tolerance=5.0, mode="bottom"
    )

    assert top.any()
    assert top_states[top].eq("top").all()
    assert not bottom.any()

    bottom_close = pd.Series([100.0, 80.0, 80.0, 80.0, 100.0])
    bottom, bottom_states = _ema_flatten_mask(
        bottom_close, period=2, lookback=1, tolerance=5.0, mode="bottom"
    )
    assert bottom.any()
    assert bottom_states[bottom].eq("bottom").all()


def test_ema_flatten_filter_normalizes_top_bottom_options():
    from ETF_screener.screener_controls import normalize_screen_filters

    filters = normalize_screen_filters(
        {"lookback_days": 10, "ema_flatten_mode": "top", "ema_flatten_period": 40}
    )

    assert filters["ema_flatten_mode"] == "top"
    assert filters["ema_flatten_period"] == 40


def test_volume_spike_mask_detects_fresh_threshold_crossing():
    volume = pd.Series([100.0] * 20 + [300.0, 100.0])

    crossed, ratio = _volume_spike_mask(volume, period=20, multiplier=2.0)

    assert crossed.iloc[20]
    assert ratio.iloc[20] >= 2.0
    assert not crossed.iloc[21]


def _ha_volume_fixture(*, baseline_price=10.0, final_price=20.0, final_volume=500.0):
    prices = [baseline_price] * 6 + [final_price]
    volumes = [100.0] * 6 + [final_volume]
    frame = pd.DataFrame(
        {
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
        }
    )
    return frame, pd.Series(volumes)


def _run_ha_volume_mask(frame, volume, **overrides):
    options = {
        "ema1_period": 3,
        "ema1_source": "close",
        "ema2_period": 3,
        "ema2_source": "close",
        "start_field": "close",
        "start_line": "ema1",
        "start_relation": "above",
        "end_field": "high",
        "end_line": "ema1",
        "end_relation": "above",
        "volume_period": 3,
        "volume_multiplier": 1.5,
        "candle_color": "any",
    }
    options.update(overrides)
    return _ha_ema_volume_mask(frame, volume, **options)


def test_heikin_ashi_ohlc_uses_recursive_open_and_transformed_extremes():
    frame = pd.DataFrame(
        {
            "open": [10.0, 12.0],
            "high": [14.0, 16.0],
            "low": [8.0, 10.0],
            "close": [12.0, 14.0],
        }
    )

    ha_open, ha_high, ha_low, ha_close = _heikin_ashi_ohlc(frame)

    assert ha_close.tolist() == [11.0, 13.0]
    assert ha_open.tolist() == [11.0, 11.0]
    assert ha_high.tolist() == [14.0, 16.0]
    assert ha_low.tolist() == [8.0, 10.0]


def test_ha_ema_volume_mask_requires_all_conditions_on_same_candle():
    frame, volume = _ha_volume_fixture()

    matched, ratio = _run_ha_volume_mask(frame, volume)

    assert not matched.iloc[:6].any()
    assert matched.iloc[6]
    assert ratio.iloc[6] >= 1.5


def test_ha_ema_volume_mask_respects_below_relations_and_volume_threshold():
    frame, volume = _ha_volume_fixture(baseline_price=20.0, final_price=5.0)

    matched, ratio = _run_ha_volume_mask(
        frame,
        volume,
        start_field="low",
        start_relation="below",
        end_field="close",
        end_relation="below",
    )

    assert matched.iloc[6]
    assert ratio.iloc[6] >= 1.5

    no_spike, _ = _run_ha_volume_mask(
        frame,
        pd.Series([100.0] * 7),
        start_field="low",
        start_relation="below",
        end_field="close",
        end_relation="below",
    )
    assert not no_spike.any()


def test_ha_ema_volume_mask_has_no_matches_during_ema_warmup():
    frame, volume = _ha_volume_fixture()

    matched, _ = _run_ha_volume_mask(frame, volume, ema1_period=5, volume_period=5)

    assert not matched.iloc[:4].any()


def test_ha_ema_volume_mask_enforces_candle_color():
    frame, volume = _ha_volume_fixture()

    green, _ = _run_ha_volume_mask(frame, volume, candle_color="green")
    red, _ = _run_ha_volume_mask(frame, volume, candle_color="red")

    assert green.iloc[6]
    assert not red.iloc[6]


def test_ha_ema_volume_mask_falls_back_to_close_when_ohlc_source_is_missing():
    full_frame, volume = _ha_volume_fixture()
    close_only_frame = full_frame[["close"]]

    matched, ratio = _run_ha_volume_mask(
        close_only_frame,
        volume,
        ema1_source="open",
        ema2_source="open",
    )

    assert matched.iloc[6]
    assert ratio.iloc[6] >= 1.5


def test_ha_ema_volume_conditions_validate_ohlc_paradoxes():
    valid = [
        {"field": "low", "enabled": True, "zone": "below_ema2"},
        {"field": "close", "enabled": True, "zone": "above_ema1"},
    ]
    invalid = [
        {"field": "low", "enabled": True, "zone": "above_ema1"},
        {"field": "high", "enabled": True, "zone": "below_ema2"},
    ]

    assert _validate_ha_ema_volume_conditions(valid) == []
    assert _validate_ha_ema_volume_conditions(invalid)


def test_ha_ema_volume_mask_applies_four_ohlc_zone_conditions():
    frame, volume = _ha_volume_fixture()
    conditions = [
        {"field": "open", "enabled": False, "zone": "above_ema1"},
        {"field": "high", "enabled": True, "zone": "above_ema1"},
        {"field": "low", "enabled": False, "zone": "below_ema2"},
        {"field": "close", "enabled": True, "zone": "above_ema1"},
    ]

    matched, _ = _run_ha_volume_mask(frame, volume, conditions=conditions)

    assert matched.iloc[6]


def test_latest_event_age_uses_calendar_days_and_includes_boundary():
    dates = _dates()
    mask = pd.Series([False, False, False, False, True, False, False, False])

    assert _latest_event_age_days(mask, dates, lookback_days=2) is None
    assert _latest_event_age_days(mask, dates, lookback_days=4) == 3


def test_latest_event_age_supports_today_as_zero_days():
    dates = _dates()
    mask = pd.Series([False] * (len(dates) - 1) + [True])

    assert _latest_event_age_days(mask, dates, lookback_days=30) == 0


def test_saved_screen_presets_support_dsl_and_filter_formats():
    config_path = Path("config") / "screener_presets.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "screen_presets_v1"
    assert payload["presets"]

    event_keys = {
        "macd_event_enabled",
        "rsi_event_enabled",
        "stoch_event_enabled",
        "supertrend_event_enabled",
        "ema_relationship_enabled",
        "volume_spike_enabled",
    }

    for preset in payload["presets"]:
        assert str(preset.get("name") or "").strip()
        dsl = str(preset.get("dsl") or "").strip()
        if dsl:
            assert "filters" not in preset
            continue

        filters = preset.get("filters")
        assert isinstance(filters, dict)
        lookback_days = filters.get("lookback_days")
        assert isinstance(lookback_days, int)
        for key in event_keys:
            age_key = key.replace("_enabled", "_age")
            if age_key in filters:
                assert 0 <= filters[age_key] <= lookback_days
