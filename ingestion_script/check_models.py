import os
from dotenv import load_dotenv
from google import genai
load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
models = client.models.list()
for m in models:
    if 'flash' in m.name.lower():
        print(m.name)
