from coinbase.rest import RESTClient
from json import dumps

# Use the full API key ID from your JSON object
api_key = "organizations/a7e9c61e-223e-4950-b174-f914e664b37b/apiKeys/169f99f5-0692-49c1-a991-01ddd40d763b"

# Use the private key from your JSON object
api_secret = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIDookEhfYRC0sAt1ETT7IeGJZ37mUKzlH8lqKNCkCtqYoAoGCCqGSM49
AwEHoUQDQgAEZrx2Nb/gxazIN+ra+01A6Ooss6OfHMSnPMhGSYQiBmyiArsTgi0w
WVWUe/y2zLKhhFgkpJshpFaN1jYvparlQA==
-----END EC PRIVATE KEY-----"""

try:
    client = RESTClient(api_key=api_key, api_secret=api_secret)
    accounts = client.get_accounts()
    print(dumps(accounts.to_dict(), indent=2))  # Convert to dict before serializing
except Exception as e:
    print(f"Error: {e}")