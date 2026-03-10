import os
from dotenv import load_dotenv

params_store_url = os.environ.get("PARAMS_STORE_URL")
print(f"PARAMS_STORE_URL before load_dotenv: {params_store_url}")

load_dotenv()
params_store_url = os.environ.get("PARAMS_STORE_URL")
print(f"PARAMS_STORE_URL after load_dotenv: {params_store_url}")
