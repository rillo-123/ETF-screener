# Super Loose - Block-Based Version
# Context: keep a minimal positive drift bias.
# Setup: price must hold around short trend support.
# Trigger: enter on immediate day-over-day strength.
# Qualify: require baseline participation.
# Invalidate: define quick invalidation.

BEGIN CONTEXT
FILTER: ema_5_slope > 0
END

BEGIN SETUP
FILTER: close >= ema_5 OR close_d1 >= ema_5_d1
END

BEGIN TRIGGER
TRIGGER: close > close_d1
END

BEGIN QUALIFY
FILTER: volume > 100K
END

BEGIN INVALIDATE
EXIT: close < ema_5 OR close < close_d1
END
