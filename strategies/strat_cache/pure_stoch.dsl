# Pure Stochastic Strategy
# Entry: %K crosses above %D AND %K is below 20 (oversold)
# Exit:  %K crosses below %D OR %K is above 80 (overbought)

# ENTRY when %K crosses above %D while in oversold territory
ENTRY:  (stoch_k < 20) AND (cross_up(stoch_k, stoch_d))

# EXIT when %K crosses below %D or enters overbought territory
EXIT:  (stoch_k > 80) OR (cross_down(stoch_k, stoch_d))