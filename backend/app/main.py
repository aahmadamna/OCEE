from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .config import settings
from .database import Base, engine
from .routers import prospect as prospect_router
from .routers import deck as deck_router

app = FastAPI(title="OffDeal BDR Engine API")

# CORS
origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure tables & storage dir
Base.metadata.create_all(bind=engine)
os.makedirs(settings.FILE_STORAGE_DIR, exist_ok=True)

# Serve generated files
app.mount("/generated", StaticFiles(directory=settings.FILE_STORAGE_DIR), name="generated")

# Routers
app.include_router(prospect_router.router, prefix="/prospects", tags=["prospects"])
app.include_router(deck_router.router, prefix="/decks", tags=["decks"])
