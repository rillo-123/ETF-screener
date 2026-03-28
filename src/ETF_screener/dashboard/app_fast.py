import json
import pandas as pd
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from ETF_screener.database import ETFDatabase
from ETF_screener.plotter_plotly import InteractivePlotter
from ETF_screener.yfinance_fetcher import YFinanceFetcher
from ETF_screener.indicators import add_indicators

app = FastAPI(title="ETF Discovery Lab API")
fetcher = YFinanceFetcher() # For on-demand fetching

# Setup templates and static files
# We can keep the same template files as Flask (Jinja2 is compatible)
templates = Jinja2Templates(directory="src/ETF_screener/dashboard/templates")
# app.mount("/static", StaticFiles(directory="src/ETF_screener/dashboard/static"), name="static")

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
    
    return templates.TemplateResponse(
        request=request, name="index.html", context={"tickers": tickers}
    )

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
        return json.loads(fig.to_json())
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
