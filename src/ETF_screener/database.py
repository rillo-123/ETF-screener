"""SQLite database interface for ETF data persistence."""

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


class ETFDatabase:
    """SQLite database for storing and querying ETF data."""

    def __init__(self, db_path: str = "data/etfs.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create ETF data table with proper indexing
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS etf_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                ema_50 REAL,
                supertrend REAL,
                st_upper REAL,
                st_lower REAL,
                signal INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, date)
            )
            """
        )

        # Create indices for efficient querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON etf_data(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON etf_data(date)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ticker_date ON etf_data(ticker, date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_volume ON etf_data(volume)"
        )

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def insert_etf_data(
        self,
        ticker: str,
        date: str,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        ema_50: Optional[float] = None,
        supertrend: Optional[float] = None,
        st_upper: Optional[float] = None,
        st_lower: Optional[float] = None,
        signal: int = 0,
    ) -> None:
        """
        Insert or update ETF data record.

        Args:
            ticker: ETF ticker symbol
            date: Trading date (YYYY-MM-DD)
            open_price: Opening price
            high: High price
            low: Low price
            close: Closing price
            volume: Trading volume
            ema_50: EMA 50 indicator value
            supertrend: Supertrend indicator value
            st_upper: Supertrend upper band
            st_lower: Supertrend lower band
            signal: Trading signal
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO etf_data 
            (ticker, date, open, high, low, close, volume, ema_50, supertrend, 
             st_upper, st_lower, signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker.upper(),
                date,
                open_price,
                high,
                low,
                close,
                volume,
                ema_50,
                supertrend,
                st_upper,
                st_lower,
                signal,
            ),
        )

        conn.commit()

    def insert_dataframe(self, df: pd.DataFrame, ticker: str) -> None:
        """
        Insert DataFrame of ETF data into database.

        Args:
            df: DataFrame with columns: Date, Open, High, Low, Close, Volume, etc.
            ticker: ETF ticker symbol
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        for _, row in df.iterrows():
            date_str = (
                row["Date"].strftime("%Y-%m-%d")
                if hasattr(row["Date"], "strftime")
                else str(row["Date"])
            )

            cursor.execute(
                """
                INSERT OR REPLACE INTO etf_data 
                (ticker, date, open, high, low, close, volume, ema_50, supertrend, 
                 st_upper, st_lower, signal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticker.upper(),
                    date_str,
                    row.get("Open"),
                    row.get("High"),
                    row.get("Low"),
                    row.get("Close"),
                    row.get("Volume", 0),
                    row.get("EMA_50"),
                    row.get("Supertrend"),
                    row.get("ST_Upper"),
                    row.get("ST_Lower"),
                    row.get("Signal", 0),
                ),
            )

        conn.commit()

    def get_etf_data(
        self, ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Retrieve ETF data for a ticker.

        Args:
            ticker: ETF ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with ETF data
        """
        conn = self._get_connection()

        query = "SELECT * FROM etf_data WHERE ticker = ?"
        params = [ticker.upper()]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date"

        df = pd.read_sql_query(query, conn, params=params)

        if not df.empty:
            df["Date"] = pd.to_datetime(df["date"])
            df = df.drop("date", axis=1)

        return df

    def get_tickers(self) -> list[str]:
        """
        Get all tickers in database.

        Returns:
            List of unique ticker symbols
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT ticker FROM etf_data ORDER BY ticker")
        return [row[0] for row in cursor.fetchall()]

    def ticker_exists(self, ticker: str) -> bool:
        """
        Check if ticker data exists in database.

        Args:
            ticker: ETF ticker symbol

        Returns:
            True if ticker exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM etf_data WHERE ticker = ? LIMIT 1", (ticker.upper(),))
        return cursor.fetchone() is not None

    def get_latest_date(self, ticker: str) -> Optional[str]:
        """
        Get latest date for a ticker.

        Args:
            ticker: ETF ticker symbol

        Returns:
            Latest date (YYYY-MM-DD) or None if no data
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT MAX(date) FROM etf_data WHERE ticker = ?", (ticker.upper(),)
        )
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

    def get_ticker_data(self, ticker: str, days: int = 60) -> pd.DataFrame:
        """
        Get historical price data for a ticker (last N days).

        Args:
            ticker: ETF ticker symbol
            days: Number of days to fetch

        Returns:
            DataFrame with OHLCV and indicator data
        """
        conn = self._get_connection()
        
        query = (
            "SELECT ticker, date, open, high, low, close, volume, ema_50, supertrend, signal "
            "FROM etf_data "
            f"WHERE ticker = ? AND date >= date('now', '-{int(days)} days') "
            "ORDER BY date ASC"
        )
        
        df = pd.read_sql_query(query, conn, params=(ticker.upper(),))
        
        if df.empty:
            return pd.DataFrame()
        
        # Rename columns to match expected format
        df.columns = ["ticker", "Date", "Open", "High", "Low", "Close", "Volume", "EMA_50", "Supertrend", "Signal"]
        df["Date"] = pd.to_datetime(df["Date"])
        
        return df

    def query_by_volume(
        self,
        min_days: int = 10,
        min_volume: int = 10_000_000,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Find ETFs with average volume above threshold in last N days.

        Args:
            min_days: Number of last days to consider
            min_volume: Minimum average volume threshold
            limit: Limit number of results (ordered by avg volume desc)

        Returns:
            DataFrame with tickers and their average volumes
        """
        conn = self._get_connection()

        query = (
            "SELECT \n"
            "    d.ticker,\n"
            "    AVG(d.volume) as avg_volume,\n"
            "    MAX(d.volume) as max_volume,\n"
            "    MIN(d.volume) as min_volume,\n"
            "    COUNT(*) as days_count,\n"
            "    MAX(CASE WHEN d.date = (SELECT MAX(date) FROM etf_data WHERE ticker = d.ticker) THEN d.open END) as open,\n"
            "    MAX(CASE WHEN d.date = (SELECT MAX(date) FROM etf_data WHERE ticker = d.ticker) THEN d.close END) as close,\n"
            "    MAX(CASE WHEN d.date = (SELECT MAX(date) FROM etf_data WHERE ticker = d.ticker) THEN d.close END) as latest_price,\n"
            "    MAX(CASE WHEN d.date = (SELECT MAX(date) FROM etf_data WHERE ticker = d.ticker) THEN d.ema_50 END) as ema_50,\n"
            "    MAX(CASE WHEN d.date = (SELECT MAX(date) FROM etf_data WHERE ticker = d.ticker) THEN d.supertrend END) as supertrend\n"
            "FROM etf_data d\n"
            f"WHERE d.date >= date('now', '-{int(min_days)} days')\n"  # nosec: safe from SQL injection
            "GROUP BY d.ticker\n"
            "HAVING AVG(d.volume) >= ?\n"
            "ORDER BY avg_volume DESC"
        )

        if limit:
            query += f" LIMIT {int(limit)}"

        df = pd.read_sql_query(query, conn, params=[min_volume])
        return df

    def prune_old_data(self, days_to_keep: int = 365) -> int:
        """
        Delete records older than specified number of days.

        Args:
            days_to_keep: Number of days to keep (default 365)

        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM etf_data WHERE date < date('now', '-' || ? || ' days')",
            (days_to_keep,),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
