# Pure MACD Rebuild - Four Layer Version (block-based)
# Layer 1 (Context): Keep trades aligned with broader trend regime.
# Layer 2 (Setup): Require momentum compression before expansion.
# Layer 3 (Trigger): Enter on fresh MACD signal-line cross up.
# Layer 4 (Risk/Quality): Require tradable participation and define invalidation.

BEGIN CONTEXT_REGIME
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN SETUP_COMPRESSION
FILTER: macd_hist_d1 <= 0
FILTER: macd > -0.5
FILTER: close > ema_50
END

BEGIN TRIGGER_MACD_CROSS
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END

BEGIN RISK_PARTICIPATION
FILTER: volume > vol_ema_20
FILTER: volume > 150K
EXIT: (macd < macd_signal AND macd_d1 >= macd_signal_d1) OR close < ema_50
END
