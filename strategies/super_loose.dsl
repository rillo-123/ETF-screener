# Super Loose - Four Layer Version (block-based)
# Layer 1 (Context): Keep a minimal positive drift bias.
# Layer 2 (Setup): Price must hold around short trend support.
# Layer 3 (Trigger): Enter on immediate day-over-day strength.
# Layer 4 (Risk/Quality): Require baseline participation and quick invalidation.

BEGIN CONTEXT_DRIFT
FILTER: ema_5_slope > 0
END

BEGIN SETUP_HOLD
FILTER: close >= ema_5 OR close_d1 >= ema_5_d1
END

BEGIN TRIGGER_STRENGTH
TRIGGER: close > close_d1
END

BEGIN RISK_BASELINE
FILTER: volume > 100K
EXIT: close < ema_5 OR close < close_d1
END
