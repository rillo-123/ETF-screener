# Buy the Dip - Block-Based Version
# Context: prefer ETFs in a persistent bullish regime.
# Setup: require a pullback that still respects the higher trend.
# Trigger: demand a fresh reclaim signal to open.
# Qualify: require healthy participation.
# Invalidate: define break conditions that disqualify buys and close positions.

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
FILTER: was_true(close > ema_200, 20)
END

BEGIN SETUP
FILTER: close > ema_50
FILTER: close <= ema_20 OR close_d1 <= ema_20_d1
FILTER: was_true(close > ema_20, 5)
END

BEGIN TRIGGER
TRIGGER: (close > ema_20 AND close_d1 <= ema_20_d1) OR cross_up(st_10_4_is_green, 0.5)
END

BEGIN QUALIFY
FILTER: volume > vol_ema_20
END

BEGIN INVALIDATE
EXIT: close < ema_50 OR cross_down(st_10_4_is_green, 0.5)
END

