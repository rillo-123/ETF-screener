# ==========================================
# MASTER STRATEGY TEMPLATE (.dsl)
# ==========================================
# This file defines the entry and exit conditions for a trading strategy.
#
# Available Indicators:
# - Moving Averages: ema_10, ema_20, ema_50, ema_100, ema_200
# - Momentum: rsi_14, macd, macd_signal, macd_hist
# - Volatility: Supertrend, ADX
# - Volume: volume, vol_ema_20 (supports 100K, 1.5M suffixes)
# - Oscillators: stoch_k, stoch_d
#
# Semantic Functions:
# - cross_up(A, B): A crosses above B
# - cross_down(A, B): A crosses below B
# - was_true(Cond, N): Condition was true within the last N bars
# - _slope: Change in indicator (e.g., ema_50_slope > 0)
# - _dN: Value of indicator N bars ago (e.g., close_d1 is yesterday's close)
#
# Logic: and, or, (parentheses)

ENTRY: cross_up(ema_10, ema_30) and (ema_50_slope -gt 0) and (volume -gt 50K)
EXIT:  cross_down(ema_10, ema_30) or (rsi_14 -gt 80)
