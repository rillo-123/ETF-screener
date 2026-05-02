# Supertrend Continuation - Block-Based Version
# Context: only trade when price is already in a long-term uptrend.
# Trigger: focus on the Supertrend color flip back to green.
# Invalidate: exit when the Supertrend flips back to red or broader trend support breaks.

BEGIN CONTEXT

FILTER: ema_100_slope > 0
FILTER: was_true(st_10_4_is_red,1)
END

BEGIN TRIGGER
TRIGGER: cross_up(close,ema_50)
END

BEGIN INVALIDATE
EXIT: st_10_4_is_green
END
