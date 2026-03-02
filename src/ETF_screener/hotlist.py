"""Generate swing trading hotlists from screened ETFs."""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.screener import ETFScreener


def generate_hotlist(
    min_avg_volume: int = 10_000_000,
    days: int = 10,
    output_dir: str = "logs",
    min_pullback: float = 2.0,
    max_distance_from_ema: float = 5.0,
    st_period: int = 10,
    st_multiplier: float = 3.0,
    timeframe: str = "1D",
) -> None:
    """
    Generate hotlist of swing trading prospects with green supertrend.

    Creates a timestamped report of ETFs with bullish technical setups:
    - Green supertrend (price > supertrend)
    - Swing-ready pullback (dipped towards EMA50 but in uptrend)
    - Sufficient volume

    Args:
        min_avg_volume: Minimum average volume threshold
        days: Number of days to analyze
        output_dir: Directory to save hotlist report
        min_pullback: Minimum pullback % from recent high
        max_distance_from_ema: Maximum distance % from EMA50
        st_period: Supertrend ATR period
        st_multiplier: Supertrend multiplier
        timeframe: Timeframe for indicators ("1D" or "1W")
    """
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hotlist_file = Path(output_dir) / f"hotlist_{timestamp}.txt"
        
        print(f"[HOTLIST] Generating swing trading prospects...")
        print(f"[HOTLIST] Criteria: Green Supertrend + Volume >= {min_avg_volume:,}\n")
        
        # Screen for volume and green supertrend
        db = ETFDatabase()
        screener = ETFScreener(db=db)
        
        # Get high-volume ETFs
        volume_results = screener.screen_by_volume(
            min_days=days,
            min_avg_volume=min_avg_volume,
            max_results=None,
            fetch_missing=False,
        )
        
        if volume_results.empty:
            print(f"[HOTLIST] No ETFs found with volume >= {min_avg_volume:,}")
            with open(hotlist_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"SWING TRADING HOTLIST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"No ETFs found with volume >= {min_avg_volume:,}\n")
            return
        
        print(f"[HOTLIST] Found {len(volume_results)} ETFs with sufficient volume")
        
        # Filter for swing setups with green supertrend
        swing_results = screener.filter_swing_setups(
            results=volume_results,
            db=db,
            min_pullback=min_pullback,
            max_distance_from_ema=max_distance_from_ema,
            require_green_supertrend=True,
            st_period=st_period,
            st_multiplier=st_multiplier,
            timeframe=timeframe,
        )
        
        # Generate report
        with open(hotlist_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"SWING TRADING HOTLIST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Criteria:\n")
            f.write(f"  • Green Supertrend (price > ST)\n")
            f.write(f"  • Swing-ready pullback (min dip: {min_pullback}%)\n")
            f.write(f"  • Distance from EMA50: <= {max_distance_from_ema}%\n")
            f.write(f"  • Minimum avg volume: {min_avg_volume:,}\n")
            f.write(f"  • Timeframe: {timeframe}\n")
            f.write(f"  • Analysis period: last {days} days\n\n")
            
            if swing_results.empty:
                f.write("No opportunities found matching criteria.\n")
                print(f"[HOTLIST] No opportunities found (0 prospects)")
            else:
                f.write(f"Found {len(swing_results)} opportunities:\n\n")
                f.write("-" * 80 + "\n")
                
                # Sort by pullback (biggest pullback first = best setup)
                if "Pullback%" in swing_results.columns:
                    swing_results = swing_results.sort_values("Pullback%", ascending=False)
                
                for idx, (_, row) in enumerate(swing_results.iterrows(), 1):
                    ticker = row.get("Ticker", row.get("Symbol", "N/A"))
                    price = row.get("Close", row.get("Price", "N/A"))
                    ema50 = row.get("EMA_50", row.get("EMA50", "N/A"))
                    pullback = row.get("Pullback%", "N/A")
                    volume = row.get("Avg Volume", row.get("AvgVolume", "N/A"))
                    
                    f.write(f"\n{idx}. {ticker}\n")
                    f.write(f"   Price:         {price}\n")
                    f.write(f"   EMA50:         {ema50}\n")
                    if pullback != "N/A":
                        try:
                            f.write(f"   Pullback:      {float(pullback):.2f}%\n")
                        except (ValueError, TypeError):
                            f.write(f"   Pullback:      {pullback}%\n")
                    if volume != "N/A":
                        try:
                            f.write(f"   Avg Volume:    {int(volume):,}\n" if isinstance(volume, (int, float)) else f"   Avg Volume:    {volume}\n")
                        except (ValueError, TypeError):
                            f.write(f"   Avg Volume:    {volume}\n")
                
                f.write("\n" + "-" * 80 + "\n")
                print(f"[HOTLIST] Found {len(swing_results)} swing trading opportunities")
            
            f.write(f"\nReport saved: {hotlist_file}\n")
        
        print(f"[OK] Hotlist saved to: {hotlist_file}\n")
        
        # Also print summary to console
        if not swing_results.empty:
            print("[HOTLIST] Top 5 prospects:")
            for idx, (_, row) in enumerate(swing_results.head(5).iterrows(), 1):
                ticker = row.get("Ticker", row.get("Symbol", "N/A"))
                price = row.get("Close", row.get("Price", "N/A"))
                try:
                    price_str = f"{float(price):.2f}" if price != "N/A" else "N/A"
                except (ValueError, TypeError):
                    price_str = str(price)
                print(f"  {idx}. {ticker:12} @ {price_str}")
        
        db.close()
        
    except Exception as e:
        print(f"[ERROR] Hotlist generation failed: {str(e)}", file=sys.stderr)
        sys.exit(1)
