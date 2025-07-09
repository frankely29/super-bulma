import time
import jwt
import uuid

class JWTAuth:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def get_auth_headers(self) -> dict:
        """
        Returns the JWT-based Authorization headers required by Coinbase Advanced.
        """
        now = int(time.time())
        nonce = str(uuid.uuid4())
        payload = {
            "aud": "SPOT",
            "iss": self.api_key,
            "nbf": now,
            "exp": now + 120,
            "iat": now,
            "jti": nonce
        }
        token = jwt.encode(payload, self.api_secret, algorithm="HS256")
        return {
            "Authorization": f"Bearer {token}",
            "CB-ACCESS-KEY": self.api_key
        }
