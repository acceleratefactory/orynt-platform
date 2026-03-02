from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoaGJxdnN5eHhkenh1eXJkeGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIzNzc1MDEsImV4cCI6MjA4Nzk1MzUwMX0.BKfQF_6TdvgKywvFfDzplJpQQqqh_jIff9ce98SwOSU'
secret = os.getenv("JWT_SECRET")

print(f"Secret: {secret}")
print(f"Header: {jwt.get_unverified_header(token)}")

try:
    # Try decoding without signature verification first
    payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_signature": False})
    print("Decoded (NO SIG):", payload)
except Exception as e:
    print("Error (NO SIG):", e)

try:
    # Try decoding with signature verification
    payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_signature": True, "verify_aud": False})
    print("Decoded (WITH SIG):", payload)
except Exception as e:
    print("Error (WITH SIG):", e)
