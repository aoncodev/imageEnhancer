from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from app.services.enhancer import enhance_image
from app.services.s3_service import S3Service
from app.services.openai_client import extract_vin_fields
import torch


router = APIRouter()
s3 = S3Service()

@router.post("/extract")
async def extract_vin(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        np_img = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return JSONResponse(status_code=400, content={"error": "Invalid image."})
        
        max_dim = 1600
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        enhanced = enhance_image(img)

        _, buffer = cv2.imencode(".png", enhanced)
        key = s3.generate_key(file.filename.replace(".", "_enhanced."))
        image_url = s3.upload_bytes(buffer.tobytes(), key, content_type="image/png")

        fields = extract_vin_fields(image_url)

        del img, enhanced, np_img, buffer
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

        return {
            "filename": file.filename,
            "s3_url": image_url,
            "fields": fields,
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
