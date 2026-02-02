import os
import json
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import hashlib
import yfinance as yf

# ---------------- Load API Key ----------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------- Helper: End-of-Month Price ----------------
def get_price_end_of_last_month(ticker):
    """
    Fetch the most recent accurate stock price at the end of the prior month.
    Falls back to the closest available date if exact month-end not available.
    """
    today = datetime.utcnow()
    first_day_this_month = datetime(today.year, today.month, 1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    last_day_str = last_day_prev_month.strftime("%Y-%m-%d")

    stock = yf.Ticker(ticker)
    # Try exact last-day-of-month
    hist = stock.history(start=last_day_str, end=last_day_str)
    if not hist.empty:
        return float(hist["Close"].iloc[-1])
    # fallback: get most recent available price before last day
    hist = stock.history(end=last_day_str)
    if not hist.empty:
        return float(hist["Close"].iloc[-1])
    return None

# ---------------- Query GPT ----------------
def query_sp500_top10(model="gpt-4o-mini"):
    """
    Query ChatGPT for top 10 S&P500 stock recommendations.
    GPT provides ticker, company_name, recommendation, confidence, reasoning.
    We append accurate end-of-prior-month price from yfinance and validate JSON.
    """
    
    prompt = """
You are a financial assistant.

Task:
1. From the S&P 500, select 10 notable stocks right now.
2. For each stock, provide:
   - Ticker
   - Company Name
   - Recommendation (Buy/Hold/Sell)
   - Confidence (0-1)
   - Short reasoning (1-2 sentences)
3. Include a timestamp in ISO 8601 UTC format for when this analysis is generated.

Output ONLY valid JSON as a list of objects in this exact format:

[
  {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "recommendation": "Buy",
    "confidence": 0.78,
    "reasoning": "Strong earnings growth and upward trend.",
    "timestamp": "2026-02-02T00:00:00Z"
  },
  ...
]
"""

    # Query GPT
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content.strip()

    # Parse GPT JSON safely
    try:
        recommendations = json.loads(content)
    except json.JSONDecodeError:
        print("❌ Failed to parse GPT JSON. Raw output:")
        print(content)
        return None

    # Validate each stock entry
    required_keys = ["ticker", "company_name", "recommendation", "confidence", "reasoning", "timestamp"]
    validated_recommendations = []
    for stock in recommendations:
        missing_keys = [k for k in required_keys if k not in stock]
        if missing_keys:
            print(f"⚠️ Missing keys for {stock.get('ticker', 'unknown')}: {missing_keys}, skipping entry")
            continue  # skip invalid entries
        # Add accurate prior month price
        ticker = stock.get("ticker")
        if ticker:
            stock["price_prior_month_end"] = get_price_end_of_last_month(ticker)
        validated_recommendations.append(stock)

    recommendations = validated_recommendations

    # Save JSON output
    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/sp500_top10_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(recommendations, f, indent=2)

    # Hash log
    hash_value = hashlib.sha256(json.dumps(recommendations).encode()).hexdigest()
    with open("hash_log.txt", "a") as log:
        log.write(f"{filename}: {hash_value}\n")

    print(f"\n✅ Saved top 10 S&P500 recommendations to {filename}")
    print(f"🔒 SHA256 hash: {hash_value}\n")
    return recommendations

# ---------------- Example Usage ----------------
if __name__ == "__main__":
    top10_data = query_sp500_top10()
    print(json.dumps(top10_data, indent=2))
