# EMA Breakout Fan-Out
# Idea:
# - Trade when price breaks above the 30 EMA.
# - Only allow the setup when the 30/50/100/200 EMAs are stacked bullishly.
# - Require the gaps between the EMAs to be widening, so the averages are fanning out.

MAX_DAYS: 20

BEGIN CONTEXT
FILTER: ema_20 < ema_30
FILTER: ema_30 > ema_50
FILTER: ema_50 > ema_100
FILTER: ema_100 > ema_200
FILTER: ema_200_slope > 0
END

BEGIN TRIGGER
TRIGGER:  between(close <= ema_50, 5, now)
END


