# Swing-oriented AVWAP pullback strategy.
# Uses the repo's rolling swing-low anchored VWAP implementation.

MAX_DAYS: 10

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_20 > ema_50
FILTER: ema_50_slope > 0
FILTER: close > avwap_low_20
END

BEGIN SETUP
FILTER: between(close <= avwap_low_20, 1, 3)
FILTER: between(close <= ema_20, 1, 3)
END

BEGIN TRIGGER
TRIGGER: close > open
TRIGGER: close > high_d1
END

BEGIN QUALIFY
FILTER: volume > vol_ema_20
END

BEGIN EXIT
EXIT: close < avwap_low_20
EXIT: close < ema_20
END
