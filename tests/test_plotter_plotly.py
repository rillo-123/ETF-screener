import base64
import json
import numpy as np
import pandas as pd

from ETF_screener.plotter_plotly import InteractivePlotter


def test_context_ribbon_preserves_false_gaps():
    dates = pd.date_range(start="2024-01-01", periods=6)
    close = np.array([101.0, 99.0, 102.0, 98.0, 103.0, 97.0])
    ema_200 = np.array([100.0] * 6)
    ema_200_slope = np.array([1.0] * 6)

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.array([1000.0] * 6),
            "ema_200": ema_200,
            "ema_200_slope": ema_200_slope,
        }
    )

    strategy_content = """
BEGIN CONTEXT_REGIME
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END
"""

    plotter = InteractivePlotter()
    fig = plotter.create_plot(df, "TEST", strategy_content=strategy_content)

    # Block name "CONTEXT_REGIME" → title case label "Context_Regime"
    context_traces = [
        t for t in fig.data if getattr(t, "name", "") == "Context_Regime - #2563eb"
    ]
    assert context_traces, "Expected context ribbon trace to be present"

    trace = context_traces[0]
    assert trace.type == "bar"

    # Validate the evaluated mask preserves false positions.
    ribbon = plotter._build_strategy_layer_ribbons(strategy_content)[0]
    clean = plotter._to_eval_condition(ribbon["condition"])
    eval_df = df.copy()
    eval_df.columns = [c.lower() for c in eval_df.columns]
    eval_df = plotter._prepare_eval_columns(eval_df, clean)
    mask = eval_df.eval(clean, engine="python").fillna(False).astype(bool)
    false_positions = np.flatnonzero(~mask.to_numpy()).tolist()
    assert false_positions == [1, 3, 5]


def test_context_ribbon_has_left_side_label_annotation():
    dates = pd.date_range(start="2024-01-01", periods=4)
    close = np.array([101.0, 99.0, 102.0, 98.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.array([1000.0] * 4),
            "ema_200": np.array([100.0] * 4),
            "ema_200_slope": np.array([1.0] * 4),
        }
    )

    strategy_content = """
BEGIN CONTEXT_REGIME
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )

    # Block "CONTEXT_REGIME" → title case "Context_Regime"
    labels = [
        a
        for a in fig.layout.annotations
        if getattr(a, "text", "") == "<b>Context_Regime</b>"
    ]
    assert labels, "Expected left-side annotation for Context_Regime"

    label = labels[0]
    assert label.xref == "paper"
    assert label.yref == "paper"
    assert label.xanchor == "left"
    assert label.align == "left"
    assert label.font.size == 10
    assert fig.layout.margin.l == 300
    assert float(label.x) == float(fig.layout.legend.x)
    assert fig.layout.legend.xanchor == "left"


def test_create_plot_hides_sell_signal_markers():
    dates = pd.date_range(start="2024-01-01", periods=5)
    close = np.array([100.0, 102.0, 101.0, 103.0, 102.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.array([1000.0] * 5),
            "Signal": np.array([0, 1, 0, -1, 0]),
            "ema_200": np.array([99.0] * 5),
            "ema_200_slope": np.array([1.0] * 5),
        }
    )

    fig = InteractivePlotter().create_plot(df, "TEST", strategy_content=None)

    trace_names = {getattr(t, "name", "") for t in fig.data}
    assert "Sell Signal" not in trace_names
    assert "Buy Signal" not in trace_names


def test_only_bottom_xaxis_shows_ticklabels_for_ribbon_layout():
    dates = pd.date_range(start="2024-01-01", periods=8)
    close = np.array([100.0, 101.0, 99.0, 102.0, 98.0, 103.0, 97.0, 104.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.array([1000.0] * 8),
            "ema_200": np.array([99.0] * 8),
            "ema_200_slope": np.array([1.0] * 8),
            "ema_50": np.array([99.5] * 8),
            "macd": np.array([0.1] * 8),
            "macd_signal": np.array([0.0] * 8),
            "macd_d1": np.array([0.05] * 8),
            "macd_signal_d1": np.array([0.01] * 8),
            "macd_hist_d1": np.array([-0.1] * 8),
            "vol_ema_20": np.array([900.0] * 8),
        }
    )

    strategy_content = """
BEGIN CONTEXT_REGIME
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN SETUP_COMPRESSION
FILTER: close > ema_50
END

BEGIN TRIGGER_MACD_CROSS
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )

    xaxis_keys = [k for k in fig.layout if str(k).startswith("xaxis")]
    assert xaxis_keys, "Expected at least one xaxis in layout"

    bottom_label_axes = [
        k for k in xaxis_keys if getattr(fig.layout[k], "showticklabels", False)
    ]
    assert len(bottom_label_axes) == 1
    bottom_axis = bottom_label_axes[0]

    for k in xaxis_keys:
        is_bottom = k == bottom_axis
        ticks = getattr(fig.layout[k], "ticks", None)
        showline = getattr(fig.layout[k], "showline", None)
        assert (ticks == "outside") == is_bottom
        assert bool(showline) == is_bottom


def test_simplified_dsl_does_not_fallback_to_default_ribbons():
    dates = pd.date_range(start="2024-01-01", periods=10)
    close = np.linspace(100.0, 105.0, 10)

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(10, 200000.0),
            "ema_200": np.linspace(95.0, 100.0, 10),
            "ema_200_slope": np.full(10, 0.1),
            "macd": np.linspace(0.1, 0.3, 10),
            "macd_signal": np.linspace(0.05, 0.25, 10),
            "macd_d1": np.linspace(0.09, 0.29, 10),
            "macd_signal_d1": np.linspace(0.06, 0.26, 10),
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    label_texts = {getattr(a, "text", "") for a in fig.layout.annotations}

    assert "<b>Context</b>" in label_texts
    assert "<b>Trigger</b>" in label_texts
    assert "<b>Setup</b>" not in label_texts
    assert "<b>Risk</b>" not in label_texts


def test_trigger_ribbon_uses_markers_for_single_bar_visibility():
    dates = pd.date_range(start="2024-01-01", periods=5)
    close = np.array([100.0, 101.0, 102.0, 103.0, 104.0])

    # Build one clear MACD cross at index 1.
    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(5, 200000.0),
            "ema_200": np.full(5, 95.0),
            "ema_200_slope": np.full(5, 0.1),
            "macd": np.array([-0.2, 0.1, 0.2, 0.25, 0.3]),
            "macd_signal": np.array([-0.1, 0.0, 0.1, 0.2, 0.25]),
            "macd_d1": np.array([-0.3, -0.2, 0.1, 0.2, 0.25]),
            "macd_signal_d1": np.array([-0.2, -0.1, 0.0, 0.1, 0.2]),
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    trigger_traces = [
        t
        for t in fig.data
        if getattr(t, "name", "").startswith("Trigger")
        and getattr(t, "type", "") == "bar"
    ]

    assert trigger_traces, "Expected trigger ribbon trace"
    assert any(" - " in getattr(t, "name", "") for t in trigger_traces)


def test_context_and_trigger_ribbons_use_same_line_width():
    dates = pd.date_range(start="2024-01-01", periods=5)
    close = np.array([100.0, 101.0, 102.0, 103.0, 104.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(5, 200000.0),
            "ema_200": np.full(5, 95.0),
            "ema_200_slope": np.full(5, 0.1),
            "macd": np.array([-0.2, 0.1, 0.2, 0.25, 0.3]),
            "macd_signal": np.array([-0.1, 0.0, 0.1, 0.2, 0.25]),
            "macd_d1": np.array([-0.3, -0.2, 0.1, 0.2, 0.25]),
            "macd_signal_d1": np.array([-0.2, -0.1, 0.0, 0.1, 0.2]),
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    context_trace = next(
        t
        for t in fig.data
        if getattr(t, "name", "").startswith("Context")
        and getattr(t, "type", "") == "bar"
    )
    trigger_trace = next(
        t
        for t in fig.data
        if getattr(t, "name", "").startswith("Trigger")
        and getattr(t, "type", "") == "bar"
    )
    # Both are bar traces; active bars should have the same height (lane_span).
    assert context_trace.type == "bar"
    assert trigger_trace.type == "bar"
    assert context_trace.width == trigger_trace.width


def test_aggregated_ribbon_uses_markers_for_single_bar_visibility():
    dates = pd.date_range(start="2024-01-01", periods=5)
    close = np.array([100.0, 101.0, 102.0, 103.0, 104.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(5, 200000.0),
            "ema_200": np.full(5, 95.0),
            "ema_200_slope": np.full(5, 0.1),
            "macd": np.array([-0.2, 0.1, 0.2, 0.25, 0.3]),
            "macd_signal": np.array([-0.1, 0.0, 0.1, 0.2, 0.25]),
            "macd_d1": np.array([-0.3, -0.2, 0.1, 0.2, 0.25]),
            "macd_signal_d1": np.array([-0.2, -0.1, 0.0, 0.1, 0.2]),
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    aggregated_traces = [t for t in fig.data if getattr(t, "name", "") == "Aggregated"]

    assert aggregated_traces, "Expected aggregated ribbon trace"
    assert aggregated_traces[0].type == "bar"
    assert aggregated_traces[0].width is not None


def test_aggregated_ribbon_matches_trigger_only_when_context_is_true():
    dates = pd.date_range(start="2024-01-01", periods=5)
    close = np.array([94.0, 101.0, 94.0, 103.0, 104.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(5, 200000.0),
            "ema_200": np.full(5, 95.0),
            "ema_200_slope": np.full(5, 0.1),
            "macd": np.array([-0.2, 0.1, -0.1, 0.2, 0.3]),
            "macd_signal": np.array([-0.1, 0.0, 0.0, 0.1, 0.2]),
            "macd_d1": np.array([-0.3, -0.2, -0.2, -0.1, 0.2]),
            "macd_signal_d1": np.array([-0.2, -0.1, -0.1, 0.0, 0.1]),
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    trigger_trace = next(
        t
        for t in fig.data
        if getattr(t, "name", "").startswith("Trigger")
        and getattr(t, "type", "") == "bar"
    )
    aggregated_trace = next(
        t for t in fig.data if getattr(t, "name", "") == "Aggregated"
    )

    def _y(trace_dict):
        y = trace_dict.get("y")
        if isinstance(y, dict) and "bdata" in y:
            return np.frombuffer(
                base64.b64decode(y["bdata"]), dtype=y.get("dtype", "f8")
            )
        return np.asarray(y, dtype=float)

    _fig_json = json.loads(fig.to_json())
    trigger_y = _y(
        next(t for t in _fig_json["data"] if t.get("name", "").startswith("Trigger - "))
    )
    aggregated_y = _y(
        next(t for t in _fig_json["data"] if t.get("name") == "Aggregated")
    )

    # Index 1: trigger fires, context true → both active
    # Index 2: context false → aggregated must be 0
    # Index 3: context true, trigger fires → both active
    assert trigger_y[1] > 0
    assert trigger_y[2] == 0
    assert trigger_y[3] > 0
    assert aggregated_y[1] > 0
    assert aggregated_y[2] == 0
    assert aggregated_y[3] > 0


def test_aggregate_rules_fallback_when_setup_block_missing():
    dates = pd.date_range(start="2024-01-01", periods=5)
    close = np.array([94.0, 101.0, 94.0, 103.0, 104.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(5, 200000.0),
            "ema_200": np.full(5, 95.0),
            "ema_200_slope": np.full(5, 0.1),
            "macd": np.array([-0.2, 0.1, -0.1, 0.2, 0.3]),
            "macd_signal": np.array([-0.1, 0.0, 0.0, 0.1, 0.2]),
            "macd_d1": np.array([-0.3, -0.2, -0.2, -0.1, 0.2]),
            "macd_signal_d1": np.array([-0.2, -0.1, -0.1, 0.0, 0.1]),
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END
"""

    plotter = InteractivePlotter()
    plotter.ribbon_config["aggregate"] = {
        "rules": [
            {
                "when": "IsContext and IsSetup and IsTrigger",
                "aggregate": "context and setup and trigger",
            },
            {
                "when": "IsContext and IsSetup",
                "aggregate": "context and setup",
            },
            {
                "when": "IsContext and IsTrigger",
                "aggregate": "context and trigger",
            },
        ],
        "fill_condition": "context and trigger",
    }

    fig = plotter.create_plot(df, "TEST", strategy_content=strategy_content)
    _fig_json = json.loads(fig.to_json())

    def _y(trace_dict):
        y = trace_dict.get("y")
        if isinstance(y, dict) and "bdata" in y:
            return np.frombuffer(
                base64.b64decode(y["bdata"]), dtype=y.get("dtype", "f8")
            )
        return np.asarray(y, dtype=float)

    aggregated_y = _y(
        next(t for t in _fig_json["data"] if t.get("name") == "Aggregated")
    )

    # With no setup block present, rules must fall back to context AND trigger.
    assert aggregated_y[1] > 0
    assert aggregated_y[2] == 0
    assert aggregated_y[3] > 0


def test_supertrend_overlay_is_solid_and_switches_regime_colors():
    dates = pd.date_range(start="2024-01-01", periods=8)
    close = np.array([101.0, 102.0, 103.0, 99.0, 98.0, 99.5, 101.5, 102.0])
    st = np.array([100.0, 100.5, 101.0, 101.2, 100.8, 100.2, 100.0, 100.1])
    is_green = np.array([1, 1, 1, 0, 0, 0, 1, 1], dtype=float)

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(8, 200000.0),
            "ST_Lower": np.where(is_green == 1, st, np.nan),
            "ST_Upper": np.where(is_green == 0, st, np.nan),
        }
    )

    strategy_content = """
BEGIN TRIGGER
TRIGGER: cross_down(st_10_4_is_green, 0.5)
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    st_traces = [t for t in fig.data if getattr(t, "name", "") == "Supertrend"]

    assert st_traces, "Expected Supertrend trace(s)"
    # Every segment must be a line trace.
    for tr in st_traces:
        assert getattr(tr, "mode", "") == "lines"

    # Both green (#16a34a) and red (#dc2626) segments must be present.
    line_colors = {tr.line.color for tr in st_traces}
    assert "#16a34a" in line_colors, "Expected green Supertrend segment"
    assert "#dc2626" in line_colors, "Expected red Supertrend segment"


def test_prepare_eval_columns_st_green_uses_supertrend_line():
    df = pd.DataFrame(
        {
            "close": np.array([100.0, 99.0, 101.0, 98.0]),
            "supertrend": np.array([99.0, 100.0, 100.5, 99.5]),
            # Include st_lower to ensure supertrend is preferred over lower-band fallback.
            "st_lower": np.array([97.0, 97.0, 97.0, 97.0]),
        }
    )

    out = InteractivePlotter()._prepare_eval_columns(df.copy(), "st_10_4_is_green")
    actual = out["st_10_4_is_green"].to_numpy()
    expected = np.array([1.0, 0.0, 1.0, 0.0])

    assert np.array_equal(actual, expected)


def test_supertrend_overlay_ignores_stale_green_flag_and_uses_line_relation():
    dates = pd.date_range(start="2024-01-01", periods=6)
    close = np.array([101.0, 102.0, 99.0, 98.0, 101.0, 102.0])
    st = np.array([100.0, 100.5, 100.8, 100.7, 100.4, 100.2])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(6, 100000.0),
            # Use ST_Lower/ST_Upper columns that the overlay code actually reads.
            # Rows 0-1,4-5: close > st → support. Rows 2-3: close < st → resistance.
            "ST_Lower": np.where(close > st, st, np.nan),
            "ST_Upper": np.where(close <= st, st, np.nan),
        }
    )

    strategy_content = """
BEGIN TRIGGER
TRIGGER: cross_down(st_10_4_is_green, 0.5)
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    st_traces = [t for t in fig.data if getattr(t, "name", "") == "Supertrend"]

    assert st_traces
    # Both green and red segments must be present (data has regime changes at rows 2 and 4).
    line_colors = {tr.line.color for tr in st_traces}
    assert "#16a34a" in line_colors, "Expected green Supertrend segment"
    assert "#dc2626" in line_colors, "Expected red Supertrend segment"


def test_context_ribbon_with_was_true_has_rendered_gaps():
    dates = pd.date_range(start="2024-01-01", periods=7)
    close = np.array([101.0, 102.0, 99.0, 98.0, 101.0, 99.0, 98.0])
    st = np.array([100.0, 100.2, 100.4, 100.6, 100.8, 101.0, 101.2])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(7, 100000.0),
            "st_10_4": st,
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: was_true(st_10_4_is_green, 2)
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    context_traces = [
        t
        for t in fig.data
        if getattr(t, "name", "").startswith("Context")
        and getattr(t, "type", "") == "bar"
    ]

    assert context_traces, "Expected context ribbon trace"

    # Validate the evaluated mask includes both true and false bars.
    ribbon = InteractivePlotter()._build_strategy_layer_ribbons(strategy_content)[0]
    clean = InteractivePlotter()._to_eval_condition(ribbon["condition"])
    eval_df = df.copy()
    eval_df.columns = [c.lower() for c in eval_df.columns]
    eval_df = InteractivePlotter()._prepare_eval_columns(eval_df, clean)
    mask = eval_df.eval(clean, engine="python").fillna(False).astype(bool)

    assert mask.any(), "Expected context condition to be true on some bars"
    assert (~mask).any(), "Expected context condition to be false on some bars"


def test_context_ribbon_current_green_and_was_true_renders():
    dates = pd.date_range(start="2024-01-01", periods=8)
    close = np.array([101.0, 102.0, 103.0, 99.0, 98.0, 101.0, 102.0, 97.0])
    st = np.array([100.0, 100.4, 100.8, 101.0, 100.9, 100.7, 100.6, 100.8])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(8, 100000.0),
            "st_10_4": st,
        }
    )

    strategy_content = """
BEGIN CONTEXT
FILTER: st_10_4_is_green AND was_true(st_10_4_is_green, 2)
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    context_traces = [
        t
        for t in fig.data
        if getattr(t, "name", "").startswith("Context")
        and getattr(t, "type", "") == "bar"
    ]

    assert context_traces, "Expected context ribbon trace"


def test_supertrend_overlay_hidden_when_strategy_has_no_supertrend():
    """Supertrend curves must NOT appear on the price panel when the DSL strategy
    does not reference any supertrend indicator (e.g. an EMA-only strategy)."""
    dates = pd.date_range(start="2024-01-01", periods=6)
    close = np.array([101.0, 102.0, 99.0, 98.0, 101.0, 102.0])
    st = np.array([100.0, 100.5, 100.8, 100.7, 100.4, 100.2])

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(6, 100000.0),
            "ema_200": np.full(6, 95.0),
            "ema_200_slope": np.full(6, 0.1),
            # Supertrend columns are present in the DataFrame …
            "ST_Lower": np.where(close > st, st, np.nan),
            "ST_Upper": np.where(close <= st, st, np.nan),
        }
    )

    # … but the strategy only uses EMA indicators.
    strategy_content = """
BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END
"""

    fig = InteractivePlotter().create_plot(
        df, "TEST", strategy_content=strategy_content
    )
    st_traces = [
        t
        for t in fig.data
        if getattr(t, "name", "") == "Supertrend"
    ]

    assert not st_traces, (
        "Supertrend overlay should NOT be drawn when the strategy does not reference supertrend"
    )
