import requests
import os
from dotenv import load_dotenv

load_dotenv()

response = requests.post(
    'https://api.cloudflare.com/client/v4/accounts/CLOUDFLARE_ACCOUNT_ID/ai/v1/chat/completions',
    headers={
        'Authorization': f'Bearer {os.getenv("CLOUDFLARE_API_TOKEN")}',
        'HTTP-Referer': 'http://localhost:8000',
        'X-Title': 'AI Chatbot'
    },
    json={
        'model': 'pruna/p-image',
        'prompt': 'a beautiful cat',
        'size': '1024x1024',
        'num_images': 1
    }
)

print(f'Status: {response.status_code}')
print(f'Response: {response.text}')
