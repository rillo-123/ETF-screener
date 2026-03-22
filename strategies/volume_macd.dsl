# Hardened MACD with Strict Zombie Disqualification
# 1. MACD Golden Cross: MACD line crosses up over Signal line
# 2. Volume Check: Volume > 1000
# 3. Trend Confirmation: Price is above the EMA 50
# 4. Momentum Stability: MACD must currently be above the Signal line
# 5. Liquidity Check: Volume EMA 20 > 5000 (Weeds out low-liquidity/stale tickers)

ENTRY: cross_up(macd, macd_signal) and volume > 1000 and close > ema_50 and macd > macd_signal and vol_ema_20 > 5000
EXIT: cross_down(macd, macd_signal) or close < ema_50
