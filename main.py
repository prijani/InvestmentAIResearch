import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import hashlib

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

