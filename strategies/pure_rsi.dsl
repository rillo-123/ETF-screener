# Trend Intensity Strategy
# Entry: Price above EMA 50 and EMA 50 is rising
# Exit:  Price falls below EMA 50 or RSI is overbought

# ENTRY when 14-period RSI crosses UP its 10-period EMA
ENTRY:  (rsi_14 < 30)

# EXIT when RSI crosses BELOW its signal line
EXIT:  (rsi_14 > 70)
