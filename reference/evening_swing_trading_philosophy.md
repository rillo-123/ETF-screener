# Evening Swing Trading Philosophy

## Objective

Build a **boring, repeatable system** that removes emotion from trading.
The goal is not to predict markets perfectly but to make consistent
decisions based on predefined rules.

------------------------------------------------------------------------

# Why Evening Swing Trading?

For someone working normal office hours in Sweden:

-   U.S. markets are open during the evening.
-   There is enough time after work to review candidates calmly.
-   There is no need to watch the market all day.
-   Positions are held for days or weeks instead of minutes.

This avoids competing with intraday traders and allows trading to fit
around a full-time job.

------------------------------------------------------------------------

# Core Philosophy

The computer should perform the repetitive work.

The human should make as few subjective decisions as possible.

Every new discretionary decision introduces emotional bias.

------------------------------------------------------------------------

# Scanner First

Instead of browsing thousands of stocks manually:

1.  Scan the universe.
2.  Filter aggressively.
3.  Produce a short candidate list.
4.  Review only those candidates.

The objective is to reduce thousands of stocks to perhaps 10--20
high-quality opportunities.

------------------------------------------------------------------------

# Typical Filters

Examples:

-   Price \> minimum threshold
-   Average volume \> minimum threshold
-   Close above 200-day moving average
-   50-day MA above 200-day MA
-   RSI within acceptable range
-   ATR within acceptable range
-   Near recent highs
-   Trend intact

These filters already exist in the current implementation.

Avoid continuously adding more.

------------------------------------------------------------------------

# Less Complexity, More Discipline

The scanner already works.

The priority is **not more features**.

The priority is making it harder to break the rules.

The production strategy should change rarely.

------------------------------------------------------------------------

# Output Should Be Simple

For each candidate:

-   Ticker
-   Setup name
-   Entry
-   Stop
-   Position size
-   Risk
-   Pass/Fail reason

Nothing more.

------------------------------------------------------------------------

# Trading Rules

If a stock is not on today's scanner output:

**Do not trade it.**

If a setup cannot be described in one sentence:

**Skip it.**

If the planned stop is unacceptable:

**Skip it.**

If the entry is missed:

**Do not chase.**

------------------------------------------------------------------------

# Risk Management

Determine risk before entering.

Calculate:

-   Entry price
-   Stop-loss
-   Risk per share
-   Position size based on fixed account risk

Place the stop immediately after entering.

The objective is to eliminate emotional decision making after entry.

------------------------------------------------------------------------

# Earnings

Avoid opening new swing positions immediately before scheduled earnings
unless the strategy specifically targets earnings events.

------------------------------------------------------------------------

# High Frequency Trading

Do not compete with HFT.

HFT firms operate on microseconds.

Swing traders operate on days or weeks.

Speed is not the edge.

Discipline is the edge.

------------------------------------------------------------------------

# Automation Goal

Eventually the workflow should be:

1.  Download data.
2.  Run scanner.
3.  Produce ranked candidates.
4.  Review briefly.
5.  Execute according to rules.
6.  Walk away.

------------------------------------------------------------------------

# Guiding Principle

The system should become progressively more boring.

Boring systems are easier to trust.

Trusted systems reduce emotional trading.

The objective is consistency rather than excitement.
