import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import hashlib
import yfinance as yf

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Real Price Data from yfinance
def get_price(ticker):
    """Fetch the latest stock price for a given ticker symbol."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1d")
    if not hist.empty:
        return hist["Close"].iloc[-1]
    return None

def query_stock(ticker, model="gpt-4o-mini"):
    """Structured query of ChatGPT for stock information including real price data."""
    price = get_price(ticker)
    prompt = f"""
You are a financial assistant.

Given:
Ticker: {ticker}
Current price: ${price:.2f}

Return ONLY valid JSON in this exact format:
{{
  "ticker": "{ticker}",
  "recommendation": "Buy/Hold/Sell",
  "confidence": number between 0 and 1,
  "reasoning": "short explanation"
}}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content.strip()

    #Parse JSON safely
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {"error": "Failed to parse JSON response"}
    data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "price": price,
        **result
    }

    #Save output
    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    #hash log
    hash_value = hashlib.sha256(json.dumps(data).encode()).hexdigest()
    with open("hash_log.txt", "a") as log:
        log.write(f"{filename}: {hash_value}\n")
    print(f"\n✅ Saved {ticker} to {filename}")
    return data

def query_chatgpt(prompt, model="gpt-4o-mini"):
    """Send a prompt to ChatGPT and store response with timestamp."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    # Collect data
    data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "prompt": prompt,
        "response": response.choices[0].message.content.strip(),
    }

    # Save to JSON
    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/chatgpt_output_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Generate hash for verification
    hash_value = hashlib.sha256(json.dumps(data).encode()).hexdigest()
    print(f"\n✅ Saved response to {filename}")
    print(f"🔒 SHA256 hash: {hash_value}\n")

    # Optionally log hash separately
    with open("hash_log.txt", "a") as log:
        log.write(f"{filename}: {hash_value}\n")

    return data

# Example prompt
if __name__ == "__main__":
    query_chatgpt("Summarize current market trends in the S&P 500.")

