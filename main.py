import os
import json
import re
import hashlib
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv
import yfinance as yf


# ==============================
# Setup
# ==============================

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==============================
# Helpers
# ==============================

def utc_now():
    return datetime.utcnow().isoformat() + "Z"


def safe_json_parse(text):
    """
    Attempts multiple ways to parse JSON safely.
    Handles markdown code blocks and extra text.
    """
    try:
        return json.loads(text)
    except:
        pass

    # Try extracting first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return None


def save_output(data, prefix="output"):
    """
    ALWAYS saves results + hash
    """
    filename = f"{OUTPUT_DIR}/{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    hash_value = hashlib.sha256(json.dumps(data).encode()).hexdigest()

    with open("hash_log.txt", "a") as log:
        log.write(f"{filename}: {hash_value}\n")

    print(f"✅ Saved → {filename}")


# ==============================
# Price functions
# ==============================

def get_end_of_month_price(ticker):
    """
    Gets most recent fully closed trading day (acts as EOM or latest accurate price)
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2mo")

    if hist.empty:
        return None

    last_close = hist["Close"].iloc[-1]
    return float(last_close)


# ==============================
# Main GPT query
# ==============================

def query_chatgpt_structured(model="gpt-4o-mini"):
    """
    Ask model for 10 S&P500 recommendations in STRICT JSON.
    Always saves raw + parsed output.
    """

    prompt = """
Return EXACTLY 10 S&P 500 stock recommendations.

Return ONLY valid JSON.

Format EXACTLY:

{
  "timestamp": "<ISO8601>",
  "recommendations": [
    {
      "ticker": "AAPL",
      "company": "Apple Inc",
      "recommendation": "Buy/Hold/Sell",
      "confidence": 0.0-1.0,
      "reasoning": "short explanation"
    }
  ]
}

No text. No markdown. JSON only.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        raw = response.choices[0].message.content.strip()

    except Exception as e:
        save_output({"error": str(e)}, prefix="error")
        return

    parsed = safe_json_parse(raw)

    if parsed is None:
        # Save raw for debugging
        save_output({
            "timestamp": utc_now(),
            "error": "JSON parse failed",
            "raw_response": raw
        }, prefix="bad_json")
        return

    # ==============================
    # Attach REAL prices
    # ==============================

    for stock in parsed.get("recommendations", []):
        ticker = stock["ticker"]
        price = get_end_of_month_price(ticker)
        stock["price"] = price

    parsed["timestamp"] = utc_now()

    save_output(parsed, prefix="stocks")


# ==============================
# Run
# ==============================

if __name__ == "__main__":
    query_chatgpt_structured()
