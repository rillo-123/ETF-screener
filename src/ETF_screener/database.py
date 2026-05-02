from ETF_screener.config_loader import get_paths
"""SQLite database interface for ETF data persistence."""

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


class ETFDatabase:
    """SQLite database for storing and querying ETF data."""

    def __init__(self, db_path: str = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file (default: data/etf_db/etfs.db)
        """
        if db_path is None:
            db_path = get_paths()["data"]["etf_db"]
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with conservative concurrency settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # Another connection may already hold the database lock during startup.
            # Fall back to the default journal mode and rely on the busy timeout.
            pass
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @staticmethod
    def _ensure_columns(
        cursor: sqlite3.Cursor,
        table_name: str,
        columns: dict[str, str],
    ) -> None:
        """Add missing columns for lightweight local schema upgrades."""
        existing = {
            str(row[1])
            for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing:
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )

    def _init_db(self) -> None:
        """Initialize database with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
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
                dividends REAL DEFAULT 0,
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
        self._ensure_columns(
            cursor,
            "etf_data",
            {
                "dividends": "REAL DEFAULT 0",
            },
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS etf_metadata (
                ticker TEXT PRIMARY KEY,
                name TEXT,
                issuer TEXT,
                asset_class TEXT,
                region TEXT,
                style TEXT,
                is_ucits INTEGER DEFAULT 0,
                is_leveraged INTEGER DEFAULT 0,
                is_inverse INTEGER DEFAULT 0,
                source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS etf_shortlist_artifacts (
                ticker TEXT PRIMARY KEY,
                as_of_date TEXT NOT NULL,
                name TEXT,
                issuer TEXT,
                asset_class TEXT,
                region TEXT,
                close REAL,
                volume INTEGER,
                recent_entry_days INTEGER,
                product_score REAL,
                exposure_score REAL,
                technical_score REAL,
                final_score REAL,
                label TEXT,
                reasons_json TEXT,
                components_json TEXT,
                artifact_version TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS swarm_world_artifacts (
                ticker TEXT PRIMARY KEY,
                as_of_date TEXT NOT NULL,
                name TEXT,
                issuer TEXT,
                asset_class TEXT,
                region TEXT,
                label TEXT,
                volume INTEGER,
                recent_entry_days INTEGER,
                product_score REAL,
                exposure_score REAL,
                technical_score REAL,
                final_score REAL,
                energy REAL,
                momentum_score REAL,
                freshness_score REAL,
                grid_row INTEGER,
                grid_col INTEGER,
                x REAL,
                y REAL,
                radius REAL,
                color TEXT,
                components_json TEXT,
                world_version TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._ensure_columns(
            cursor,
            "swarm_world_artifacts",
            {
                "grid_row": "INTEGER",
                "grid_col": "INTEGER",
            },
        )

        # Create indices for efficient querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON etf_data(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON etf_data(date)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ticker_date ON etf_data(ticker, date)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_volume ON etf_data(volume)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_etf_metadata_region ON etf_metadata(region)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_shortlist_label ON etf_shortlist_artifacts(label)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_shortlist_score ON etf_shortlist_artifacts(final_score DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_shortlist_asof ON etf_shortlist_artifacts(as_of_date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_swarm_label ON swarm_world_artifacts(label)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_swarm_energy ON swarm_world_artifacts(energy DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_swarm_asof ON swarm_world_artifacts(as_of_date)"
        )

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self.connection is None:
            self.connection = self._connect()
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
            INSERT INTO etf_data
            (ticker, date, open, high, low, close, dividends, volume, ema_50, supertrend,
             st_upper, st_lower, signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                dividends = excluded.dividends,
                volume = excluded.volume,
                ema_50 = excluded.ema_50,
                supertrend = excluded.supertrend,
                st_upper = excluded.st_upper,
                st_lower = excluded.st_lower,
                signal = excluded.signal
            """,
            (
                ticker.upper(),
                date,
                open_price,
                high,
                low,
                close,
                0.0,
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

        data_to_insert = []
        for _, row in df.iterrows():
            # Standardize date to YYYY-MM-DD
            if hasattr(row["Date"], "strftime"):
                date_str = row["Date"].strftime("%Y-%m-%d")
            else:
                # Try parsing if it's a string, or just use as is
                try:
                    date_str = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")
                except Exception:
                    date_str = str(row["Date"]).split(" ")[
                        0
                    ]  # Remove time component if present

            data_to_insert.append(
                (
                    ticker.upper(),
                    date_str,
                    row.get("Open"),
                    row.get("High"),
                    row.get("Low"),
                    row.get("Close"),
                    row.get("Dividends", row.get("dividends", 0.0)) or 0.0,
                    row.get("Volume", 0),
                    row.get("EMA_50"),
                    row.get("Supertrend"),
                    row.get("ST_Upper"),
                    row.get("ST_Lower"),
                    row.get("Signal", 0),
                )
            )

        cursor.executemany(
            """
            INSERT INTO etf_data
            (ticker, date, open, high, low, close, dividends, volume, ema_50, supertrend,
             st_upper, st_lower, signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                dividends = excluded.dividends,
                volume = excluded.volume,
                ema_50 = excluded.ema_50,
                supertrend = excluded.supertrend,
                st_upper = excluded.st_upper,
                st_lower = excluded.st_lower,
                signal = excluded.signal
            """,
            data_to_insert,
        )

        conn.commit()

    def get_etf_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
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

        cursor.execute(
            "SELECT 1 FROM etf_data WHERE ticker = ? LIMIT 1", (ticker.upper(),)
        )
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

    def get_latest_market_date(self) -> Optional[str]:
        """Get the latest trading date stored across the ETF universe."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM etf_data")
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

    def get_latest_shortlist_date(self) -> Optional[str]:
        """Get the latest artifact date stored for shortlist snapshots."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(as_of_date) FROM etf_shortlist_artifacts")
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

    def get_latest_shortlist_updated_at(self) -> Optional[str]:
        """Get the last write timestamp for shortlist artifacts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(updated_at) FROM etf_shortlist_artifacts")
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

    def get_latest_swarm_world_date(self) -> Optional[str]:
        """Get the latest artifact date stored for swarm world snapshots."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(as_of_date) FROM swarm_world_artifacts")
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

    def get_latest_swarm_world_updated_at(self) -> Optional[str]:
        """Get the last write timestamp for swarm world artifacts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(updated_at) FROM swarm_world_artifacts")
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

    def get_ticker_latest_dates(self) -> dict[str, str]:
        """Return the most recent stored market date for each ticker."""
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT ticker, MAX(date) AS latest_date
            FROM etf_data
            GROUP BY ticker
            """
        ).fetchall()
        return {
            str(row["ticker"] if isinstance(row, sqlite3.Row) else row[0]).upper(): str(
                row["latest_date"] if isinstance(row, sqlite3.Row) else row[1]
            )
            for row in rows
            if (row["latest_date"] if isinstance(row, sqlite3.Row) else row[1])
        }

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

        # Modified query to be more resilient to lack of depth
        # We fetch the last N rows instead of a fixed 1-year lookback
        query = (
            "SELECT ticker, date, open, high, low, close, volume, ema_50, supertrend, st_upper, st_lower, signal "
            "FROM etf_data "
            "WHERE ticker = ? "
            "ORDER BY date DESC LIMIT ?"
        )

        # We need to be careful with pd.read_sql_query when LIMIT is used
        # SQLite parameters must be clean

        cursor = conn.cursor()
        cursor.execute(query, (ticker.upper(), int(days)))
        rows = cursor.fetchall()

        if not rows:
            return pd.DataFrame()

        columns = [
            "ticker",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "ema_50",
            "supertrend",
            "st_upper",
            "st_lower",
            "signal",
        ]
        df_raw = pd.DataFrame(rows, columns=columns)

        # Sort back to ascending for technical analysis
        df_raw = df_raw.sort_values("date").reset_index(drop=True)

        # Check for "zombie" tickers: return empty if 2+ days have 0 volume in the LATEST data
        # (Only check the last 30 days of data retrieved to avoid penalizing history)
        df_check = df_raw.tail(30)
        if (df_check["volume"] == 0).sum() >= 2:
            return pd.DataFrame()

        # Ensure we don't have duplicates before renaming
        df = df_raw.drop_duplicates(subset=["date"]).copy()

        # Rename columns to match expected format
        df.columns = [
            "ticker",
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "EMA_50",
            "Supertrend",
            "ST_Upper",
            "ST_Lower",
            "Signal",
        ]
        df["Date"] = pd.to_datetime(df["Date"])

        return df

    def get_oldest_date(self, ticker: str) -> Optional[str]:
        """
        Get oldest date for a ticker in database.

        Args:
            ticker: ETF ticker symbol

        Returns:
            Oldest date (YYYY-MM-DD) or None if no data
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT MIN(date) FROM etf_data WHERE ticker = ?", (ticker.upper(),)
        )
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

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

    def upsert_etf_metadata(self, rows: list[dict]) -> None:
        """Insert or update ETF metadata rows used by the shortlist engine."""
        if not rows:
            return

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO etf_metadata (
                ticker, name, issuer, asset_class, region, style,
                is_ucits, is_leveraged, is_inverse, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name = excluded.name,
                issuer = excluded.issuer,
                asset_class = excluded.asset_class,
                region = excluded.region,
                style = excluded.style,
                is_ucits = excluded.is_ucits,
                is_leveraged = excluded.is_leveraged,
                is_inverse = excluded.is_inverse,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                (
                    row["ticker"],
                    row.get("name"),
                    row.get("issuer"),
                    row.get("asset_class"),
                    row.get("region"),
                    row.get("style"),
                    int(bool(row.get("is_ucits"))),
                    int(bool(row.get("is_leveraged"))),
                    int(bool(row.get("is_inverse"))),
                    row.get("source", "config/xetra.json"),
                )
                for row in rows
            ],
        )
        conn.commit()

    def upsert_shortlist_artifacts(self, rows: list[dict]) -> None:
        """Insert or update shortlist snapshot rows."""
        if not rows:
            return

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO etf_shortlist_artifacts (
                ticker, as_of_date, name, issuer, asset_class, region, close, volume,
                recent_entry_days, product_score, exposure_score, technical_score,
                final_score, label, reasons_json, components_json, artifact_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                as_of_date = excluded.as_of_date,
                name = excluded.name,
                issuer = excluded.issuer,
                asset_class = excluded.asset_class,
                region = excluded.region,
                close = excluded.close,
                volume = excluded.volume,
                recent_entry_days = excluded.recent_entry_days,
                product_score = excluded.product_score,
                exposure_score = excluded.exposure_score,
                technical_score = excluded.technical_score,
                final_score = excluded.final_score,
                label = excluded.label,
                reasons_json = excluded.reasons_json,
                components_json = excluded.components_json,
                artifact_version = excluded.artifact_version,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                (
                    row["ticker"],
                    row["as_of_date"],
                    row.get("name"),
                    row.get("issuer"),
                    row.get("asset_class"),
                    row.get("region"),
                    row.get("close"),
                    row.get("volume"),
                    row.get("recent_entry_days"),
                    row.get("product_score"),
                    row.get("exposure_score"),
                    row.get("technical_score"),
                    row.get("final_score"),
                    row.get("label"),
                    row.get("reasons_json"),
                    row.get("components_json"),
                    row.get("artifact_version"),
                )
                for row in rows
            ],
        )
        conn.commit()

    def upsert_swarm_world_artifacts(self, rows: list[dict]) -> None:
        """Insert or update swarm world snapshot rows."""
        if not rows:
            return

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO swarm_world_artifacts (
                ticker, as_of_date, name, issuer, asset_class, region, label,
                volume, recent_entry_days, product_score, exposure_score,
                technical_score, final_score, energy, momentum_score,
                freshness_score, grid_row, grid_col, x, y, radius, color,
                components_json, world_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                as_of_date = excluded.as_of_date,
                name = excluded.name,
                issuer = excluded.issuer,
                asset_class = excluded.asset_class,
                region = excluded.region,
                label = excluded.label,
                volume = excluded.volume,
                recent_entry_days = excluded.recent_entry_days,
                product_score = excluded.product_score,
                exposure_score = excluded.exposure_score,
                technical_score = excluded.technical_score,
                final_score = excluded.final_score,
                energy = excluded.energy,
                momentum_score = excluded.momentum_score,
                freshness_score = excluded.freshness_score,
                grid_row = excluded.grid_row,
                grid_col = excluded.grid_col,
                x = excluded.x,
                y = excluded.y,
                radius = excluded.radius,
                color = excluded.color,
                components_json = excluded.components_json,
                world_version = excluded.world_version,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                (
                    row["ticker"],
                    row["as_of_date"],
                    row.get("name"),
                    row.get("issuer"),
                    row.get("asset_class"),
                    row.get("region"),
                    row.get("label"),
                    row.get("volume"),
                    row.get("recent_entry_days"),
                    row.get("product_score"),
                    row.get("exposure_score"),
                    row.get("technical_score"),
                    row.get("final_score"),
                    row.get("energy"),
                    row.get("momentum_score"),
                    row.get("freshness_score"),
                    row.get("row"),
                    row.get("col"),
                    row.get("x"),
                    row.get("y"),
                    row.get("radius"),
                    row.get("color"),
                    row.get("components_json"),
                    row.get("world_version"),
                )
                for row in rows
            ],
        )
        conn.commit()

    def get_shortlist(
        self, limit: Optional[int] = 50, label: Optional[str] = None
    ) -> pd.DataFrame:
        """Return the persisted shortlist snapshot sorted by recommendation quality."""
        conn = self._get_connection()

        query = (
            "SELECT * FROM etf_shortlist_artifacts "
            "WHERE (? IS NULL OR label = ?) "
            "ORDER BY CASE label "
            "WHEN 'Buy' THEN 0 "
            "WHEN 'Watch' THEN 1 "
            "ELSE 2 END, final_score DESC, ticker ASC"
        )
        params: list[object] = [label, label]

        if limit is not None:
            query += f" LIMIT {max(1, int(limit))}"

        return pd.read_sql_query(query, conn, params=params)

    def get_swarm_world(
        self, limit: Optional[int] = None, label: Optional[str] = None
    ) -> pd.DataFrame:
        """Return the persisted swarm world snapshot sorted by ecosystem energy."""
        conn = self._get_connection()

        query = (
            "SELECT * FROM swarm_world_artifacts "
            "WHERE (? IS NULL OR label = ?) "
            "ORDER BY CASE label "
            "WHEN 'Buy' THEN 0 "
            "WHEN 'Watch' THEN 1 "
            "ELSE 2 END, energy DESC, final_score DESC, ticker ASC"
        )
        params: list[object] = [label, label]

        if limit is not None:
            query += f" LIMIT {max(1, int(limit))}"

        return pd.read_sql_query(query, conn, params=params)

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

    def __exit__(self, exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.close()
