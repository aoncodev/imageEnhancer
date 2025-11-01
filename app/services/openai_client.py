import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_vin_fields(image_url: str):
    prompt = """
    You are an OCR assistant. Analyze the uploaded car registration or inspection image.
    Extract and return JSON with fields:
    {
        "vin": "...",
        "car_model": "...",
        "manufacturer": "...",
        "engine_cc": "...",
        "weight": "...",
        "manufacture_date": "..."
    }
    Return ONLY valid JSON, no markdown or explanations.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise OCR extraction model."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]},
        ],
        temperature=0,
    )

    message_content = response.choices[0].message.content

    # Handle multimodal format (list or string)
    if isinstance(message_content, list):
        text_blocks = [block["text"] for block in message_content if block["type"] == "text"]
        raw_text = "\n".join(text_blocks).strip()
    else:
        raw_text = str(message_content).strip()

    # Try to clean markdown fences and parse as JSON
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        return {
            "vin": parsed.get("vin"),
            "car_model": parsed.get("car_model"),
            "manufacturer": parsed.get("manufacturer"),
            "engine_cc": parsed.get("engine_cc"),
            "weight": parsed.get("weight"),
            "manufacture_date": parsed.get("manufacture_date"),
            "raw_response": raw_text,
            "image_url": image_url
        }
    except Exception:
        # fallback if GPT response is not valid JSON
        return {
            "vin": None,
            "car_model": None,
            "manufacturer": None,
            "engine_cc": None,
            "weight": None,
            "manufacture_date": None,
            "raw_response": raw_text,
            "error": "Invalid JSON format",
            "image_url": image_url
        }
