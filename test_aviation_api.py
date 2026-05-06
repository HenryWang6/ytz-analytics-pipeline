import os
import requests
import json
from dotenv import load_dotenv

# 1. Load the environment variables from your .env file
load_dotenv()

# 2. Retrieve your specific Aviation API key
api_key = os.getenv("AVIATION_API_KEY")

if not api_key or api_key == "your_aviationstack_or_opensky_api_key_here":
    print("🚨 Error: Please replace the placeholder in your .env file with your actual API key.")
    exit()

# 3. Define the AviationStack endpoint for real-time flights
url = "http://api.aviationstack.com/v1/flights"

# 4. Set the parameters (limiting to 1 record just to see the structure)
params = {
    'access_key': api_key,
    'limit': 1 
}

print("Fetching live flight data...")

# 5. Make the request and format the JSON output
try:
    response = requests.get(url, params=params)
    response.raise_for_status() 
    
    data = response.json()
    
    print("\n✈️  --- Raw Aviation JSON Payload --- ✈️\n")
    print(json.dumps(data, indent=4))
    
except requests.exceptions.RequestException as e:
    print(f"API Request failed: {e}")