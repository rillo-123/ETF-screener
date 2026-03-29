# Buy the Dip (Supertrend)
# A loose strategy designed to find entries during a trend.
# TRIGGER: The moment Supertrend flips from Red to Green.
# FILTER:  Price should already be above a 50 EMA.

TRIGGER: cross_up(st_10_4_is_green, 0.5)
FILTER:  close > ema_50
EXIT:    st_10_4_is_green == 0
