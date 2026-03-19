# MACD Momentum Strategy
# Entry: MACD Signal Cross Up
# Exit:  MACD Signal Cross Down or RSI Overbought

ENTRY: cross_up(macd, macd_signal)
EXIT:  cross_down(macd, macd_signal) or (rsi_14 -gt 80)
