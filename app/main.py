from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI



# ✅ Lifespan context replaces on_event()
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting VIN Extractor service...")

    # 🔹 Import enhancer here so model loads & warms up before serving
    from app.services import enhancer
    _ = enhancer.model  # Access once to trigger load/warm-up
    print("[INFO] DnCNN model preloaded and ready.")

    yield  # 👈 Application runs between startup and shutdown

    print("[INFO] Shutting down VIN Extractor service...")



app = FastAPI(title="VIN Extractor API", version="1.0")

from app.routers import extract
app.include_router(extract.router, prefix="/api", tags=["VIN"])
