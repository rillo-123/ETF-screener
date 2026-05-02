"""Build and cache ETF shortlist artifacts for the dashboard."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import add_indicators
from ETF_screener.storage import ParquetStorage


class ETFShortlistEngine:
    """Compute an ETF-first shortlist snapshot and persist it for reuse."""

    ARTIFACT_VERSION = "shortlist_v1"
    TRUSTED_ISSUERS = {
        "iShares",
        "Vanguard",
        "Xtrackers",
        "Amundi",
        "SPDR",
        "Invesco",
        "WisdomTree",
        "L&G",
    }

    def __init__(
        self,
        db_path: str | None = None,
        metadata_path: str | None = None,
        storage: Optional[ParquetStorage] = None,
    ):
        self.db = ETFDatabase(db_path=db_path)
        self.storage = storage or ParquetStorage()
        self.metadata_path = Path(metadata_path or "config/xetra.json")
        self.metadata_map = self._load_metadata_map()

    def _load_metadata_map(self) -> dict[str, dict[str, Any]]:
        if not self.metadata_path.exists():
            return {}

        with open(self.metadata_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)

        normalized: dict[str, dict[str, Any]] = {}
        if not isinstance(raw, dict):
            return normalized

        for ticker, info in raw.items():
            if isinstance(info, dict):
                payload = info.copy()
            else:
                payload = {"name": str(info)}
            payload.setdefault("name", str(ticker))
            normalized[str(ticker).upper()] = payload
        return normalized

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
            if pd.isna(result):
                return default
            return result
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        rename_map = {}
        for column in df.columns:
            lower = str(column).lower()
            if lower == "date":
                rename_map[column] = "Date"
            elif lower == "open":
                rename_map[column] = "Open"
            elif lower == "high":
                rename_map[column] = "High"
            elif lower == "low":
                rename_map[column] = "Low"
            elif lower == "close":
                rename_map[column] = "Close"
            elif lower == "volume":
                rename_map[column] = "Volume"
            elif lower == "ema_50":
                rename_map[column] = "EMA_50"
            elif lower == "supertrend":
                rename_map[column] = "Supertrend"
            elif lower == "st_upper":
                rename_map[column] = "ST_Upper"
            elif lower == "st_lower":
                rename_map[column] = "ST_Lower"
            elif lower == "signal":
                rename_map[column] = "Signal"
            elif lower == "rsi":
                rename_map[column] = "RSI"
            elif lower == "macd":
                rename_map[column] = "MACD"
            elif lower == "macd_signal":
                rename_map[column] = "MACD_Signal"
            elif lower == "pullback_pct":
                rename_map[column] = "Pullback_Pct"
            elif lower == "ema_distance_pct":
                rename_map[column] = "EMA_Distance_Pct"

        normalized = df.rename(columns=rename_map).copy()
        if "Date" in normalized.columns:
            normalized["Date"] = pd.to_datetime(normalized["Date"])
            normalized = normalized.sort_values("Date").reset_index(drop=True)
        return normalized

    @staticmethod
    def _needs_enrichment(df: pd.DataFrame) -> bool:
        required = {
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "EMA_50",
            "Supertrend",
            "Signal",
            "RSI",
            "MACD",
            "MACD_Signal",
            "Pullback_Pct",
            "EMA_Distance_Pct",
        }
        if not required.issubset(set(df.columns)):
            return True

        for column in ["EMA_50", "Supertrend", "RSI", "MACD", "MACD_Signal"]:
            if column not in df.columns or df[column].notna().sum() == 0:
                return True

        return False

    def _load_frame(self, ticker: str) -> pd.DataFrame:
        df = self.storage.load_etf_data(ticker)
        df = self._normalize_frame(df)
        if df.empty:
            with ETFDatabase(db_path=str(self.db.db_path)) as db:
                df = db.get_ticker_data(ticker, days=320)
            df = self._normalize_frame(df)

        if df.empty:
            return df

        if self._needs_enrichment(df):
            df = add_indicators(df)
            df = self._normalize_frame(df)

        return df.tail(320).reset_index(drop=True)

    @staticmethod
    def _find_recent_signal_age(df: pd.DataFrame, max_bars: int = 30) -> int | None:
        if df.empty or "Signal" not in df.columns:
            return None

        signals = df["Signal"].fillna(0).astype(int)
        limit = min(len(df), max_bars + 1)
        for age in range(limit):
            idx = len(df) - 1 - age
            if idx < 0:
                break
            if signals.iloc[idx] != 1:
                continue
            if idx + 1 < len(df) and (signals.iloc[idx + 1 :] == -1).any():
                continue
            return age

        return None

    @staticmethod
    def _detect_issuer(name: str) -> str:
        upper = name.upper()
        if "ISH" in upper or "ISHARES" in upper:
            return "iShares"
        if "VANG" in upper or "VANGUARD" in upper:
            return "Vanguard"
        if "XTR" in upper or "XTRACK" in upper:
            return "Xtrackers"
        if "AMUNDI" in upper or "LYXOR" in upper or "MUL AMUN" in upper:
            return "Amundi"
        if "SPDR" in upper:
            return "SPDR"
        if "INVESCO" in upper:
            return "Invesco"
        if "WISDOMTREE" in upper:
            return "WisdomTree"
        if "L+G" in upper or "LEGAL" in upper:
            return "L&G"
        return "Other"

    @staticmethod
    def _classify_asset_class(name: str) -> str:
        upper = name.upper()
        if any(keyword in upper for keyword in ["BOND", "TREAS", "GILT", "CORP", "AGG"]):
            return "Bond"
        if any(keyword in upper for keyword in ["GOLD", "SILVER", "OIL", "COPPER", "ETC"]):
            return "Commodity"
        if any(keyword in upper for keyword in ["BITCOIN", "ETHEREUM", "CRYPTO", "DIGITAL"]):
            return "Crypto"
        return "Equity"

    @staticmethod
    def _classify_region(name: str) -> str:
        upper = name.upper()
        if any(keyword in upper for keyword in ["WORLD", "ALL-WORLD", "ACWI", "MSCI AC"]):
            return "Global"
        if any(keyword in upper for keyword in ["S&P 500", "SP500", "USA", "US ", "NASDAQ", "RUSSELL"]):
            return "United States"
        if any(keyword in upper for keyword in ["EUROPE", "STOXX", "EMU", "EURO ", "MSCI EUROPE"]):
            return "Europe"
        if any(keyword in upper for keyword in ["DAX", "GERMANY", "GERMAN"]):
            return "Germany"
        if any(keyword in upper for keyword in ["EMERGING", "EM ", "MSCI EM"]):
            return "Emerging Markets"
        if any(keyword in upper for keyword in ["JAPAN", "NIKKEI", "TOPIX"]):
            return "Japan"
        if any(keyword in upper for keyword in ["CHINA", "CSI", "HANG SENG"]):
            return "China"
        if "ASIA" in upper:
            return "Asia"
        return "Other"

    @staticmethod
    def _classify_style(name: str) -> str:
        upper = name.upper()
        if any(keyword in upper for keyword in ["2X", "3X", "LEVDAX", "DAILY", "LEVER"]):
            return "Leveraged"
        if any(keyword in upper for keyword in ["SHORT", "INVERSE", "BEAR"]):
            return "Inverse"
        if any(
            keyword in upper
            for keyword in [
                "WORLD",
                "ALL-WORLD",
                "MSCI",
                "S&P 500",
                "STOXX",
                "DAX",
                "NASDAQ 100",
            ]
        ):
            return "Core Broad Market"
        if any(keyword in upper for keyword in ["DIVID", "VALUE", "QUALITY", "MIN VOL"]):
            return "Factor Income"
        if any(
            keyword in upper
            for keyword in [
                "TECH",
                "BANK",
                "FINANC",
                "HEALTH",
                "ENERGY",
                "REIT",
                "ESG",
                "CLEAN",
            ]
        ):
            return "Sector/Thematic"
        return "Specialist"

    def _build_metadata(self, ticker: str) -> dict[str, Any]:
        raw = self.metadata_map.get(ticker, {})
        name = str(raw.get("name") or ticker)
        upper = name.upper()
        style = self._classify_style(name)
        is_leveraged = style == "Leveraged"
        is_inverse = style == "Inverse"
        return {
            "ticker": ticker,
            "name": name,
            "issuer": self._detect_issuer(name),
            "asset_class": self._classify_asset_class(name),
            "region": self._classify_region(name),
            "style": style,
            "is_ucits": any(
                keyword in upper for keyword in ["UCITS", "UC.ETF", "U.ETF", "UETF"]
            ),
            "is_leveraged": is_leveraged,
            "is_inverse": is_inverse,
            "source": str(self.metadata_path),
        }

    def _score_product(self, meta: dict[str, Any], volume: float) -> tuple[float, list[str]]:
        score = 50.0
        reasons: list[str] = []

        if meta["issuer"] in self.TRUSTED_ISSUERS:
            score += 15
            reasons.append(f"Trusted issuer: {meta['issuer']}")
        if meta["is_ucits"]:
            score += 15
            reasons.append("UCITS wrapper")
        if meta["is_leveraged"]:
            score -= 35
            reasons.append("Leveraged product")
        if meta["is_inverse"]:
            score -= 35
            reasons.append("Inverse/short exposure")
        if meta["asset_class"] == "Crypto":
            score -= 15
            reasons.append("High-volatility crypto exposure")
        elif meta["asset_class"] == "Commodity":
            score -= 8
            reasons.append("Commodity-style holding")
        if meta["style"] == "Core Broad Market":
            score += 10
            reasons.append("Plain broad-market structure")
        if volume >= 500_000:
            score += 5
            reasons.append("Healthy recent volume")

        return max(0.0, min(score, 100.0)), reasons

    @staticmethod
    def _score_exposure(meta: dict[str, Any]) -> tuple[float, list[str]]:
        score = 50.0
        reasons: list[str] = []

        if meta["style"] == "Core Broad Market":
            score += 25
            reasons.append("Broad diversified exposure")
        elif meta["style"] == "Factor Income":
            score += 8
            reasons.append("Simple factor tilt")
        elif meta["style"] == "Sector/Thematic":
            score -= 10
            reasons.append("Sector/theme concentration")
        elif meta["style"] in {"Leveraged", "Inverse"}:
            score -= 25
            reasons.append("Tactical rather than core exposure")

        if meta["region"] in {"Global", "United States", "Europe", "Emerging Markets"}:
            score += 10
        elif meta["region"] == "Other":
            score -= 5

        if meta["asset_class"] == "Bond":
            score += 5
        elif meta["asset_class"] in {"Commodity", "Crypto"}:
            score -= 10

        return max(0.0, min(score, 100.0)), reasons

    def _score_technical(
        self, df: pd.DataFrame, recent_entry_days: int | None
    ) -> tuple[float, dict[str, float], list[str]]:
        latest = df.iloc[-1]
        close = self._safe_float(latest.get("Close"))
        ema_50 = self._safe_float(latest.get("EMA_50"))
        supertrend = self._safe_float(latest.get("Supertrend"))
        rsi = self._safe_float(latest.get("RSI"), 50.0)
        macd = self._safe_float(latest.get("MACD"))
        macd_signal = self._safe_float(latest.get("MACD_Signal"))
        pullback_pct = self._safe_float(latest.get("Pullback_Pct"))
        volume = self._safe_float(latest.get("Volume"))

        ema_50_prev = ema_50
        if len(df) > 5:
            ema_50_prev = self._safe_float(df.iloc[-5].get("EMA_50"), ema_50)
        ema_50_slope_pct = 0.0
        if ema_50_prev:
            ema_50_slope_pct = ((ema_50 / ema_50_prev) - 1.0) * 100.0

        score = 50.0
        reasons: list[str] = []

        if close > ema_50:
            score += 18
            reasons.append("Price above EMA 50")
        else:
            score -= 18
            reasons.append("Below EMA 50")

        if ema_50_slope_pct > 0:
            score += 12
            reasons.append("EMA 50 rising")
        else:
            score -= 8

        if close > supertrend:
            score += 16
            reasons.append("Above Supertrend")
        else:
            score -= 10

        if macd > macd_signal:
            score += 12
            reasons.append("MACD supports trend")
        else:
            score -= 6

        if 45 <= rsi <= 68:
            score += 10
            reasons.append("RSI in healthy range")
        elif 35 <= rsi < 45 or 68 < rsi <= 75:
            score += 4
        else:
            score -= 6

        if close > ema_50 and 2 <= pullback_pct <= 8:
            score += 8
            reasons.append("Constructive pullback")

        if recent_entry_days is not None:
            freshness = max(0.0, 14.0 - (float(recent_entry_days) * 2.0))
            score += freshness
            reasons.append(f"Recent signal {recent_entry_days}d ago")

        if volume >= 250_000:
            score += 4

        components = {
            "ema_50_slope_pct": round(ema_50_slope_pct, 3),
            "rsi": round(rsi, 2),
            "pullback_pct": round(pullback_pct, 2),
            "close_above_ema_50": float(close > ema_50),
            "close_above_supertrend": float(close > supertrend),
            "macd_above_signal": float(macd > macd_signal),
        }

        return max(0.0, min(score, 100.0)), components, reasons

    @staticmethod
    def _label_row(
        product_score: float, exposure_score: float, technical_score: float, final_score: float
    ) -> str:
        if final_score >= 70 and product_score >= 55 and technical_score >= 60:
            return "Buy"
        if final_score >= 55 and product_score >= 45:
            return "Watch"
        return "Skip"

    def _analyze_ticker(self, ticker: str) -> Optional[dict[str, Any]]:
        df = self._load_frame(ticker)
        if df.empty or len(df) < 60:
            return None

        meta = self._build_metadata(ticker)
        recent_entry_days = self._find_recent_signal_age(df)
        latest = df.iloc[-1]
        close = self._safe_float(latest.get("Close"))
        volume = int(self._safe_float(latest.get("Volume"), 0.0))
        as_of_date = pd.to_datetime(latest.get("Date")).strftime("%Y-%m-%d")

        product_score, product_reasons = self._score_product(meta, volume)
        exposure_score, exposure_reasons = self._score_exposure(meta)
        technical_score, technical_components, technical_reasons = self._score_technical(
            df, recent_entry_days
        )
        final_score = round(
            (0.40 * product_score) + (0.20 * exposure_score) + (0.40 * technical_score),
            2,
        )
        label = self._label_row(
            product_score, exposure_score, technical_score, final_score
        )
        reasons = (product_reasons + exposure_reasons + technical_reasons)[:6]
        components = {
            "product_score": round(product_score, 2),
            "exposure_score": round(exposure_score, 2),
            "technical_score": round(technical_score, 2),
            "final_score": round(final_score, 2),
            "style": meta["style"],
            "recent_entry_days": recent_entry_days,
            **technical_components,
        }

        return {
            "metadata": meta,
            "artifact": {
                "ticker": ticker,
                "as_of_date": as_of_date,
                "name": meta["name"],
                "issuer": meta["issuer"],
                "asset_class": meta["asset_class"],
                "region": meta["region"],
                "close": round(close, 4),
                "volume": volume,
                "recent_entry_days": recent_entry_days,
                "product_score": round(product_score, 2),
                "exposure_score": round(exposure_score, 2),
                "technical_score": round(technical_score, 2),
                "final_score": round(final_score, 2),
                "label": label,
                "reasons_json": json.dumps(reasons),
                "components_json": json.dumps(components),
                "artifact_version": self.ARTIFACT_VERSION,
            },
        }

    def build_shortlist(
        self,
        tickers: Optional[list[str]] = None,
        max_workers: Optional[int] = None,
    ) -> pd.DataFrame:
        universe = tickers or self.db.get_tickers()
        if not universe:
            return pd.DataFrame()

        worker_count = max_workers or min(8, max(2, os.cpu_count() or 4))
        metadata_rows: list[dict[str, Any]] = []
        artifact_rows: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self._analyze_ticker, ticker.upper()): ticker.upper()
                for ticker in universe
            }
            for future in as_completed(futures):
                result = future.result()
                if not result:
                    continue
                metadata_rows.append(result["metadata"])
                artifact_rows.append(result["artifact"])

        self.db.upsert_etf_metadata(metadata_rows)
        self.db.upsert_shortlist_artifacts(artifact_rows)
        return self.db.get_shortlist(limit=None)

    def get_shortlist(
        self,
        limit: int = 50,
        label: str | None = None,
        refresh: bool = False,
        max_workers: Optional[int] = None,
    ) -> pd.DataFrame:
        market_date = self.db.get_latest_market_date()
        shortlist_date = self.db.get_latest_shortlist_date()

        if refresh or not shortlist_date or shortlist_date != market_date:
            self.build_shortlist(max_workers=max_workers)

        return self.db.get_shortlist(limit=limit, label=label)
