"""Quick test to see the error"""
import sys
import traceback

try:
    from app.main import app
    from app.database import get_all_sites, get_process_paths, get_waste_observations, get_dashboard_stats
    
    print("[OK] App imported successfully")
    
    # Test database
    stats = get_dashboard_stats()
    print(f"[OK] Database working: {stats['total_sites']} sites")
    
    # Test if we can create a response
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    print("[OK] TestClient created")
    
    response = client.get("/")
    print(f"Response status: {response.status_code}")
    print(f"Response length: {len(response.text)} chars")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("[OK] Homepage loads successfully!")
        
except Exception as e:
    print(f"[ERROR] {e}")
    traceback.print_exc()
