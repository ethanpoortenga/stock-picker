"""
Backtest the stock picking strategy over historical data.

Simulates running the picker each trading day and checks if the pick
gained 1%+ the following day.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from universe import get_sp500_tickers
from picker import compute_rsi, score_stock


def run_backtest(start_date: str = "2024-06-01", end_date: str = "2025-12-31"):
    """Run backtest over date range."""
    tickers = get_sp500_tickers()
    print(f"Running backtest from {start_date} to {end_date}")
    print(f"Universe: {len(tickers)} S&P 500 stocks")

    # Download all data for the full period (plus lookback buffer)
    buffer_start = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=150)).strftime("%Y-%m-%d")
    fetch_end = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=10)).strftime("%Y-%m-%d")

    print("Downloading historical data (this may take a minute)...")
    all_data = yf.download(
        tickers,
        start=buffer_start,
        end=fetch_end,
        group_by="ticker",
        progress=True,
        threads=True,
    )
    print("Data downloaded.")

    # Get trading days in our backtest range
    # Use SPY as reference for trading days
    spy_data = yf.download("SPY", start=start_date, end=end_date, progress=False)
    trading_days = spy_data.index.strftime("%Y-%m-%d").tolist()

    results = []
    wins = 0
    losses = 0
    total_return = 0

    for i, day in enumerate(trading_days[:-1]):  # skip last day (need next day for result)
        day_dt = datetime.strptime(day, "%Y-%m-%d")
        next_day = trading_days[i + 1]

        # Score all stocks using data up to this day
        scores = {}
        for ticker in tickers:
            try:
                if ticker not in all_data.columns.get_level_values(0):
                    continue
                hist = all_data[ticker].loc[:day].dropna()
                s = score_stock(hist)
                if s is not None and s > 0:
                    scores[ticker] = s
            except Exception:
                continue

        if not scores:
            continue

        best_ticker = max(scores, key=scores.get)

        # Get the result
        try:
            ticker_data = all_data[best_ticker].dropna()
            day_idx = ticker_data.index.get_indexer([pd.Timestamp(day)], method="nearest")[0]
            next_idx = ticker_data.index.get_indexer([pd.Timestamp(next_day)], method="nearest")[0]

            if day_idx >= len(ticker_data) - 1 or next_idx <= day_idx:
                continue

            pick_price = float(ticker_data["Close"].iloc[day_idx])
            next_price = float(ticker_data["Close"].iloc[next_idx])
            ret = ((next_price / pick_price) - 1) * 100

            is_win = ret >= 1.0
            if is_win:
                wins += 1
            else:
                losses += 1
            total_return += ret

            result = {
                "date": day,
                "ticker": best_ticker,
                "price_at_pick": round(pick_price, 2),
                "score": round(scores[best_ticker], 1),
                "next_day_close": round(next_price, 2),
                "actual_return": round(ret, 2),
                "result": "win" if is_win else "loss",
            }
            results.append(result)

            status = "WIN" if is_win else "loss"
            if (i + 1) % 20 == 0 or i < 5:
                print(f"  [{i+1}/{len(trading_days)-1}] {day} {best_ticker}: {ret:+.2f}% ({status})")

        except Exception:
            continue

    # Calculate stats
    total_picks = wins + losses
    win_rate = (wins / total_picks * 100) if total_picks > 0 else 0
    avg_return = total_return / total_picks if total_picks > 0 else 0
    returns = [r["actual_return"] for r in results]
    sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if returns and np.std(returns) > 0 else 0

    stats = {
        "start_date": start_date,
        "end_date": end_date,
        "total_picks": total_picks,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "avg_daily_return": round(avg_return, 2),
        "total_return": round(total_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "best_pick": max(results, key=lambda x: x["actual_return"]) if results else None,
        "worst_pick": min(results, key=lambda x: x["actual_return"]) if results else None,
        "picks": results,
    }

    print(f"\n{'='*50}")
    print(f"BACKTEST RESULTS: {start_date} to {end_date}")
    print(f"{'='*50}")
    print(f"Total picks: {total_picks}")
    print(f"Wins (>=1%): {wins} | Losses: {losses}")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Avg daily return: {avg_return:.2f}%")
    print(f"Total return: {total_return:.2f}%")
    print(f"Sharpe ratio (annualized): {sharpe:.2f}")

    if stats["best_pick"]:
        bp = stats["best_pick"]
        print(f"Best: {bp['ticker']} on {bp['date']} ({bp['actual_return']:+.2f}%)")
    if stats["worst_pick"]:
        wp = stats["worst_pick"]
        print(f"Worst: {wp['ticker']} on {wp['date']} ({wp['actual_return']:+.2f}%)")

    # Save results
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "backtest.json").write_text(json.dumps(stats, indent=2))
    print(f"\nResults saved to data/backtest.json")

    return stats


if __name__ == "__main__":
    run_backtest()
