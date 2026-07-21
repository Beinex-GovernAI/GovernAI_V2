
from dotenv import load_dotenv
import os
print('Before:', os.environ.get('FOUNDRY_BASE_URL'))
load_dotenv()
print('After:', os.environ.get('FOUNDRY_BASE_URL'))

