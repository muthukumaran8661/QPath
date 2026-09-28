import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.api.routes import router as api_router
from app.api.websocket import ws_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Adaptive Quantum-Inspired Traffic Route Optimizer",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cross-Origin Resource Sharing (CORS) - Support Web, Render, and Capacitor Mobile
capacitor_origins = [
    "https://localhost",
    "capacitor://localhost",
    "http://localhost",
    "https://qpath.onrender.com",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=capacitor_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include REST and WebSocket Routers
app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(ws_router)

@app.get("/", summary="Web Application Dashboard")
async def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/manifest.json", summary="PWA Web App Manifest")
async def serve_manifest():
    manifest_file = os.path.join(static_dir, "manifest.json")
    if os.path.exists(manifest_file):
        return FileResponse(manifest_file, media_type="application/manifest+json")
    return {"name": "QPath"}

@app.get("/sw.js", summary="PWA Service Worker")
async def serve_sw():
    sw_file = os.path.join(static_dir, "sw.js")
    if os.path.exists(sw_file):
        return FileResponse(
            sw_file,
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"}
        )
    return ""

@app.get("/health", summary="Service Health Check")
async def health():
    return {"status": "healthy", "quantum_engine": "active"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
