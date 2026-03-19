# MACD Strategy with EMA Slope Trend Filter - Stay on if EMA 50 Slope is Positive
# Entry: MACD Signal Cross Up
# Exit:  (MACD Signal Cross Down AND EMA 50 Slope <= 0) OR (EMA 50 Slope <= 0)

ENTRY: cross_up(macd, macd_signal) 
EXIT:  cross_down(macd, macd_signal) OR (ema_50_slope <= 0)