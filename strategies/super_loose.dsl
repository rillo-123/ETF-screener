# Ultimate Loose Strategy
# Specifically designed for the existing 20-35 day data samples.
# This strategy uses very short windows to ensure indicators can actually calculate.

TRIGGER: close > close_d1
FILTER:  close > ema_5
EXIT:    close < ema_5
