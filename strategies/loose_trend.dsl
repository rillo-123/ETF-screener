# Loose Trend-Following Strategy
# Designed to capture basic bullish momentum.
# Very likely to return multiple hits in a neutral/bullish market.

TRIGGER: close > ema_20
FILTER:  ema_20 > ema_50
EXIT:    close < ema_50
