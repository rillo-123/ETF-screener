# RSI Risk-Mitigated - Four Layer Version (block-based)
# Layer 1 (Context): Only trade in broader uptrends.
# Layer 2 (Setup): Mild pullback condition inside that trend.
# Layer 3 (Trigger): RSI momentum reclaim without requiring extreme oversold.
# Layer 4 (Risk/Quality): Require liquidity and define fast invalidation.

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

BEGIN RISK
FILTER: volume > 75K
EXIT: rsi_14 > 70 OR close < ema_200 OR cross_down(rsi_14, 45)
END
