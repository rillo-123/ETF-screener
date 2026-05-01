# Mixed Test Strat

BEGIN CONTEXT
FILTER: ema_200_slope >= 0  # allow flat or uptrend
END

BEGIN SETUP
FILTER: close <= ema_20  # allow equal to ema_20
END

BEGIN TRIGGER
TRIGGER: cross_down(st_10_4_is_green, 1.0)  # require a bigger move for trigger
END

BEGIN INVALIDATE
EXIT: close < ema_30
END

