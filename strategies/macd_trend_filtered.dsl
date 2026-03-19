# MACD Momentum Strategy with Trend Filter
# Entry: MACD Signal Cross Up AND Price > EMA 50
# Exit:  MACD Signal Cross Down OR Price < EMA 50

ENTRY: cross_up(macd, macd_signal) AND (close > ema_50)
EXIT:  cross_down(macd, macd_signal) OR (close < ema_50)