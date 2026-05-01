# Supertrend Continuation - Block-Based Version
# Context: only trade when price is already in a long-term uptrend.
# Trigger: focus on the Supertrend color flip back to green.
# Invalidate: exit when the Supertrend flips back to red or broader trend support breaks.

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
FILTER: was_true(st_10_4_is_green,1)
END

BEGIN TRIGGER
TRIGGER: st_10_4_is_red
END

BEGIN INVALIDATE
EXIT: close < ema_50
END
