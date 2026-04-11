# RSI Risk-Mitigated - Block-Based Version
# Context: only trade in broader uptrends.
# Setup: mild pullback condition inside that trend.
# Trigger: RSI momentum reclaim without requiring extreme oversold.
# Qualify: require liquidity.
# Invalidate: define fast invalidation.

BEGIN CONTEXT
FILTER: close > ema_200
END

BEGIN SETUP
FILTER: rsi_14 < 50
FILTER: close >= ema_200
END

BEGIN TRIGGER
TRIGGER: cross_up(rsi_14, 40) OR (rsi_14 > 45 AND rsi_14_d1 <= 45)
END

BEGIN QUALIFY
FILTER: volume > 75K
END

BEGIN INVALIDATE
EXIT: rsi_14 > 70 OR close < ema_200 OR cross_down(rsi_14, 45)
END
