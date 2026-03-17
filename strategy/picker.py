"""
Stock Picker Strategy: Momentum + Mean Reversion

Scores S&P 500 stocks daily and picks the one most likely to gain 1%+ next day.

Signals used:
1. RSI(14) in the 30-45 range (oversold but not crashing)
2. Price above 50-day SMA (uptrend)
3. 5-day return slightly negative (short-term dip in uptrend)
4. Volume spike (above 20-day avg volume) — institutional interest
5. 20-day momentum positive (medium-term trend intact)
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from universe import get_sp500_tickers


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def score_stock(hist: pd.DataFrame) -> float | None:
    """Score a stock based on our signals. Higher = better pick."""
    if hist is None or len(hist) < 60:
        return None

    close = hist["Close"]
    volume = hist["Volume"]

    # Compute indicators
    rsi = compute_rsi(close).iloc[-1]
    sma_50 = close.rolling(50).mean().iloc[-1]
    sma_20 = close.rolling(20).mean().iloc[-1]
    current_price = close.iloc[-1]
    ret_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0
    ret_20d = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
    avg_volume = volume.rolling(20).mean().iloc[-1]
    current_volume = volume.iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

    score = 0.0

    # Signal 1: RSI in sweet spot (30-45) — oversold but recovering
    if 30 <= rsi <= 45:
        score += 30
    elif 25 <= rsi < 30:
        score += 15  # very oversold, riskier
    elif 45 < rsi <= 55:
        score += 10  # neutral

    # Signal 2: Price above 50-day SMA (uptrend)
    if current_price > sma_50:
        score += 20

    # Signal 3: Short-term dip (-3% to -0.5% over 5 days)
    if -3 <= ret_5d <= -0.5:
        score += 25
    elif -5 <= ret_5d < -3:
        score += 10

    # Signal 4: Volume spike
    if volume_ratio > 1.5:
        score += 15
    elif volume_ratio > 1.2:
        score += 8

    # Signal 5: 20-day momentum positive
    if ret_20d > 0:
        score += 10
        if ret_20d > 3:
            score += 5

    # Penalty: avoid extremely volatile or crashing stocks
    if rsi < 20 or ret_5d < -8:
        score -= 30

    return score


def pick_stock(date_str: str | None = None) -> dict:
    """Pick the best stock for tomorrow. Returns pick info dict."""
    tickers = get_sp500_tickers()
    print(f"Scoring {len(tickers)} stocks...")

    end_date = datetime.now() if date_str is None else datetime.strptime(date_str, "%Y-%m-%d")
    start_date = end_date - timedelta(days=120)

    # Download all data in batch for speed
    print("Downloading market data...")
    data = yf.download(
        tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        group_by="ticker",
        progress=False,
        threads=True,
    )

    scores = {}
    for ticker in tickers:
        try:
            if ticker in data.columns.get_level_values(0):
                hist = data[ticker].dropna()
                s = score_stock(hist)
                if s is not None:
                    scores[ticker] = s
        except Exception:
            continue

    if not scores:
        return {"error": "No stocks scored"}

    # Pick the top scorer
    best_ticker = max(scores, key=scores.get)
    best_score = scores[best_ticker]

    # Get some context for the pick
    hist = data[best_ticker].dropna()
    close = hist["Close"]
    rsi = compute_rsi(close).iloc[-1]
    ret_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100
    current_price = float(close.iloc[-1])

    pick = {
        "date": end_date.strftime("%Y-%m-%d"),
        "ticker": best_ticker,
        "price_at_pick": round(current_price, 2),
        "score": round(best_score, 1),
        "rsi": round(float(rsi), 1),
        "five_day_return": round(float(ret_5d), 2),
        "target_price": round(current_price * 1.01, 2),
        "result": None,  # filled in next day
        "actual_return": None,
    }

    print(f"\nPICK: {best_ticker} @ ${current_price:.2f} (score: {best_score:.1f}, RSI: {rsi:.1f})")
    return pick


def save_pick(pick: dict, data_dir: Path = None):
    """Append pick to picks.json."""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    picks_file = data_dir / "picks.json"

    picks = []
    if picks_file.exists():
        picks = json.loads(picks_file.read_text())

    # Don't duplicate
    if not any(p["date"] == pick["date"] for p in picks):
        picks.append(pick)
        picks_file.write_text(json.dumps(picks, indent=2))
        print(f"Saved pick for {pick['date']}")
    else:
        print(f"Pick for {pick['date']} already exists")


def update_results(data_dir: Path = None):
    """Update past picks with actual next-day results."""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data"
    picks_file = data_dir / "picks.json"

    if not picks_file.exists():
        return

    picks = json.loads(picks_file.read_text())
    updated = False

    for pick in picks:
        if pick["result"] is not None:
            continue

        pick_date = datetime.strptime(pick["date"], "%Y-%m-%d")
        # Need at least 2 trading days after pick to get result
        if datetime.now() - pick_date < timedelta(days=2):
            continue

        try:
            ticker_data = yf.download(
                pick["ticker"],
                start=pick["date"],
                end=(pick_date + timedelta(days=5)).strftime("%Y-%m-%d"),
                progress=False,
            )
            if len(ticker_data) >= 2:
                next_day_close = float(ticker_data["Close"].iloc[1])
                pick_price = pick["price_at_pick"]
                actual_return = ((next_day_close / pick_price) - 1) * 100
                pick["actual_return"] = round(actual_return, 2)
                pick["result"] = "win" if actual_return >= 1.0 else "loss"
                pick["next_day_close"] = round(next_day_close, 2)
                updated = True
        except Exception:
            continue

    if updated:
        picks_file.write_text(json.dumps(picks, indent=2))
        print("Updated results")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    update_results()
    pick = pick_stock(date_arg)
    if "error" not in pick:
        save_pick(pick)
