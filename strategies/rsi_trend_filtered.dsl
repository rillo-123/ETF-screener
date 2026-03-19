# RSI with EMA 50 filter to avoid catching falling knives
# Entry: RSI oversold AND price is above EMA 50 (bullish trend)
# Exit:  RSI overbought OR price drops below EMA 50

ENTRY:  (rsi_14 < 30) AND (close > ema_50)

EXIT:   (rsi_14 > 70) OR (close < ema_50)
