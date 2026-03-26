# Supertrend Breakdown Strategy (BASF Dip Finder 10/4)
# Detects when a long-term green trend finally breaks down into red.

TRIGGER: cross_down(st_10_4_is_green, 0.5)
FILTER:  was_true(st_10_4_is_green, 10)
EXIT:    st_10_4_is_green
