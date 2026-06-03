MAX_DAYS: 10

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN SETUP
FILTER: close > avwap_low_20
FILTER: between(close <= avwap_low_20, 1, 3)
END

BEGIN TRIGGER
TRIGGER: cross_up(close, avwap_low_20)
END

BEGIN QUALIFY
FILTER: volume > vol_ema_20
END

BEGIN EXIT
EXIT: close < avwap_low_20
EXIT: ema_200_slope <= 0
END
