"""ETF discovery and validation module."""

import json
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from yfinance import Ticker


class ETFDiscovery:
    """Discover and validate XETRA ETF tickers."""

    # Expanded list of common XETRA ETFs (curated from major providers)
    INITIAL_XETRA_ETFS = [
        # iShares Core (largest provider on XETRA)
        "EXS1.DE",  "EUNL.DE",  "EUSA.DE",  "IUSB.DE",  "IUAG.DE",
        "IDRX.DE",  "IDVX.DE",  "IDVY.DE",  "EUNX.DE",  "IEAU.DE",
        "IEUD.DE",  "IEPD.DE",  "IEAG.DE",  "IEAP.DE",  "IEVX.DE",
        "EIUV.DE",  "EUNQ.DE",  "EUNH.DE",  "EURE.DE",  "IAMX.DE",
        
        # Xtrackers (Deutsche Börse owned)
        "XDEU.DE",  "XESC.DE",  "XESX.DE",  "XMEU.DE",  "XNEU.DE",
        "XGLD.DE",  "XBTI.DE",  "XSPU.DE",  "XUUS.DE",  "XXRA.DE",
        "XCNS.DE",  "XCRA.DE",  "XDIV.DE",  "XDTE.DE",  "XEMD.DE",
        "XERX.DE",  "XFIN.DE",  "XHYG.DE",  "XMMU.DE",  "XMUS.DE",
        
        # Vanguard
        "VWRL.DE",  "VUSA.DE",  "VUSD.DE",  "VEUR.DE",  "VUJP.DE",
        "VGOV.DE",  "VEVT.DE",  "VANG.DE",  "VDIV.DE",  "VCNS.DE",
        
        # SPDR
        "XSPU.DE",  "XSPE.DE",  "XSPD.DE",
        
        # Lyxor/Amundi
        "EUSA.DE",  "EUDT.DE",  "EUCX.DE",  "EUNX.DE",
        
        # iShares Bonds & Income
        "IBCI.DE",  "IBCS.DE",  "IBDE.DE",  "IBGG.DE",  "IBMT.DE",
        "IBTX.DE",  "IBCX.DE",  "IBEU.DE",  "ICHA.DE",
        
        # iShares Asia-Pacific & EM
        "RIEM.DE",  "ASSE.DE",  "ASEM.DE",
        
        # Dividend & Value Focus
        "XDIV.DE",  "DHDX.DE",  "IDVX.DE",  "IEMX.DE",
        
        # Growth & Tech
        "XCNS.DE",  "XNEU.DE",  "XMUS.DE",  "XMMU.DE",
        
        # Commodities & Precious Metals
        "XGLD.DE",  "XSLV.DE",  "XPAT.DE",  "XCOP.DE",  "XOIL.DE",
        
        # Crypto & Digital Assets  
        "XBTI.DE",  "XETH.DE",
        
        # ESG / Sustainability
        "EIUN.DE",  "EUNX.DE",  "XDXE.DE",
        
        # Real Estate (REITs)
        "XREA.DE",  "REIT.DE",  
        
        # Emerging Markets 
        "XMEU.DE",  "XMEA.DE",  "XMAM.DE",
    ]

    def __init__(self, etfs_file: str = "etfs.json", blacklist_file: str = "blacklist.json"):
        """Initialize discovery with output files."""
        self.etfs_file = Path(etfs_file)
        self.blacklist_file = Path(blacklist_file)
        self.working_etfs = self._load_json(self.etfs_file) or {}
        self.blacklist = self._load_json(self.blacklist_file) or {}

    @staticmethod
    def _load_json(file_path: Path) -> Optional[dict]:
        """Load JSON file if it exists."""
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
        return None

    def _save_json(self, data: dict, file_path: Path) -> None:
        """Save data to JSON file."""
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def validate_ticker(self, ticker: str) -> bool:
        """
        Check if ticker has data on Yahoo Finance.

        Args:
            ticker: ETF ticker symbol

        Returns:
            True if data available, False otherwise
        """
        try:
            t = Ticker(ticker)
            # Try to get basic info
            info = t.info
            # Check if we got actual data back (not just empty dict)
            if info and len(info) > 0:
                return True
            
            # Alternative: try to get historical data
            hist = t.history(period="1d")
            if hist is not None and not hist.empty:
                return True
            
            return False
        except Exception as e:
            print(f"  Error checking {ticker}: {str(e)}")
            return False

    def discover(self, tickers: Optional[list[str]] = None, verbose: bool = True) -> dict:
        """
        Discover and validate ETF tickers.

        Args:
            tickers: List of tickers to validate. If None, uses INITIAL_XETRA_ETFS
            verbose: Print progress

        Returns:
            Dict with 'working' and 'blacklisted' keys
        """
        if tickers is None:
            tickers = self.INITIAL_XETRA_ETFS

        if verbose:
            print(f"Validating {len(tickers)} ETF tickers...\n")

        for ticker in tickers:
            # Skip if already processed
            if ticker in self.working_etfs or ticker in self.blacklist:
                continue

            if verbose:
                print(f"Testing {ticker}...", end=" ")

            if self.validate_ticker(ticker):
                if verbose:
                    print("✓ Working")
                self.working_etfs[ticker] = {"status": "active"}
            else:
                if verbose:
                    print("✗ Delisted/Unavailable")
                self.blacklist[ticker] = {"status": "invalid"}

        # Save results
        self._save_json(self.working_etfs, self.etfs_file)
        self._save_json(self.blacklist, self.blacklist_file)

        if verbose:
            print("\n✓ Results saved:")
            print(f"  {self.etfs_file}: {len(self.working_etfs)} working ETFs")
            print(f"  {self.blacklist_file}: {len(self.blacklist)} blacklisted")

        return {
            "working": self.working_etfs,
            "blacklisted": self.blacklist,
        }

    def discover_parallel(
        self, tickers: Optional[list[str]] = None, max_workers: int = 5, verbose: bool = True
    ) -> dict:
        """
        Discover and validate ETF tickers in parallel (faster for large lists).

        Args:
            tickers: List of tickers to validate. If None, uses expanded curated list
            max_workers: Number of parallel workers
            verbose: Print progress

        Returns:
            Dict with 'working' and 'blacklisted' keys
        """
        # Use curated list if no tickers provided
        if tickers is None:
            tickers = self.INITIAL_XETRA_ETFS
            if verbose:
                print(f"Using curated XETRA ETF list ({len(tickers)} tickers)")
        
        tickers = [t for t in tickers if t not in self.working_etfs and t not in self.blacklist]

        if not tickers:
            if verbose:
                print(f"No new tickers to validate. Already have {len(self.working_etfs)} working and {len(self.blacklist)} blacklisted.")
            return {"working": self.working_etfs, "blacklisted": self.blacklist}

        if verbose:
            print(f"Validating {len(tickers)} ETF tickers in parallel ({max_workers} workers)...\n")

        tested = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.validate_ticker_batch, ticker): ticker for ticker in tickers}
            
            for future in as_completed(futures):
                ticker, is_valid = future.result()
                tested += 1
                
                if is_valid:
                    self.working_etfs[ticker] = {"status": "active"}
                    status = "✓"
                else:
                    self.blacklist[ticker] = {"status": "invalid"}
                    status = "✗"
                
                if verbose and tested % 10 == 0:  # Print progress every 10 tickers
                    print(f"  Progress: {tested}/{len(tickers)} tested ({status})")
        
        # Save results
        self._save_json(self.working_etfs, self.etfs_file)
        self._save_json(self.blacklist, self.blacklist_file)

        if verbose:
            print("\n✓ Batch validation complete:")
            print(f"  {self.etfs_file}: {len(self.working_etfs)} total working ETFs")
            print(f"  {self.blacklist_file}: {len(self.blacklist)} total blacklisted")

        return {
            "working": self.working_etfs,
            "blacklisted": self.blacklist,
        }

    def get_working_tickers(self) -> list[str]:
        """Get list of validated working ticker symbols."""
        return list(self.working_etfs.keys())

    def add_to_blacklist(self, ticker: str, reason: str = "manual") -> None:
        """Add ticker to blacklist."""
        self.blacklist[ticker] = {"status": "invalid", "reason": reason}
        if ticker in self.working_etfs:
            del self.working_etfs[ticker]
        self._save_json(self.working_etfs, self.etfs_file)
        self._save_json(self.blacklist, self.blacklist_file)

    def add_to_working(self, ticker: str) -> None:
        """Add ticker to working list."""
        self.working_etfs[ticker] = {"status": "active"}
        if ticker in self.blacklist:
            del self.blacklist[ticker]
        self._save_json(self.working_etfs, self.etfs_file)
        self._save_json(self.blacklist, self.blacklist_file)

    def fetch_xetra_etfs_from_justetfs(self) -> list[str]:
        """
        Fetch list of XETRA ETFs from justETFs.com.

        Returns:
            List of XETRA ETF tickers
        """
        tickers = []
        base_url = "https://www.justetf.com/de/find-etf.html"
        
        try:
            print("Fetching XETRA ETF list from justETFs...")
            
            # Set parameters for XETRA exchange, all ETFs
            params = {
                "exchange": "Xetra",
                "country": "",
                "assetClass": "",
                "strategy": "",
                "rating": "",
                "priceMin": "",
                "priceMax": "",
                "volumeMin": "",
                "volumeMax": "",
                "costsMin": "",
                "costsMax": "",
                "sortField": "name",
                "sortOrder": "asc",
                "pageNumber": 0,
            }
            
            # Make request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all ETF rows in the table
            rows = soup.find_all("tr", class_="etf-row")
            
            if not rows:
                print("  Warning: Could not parse table from justETFs")
                return tickers
            
            print(f"  Found {len(rows)} ETFs on page")
            
            # Extract ticker symbols (ISIN codes and ticker symbols)
            for row in rows:
                # Try to find ticker in the row
                ticker_elem = row.find("td", class_="etf-symbol")
                if ticker_elem:
                    ticker = ticker_elem.get_text(strip=True)
                    if ticker and ticker.endswith(".DE"):
                        tickers.append(ticker)
            
            print(f"  Extracted {len(tickers)} XETRA ETF tickers")
            return tickers
            
        except Exception as e:
            print(f"  Error fetching from justETFs: {str(e)}")
            return tickers

    def validate_ticker_batch(self, ticker: str) -> tuple[str, bool]:
        """
        Check if ticker has data. Returns tuple for batch processing.

        Args:
            ticker: ETF ticker symbol

        Returns:
            Tuple of (ticker, is_valid)
        """
        try:
            t = Ticker(ticker, session=None)
            # Try to get basic info
            info = t.info
            if info and len(info) > 0:
                return (ticker, True)
            
            # Alternative: try to get historical data
            hist = t.history(period="1d")
            if hist is not None and not hist.empty:
                return (ticker, True)
            
            return (ticker, False)
        except Exception:
            return (ticker, False)
