# Supertrend Pullback EMA50 Slope Turnup
# Idea:
# - Keep the long-term trend positive with EMA200 slope > 0.
# - Require Supertrend 10,4 to have crossed down through EMA50 in the last few bars.
# - Trigger when EMA50 slope flips from non-positive to positive.
# - Exit if Supertrend recaptures EMA50 or EMA200 slope turns non-positive.

MAX_DAYS: 12

BEGIN CONTEXT
FILTER: ema_200_slope > 0
END

BEGIN SETUP
FILTER: (st_10_4 < ema_50 and st_10_4_d1 >= ema_50_d1) or (st_10_4_d1 < ema_50_d1 and st_10_4_d2 >= ema_50_d2) or (st_10_4_d2 < ema_50_d2 and st_10_4_d3 >= ema_50_d3) or (st_10_4_d3 < ema_50_d3 and st_10_4_d4 >= ema_50_d4) or (st_10_4_d4 < ema_50_d4 and st_10_4_d5 >= ema_50_d5) or (st_10_4_d5 < ema_50_d5 and st_10_4_d6 >= ema_50_d6)
END

BEGIN TRIGGER
TRIGGER: ema_50_slope_cross_up
END

BEGIN EXIT
EXIT: cross_up(st_10_4, ema_50)
EXIT: ema_200_slope <= 0
END

