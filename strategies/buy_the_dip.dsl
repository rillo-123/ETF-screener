# Buy the Dip - Four Layer Version (descriptive block identifiers)
# Layer 1 (Context): Prefer ETFs in a persistent bullish regime.
# Layer 2 (Setup): Require a pullback that still respects the higher trend.
# Layer 3 (Trigger): Demand a fresh reclaim signal to open.
# Layer 4 (Risk/Quality): Require healthy participation and define invalidation.

BEGIN CONTEXT_REGIME
FILTER: close > ema_200
FILTER: ema_200_slope > 0
FILTER: was_true(close > ema_200, 20)
END

BEGIN SETUP_PULLBACK
FILTER: close > ema_50
FILTER: close <= ema_20 OR close_d1 <= ema_20_d1
FILTER: was_true(close > ema_20, 5)
END

BEGIN TRIGGER_RECLAIM
TRIGGER: (close > ema_20 AND close_d1 <= ema_20_d1) OR cross_up(st_10_4_is_green, 0.5)
END

BEGIN RISK_GUARD
FILTER: volume > vol_ema_20
FILTER: adx > 18
EXIT: close < ema_50 OR st_10_4_is_green == 0
END
