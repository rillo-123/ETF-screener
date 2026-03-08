# Trend Intensity Strategy
# Entry: Price above EMA 50 and EMA 50 is rising
# Exit:  Price falls below EMA 50 or RSI is overbought

# ENTRY when 14-period RSI crosses UP its 10-period EMA
ENTRY: cross_up(rsi_14, rsi_ema_14_10) and (rsi_14 < 30)

# EXIT when RSI crosses BELOW its signal line
EXIT: cross_down(rsi_14, rsi_ema_14_10) and (rsi_14 > 70)
