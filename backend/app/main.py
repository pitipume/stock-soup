from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.modules.vi.router import router as vi_router

app = FastAPI(
    title="StockSoup API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vi_router, prefix="/vi", tags=["VI Scanner"])


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
