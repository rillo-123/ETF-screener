# Supertrend Continuation - Block-Based Version
# Context: only trade when price is already in a long-term uptrend.
# Trigger: focus on the Supertrend color flip back to green.
# Invalidate: exit when the Supertrend flips back to red or broader trend support breaks.

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: cross_up(st_10_4_is_green, 0.5) OR cross_up(close, st_10_4)
END

BEGIN INVALIDATE
EXIT: cross_down(st_10_4_is_green, 0.5) OR close < ema_50
END
