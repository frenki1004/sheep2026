from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as ontology_router
from app.config import get_settings
from app.db import spatialite_available

settings = get_settings()

app = FastAPI(
    title="Sheep AI 2026",
    description="Ontology backend for the Split illegal-construction detector.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only — tighten before any non-localhost deploy.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "pilot": settings.pilot_name,
        "spatialite": spatialite_available(),
    }


@app.get("/config/pilot")
def pilot_config() -> dict[str, object]:
    return {
        "name": settings.pilot_name,
        "bbox": settings.pilot_bbox,
    }


app.include_router(ontology_router)
