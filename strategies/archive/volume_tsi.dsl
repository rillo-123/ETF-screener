# Volume and TSI crossover strategy with EMA filter
# 1. TSI crosses up over its signal line
# 2. Volume > 1000
# 3. Price must be above EMA 50 for trend confirmation
# 4. TSI must currently be above signal (active momentum)

ENTRY: cross_up(tsi, tsi_signal) and volume > 1000 and close > ema_50 and tsi > tsi_signal
EXIT: cross_down(tsi, tsi_signal) or close < ema_50