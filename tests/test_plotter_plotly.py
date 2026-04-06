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

    # Find the context ribbon trace.
    context_traces = [
        t for t in fig.data
        if getattr(t, "name", "") == "Layer 1 Context - #2563eb"
    ]
    assert context_traces, "Expected context ribbon trace to be present"

    trace = context_traces[0]
    assert trace.connectgaps is False

    # Validate the evaluated mask itself preserves false positions.
    cond = plotter._build_strategy_layer_ribbons(strategy_content)[0]["layers"][0]["condition"]
    clean = plotter._to_eval_condition(cond)
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

    fig = InteractivePlotter().create_plot(df, "TEST", strategy_content=strategy_content)

    labels = [a for a in fig.layout.annotations if getattr(a, "text", "") == "<b>L1 Context</b>"]
    assert labels, "Expected left-side annotation for L1 Context"

    label = labels[0]
    assert label.xref == "paper"
    assert label.yref == "paper"
    assert label.xanchor == "left"
    assert label.align == "left"
    assert label.font.size == 10
    assert label.font.color == "#3b82f6"
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
    assert "Buy Signal" in trace_names


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

    fig = InteractivePlotter().create_plot(df, "TEST", strategy_content=strategy_content)

    xaxis_keys = [k for k in fig.layout if str(k).startswith("xaxis")]
    assert xaxis_keys, "Expected at least one xaxis in layout"

    bottom_label_axes = [k for k in xaxis_keys if getattr(fig.layout[k], "showticklabels", False)]
    assert len(bottom_label_axes) == 1
    bottom_axis = bottom_label_axes[0]

    for k in xaxis_keys:
        is_bottom = (k == bottom_axis)
        ticks = getattr(fig.layout[k], "ticks", None)
        showline = getattr(fig.layout[k], "showline", None)
        assert (ticks == "outside") == is_bottom
        assert bool(showline) == is_bottom
