# Hardened MACD with Strict Zombie Disqualification

TRIGGER: cross_up(macd, macd_signal)
FILTER: volume > 1000 and close > ema_50 and macd > macd_signal and vol_ema_20 > 5000
EXIT: cross_down(macd, macd_signal) or close < ema_50
