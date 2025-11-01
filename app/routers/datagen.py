from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
import os
import json
import random

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------------
# Helper functions
# -------------------------------------------------------

def generate_birth_segment():
    """Generate YYMMDD between 1970–2000."""
    year = random.randint(1970, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{str(year)[2:]}{month:02d}{day:02d}"

def generate_iin(country: str) -> str:
    """Generate IIN following country-specific formats."""
    birth = generate_birth_segment()

    if country == "Russia":
        return "".join(str(random.randint(0, 9)) for _ in range(12))
    elif country == "Kazakhstan":
        return birth + "".join(str(random.randint(0, 9)) for _ in range(6))
    elif country == "Kyrgyzstan":
        return birth + "".join(str(random.randint(0, 9)) for _ in range(8))
    elif country == "Uzbekistan":
        return birth + "".join(str(random.randint(0, 9)) for _ in range(8))
    return "000000000000"

def generate_phone(country: str) -> str:
    """Generate a realistic phone number for each country."""
    codes = {
        "Russia": "+7",
        "Kazakhstan": "+7",
        "Kyrgyzstan": "+996",
        "Uzbekistan": "+998"
    }
    code = codes.get(country, "+000")
    number_length = 9 if country in ["Kyrgyzstan", "Uzbekistan"] else 10
    digits = "".join(str(random.randint(0, 9)) for _ in range(number_length))
    return f"{code}{digits}"

# -------------------------------------------------------
# Main API endpoint
# -------------------------------------------------------

@router.post("/generate-consignee")
async def generate_consignee(data: dict):
    """
    Request example:
    {
        "country": "Kazakhstan"
    }

    Response:
    {
        "country": "Kazakhstan",
        "data": {
            "consignee_name": "...",
            "consignee_address": "...",
            "consignee_iin": "...",
            "consignee_tel": "..."
        }
    }
    """
    try:
        country = data.get("country")
        valid = ["Russia", "Kazakhstan", "Kyrgyzstan", "Uzbekistan"]
        if country not in valid:
            raise HTTPException(status_code=400, detail=f"Country must be one of {valid}")

        # 🔮 Ask OpenAI only for English-transliterated name/address
        prompt = f"""
        Generate one realistic consignee record for {country}.
        Requirements:
        - Output must be in English (default language).
        - Use only Latin alphabet, no Cyrillic or special characters.
        - Return ONLY valid JSON with these two fields:
          {{
            "consignee_name": "...",
            "consignee_address": "..."
          }}
        - The name and address should look natural for {country} (e.g., common local person name
          and city/street transliterated into English).
        - Do not include explanations or any text outside the JSON object.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You generate localized consignee data in English using Latin alphabet."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )

        raw_output = response.choices[0].message.content.strip()

        # 🧹 Parse JSON safely
        try:
            partial = json.loads(raw_output)
        except json.JSONDecodeError:
            start = raw_output.find("{")
            end = raw_output.rfind("}")
            if start != -1 and end != -1:
                partial = json.loads(raw_output[start:end + 1])
            else:
                raise ValueError("OpenAI did not return valid JSON")

        # ✅ Add correct IIN and phone
        partial["consignee_iin"] = generate_iin(country)
        partial["consignee_tel"] = generate_phone(country)

        return JSONResponse(content={"country": country, "data": partial})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
