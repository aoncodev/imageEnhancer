from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.services.s3_service import S3Service
import os
import tempfile
import re
import requests
from io import BytesIO
from PIL import Image
import json

router = APIRouter()
s3 = S3Service()

@router.post("/generate-docx")
async def generate_docx(request: Request):
    """Generate invoice with bolded text, formatted numbers, and logo/seal images."""
    try:
        data = await request.json()
        print("\n📦 Incoming JSON data:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if not isinstance(data, dict) or not data:
            raise HTTPException(status_code=400, detail="Request body must be a non-empty JSON object")

        return await generate_docx_from_data(data)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🧠 Core logic — formatting, bold text, images, and centering
# -------------------------------------------------------------
async def generate_docx_from_data(data: dict):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(base_dir, "invoice_template.docx")

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found at {template_path}")

        doc = Document(template_path)
        print(f"📄 Loaded template: {template_path}")

        # ---------------------------------------------------------
        # 🖼️ Download images (logo + seal)
        # ---------------------------------------------------------
        def download_image(url):
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return BytesIO(resp.content)

        logo_data, seal_data = None, None
        logo_height_in = None

        if data.get("logo_image"):
            try:
                logo_data = download_image(data["logo_image"])
                with Image.open(logo_data) as img:
                    w, h = img.size
                    logo_height_in = (h / w) * 1.3
                logo_data.seek(0)
                print(f"✅ Logo downloaded (height: {logo_height_in:.2f}in)")
            except Exception as e:
                print(f"⚠️ Failed to download logo: {e}")

        if data.get("seal_image"):
            try:
                seal_data = download_image(data["seal_image"])
                print("✅ Seal downloaded")
            except Exception as e:
                print(f"⚠️ Failed to download seal: {e}")

        # ---------------------------------------------------------
        # 🔢 Format numeric values with commas
        # ---------------------------------------------------------
        for key in ["unit_price", "weight", "volume"]:
            if key in data and data[key]:
                try:
                    val_str = str(data[key]).replace(",", "").strip()
                    if val_str:
                        val = float(val_str)
                        if val.is_integer():
                            data[key] = f"{int(val):,}"
                        else:
                            data[key] = f"{val:,.2f}"
                        print(f"🔢 Formatted {key}: {data[key]}")
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Could not format {key}: {e}")

        # ---------------------------------------------------------
        # ✍️ Replace text placeholders with bold values
        # ---------------------------------------------------------
        def replace_text_in_paragraph(paragraph):
            full_text = "".join(run.text for run in paragraph.runs)
            if not re.search(r"\{\s*\w+\s*\}", full_text):
                return

            new_text = full_text
            for key, value in data.items():
                if key in ["logo_image", "seal_image"]:
                    continue
                pattern = re.compile(rf"\{{\s*{re.escape(key)}\s*\}}", re.IGNORECASE)
                new_text = pattern.sub(str(value), new_text)

            if new_text != full_text:
                for run in paragraph.runs[:]:
                    paragraph._element.remove(run._element)
                run = paragraph.add_run(new_text)
                run.bold = True

        def replace_text_in_cell(cell):
            for paragraph in cell.paragraphs:
                replace_text_in_paragraph(paragraph)

        for paragraph in doc.paragraphs:
            replace_text_in_paragraph(paragraph)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    replace_text_in_cell(cell)

        # ---------------------------------------------------------
        # 🖼️ Insert images
        # ---------------------------------------------------------
        def insert_images_in_paragraph(paragraph):
            full_text = "".join(run.text for run in paragraph.runs)
            has_logo = re.search(r"\{\s*logo_image\s*\}", full_text)
            has_seal = re.search(r"\{\s*seal_image\s*\}", full_text)
            if not (has_logo or has_seal):
                return

            parts = re.split(r"(\{\s*logo_image\s*\}|\{\s*seal_image\s*\})", full_text)
            for run in paragraph.runs[:]:
                paragraph._element.remove(run._element)

            for part in parts:
                if re.match(r"\{\s*logo_image\s*\}", part) and logo_data:
                    logo_data.seek(0)
                    run = paragraph.add_run()
                    run.add_picture(logo_data, width=Inches(1.3))
                elif re.match(r"\{\s*seal_image\s*\}", part) and seal_data:
                    seal_data.seek(0)
                    run = paragraph.add_run()
                    run.add_picture(seal_data, width=Inches(1.2))
                elif part.strip():
                    run = paragraph.add_run(part)
                    run.bold = True

        def insert_images_in_cell(cell):
            for paragraph in cell.paragraphs:
                insert_images_in_paragraph(paragraph)

        for paragraph in doc.paragraphs:
            insert_images_in_paragraph(paragraph)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    insert_images_in_cell(cell)

        # ---------------------------------------------------------
        # 💪 Make all text bold
        # ---------------------------------------------------------
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                run.bold = True
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True

        # ---------------------------------------------------------
        # 🧭 Center the QTY / UNIT PRICE / WEIGHT / VOLUME block
        # ---------------------------------------------------------
        def center_table_headers(doc):
            target_headers = ["QTY", "UNIT PRICE", "WEIGHT", "VOLUME"]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            text = paragraph.text.strip().upper()
                            if any(header in text for header in target_headers):
                                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                for run in paragraph.runs:
                                    run.bold = True

        center_table_headers(doc)

        # ---------------------------------------------------------
        # 💾 Save and upload
        # ---------------------------------------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            temp_path = tmp.name
            doc.save(temp_path)

        print(f"💾 Document saved: {temp_path}")
        key = s3.generate_key("invoice_generated.docx", folder="docx-temp")
        with open(temp_path, "rb") as f:
            s3_url = s3.upload_bytes(
                data=f.read(),
                key=key,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        os.unlink(temp_path)
        print(f"✅ Uploaded to S3: {s3_url}")

        return JSONResponse({
            "message": "Invoice generated successfully",
            "download_url": s3_url
        })

    except Exception as e:
        print(f"❌ ERROR during generation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
