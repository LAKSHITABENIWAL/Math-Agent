# backend/test_groq_new.py
from openai import OpenAI
from dotenv import load_dotenv
import os, json

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"

client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_API_BASE)

resp = client.chat.completions.create(
    model="openai/gpt-oss-20b",   # <-- pick any model from your list
    messages=[{"role":"user","content":"Hello Groq! Please reply briefly."}],
    temperature=0.1,
    max_tokens=100,
)

# Print full response minimally
print("Model used:", resp.model)
print("Reply:\n", resp.choices[0].message.content)
