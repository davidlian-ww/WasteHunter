print("Starting...")
try:
    print("1. Importing FastAPI")
    from fastapi import FastAPI
    print("2. OK")
    
    print("3. Importing app...")
    from app.main import app
    print("4. App imported!")
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
