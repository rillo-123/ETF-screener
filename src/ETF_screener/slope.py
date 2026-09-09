"""Scale-independent change in percent per observation interval."""

import math


def normalized_slope(current: float, previous: float, window: int) -> float:
    """Return 100 * (current / previous - 1) / window, or NaN if undefined.

    The caller supplies observations exactly ``window`` candles apart. This is
    arithmetic relative change per candle, not a compounded or regression rate.
    """
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError("Slope window must be a positive integer")
    if not math.isfinite(current) or not math.isfinite(previous) or previous == 0:
        return math.nan
    result = 100.0 * (current / previous - 1.0) / window
    return result if math.isfinite(result) else math.nan
