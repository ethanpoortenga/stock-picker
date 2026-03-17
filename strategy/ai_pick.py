"""
AI-enhanced stock picker.

Flow:
1. Quantitative signals score all S&P 500 stocks (free, no tokens)
2. Top 5 candidates + their stats sent to Claude Haiku (~500 tokens)
3. AI picks the final one with a short reasoning

Token budget: ~800 input + ~100 output = ~900 tokens/day ≈ $0.001/day
"""

import json
import os

import anthropic


def ai_select(candidates: list[dict]) -> dict:
    """Use Claude Haiku to pick the best candidate from top 5."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Build a compact summary of each candidate
    lines = []
    for c in candidates:
        lines.append(
            f"{c['ticker']}: ${c['price']:.2f}, RSI={c['rsi']:.0f}, "
            f"5d={c['ret_5d']:+.1f}%, 20d={c['ret_20d']:+.1f}%, "
            f"vol_ratio={c['volume_ratio']:.1f}x, above_sma50={'Y' if c['above_sma50'] else 'N'}"
        )
    candidates_text = "\n".join(lines)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[
            {
                "role": "user",
                "content": (
                    "You pick one stock each day that will go up 1%+ tomorrow. "
                    "Here are today's top 5 candidates by quantitative score:\n\n"
                    f"{candidates_text}\n\n"
                    "Pick ONE ticker. Reply with ONLY a JSON object: "
                    '{"ticker": "XXX", "reasoning": "one sentence why"}'
                ),
            }
        ],
    )

    text = response.content[0].text.strip()
    # Parse the JSON from the response
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
        else:
            # Fallback to top quant pick
            return {"ticker": candidates[0]["ticker"], "reasoning": "Top quantitative score"}

    return result
