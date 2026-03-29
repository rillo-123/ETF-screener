import json
import pandas as pd
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ETF_screener.database import ETFDatabase
from ETF_screener.plotter_plotly import InteractivePlotter
from ETF_screener.yfinance_fetcher import YFinanceFetcher
from ETF_screener.indicators import add_indicators
from ETF_screener.backtester import Backtester

app = FastAPI(title="ETF Discovery Lab API")
fetcher = YFinanceFetcher() # For on-demand fetching

# Setup templates and static files
# We can keep the same template files as Flask (Jinja2 is compatible)
templates = Jinja2Templates(directory="src/ETF_screener/dashboard/templates")

def get_strategies():
    """Load all .dsl strategies from the strategies directory."""
    strategies = []
    strat_dir = Path("strategies")
    if strat_dir.exists():
        for dsl_file in strat_dir.glob("*.dsl"):
            strategies.append(dsl_file.stem)
    return sorted(strategies)

def load_strategy_content(name):
    """Load the content of a strategy file."""
    strat_path = Path("strategies") / f"{name}.dsl"
    if strat_path.exists():
        return strat_path.read_text(encoding='utf-8')
    return ""

# Database access function (FastAPI style)
def get_db():
    return ETFDatabase(db_path="data/etfs.db")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page."""
    db = get_db()
    conn = db._get_connection()
    try:
        # Get all distinct tickers from DB OR from etfs.json if DB is fresh
        tickers = pd.read_sql_query("SELECT DISTINCT ticker FROM etf_data ORDER BY ticker", conn)['ticker'].tolist()
        if not tickers:
             # Fallback to etfs.json if DB is empty
             etf_path = Path("config/etfs.json")
             if etf_path.exists():
                 with open(etf_path, "r") as f:
                     tickers = json.load(f).get("tickers", [])
    except Exception as e:
        tickers = []
    
    strategies = get_strategies()
    return templates.TemplateResponse(
        request=request, name="index.html", context={
            "tickers": tickers, 
            "strategies": strategies
        }
    )

@app.get("/api/strategies")
async def list_strategies():
    """Get list of available strategies."""
    return get_strategies()

@app.get("/api/strategy/{name}")
async def get_strategy(name: str):
    """Get strategy content."""
    content = load_strategy_content(name)
    if not content:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"name": name, "content": content}

@app.post("/api/strategy/save")
async def save_strategy(request: Request):
    """Save a strategy to the strategies directory."""
    data = await request.json()
    name = data.get("name")
    content = data.get("content")
    
    if not name or not content:
        raise HTTPException(status_code=400, detail="Name and content required")
    
    # Sanitize name
    name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Invalid strategy name")
        
    strat_path = Path("strategies") / f"{name}.dsl"
    try:
        strat_path.parent.mkdir(parents=True, exist_ok=True)
        strat_path.write_text(content, encoding='utf-8')
        return {"status": "success", "message": f"Saved to {strat_path.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screen")
async def screen(strategy: Optional[str] = None, dsl_content: Optional[str] = None):
    """Run a dynamic screen based on selected strategies or provided DSL."""
    db = get_db()
    
    # Priority: 1. Provided DSL content (from Lab), 2. Named strategy (from dropdown)
    content = ""
    if dsl_content:
        content = dsl_content
    elif strategy:
        content = load_strategy_content(strategy)

    if not content:
        # Fallback to simple trend screen if no strategy found/selected
        conn = db._get_connection()
        query = """
            SELECT ticker, close, volume, supertrend, st_lower
            FROM etf_data 
            WHERE date = (SELECT MAX(date) FROM etf_data)
            AND close > st_lower
            ORDER BY volume DESC
            LIMIT 50
        """
        df = pd.read_sql_query(query, conn)
        matches = df.to_dict(orient='records')
        return matches

    import re
    # Parse DSL
    trigger = re.search(r'TRIGGER:\s*(.*)', content, re.IGNORECASE)
    filter_ = re.search(r'FILTER:\s*(.*)', content, re.IGNORECASE)
    entry = re.search(r'ENTRY:\s*(.*)', content, re.IGNORECASE)
    exit_ = re.search(r'EXIT:\s*(.*)', content, re.IGNORECASE)
    
    final_entry = ""
    if trigger and filter_:
        final_entry = f"({trigger.group(1).strip()}) and ({filter_.group(1).strip()})"
    elif entry:
        final_entry = entry.group(1).strip()
    
    final_exit = exit_.group(1).strip() if exit_ else "False"
    
    # Build a cleaner ticker universe so the backtester doesn't waste workers on stale symbols.
    conn = db._get_connection()
    universe_query = """
        WITH ranked AS (
            SELECT
                ticker,
                date,
                volume,
                ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
            FROM etf_data
        ),
        agg AS (
            SELECT
                ticker,
                MAX(date) AS last_date,
                COUNT(*) AS total_rows,
                SUM(CASE WHEN volume > 0 THEN 1 ELSE 0 END) AS nonzero_volume_rows,
                SUM(CASE WHEN rn <= 30 THEN 1 ELSE 0 END) AS recent_rows,
                SUM(CASE WHEN rn <= 30 AND volume = 0 THEN 1 ELSE 0 END) AS recent_zero_volume_rows
            FROM ranked
            GROUP BY ticker
        )
        SELECT ticker
        FROM agg
        WHERE total_rows >= 50
          AND nonzero_volume_rows >= 10
          AND recent_rows >= 10
          AND recent_zero_volume_rows < 2
          AND last_date >= date('now', '-180 day')
    """
    universe_df = pd.read_sql_query(universe_query, conn)
    tickers = universe_df['ticker'].tolist()
    
    # Run backtest for current status
    bt = Backtester()
    results = bt.run_parallel_backtest(
        tickers, 
        bt.scripted_strategy,
        days=200, 
        strategy_kwargs={"entry_script": final_entry, "exit_script": final_exit}
    )
    
    # Filter for currently active signals (in a position or just triggered)
    matches = []
    errors = []
    for res in results:
        if not res: continue
        
        ticker = res.get('ticker', 'UNKNOWN')
        if "error" in res:
            errors.append({"ticker": ticker, "error": res["error"]})
            continue
        
        df = res.get('df')
        if df is None or df.empty:
            errors.append({"ticker": ticker, "error": "No data or empty strategy result"})
            continue
        
        # Align with CLI behavior: a match is an active entry signal on the latest bar.
        try:
            last_row = df.iloc[-1]
            latest_signal = last_row.get('signal', last_row.get('Signal', 0))
            has_latest_entry = latest_signal == 1
            
            # Additional metadata for the UI
            prev_row = df.iloc[-2] if len(df) > 1 else last_row
            
            if has_latest_entry:
                # Handle possible column name variations (database vs dataframe)
                close_val = float(last_row['close']) if 'close' in last_row else float(last_row.get('Close', 0))
                vol_val = float(last_row['volume']) if 'volume' in last_row else float(last_row.get('Volume', 0))
                prev_close = float(prev_row['close']) if 'close' in prev_row else float(prev_row.get('Close', 0))
                change_pct = ((close_val / prev_close) - 1) * 100 if prev_close else 0
                
                matches.append({
                    "ticker": ticker,
                    "close": close_val,
                    "volume": vol_val,
                    "status": "Entry Signal",
                    "return_pct": float(res.get('total_return_pct', 0)),
                    "change_pct": change_pct
                })
        except Exception as e:
            errors.append({"ticker": ticker, "error": str(e)})
            
    # Sort by volume
    matches = sorted(matches, key=lambda x: x['volume'], reverse=True)
    
    # Return matched ETFs along with errors for the UI
    return {
        "matches": matches,
        "errors": errors[:50],  # Limit errors returned to UI
        "total_errors": len(errors),
        "total_candidates": len(tickers)
    }

@app.get("/api/chart/{ticker}")
async def get_chart(ticker: str, days: int = 365*2):
    """Generate and return an interactive chart for a ticker. Fetches if missing."""
    db = get_db()
    ticker = ticker.upper()
    
    # 1. Try to get data from database
    conn = db._get_connection()
    query = f"SELECT * FROM etf_data WHERE ticker = ? ORDER BY date DESC LIMIT {days}"
    df = pd.read_sql_query(query, conn, params=(ticker,))
    
    # 2. If data is missing or too sparse (less than 100 days for indicators), fetch it!
    # Increased minimum requirement to 100 days to ensure enough lookback for EMA50 and ATR
    if df.empty or len(df) < 100:
        print(f"Cache miss for {ticker} (or insufficient data, count={len(df)}). Fetching from Yahoo Finance...")
        try:
            # Fetch fresh data - Updated to use correct method name: fetch_historical_data
            # Force at least 365 days of data for high resolution indicators
            fetched_df = fetcher.fetch_historical_data(ticker, days=max(days, 365))
            if not fetched_df.empty:
                print(f"Fetched {len(fetched_df)} rows for {ticker}. Processing indicators...")
                # Add indicators before storing
                processed_df = add_indicators(fetched_df)
                
                # Check if supertrend was calculated
                has_st = not processed_df['Supertrend'].isna().all() if 'Supertrend' in processed_df.columns else False
                print(f"Indicator processing complete. Supertrend calculated: {has_st}")
                
                # Store in DB for next time
                for _, row in processed_df.iterrows():
                    db.insert_etf_data(
                        ticker=ticker,
                        date=row['Date'].strftime('%Y-%m-%d'),
                        open_price=row['Open'],
                        high=row['High'],
                        low=row['Low'],
                        close=row['Close'],
                        volume=int(row['Volume']),
                        ema_50=row.get('EMA_50'),
                        supertrend=row.get('Supertrend'),
                        st_upper=row.get('ST_Upper'),
                        st_lower=row.get('ST_Lower')
                    )
                
                # Use the new data for the plot
                df = processed_df.sort_values('Date').tail(days)
        except Exception as e:
            print(f"Failed to fetch {ticker} on demand: {e}")
            # Instead of crashing, let's return a specific error that the UI can catch
            raise HTTPException(status_code=404, detail=f"Data fetch failed for {ticker}: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for ticker {ticker}")
        
    df = df.sort_values('date' if 'date' in df.columns else 'Date')
    # Match the plotter's expected column names (normalized)
    rename_cols = {
        'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 
        'close': 'Close', 'volume': 'Volume', 'ema_50': 'EMA_50', 
        'supertrend': 'Supertrend', 'st_upper': 'ST_Upper', 'st_lower': 'ST_Lower',
        'signal': 'Signal'
    }
    # Direct rename to ensure uppercase matching for plotter
    df = df.rename(columns=rename_cols)
    
    # Check if we have the critical columns after normalization
    required = ['Date', 'Close', 'Open', 'High', 'Low']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        print(f"Normalizing column names from DB for {ticker}. Missing: {missing}. Available: {df.columns.tolist()}")
        # Check if we have 'open_price' instead of 'open' (some legacy code used 'open_price')
        if 'open_price' in df.columns and 'Open' not in df.columns:
            df = df.rename(columns={'open_price': 'Open'})
            missing = [c for c in required if c not in df.columns]

    if missing:
        # If still missing, we might have a data integrity issue
        print(f"CRITICAL: {ticker} is missing required columns {missing} for plotting.")
        raise HTTPException(status_code=500, detail=f"Database schema mismatch for {ticker}. Missing {missing}")
    
    plotter = InteractivePlotter()
    try:
        fig = plotter.create_plot(df, ticker)
        # Fastapi JSONResponse or direct dict return will handle this.
        # But we need to ensure it's a DICT, not a JSON string, 
        # because the frontend is now expecting the un-wrapped object.
        import json
        fig_json = fig.to_json()
        fig_dict = json.loads(fig_json)
        return {
            "ticker": ticker, 
            "figure": fig_json, 
            "data": fig_dict.get("data", []), 
            "layout": fig_dict.get("layout", {})
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Plotter failed for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Plot generation failed: {str(e)}")

@app.get("/api/screen")
async def screen():
    """Run a quick dynamic screen based on parameters."""
    db = get_db()
    conn = db._get_connection()
    query = """
        SELECT ticker, close, volume, supertrend, st_lower
        FROM etf_data 
        WHERE date = (SELECT MAX(date) FROM etf_data)
        AND close > st_lower
        ORDER BY volume DESC
        LIMIT 50
    """
    try:
        df = pd.read_sql_query(query, conn)
        return df.to_dict(orient='records')
    except Exception as e:
        return []

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app_fast:app", host="127.0.0.1", port=5000, reload=True)
