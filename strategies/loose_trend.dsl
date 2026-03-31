# Loose Trend - Four Layer Version (block-based)
# Layer 1 (Context): Stay in established uptrends.
# Layer 2 (Setup): Require pullback-to-trend structure to still be intact.
# Layer 3 (Trigger): Enter on fresh momentum reclaim.
# Layer 4 (Risk/Quality): Keep only liquid continuation and define invalidation.

BEGIN CONTEXT_UPTREND
FILTER: close > ema_200
FILTER: ema_50 > ema_200
END

BEGIN SETUP_PULLBACK
FILTER: close > ema_50
FILTER: ema_20 > ema_50
END

BEGIN TRIGGER_MOMENTUM_RECLAIM
TRIGGER: close > ema_20 AND close_d1 <= ema_20_d1
END

BEGIN RISK_LIQUIDITY
FILTER: volume > vol_ema_20
EXIT: close < ema_50 OR (close < ema_20 AND close_d1 >= ema_20_d1)
END
