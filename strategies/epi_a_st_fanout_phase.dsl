# EPI-A.ST Fan-Out Phase
# This is a phase strategy, not a tight breakout entry.
# It highlights the point where the EMA ribbon starts to spread and the 100/200
# relationship has recently turned favorable.

MAX_DAYS: 15

BEGIN CONTEXT
FILTER: close > ema_30
FILTER: ema_30 > ema_50
FILTER: ema_50 > ema_100
FILTER: ema_100 > ema_200
FILTER: ema_30_slope > 0
FILTER: ema_50_slope > 0
FILTER: ema_100_slope > 0
FILTER: ema_200_slope > 0
FILTER: (ema_30 - ema_50) > (ema_30_d1 - ema_50_d1)
FILTER: (ema_50 - ema_100) > (ema_50_d1 - ema_100_d1)
FILTER: (ema_100 - ema_200) > (ema_100_d1 - ema_200_d1)
END

BEGIN TRIGGER
TRIGGER: was_true(ema_100 <= ema_200, 5)
END

BEGIN INVALIDATE
EXIT: ema_30 < ema_50
EXIT: ema_50 < ema_100
EXIT: ema_100 < ema_200
END
