import json
import sys
from app import app, ACTIVE_FARM_CONTEXT

client = app.test_client()

# Set active farm location
payload = {
    "query": "Will the current temperature affect my crop?",
    "farm_context": {
        "location": {
            "latitude": 16.5062,
            "longitude": 80.6480,
            "place_name": "Vijayawada, Andhra Pradesh, India"
        },
        "crop": {
            "name": "Rice",
            "variety": "MTU-1010",
            "growth_stage": "Flowering"
        }
    }
}

print("--- POST /api/rag/chat with location & crop ---")
res = client.post('/api/rag/chat', json=payload)
print('Status:', res.status_code)
data = res.get_json()
fc = data.get('farm_context', {})
print('Weather in response:', json.dumps(fc.get('weather'), indent=2))
print('Crop in response:', json.dumps(fc.get('crop'), indent=2))
print('Sources in response:', json.dumps(data.get('sources'), indent=2))
with open('diag_answer.txt', 'w', encoding='utf-8') as f:
    f.write(data.get('answer', ''))
print('Answer written to diag_answer.txt')
