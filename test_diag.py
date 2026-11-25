import json
from app import app, ACTIVE_FARM_CONTEXT

print("Initial ACTIVE_FARM_CONTEXT:", json.dumps(ACTIVE_FARM_CONTEXT, indent=2))

client = app.test_client()

print("\n--- TEST: Sending chat request without farm_context ---")
res = client.post('/api/rag/chat', json={'query': 'Will the current temperature affect my crop?'})
print('Status:', res.status_code)
data = res.get_json()
print('Response farm_context:', json.dumps(data.get('farm_context'), indent=2))
print('Response answer:\n', data.get('answer'))
