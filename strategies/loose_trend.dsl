# Loose Trend - Block-Based Version
# Context: stay in established uptrends.
# Setup: require pullback-to-trend structure to still be intact.
# Trigger: enter on fresh momentum reclaim.
# Qualify: keep only liquid continuation.
# Invalidate: define invalidation states.

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_50 > ema_200
END

BEGIN SETUP
FILTER: close > ema_50
FILTER: ema_20 > ema_50
END

BEGIN TRIGGER
TRIGGER: close > ema_20 AND close_d1 <= ema_20_d1
END

BEGIN QUALIFY
FILTER: volume > vol_ema_20
END

BEGIN INVALIDATE
EXIT: close < ema_50 OR (close < ema_20 AND close_d1 >= ema_20_d1)
END
