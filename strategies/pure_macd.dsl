# Pure MACD - Simplified Two Layer Version
# Layer 1 (Context): Keep trades aligned with broader trend regime.
# Layer 2 (Trigger): Enter on fresh MACD signal-line cross up.

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER: macd > macd_signal AND macd_d1 < macd_signal_d1
END
