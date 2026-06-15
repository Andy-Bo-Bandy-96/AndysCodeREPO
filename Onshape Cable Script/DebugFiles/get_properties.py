import os
from onshape_client.client import Client

# 1. Grab the variables and scrub them clean
url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')

# 2. THE FIX: Build a simple Python dictionary. 
# This bypasses all environment variables and auto-readers completely.
my_config = {
    "base_url": url,
    "access_key": access,
    "secret_key": secret
}

print("Sending securely signed request with explicit dictionary...")

try:
    # 3. Hand the dictionary directly into the Client
    client = Client(configuration=my_config)
    
    # 4. Request the path
    response = client.api_client.request('GET', '/api/metadataproperties')
    
    for prop in response.data['items']:
        if prop['name'] == 'Part number':
            print("\n" + "=" * 40)
            print("🎯 FOUND IT! Your Part Number Property ID is:")
            print(prop['id'])
            print("=" * 40 + "\n")
            
except Exception as e:
    print(f"\nCRASHED! The exact error is: {e}")