# Supertrend Red-to-Green EMA50 Crossup
# Idea:
# - Treat Supertrend above EMA50 as red and below EMA50 as green.
# - Allow a few bars for Supertrend to spend time below EMA50 before entry.
# - Trigger when Supertrend crosses up through EMA50.
# - Keep the long-term trend positive with EMA200 slope > 0.

MAX_DAYS: 15

BEGIN CONTEXT
FILTER: ema_200_slope > 0
END

BEGIN SETUP
FILTER: (st_10_4 < ema_50) or (st_10_4_d1 < ema_50_d1) or (st_10_4_d2 < ema_50_d2) or (st_10_4_d3 < ema_50_d3) or (st_10_4_d4 < ema_50_d4)
END

BEGIN TRIGGER
TRIGGER: cross_up(st_10_4, ema_50)
END

BEGIN EXIT
EXIT: cross_down(st_10_4, ema_50)
EXIT: ema_200_slope <= 0
END

