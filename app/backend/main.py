import os
import time
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from database import init_db
from routers import auth, telemetry, ai

init_db()

app = FastAPI(
    title="AgriSense - Farmer Platform Backend API",
    description="Enterprise Platform: Salted PBKDF2 Auth, Rate Limiting, OTA Updates, Anti-XSS Shield, and Live Telemetry.",
    version="3.0.0"
)

# SECURITY HEADERS MIDDLEWARE
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# GLOBAL EXCEPTION HANDLERS
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[UNHANDLED SERVER EXCEPTION] {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal AgriSense Server Error. Our security guard team has logged this event.",
            "timestamp": time.time()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "timestamp": time.time()
        }
    )

raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_web_dashboard():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"error": "index.html not found", "path": index_path})

# MOUNT MODULAR ROUTERS
app.include_router(auth.router)
app.include_router(telemetry.router)
app.include_router(ai.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
