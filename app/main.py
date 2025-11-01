from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI

load_dotenv()

# ✅ Lifespan context replaces on_event()
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting VIN Extractor service...")

    # 🔹 Import enhancer here so ONNXRuntime session loads before first request
    from app.services import enhancer
    _ = enhancer.enhance_image  # Access once to ensure model file loads
    print("[INFO] DnCNN ONNX model preloaded and ready.")

    yield  # 👈 Application runs between startup and shutdown

    print("[INFO] Shutting down VIN Extractor service...")

# ✅ Pass lifespan handler to FastAPI
app = FastAPI(title="VIN Extractor API", version="1.0", lifespan=lifespan)

# ✅ Register routers

from app.routers import datagen, invoice, extract

app.include_router(extract.router, prefix="/api", tags=["VIN"])
app.include_router(datagen.router, prefix="/api", tags=["Data Generation"])
app.include_router(invoice.router, prefix="/api", tags=["Invoice Generation"])
