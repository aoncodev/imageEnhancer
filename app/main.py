from dotenv import load_dotenv
load_dotenv()


from fastapi import FastAPI
from app.routers import extract

app = FastAPI(title="VIN Extractor API", version="1.0")
app.include_router(extract.router, prefix="/api", tags=["VIN"])
