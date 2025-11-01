from dotenv import load_dotenv
load_dotenv()


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import extract

app = FastAPI(title="VIN Extractor API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for now allow all; can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract.router, prefix="/api", tags=["VIN"])
