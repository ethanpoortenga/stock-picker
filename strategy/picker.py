"""
Stock Picker: Quant signals → AI final selection.

1. Score all S&P 500 stocks using momentum + mean reversion signals
2. Take top 5 candidates
3. Claude Haiku picks the final one with a reasoning (~900 tokens/day)
"""

import json
import os
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


def score_stock(hist: pd.DataFrame) -> tuple[float | None, dict | None]:
    """Score a stock. Returns (score, details) or (None, None)."""
    if hist is None or len(hist) < 60:
        return None, None

    close = hist["Close"]
    volume = hist["Volume"]

    rsi = float(compute_rsi(close).iloc[-1])
    sma_50 = float(close.rolling(50).mean().iloc[-1])
    current_price = float(close.iloc[-1])
    ret_5d = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) >= 6 else 0.0
    ret_20d = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) >= 21 else 0.0
    avg_volume = float(volume.rolling(20).mean().iloc[-1])
    current_volume = float(volume.iloc[-1])
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0.0

    score = 0.0

    if 30 <= rsi <= 45:
        score += 30
    elif 25 <= rsi < 30:
        score += 15
    elif 45 < rsi <= 55:
        score += 10

    if current_price > sma_50:
        score += 20

    if -3 <= ret_5d <= -0.5:
        score += 25
    elif -5 <= ret_5d < -3:
        score += 10

    if volume_ratio > 1.5:
        score += 15
    elif volume_ratio > 1.2:
        score += 8

    if ret_20d > 0:
        score += 10
        if ret_20d > 3:
            score += 5

    if rsi < 20 or ret_5d < -8:
        score -= 30

    details = {
        "price": current_price,
        "rsi": rsi,
        "ret_5d": ret_5d,
        "ret_20d": ret_20d,
        "volume_ratio": volume_ratio,
        "above_sma50": current_price > sma_50,
    }

    return score, details


def pick_stock(date_str: str | None = None) -> dict:
    """Pick the best stock for tomorrow."""
    tickers = get_sp500_tickers()
    print(f"Scoring {len(tickers)} stocks...")

    end_date = datetime.now() if date_str is None else datetime.strptime(date_str, "%Y-%m-%d")
    start_date = end_date - timedelta(days=120)

    print("Downloading market data...")
    data = yf.download(
        tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        group_by="ticker",
        progress=False,
        threads=True,
    )

    scored = {}
    details = {}
    for ticker in tickers:
        try:
            if ticker in data.columns.get_level_values(0):
                hist = data[ticker].dropna()
                s, d = score_stock(hist)
                if s is not None:
                    scored[ticker] = s
                    details[ticker] = d
        except Exception:
            continue

    if not scored:
        return {"error": "No stocks scored"}

    # Top 5 candidates for AI
    top5 = sorted(scored, key=scored.get, reverse=True)[:5]
    candidates = [{"ticker": t, **details[t]} for t in top5]

    print(f"Top 5: {[c['ticker'] for c in candidates]}")

    # AI picks the final one
    reasoning = None
    use_ai = os.environ.get("ANTHROPIC_API_KEY")
    if use_ai:
        try:
            from ai_pick import ai_select
            ai_result = ai_select(candidates)
            chosen_ticker = ai_result.get("ticker", top5[0])
            reasoning = ai_result.get("reasoning")
            # Validate it's actually in our candidates
            if chosen_ticker not in top5:
                chosen_ticker = top5[0]
            print(f"AI picked: {chosen_ticker} — {reasoning}")
        except Exception as e:
            print(f"AI selection failed ({e}), using top quant pick")
            chosen_ticker = top5[0]
    else:
        print("No ANTHROPIC_API_KEY, using top quant pick")
        chosen_ticker = top5[0]

    d = details[chosen_ticker]
    pick = {
        "date": end_date.strftime("%Y-%m-%d"),
        "ticker": chosen_ticker,
        "price_at_pick": round(d["price"], 2),
        "score": round(scored[chosen_ticker], 1),
        "rsi": round(d["rsi"], 1),
        "five_day_return": round(d["ret_5d"], 2),
        "target_price": round(d["price"] * 1.01, 2),
        "result": None,
        "actual_return": None,
    }
    if reasoning:
        pick["reasoning"] = reasoning

    print(f"\nPICK: {chosen_ticker} @ ${d['price']:.2f} (score: {scored[chosen_ticker]:.1f})")
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
