"""
Debug script to see what's happening with JSON serialization
"""
import json
from app.schemas import AnswerRequest

# Create a request object
request = AnswerRequest(
    url="https://example.com",
    question="Test question?",
    max_depth=2
)

print("Original request:")
print(f"  URL: {request.url} (type: {type(request.url)})")
print(f"  URL string: {str(request.url)}")

# Serialize to JSON
json_str = request.model_dump_json()
print(f"\nJSON string: {json_str}")

# Parse JSON
json_data = json.loads(json_str)
print(f"\nParsed JSON data:")
print(f"  URL: {json_data['url']} (type: {type(json_data['url'])})")
print(f"  URL string: {str(json_data['url'])}")

# Try deserializing back
try:
    request_restored = AnswerRequest.model_validate(json_data)
    print(f"\nRestored request:")
    print(f"  URL: {request_restored.url} (type: {type(request_restored.url)})")
    print(f"  URL string: {str(request_restored.url)}")
except Exception as e:
    print(f"Error restoring: {e}")