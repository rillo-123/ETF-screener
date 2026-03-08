# Trend Intensity Strategy
# Entry: Price above EMA 50 and EMA 50 is rising
# Exit:  Price falls below EMA 50 or RSI is overbought

ENTRY: (close -gt ema_50) and (ema_50_slope -gt 0)
EXIT:  (close -lt ema_50) or (rsi_14 -gt 75)
