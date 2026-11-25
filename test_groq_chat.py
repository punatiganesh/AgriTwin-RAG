import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=key)

for model in ["groq/compound", "groq/compound-mini", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, answer in 5 words."}],
            max_tokens=30
        )
        print(f"Model {model} SUCCESS:", resp.choices[0].message.content)
    except Exception as e:
        print(f"Model {model} FAILED:", e)
