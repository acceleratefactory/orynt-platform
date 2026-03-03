import httpx

r = httpx.get("http://localhost:8000/openapi.json", timeout=5)
spec = r.json()

paths = list(spec.get("paths", {}).keys())
flw_routes = [p for p in paths if "flutterwave" in p]
paystack_routes = [p for p in paths if "paystack" in p]

print("Flutterwave routes:")
for p in flw_routes:
    print(" ", p)

print("Paystack routes:")
for p in paystack_routes:
    print(" ", p)

print("\nAll integration routes:")
for p in paths:
    if "integrat" in p or "webhook" in p:
        print(" ", p)
