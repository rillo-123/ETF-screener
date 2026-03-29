''' Backtesting engine for ETF trading strategies. '''
import pandas as pd
import numpy as np
import re, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Callable, Optional

from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import (
    calculate_rsi, calculate_ema, calculate_supertrend, 
    calculate_adx, calculate_macd, calculate_stochastic, calculate_rsi_ema,
    calculate_stoch_rsi, calculate_linreg_slope, calculate_tsi
)
from ETF_screener.strategy_manager import CachedStrategyManager

def _worker_run_remote(ticker, db_path, initial_capital, commission, slippage_pct, base_strategy, days, indicators_setup, kwargs):
    bt = Backtester(db_path=db_path, initial_capital=initial_capital, commission=commission, slippage_pct=slippage_pct)
    return bt.run_strategy(ticker=ticker, strategy_func=base_strategy, days=days, indicators_setup=indicators_setup, strategy_kwargs=kwargs)

class Backtester:
    def __init__(self, db_path="data/etfs.db", initial_capital=10000.0, commission=5.0, slippage_pct=0.1):
        self.db_path = db_path
        # self.db = ETFDatabase(db_path) # Removed to allow pickling for multiprocessing
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage_pct = slippage_pct

    @property
    def db(self):
        """Lazy loader for database to avoid pickling issues in parallel mode."""
        return ETFDatabase(self.db_path)

    @db.setter
    def db(self, value):
        """Setter for testing/mocking."""
        if hasattr(value, 'db_path'):
            self.db_path = value.db_path
        # We don't store the connection object itself to maintain pickling compatibility

    def run_strategy(self, ticker, strategy_func, days=365, indicators_setup=None, strategy_kwargs=None):
        db = self.db
        manager = CachedStrategyManager(db)
        
        # This will hold the original metadata from the strategy function (e.g. b_em, b_r)
        strategy_result_meta = {}

        # Determine if we should look for or save to a parquet cache
        # Cache key is based on ticker and strategy name if scripted
        cache_dir = Path("data/cache")
        cache_path = None
        strategy_name = "unknown"
        if strategy_kwargs and 'entry_script' in strategy_kwargs:
            import hashlib
            # Create a unique hash for the strategy logic
            strat_hash = hashlib.md5(f"{strategy_kwargs.get('entry_script')}_{strategy_kwargs.get('exit_script')}".encode()).hexdigest()[:8]
            strategy_name = f"dsl_{strat_hash}"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / f"{ticker}_{strategy_name}_{days}.parquet"

        # Try loading from cache first
        if cache_path and cache_path.exists():
            try:
                df = pd.read_parquet(cache_path)
                # Verify it has enough data
                if df is None or df.empty:
                    df = None
            except Exception as e:
                print(f"Warning: Failed to read cache {cache_path}: {e}")
                df = None
        else:
            df = None

        if df is None:
            if indicators_setup:
                df = manager.prepare_data(ticker, indicators_setup, days=days)
            else:
                df = db.get_ticker_data(ticker, days=days)
            
            if df is None or df.empty: return {"error": f"No data for {ticker}"}
            df['Date'] = pd.to_datetime(df.get('Date', df.get('date')))
            df = df.sort_values('Date').reset_index(drop=True)
            price_col = 'Close' if 'Close' in df else 'close'
            kwargs = strategy_kwargs or {}
            
            is_scripted = False
            if hasattr(strategy_func, '__name__') and strategy_func.__name__ == 'scripted_strategy':
                is_scripted = True
            elif hasattr(strategy_func, '__func__') and strategy_func.__func__.__name__ == 'scripted_strategy':
                is_scripted = True

            if is_scripted:
                res = strategy_func(df, ticker=ticker, **kwargs)
            else:
                res = strategy_func(df, **kwargs)
                
            if res is None: return {"error": "Strategy function returned None"}
            
            # Store the original result metadata (like b_em, b_r) for later merging
            if isinstance(res, dict):
                if "df" not in res or res["df"] is None or res["df"].empty:
                    return {"error": "Empty dataframe after strategy run"}
                df = res["df"]
                strategy_result_meta = res
            else:
                if res.empty: return {"error": "Empty dataframe after strategy run"}
                df = res
                strategy_result_meta = {"df": df}
                
            # If we calculated signals, save them to parquet for next time
            if cache_path and not df.empty:
                try:
                    df.to_parquet(cache_path, compression='snappy')
                except Exception as e:
                    print(f"Warning: Failed to save cache {cache_path}: {e}")
            
        if 'Signal' in df.columns and 'signal' not in df: df['signal'] = df['Signal']
        if 'signal' not in df.columns: return {"error": "No signal col"}
        
        capital = self.initial_capital; position = 0; trades = []; equity = [capital]
        max_equity = self.initial_capital; mdd = 0
        price_col = 'Close' if 'Close' in df else 'close'
        for i in range(len(df)):
            price = df.iloc[i][price_col]; signal = df.iloc[i]["signal"]
            current_equity = capital + position*(price)
            equity.append(current_equity)
            
            # Simple Max Drawdown calculation
            if current_equity > max_equity: max_equity = current_equity
            dd = (max_equity - current_equity) / max_equity if max_equity > 0 else 0
            if dd > mdd: mdd = dd

            if signal == 1 and position == 0:
                buy_price = price * (1 + self.slippage_pct/100); capital -= self.commission; position = capital/buy_price; capital = 0
                trades.append({'type':'BUY','date':df.iloc[i]['Date'],'price':buy_price})
                df.at[i, 'Signal'] = 1 # Update signal column to match true trade execution
            elif signal == -1 and position > 0:
                sell_price = price * (1 - self.slippage_pct/100); capital = (position*sell_price) - self.commission; position = 0;
                trades.append({'type':'SELL','date':df.iloc[i]['Date'],'price':sell_price,'profit':(sell_price-trades[-1]['price'])/trades[-1]['price']})
                df.at[i, 'Signal'] = -1 # Update signal column to match true trade execution
            else:
                df.at[i, 'Signal'] = 0
        
        final_val = capital + position*(df.iloc[-1][price_col])
        closed_trades = [t for t in trades if t['type']=='SELL']
        win_rate = 0
        profit_factor = 0
        sharpe = 0
        
        # Calculate Sharpe Ratio from equity curve
        equity_series = pd.Series(equity)
        if len(equity_series) > 1:
            daily_returns = equity_series.pct_change(fill_method=None).dropna()
            if daily_returns.std() > 0:
                # Annualized Sharpe (assuming 252 trading days)
                sharpe = round((daily_returns.mean() / daily_returns.std()) * np.sqrt(252), 2)

        if closed_trades:
            wins = [t for t in closed_trades if t['profit'] > 0]
            win_rate = round((len(wins) / len(closed_trades)) * 100, 2)
            
            gross_profits = sum([t['profit'] for t in closed_trades if t['profit'] > 0])
            gross_losses = abs(sum([t['profit'] for t in closed_trades if t['profit'] < 0]))
            profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 0 else (round(gross_profits, 2) if gross_profits > 0 else 0)
            
        results = {
            'ticker': ticker,
            'final_value': final_val, 
            'total_return_pct': round(((final_val - self.initial_capital) / self.initial_capital) * 100, 2), 
            'num_trades': len(closed_trades),
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': round(mdd * 100, 2),
            'df': df
        }
        
        # Merge metadata from strategy result if available (like b_em, b_r)
        if isinstance(strategy_result_meta, dict):
            for k, v in strategy_result_meta.items():
                if k not in ['df']: # Don't overwrite the main df with metadata df
                    results[k] = v
                    
        return results
    
    def scripted_strategy(self, df, ticker, entry_script, exit_script, manager=None, additional_indicators=None):
        if manager is None:
            db = ETFDatabase(self.db_path)
            manager = CachedStrategyManager(db)
        
        df_eval = df.copy(); df_eval.columns = [c.lower() for c in df_eval.columns]
        # Clean the copy to avoid duplicate labels error when we start adding indicators
        df_eval = df_eval.loc[:, ~df_eval.columns.duplicated()]
        
        def ensure_indicator(c):
            # Strip trailing _d[number] for indicator lookup
            base_c = re.sub(r'_d\d+$', '', c)
            if base_c not in df_eval.columns:
                if re.match(r'ema_\d+', base_c): df_eval[base_c] = manager.get_indicator(df, ticker, calculate_ema, base_c, period=int(base_c.split("_")[1]))
                elif re.match(r'rsi_\d+', base_c): df_eval[base_c] = manager.get_indicator(df, ticker, calculate_rsi, base_c, period=int(base_c.split("_")[1]))
                elif re.match(r'rsi_ema_\d+_\d+', base_c): 
                    # rsi_ema_14_10
                    parts = base_c.split("_")
                    df_eval[base_c] = manager.get_indicator(df, ticker, calculate_rsi_ema, base_c, rsi_period=int(parts[2]), ema_period=int(parts[3]))
                elif re.match(r'supertrend_\d+_\d+', base_c) or re.match(r'st_\d+_\d+', base_c):
                    # st_10_4 or supertrend_10_4
                    parts = base_c.split("_")
                    p = int(parts[1]); m = float(parts[2])
                    df_eval[base_c] = manager.get_indicator(df, ticker, calculate_supertrend, f"supertrend_{p}_{m}", period=p, multiplier=m)
                elif base_c=="adx": df_eval[base_c] = manager.get_indicator(df, ticker, calculate_adx, base_c, period=14)
                elif base_c in set(["st", "supertrend"]): df_eval[base_c] = manager.get_indicator(df, ticker, calculate_supertrend, "supertrend_10_3.0", period=10, multiplier=3.0)
                elif base_c in ["macd", "macd_signal", "macd_hist"]:
                    res = manager.get_indicator(df, ticker, calculate_macd, "macd_all", fast=12, slow=26, signal=9)
                    if isinstance(res, tuple) and len(res) == 3:
                        df_eval["macd"], df_eval["macd_signal"], df_eval["macd_hist"] = res
                    elif not isinstance(res, tuple):
                        # If we accidentally have a single-return cache from earlier
                        df_eval["macd"] = res
                elif base_c in ["stoch_k", "stoch_d"]:
                    res = manager.get_indicator(df, ticker, calculate_stochastic, "stoch_all", k_period=14, d_period=3)
                    if isinstance(res, tuple) and len(res) == 2:
                        df_eval["stoch_k"], df_eval["stoch_d"] = res[0], res[1]
                elif base_c in ["stoch_rsi_k", "stoch_rsi_d"]:
                    res = manager.get_indicator(df, ticker, calculate_stoch_rsi, "stoch_rsi_all", rsi_period=14, stoch_period=14, k_period=3, d_period=3)
                    if isinstance(res, tuple) and len(res) == 2:
                        df_eval["stoch_rsi_k"], df_eval["stoch_rsi_d"] = res[0], res[1]
                elif base_c in ["tsi", "tsi_signal"]:
                    res = manager.get_indicator(df, ticker, calculate_tsi, "tsi_all", long=25, short=13, signal=13)
                    if isinstance(res, tuple) and len(res) == 2:
                        df_eval["tsi"], df_eval["tsi_signal"] = res[0], res[1]
                elif "_slope" in base_c:
                    # Capture ema_10_slope, rsi_14_slope, etc.
                    target_ind = base_c.replace("_slope", "")
                    ensure_indicator(target_ind)
                    if target_ind in df_eval.columns:
                        # Use LinReg Slope if its a noisy signal, otherwise simple diff
                        if any(x in target_ind for x in ["rsi", "stoch", "macd", "close"]):
                            # Use 7-day window for "best fit" slope
                            df_eval[base_c] = manager.get_indicator(df, ticker, calculate_linreg_slope, f"{target_ind}_lr_slope", series=df_eval[target_ind], period=7)
                        else:
                            # Use simple diff for smoother EMAs to be more responsive/accurate to crossing zero
                            df_eval[base_c] = df_eval[target_ind].diff().fillna(0)
                elif base_c == "vol_ema_20":
                    # Simple volume smoothing
                    df_eval[base_c] = df_eval['volume'].ewm(span=20, adjust=False).mean()
                elif base_c == "st_10_4_is_green":
                    # Hardcoded support for the user's current favorite indicator
                    res = manager.get_indicator(df, ticker, calculate_supertrend, "supertrend_10_4.0", period=10, multiplier=4.0)
                    if isinstance(res, tuple):
                        _, _, lb = res
                    else:
                        lb = None
                    if lb is not None:
                        df_eval[base_c] = (df_eval['close'] > lb).astype(float)
                    else:
                        df_eval[base_c] = 0.0
            
            # If it's a delayed primitive (e.g., ema_10_d1), create the shifted column
            # Special case for cross_up(a, b) and cross_down(a, b) which use _d1
            if c != base_c and c not in df_eval.columns:
                if base_c in df_eval.columns:
                    delay_match = re.search(r'_d(\d+)$', c)
                    if delay_match:
                        delay = int(delay_match.group(1))
                        df_eval[c] = df_eval[base_c].shift(delay)
            elif c == base_c and f"{c}_d1" not in df_eval.columns:
                # Always ensure _d1 exists for cross_up/down support if the base indicator is asked for
                df_eval[f"{c}_d1"] = df_eval[c].shift(1)

        def p(s):
            # 1. Expand aliases FIRST
            def sub_st(st_m): 
                pv, mv, sv = st_m.group(1), st_m.group(2), st_m.group(3)
                ind = f"st_{pv}_{mv}"
                return f" (close > {ind}) " if "green" in sv else f" (close < {ind}) "
            
            # Record literal aliases before any mangling
            s = re.sub(r'\b(?:st|supertrend)_(\d+)_(\d+)_is_(green|red)\b', sub_st, s)
            s = s.replace('st_is_green', ' (close > supertrend) ').replace('st_is_red', ' (close < supertrend) ')

            # 2. Shifting helper
            def _shift(expr, delay):
                def repl(m):
                    word = m.group(1).lower()
                    if word in ['and', 'or', 'not', 'true', 'false', 'cross_up', 'cross_down', 'was_true']: return word
                    if word.isdigit(): return word
                    # Don't double-suffix if it already has one
                    if f"_d{delay}" in word: return word
                    return f"{word}_d{delay}"
                return re.sub(r'([a-z][a-z0-9_]*)\b', repl, expr)

            # 3. Expansion helpers
            def handle_cross(m):
                content = m.group(0).split('(', 1)[1].rsplit(')', 1)[0]
                mode = 'cross_up' if 'cross_up' in m.group(0) else 'cross_down'
                parts = content.split(',', 1)
                a, b = parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "0.5")
                ad, bd = _shift(a, 1), _shift(b, 1)
                # Boolean logic to avoid pd.eval scalar error (bitwise ops on bools)
                an, ap = (f"(({a}) >= 1.0)", f"(({ad}) >= 1.0)") if any(c in a for c in '><=') else (a, ad)
                bn, bp = (f"(({b}) >= 1.0)", f"(({bd}) >= 1.0)") if any(c in b for c in '><=') else (b, bd)
                if mode == 'cross_up': return f"({an} & ~{ap})"
                return f"(~{an} & {ap})"

            def handle_wt(m):
                content = m.group(0).split('(', 1)[1].rsplit(')', 1)[0]
                parts = content.split(',', 1)
                e, d = parts[0].strip(), parts[1].strip()
                # Check for nested logic or simple name
                return f"({_shift(e, int(d))})"

            s = re.sub(r'\bcross_up\s*\((?:[^()]+|\([^()]*\))+\)', handle_cross, s)
            s = re.sub(r'\bcross_down\s*\((?:[^()]+|\([^()]*\))+\)', handle_cross, s)
            s = re.sub(r'\bwas_true\s*\((?:[^()]+|\([^()]*\))+\)', handle_wt, s)

            # 4. Final Cleanup
            s = s.lower()
            # Replace 'and'/'or' with '&'/'|' but only if not part of a symbol
            s = re.sub(r'\band\b', ' & ', s).replace('  ', ' ')
            s = re.sub(r'\bor\b', ' | ', s).replace('  ', ' ')
            
            # 5. Comparison Normalization
            # Ensure we wrap comparison expressions in parentheses for bitwise order of operations.
            # This avoids 'BoolOp' errors in pd.eval engine='python'
            # Note: We look for [symbol/number] [op] [symbol/number]
            comp_pat = r'([a-z0-9_][a-z0-9_.]*(?:\s*[<>!=]=?|>=|<=)\s*[a-z0-9._]+)'
            # But don't wrap if already wrapped
            def wrap_comp(m):
                expr = m.group(1).strip()
                # If it's already got a paren on either side in the full string, skip? 
                # Better: wrap everything, pd.eval handles nested parens fine.
                return f"({expr})"
            
            s = re.sub(comp_pat, wrap_comp, s)
            
            # Literals
            s = re.sub(r'\b(\d+(?:\.\d+)?)([km])\b', lambda m: str(int(float(m.group(1)) * (1000 if m.group(2)=='k' else 1000000))), s)

            # Manglings - BE CAREFUL HERE. We don't want to mangle st_10_4 into st_10_d1
            # Only mangle [word]_d[N]_d[M] or simple [num]_d[N]
            s = re.sub(r'(\d+\.\d+)_d\d+', r'\1', s)
            s = s.replace('c(lose', 'close').replace('h(igh', 'high').replace('l(ow', 'low').replace('o(pen', 'open')
            
            # Standard comparison wrapping (adds parens around simple comparisons)
            # This is risky for complex DSL names. Let's skip it if we have underscores in both sides
            # comp_regex = r'\b(?!(?:and|or|not|&|\|)\b)([a-z][a-z0-9._]*\s*(?:[<>!=]+|>=|<=)\s*[0-9.a-z_]+)\b'
            # s = re.sub(comp_regex, r'(\1)', s)
            
            # Balance check / space normalization
            s = s.replace('  ', ' ').strip()
            return s
        
        # Pre-process scripts to handle cross_up/down and suffixes
        e_s = p(entry_script); r_s = p(exit_script)
        
        # Discover all symbols including those with _d[N] suffixes
        symbols_to_ensure = set(re.findall(r'[a-z][a-z_0-9]*', e_s + " " + r_s))
        
        # Sort so we calculate base indicators BEFORE their delayed versions
        # Ensure we capture st_10_4 if it appeared in the translation
        for c in sorted(list(symbols_to_ensure), key=lambda x: '_d' in x):
            if c in ['and','or','supertrend','close','open','high','low','volume','date','st']:
                continue
            try:
                ensure_indicator(c)
            except KeyError:
                pass
        
        # Double check for common supertrend patterns that might have been expanded
        for c in list(symbols_to_ensure):
            if re.match(r'st_\d+_\d+', c) and c not in df_eval.columns:
                ensure_indicator(c)
        
        # Also ensure any additional indicators needed (e.g. for ribbons) are calculated.
        if additional_indicators:
            for c in additional_indicators:
                try:
                    ensure_indicator(c.lower())
                except KeyError:
                    pass
        
        try:
            # We use engine='python' and parser='python' to allow python-style keywords 
            # and avoid conflicts with ticker symbols that are also pandas/numexpr keywords.
            # However, we MUST use bitwise operators (&, |) for series logic 
            # as 'and'/'or' are not supported for Series evaluation in pd.eval().
            print(f"DEBUG_EXPR_ENTRY: {e_s}")
            b_em = df_eval.eval(e_s, engine='python', parser='python')
            print(f"DEBUG_EXPR_EXIT: {r_s}")
            b_r = df_eval.eval(r_s, engine='python', parser='python')
        except Exception as e:
            # Output the transformed scripts to identify EXACTLY which character is failing
            print(f"ERROR_IN_EVAL: {e}")
            print(f"TRANSFORMED ENTRY: {e_s}")
            print(f"TRANSFORMED EXIT:  {r_s}")
            import traceback
            traceback.print_exc()
            return None
            
        # Core alignment
        df = df.copy()
        # Transfer all newly calculated indicators from df_eval back to df
        for col in df_eval.columns:
            if col not in df.columns:
                df[col] = df_eval[col]
        df['signal'] = 0
        df.loc[b_em == True, 'signal'] = 1
        df.loc[b_r == True, 'signal'] = -1
        return {"df": df}

    def run_parallel_backtest(self, tickers, base_strategy, days=365, indicators_setup=None, strategy_kwargs=None, max_workers=None):
        import concurrent.futures
        from tqdm import tqdm
        results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            task_dict = {executor.submit(_worker_run_remote, t, self.db_path, self.initial_capital, self.commission, self.slippage_pct, base_strategy, days, indicators_setup, strategy_kwargs): t for t in tickers}
            with tqdm(total=len(tickers), desc="Discovery", unit="ticker", leave=False) as pbar:
                for future in concurrent.futures.as_completed(task_dict):
                    ticker = task_dict[future]
                    pbar.set_postfix_str(f"Processing: {ticker}")
                    results.append(future.result())
                    pbar.update(1)
        return results

def rsi_strategy(df, p=14, os=30):
    rsi=calculate_rsi(df, p); df["signal"]=0; df.loc[rsi<os,"signal"]=1; return df
def ema_cross_strategy(df, f=20, s=50):
    f_e = calculate_ema(df, f); s_e = calculate_ema(df, s); df["signal"] = 0
    df.loc[(f_e > s_e) & (f_e.shift(1) <= s_e.shift(1)), "signal"] = 1
    df.loc[(f_e < s_e) & (f_e.shift(1) >= s_e.shift(1)), "signal"] = -1
    return df
def ema_supertrend_strategy(df, f=10, s=30, st_p=10, st_m=3.0):
    price = "Close" if "Close" in df else "close"
    f_e = calculate_ema(df[price], f); s_e = calculate_ema(df[price], s)
    st = calculate_supertrend(df, st_p, st_m)[0]
    df["signal"] = 0
    df.loc[(f_e > s_e) & (df[price] > st), "signal"] = 1
    df.loc[(f_e < s_e) | (df[price] < st), "signal"] = -1
    return df
