from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from app.services.enhancer import enhance_image
from app.services.s3_service import S3Service
from app.services.openai_client import extract_vin_fields

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
        
        

        enhanced = enhance_image(img)

        _, buffer = cv2.imencode(".png", enhanced)
        key = s3.generate_key(file.filename.replace(".", "_enhanced."))
        image_url = s3.upload_bytes(buffer.tobytes(), key, content_type="image/png")

        fields = extract_vin_fields(image_url)

        return {
            "filename": file.filename,
            "s3_url": image_url,
            "fields": fields,
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
