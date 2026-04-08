"""Production server - no reload, stable for multi-user sharing."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="warning",
        access_log=True,
    )
