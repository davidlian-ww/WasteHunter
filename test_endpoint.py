from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

try:
    print("Testing GET /")
    resp = client.get('/')
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("✅ SUCCESS!")
        if "TIMWOOD" in resp.text:
            print("✅ Page content loaded!")
        else:
            print("❌ Page loaded but no TIMWOOD text")
    else:
        print(f"❌ Got status {resp.status_code}")
        print(resp.text[:500])
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()
