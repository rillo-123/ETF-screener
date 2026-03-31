from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
from pathlib import Path
from ETF_screener.database import ETFDatabase
from ETF_screener.plotter_plotly import InteractivePlotter
from ETF_screener.indicators import add_indicators

app = Flask(__name__)

def get_db():
    """Get a thread-safe database connection."""
    return ETFDatabase()

@app.route('/')
def index():
    """Main dashboard page."""
    db = get_db()
    conn = db._get_connection()
    tickers = pd.read_sql_query("SELECT DISTINCT ticker FROM etf_data ORDER BY ticker", conn)['ticker'].tolist()
    return render_template('index.html', tickers=tickers)

@app.route('/api/chart/<ticker>')
def get_chart(ticker):
    """Generate and return an interactive chart for a ticker."""
    db = get_db()
    days = request.args.get('days', 365*2, type=int)
    strategy = request.args.get('strategy', default=None, type=str)
    dsl_content = request.args.get('dsl_content', default=None, type=str)
    
    # Get data from database
    conn = db._get_connection()
    query = f"SELECT * FROM etf_data WHERE ticker = ? ORDER BY date DESC LIMIT {days}"
    df = pd.read_sql_query(query, conn, params=(ticker.upper(),))
    
    if df.empty:
        return jsonify({"error": "No data found"}), 404
        
    df = df.sort_values('date')
    # Match the plotter's expected column names
    df = df.rename(columns={
        'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 
        'close': 'Close', 'volume': 'Volume', 'ema_50': 'EMA_50', 
        'supertrend': 'Supertrend', 'st_upper': 'ST_Upper', 'st_lower': 'ST_Lower'
    })
    
    strategy_content = ""
    if dsl_content:
        strategy_content = dsl_content
    elif strategy:
        strat_path = Path("strategies") / f"{strategy}.dsl"
        if strat_path.exists():
            strategy_content = strat_path.read_text(encoding='utf-8')

    plotter = InteractivePlotter()
    fig = plotter.create_plot(df, ticker.upper(), strategy_content=strategy_content)
    
    # Return figure as JSON for Plotly.js to render
    return fig.to_json()

@app.route('/api/screen')
def screen():
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
    df = pd.read_sql_query(query, conn)
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
