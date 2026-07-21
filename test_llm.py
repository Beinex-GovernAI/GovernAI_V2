
import sys
import os
sys.path.append('C:/Users/georg/GovernAI-/governnew')
from governai.services.llm.foundry_client import get_default_client

client = get_default_client()
print('Base URL:', client.connection_info.base_url)
print('Model ID:', client.model_id)
try:
    res = client.chat_completion([{'role': 'user', 'content': 'hello'}])
    print('Response:', res)
except Exception as e:
    print('ERROR:', repr(e))

