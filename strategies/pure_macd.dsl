# Pure MACD - Block-Based Version
# Context: only take longs in a healthy primary uptrend.
# Setup: require MACD to be in a pullback/rebuild zone.
# Qualify: require participation quality before allowing entries.
# Trigger: enter on a fresh MACD signal-line reclaim.
# Invalidate: define states that disqualify buys and force exits.

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN SETUP
FILTER: macd < 0 OR macd_signal < 0
FILTER: macd > macd_d1
END

BEGIN QUALIFY
FILTER: volume > vol_ema_20
END

BEGIN TRIGGER
TRIGGER: cross_up(macd, macd_signal) OR (macd > macd_signal AND macd_d1 <= macd_signal_d1)
END

BEGIN INVALIDATE
EXIT: cross_down(macd, macd_signal) OR close < ema_50
END
