"""
Python API for ETF Screener - chainable, fluent interface.

Example usage:
    screener = Screener(min_volume=10000)
    results = (screener
        .filter_supertrend('green', timeframe='1W', multiplier=1.0)
        .filter_close(gte=50, lte=100)
        .filter_ema(lt=90)
        .execute())
    
    print(results)  # DataFrame with matching ETFs
"""

from typing import Optional, List, Dict, Tuple
import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.screener import ETFScreener
from ETF_screener.indicators import add_indicators, calculate_consecutive_streak
from ETF_screener.yfinance_fetcher import YFinanceFetcher


class Screener:
    """Chainable API for ETF screening and filtering."""
    
    # Operator constants
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NE = "ne"
    
    def __init__(
        self,
        min_volume: int = 10_000_000,
        days: int = 10,
        data_dir: str = "data",
        db: Optional[ETFDatabase] = None,
    ):
        """
        Initialize screener.
        
        Args:
            min_volume: Minimum average volume threshold (default 10M)
            days: Number of days to analyze (default 10)
            data_dir: Directory containing etfs.json (default "data")
            db: Database instance (created if not provided)
        """
        self.min_volume = min_volume
        self.days = days
        self.data_dir = data_dir
        self.db = db or ETFDatabase()
        self.screener = ETFScreener(db=self.db)
        
        # Store filter specifications
        self._filters = {
            'supertrend': None,
            'swing': None,
            'conditions': {},
            'red_streak': 0,
        }
        
    def filter_supertrend(
        self,
        color: str,
        timeframe: str = "1D",
        period: int = 10,
        multiplier: float = 3.0,
    ) -> "Screener":
        """
        Filter by Supertrend color (uptrend/downtrend).
        
        Args:
            color: 'green' (price > supertrend) or 'red' (price < supertrend)
            timeframe: '1D' (daily) or '1W' (weekly)
            period: ATR period for Supertrend (default 10)
            multiplier: Band multiplier (default 3.0)
            
        Returns:
            self for chaining
        """
        if color not in ('green', 'red'):
            raise ValueError("color must be 'green' or 'red'")
        if timeframe not in ('1D', '1W'):
            raise ValueError("timeframe must be '1D' or '1W'")
            
        self._filters['supertrend'] = {
            'color': color,
            'timeframe': timeframe,
            'period': period,
            'multiplier': multiplier,
        }
        return self
    
    def filter_close(self, gt: Optional[float] = None, gte: Optional[float] = None,
                     lt: Optional[float] = None, lte: Optional[float] = None,
                     eq: Optional[float] = None, ne: Optional[float] = None) -> "Screener":
        """
        Filter by close price.
        
        Args:
            gt: Close price > value
            gte: Close price >= value
            lt: Close price < value
            lte: Close price <= value
            eq: Close price == value
            ne: Close price != value
            
        Returns:
            self for chaining
        """
        return self._add_condition('close', gt=gt, gte=gte, lt=lt, lte=lte, eq=eq, ne=ne)
    
    def filter_ema(self, gt: Optional[float] = None, gte: Optional[float] = None,
                   lt: Optional[float] = None, lte: Optional[float] = None,
                   eq: Optional[float] = None, ne: Optional[float] = None) -> "Screener":
        """
        Filter by EMA50.
        
        Args:
            gt: EMA > value
            gte: EMA >= value
            lt: EMA < value
            lte: EMA <= value
            eq: EMA == value
            ne: EMA != value
            
        Returns:
            self for chaining
        """
        return self._add_condition('ema', gt=gt, gte=gte, lt=lt, lte=lte, eq=eq, ne=ne)
    
    def filter_pullback(self, gt: Optional[float] = None, gte: Optional[float] = None,
                        lt: Optional[float] = None, lte: Optional[float] = None,
                        eq: Optional[float] = None, ne: Optional[float] = None) -> "Screener":
        """
        Filter by pullback % from recent high.
        
        Args:
            gt: Pullback > value %
            gte: Pullback >= value %
            lt: Pullback < value %
            lte: Pullback <= value %
            eq: Pullback == value %
            ne: Pullback != value %
            
        Returns:
            self for chaining
        """
        return self._add_condition('pullback', gt=gt, gte=gte, lt=lt, lte=lte, eq=eq, ne=ne)
    
    def filter_volume(self, gt: Optional[float] = None, gte: Optional[float] = None,
                      lt: Optional[float] = None, lte: Optional[float] = None,
                      eq: Optional[float] = None, ne: Optional[float] = None) -> "Screener":
        """
        Filter by average volume.
        
        Args:
            gt: Volume > value
            gte: Volume >= value
            lt: Volume < value
            lte: Volume <= value
            eq: Volume == value
            ne: Volume != value
            
        Returns:
            self for chaining
        """
        return self._add_condition('volume', gt=gt, gte=gte, lt=lt, lte=lte, eq=eq, ne=ne)
    
    def filter_red_streak(self, min_days: int) -> "Screener":
        """
        Filter for ETFs in RED (downtrend) for minimum consecutive days.
        
        Used with filter_supertrend('red') for reversal candidates.
        
        Args:
            min_days: Minimum consecutive RED days (e.g., 10 for strong downtrend)
            
        Returns:
            self for chaining
        """
        self._filters['red_streak'] = min_days
        return self
    
    def filter_swing(self, min_pullback: float = 2.0, max_ema_distance: float = 5.0) -> "Screener":
        """
        Filter for swing-ready setups (price dipped to EMA50 in uptrend).
        
        Args:
            min_pullback: Minimum pullback % from recent high (default 2.0)
            max_ema_distance: Maximum distance % from EMA50 (default 5.0)
            
        Returns:
            self for chaining
        """
        self._filters['swing'] = {
            'min_pullback': min_pullback,
            'max_ema_distance': max_ema_distance,
        }
        return self
    
    def _add_condition(self, field: str, gt: Optional[float] = None,
                      gte: Optional[float] = None, lt: Optional[float] = None,
                      lte: Optional[float] = None, eq: Optional[float] = None,
                      ne: Optional[float] = None) -> "Screener":
        """Add condition to filter (internal helper)."""
        conditions = []
        if gt is not None:
            conditions.append(('gt', gt))
        if gte is not None:
            conditions.append(('gte', gte))
        if lt is not None:
            conditions.append(('lt', lt))
        if lte is not None:
            conditions.append(('lte', lte))
        if eq is not None:
            conditions.append(('eq', eq))
        if ne is not None:
            conditions.append(('ne', ne))
        
        if conditions:
            self._filters['conditions'][field] = conditions
        
        return self
    
    def execute(self) -> Optional[pd.DataFrame]:
        """
        Execute all filters and return matching ETFs.
        
        Returns:
            DataFrame with matching ETFs, or None if no matches
        """
        from ETF_screener.main import evaluate_condition
        
        # Step 1: Screen by volume
        results = self.screener.screen_by_volume(
            min_days=self.days,
            min_avg_volume=self.min_volume,
            max_results=None,
        )
        
        if results.empty:
            return None
        
        # Step 2: Apply swing filter
        if self._filters['swing'] and not results.empty:
            swing_config = self._filters['swing']
            results = self.screener.filter_swing_setups(
                results,
                db=self.db,
                min_pullback=swing_config['min_pullback'],
                max_distance_from_ema=swing_config['max_ema_distance'],
                require_green_supertrend=True,
            )
        
        if results.empty:
            return None
        
        # Step 3: Apply supertrend filter
        if self._filters['supertrend'] and not results.empty:
            st_config = self._filters['supertrend']
            filtered_results = []
            
            for _, row in results.iterrows():
                ticker = row["ticker"]
                try:
                    hist_df = self.db.get_ticker_data(
                        ticker,
                        days=90 if st_config['timeframe'] == '1W' else 60
                    )
                    if hist_df.empty or len(hist_df) < 10:
                        continue
                    
                    hist_df = add_indicators(
                        hist_df,
                        st_period=st_config['period'],
                        st_multiplier=st_config['multiplier'],
                        timeframe=st_config['timeframe']
                    )
                    latest = hist_df.iloc[-1]
                    
                    # Calculate streak
                    streak_days, streak_status = calculate_consecutive_streak(hist_df)
                    
                    # Check color
                    if st_config['color'] == 'green' and latest["Close"] > latest["Supertrend"]:
                        row_copy = row.copy()
                        row_copy["streak_days"] = streak_days
                        row_copy["streak_status"] = streak_status
                        filtered_results.append(row_copy)
                    elif st_config['color'] == 'red' and latest["Close"] <= latest["Supertrend"]:
                        row_copy = row.copy()
                        row_copy["streak_days"] = streak_days
                        row_copy["streak_status"] = streak_status
                        
                        # Check red streak minimum
                        if streak_days >= self._filters['red_streak']:
                            filtered_results.append(row_copy)
                
                except Exception:
                    continue
            
            results = pd.DataFrame(filtered_results) if filtered_results else pd.DataFrame()
        
        if results.empty:
            return None
        
        # Step 4: Apply conditional filters
        if self._filters['conditions'] and not results.empty:
            for field, ops_list in self._filters['conditions'].items():
                if not ops_list:
                    continue
                
                filtered_results = []
                for _, row in results.iterrows():
                    # Fetch indicators if not already present
                    if field not in row or pd.isna(row[field]):
                        try:
                            ticker = row["ticker"]
                            hist_df = self.db.get_ticker_data(ticker, days=90)
                            if hist_df.empty or len(hist_df) < 10:
                                continue
                            
                            st_timeframe = self._filters['supertrend']['timeframe'] if self._filters['supertrend'] else '1D'
                            st_period = self._filters['supertrend']['period'] if self._filters['supertrend'] else 10
                            st_mult = self._filters['supertrend']['multiplier'] if self._filters['supertrend'] else 3.0
                            
                            hist_df = add_indicators(hist_df, st_period=st_period, st_multiplier=st_mult, timeframe=st_timeframe)
                            latest = hist_df.iloc[-1]
                            row = row.copy()
                            row["close"] = latest["Close"]
                            row["ema"] = latest["EMA_50"]
                            row["supertrend"] = latest["Supertrend"]
                        except Exception:
                            continue
                    
                    # Check all conditions for this field
                    passes_all = True
                    for op, threshold in ops_list:
                        field_value = None
                        if field == "close":
                            field_value = row.get("close") or row.get("Close")
                        elif field == "ema":
                            field_value = row.get("ema") or row.get("EMA_50") or row.get("ema_50")
                        elif field == "pullback":
                            field_value = row.get("pullback") or row.get("Pullback_Pct")
                        elif field == "volume":
                            field_value = row.get("volume") or row.get("Avg Vol") or row.get("avg_vol")
                        
                        if field_value is None or not evaluate_condition(field_value, op, threshold):
                            passes_all = False
                            break
                    
                    if passes_all:
                        filtered_results.append(row)
                
                results = pd.DataFrame(filtered_results) if filtered_results else pd.DataFrame()
        
        return results if not results.empty else None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.db.close()
    
    def close(self):
        """Close database connection."""
        self.db.close()
