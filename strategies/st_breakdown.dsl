# Supertrend Breakdown - Block-Based Version
# Context: prior uptrend existed and is now vulnerable.
# Setup: price structure has started to weaken.
# Trigger: confirm the actual trend-color breakdown event.
# Invalidate: define bounce/reversal conditions.

BEGIN CONTEXT
FILTER: st_10_4_is_green
END

BEGIN SETUP
FILTER: close < ema_50
FILTER: ema_50_slope < 0
END

BEGIN TRIGGER
TRIGGER: cross_down(st_10_4_is_green, 0.5) OR (close < ema_20 AND close_d1 >= ema_20_d1)
END

BEGIN INVALIDATE
EXIT: cross_up(st_10_4_is_green, 0.5) OR close > ema_20
END

