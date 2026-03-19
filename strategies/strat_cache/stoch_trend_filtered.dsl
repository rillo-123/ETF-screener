# Stochastic with Trend Confirmation (EMA 50)
# Entry: Stochastic K crosses up D AND price is above EMA 50 (bullish filter)
# Exit:  Stochastic crosses down OR price drops below EMA 50

ENTRY:  (cross_up(stoch_k, stoch_d)) AND (close > ema_50)

# We exit early if the trend breaks OR if the stochastic overextends
EXIT:   (cross_down(stoch_k, stoch_d)) OR (close < ema_50)
