# EMA Breakout Fan-Out
# Idea:
# - Trade when price breaks above the 30 EMA.
# - Only allow the setup when the 30/50/100/200 EMAs are stacked bullishly.
# - Require the gaps between the EMAs to be widening, so the averages are fanning out.

MAX_DAYS: 20

BEGIN CONTEXT
FILTER: close > ema_200
FILTER: ema_30 > ema_50
FILTER: ema_50 > ema_100
FILTER: ema_100 > ema_200
FILTER: ema_100_slope > 0
FILTER: ema_200_slope > 0
FILTER: (ema_30 - ema_50) > (ema_30_d1 - ema_50_d1)
FILTER: (ema_50 - ema_100) > (ema_50_d1 - ema_100_d1)
FILTER: (ema_100 - ema_200) > (ema_100_d1 - ema_200_d1)
END

BEGIN TRIGGER
TRIGGER:  between(ema_20 <= ema_30, 3, now)
END

BEGIN EXIT
EXIT:  cross_down(ema_20, ema_100)
END

