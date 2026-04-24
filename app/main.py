from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import import_router, averages_router, stats_router, artifacts_router

app = FastAPI(
    title="SW Farming API",
    description="API de calcul et d'analyse de runes Summoners War",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router.router)
app.include_router(averages_router.router)
app.include_router(stats_router.router)
app.include_router(artifacts_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
