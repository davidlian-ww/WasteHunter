import sys, traceback
try:
    from app.main import app
    from fastapi.testclient import TestClient
    print("Imports OK")
    client = TestClient(app)
    resp = client.get('/')
    print(f'Status: {resp.status_code}')
    if resp.status_code == 200:
        print('✅ WORKS! Dashboard loaded!')
    else:
        print(f'❌ Error {resp.status_code}')
        print(resp.text[:500])
except Exception as e:
    print(f'❌ Exception: {e}')
    traceback.print_exc()
