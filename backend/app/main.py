from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router as api_router
from app.api.websocket import ws_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Adaptive Quantum-Inspired Traffic Route Optimizer for Smart India Hackathon 2026",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cross-Origin Resource Sharing (CORS) for Flutter Web & Mobile
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST and WebSocket Routers
app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(ws_router)

@app.get("/", summary="Root Health Check")
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "city_hub": settings.DEFAULT_CITY
    }

@app.get("/health", summary="Service Health")
async def health():
    return {"status": "healthy", "quantum_engine": "active"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
