# Supertrend Breakdown - Four Layer Version (block-based)
# Layer 1 (Context): Prior uptrend existed and is now vulnerable.
# Layer 2 (Setup): Price structure has started to weaken.
# Layer 3 (Trigger): Confirm the actual trend-color breakdown event.
# Layer 4 (Risk/Quality): Favor decisive moves and define invalidation.

BEGIN CONTEXT_REGIME
FILTER: was_true(st_10_4_is_green, 10)
END

BEGIN SETUP_BREAKDOWN
FILTER: close < ema_50
FILTER: ema_50_slope < 0
END

BEGIN TRIGGER_BREAKDOWN
TRIGGER: cross_down(st_10_4_is_green, 0.5) OR (close < ema_20 AND close_d1 >= ema_20_d1)
END

BEGIN RISK_QUALITY
FILTER: adx > 18
EXIT: st_10_4_is_green == 1 OR close > ema_20
END
