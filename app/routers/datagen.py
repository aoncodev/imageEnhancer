from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
import os
import json
import random
from datetime import datetime

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------------
# Utility: Random Generators
# -------------------------------------------------------

def generate_birth_segment():
    """Generate YYMMDD between 1970–2000."""
    year = random.randint(1970, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{str(year)[2:]}{month:02d}{day:02d}"

def generate_iin(country: str) -> str:
    """Generate realistic IIN (Individual Identification Number)."""
    birth = generate_birth_segment()

    if country == "Kazakhstan":
        # YYMMDD + 6 random digits
        return birth + "".join(str(random.randint(0, 9)) for _ in range(6))
    elif country == "Kyrgyzstan":
        # YYMMDD + 8 random digits
        return birth + "".join(str(random.randint(0, 9)) for _ in range(8))
    elif country == "Uzbekistan":
        # YYMMDD + 8 random digits
        return birth + "".join(str(random.randint(0, 9)) for _ in range(8))
    elif country == "Russia":
        # 12 digits, Russian SNILS-like format
        return "".join(str(random.randint(0, 9)) for _ in range(12))
    return "000000000000"

def generate_phone(country: str) -> str:
    """Generate realistic full phone numbers by country (with valid operator codes and correct total length)."""
    operator_prefixes = {
        # Russia: +7 + 3-digit operator code + 7-digit subscriber number (total 11 digits)
        "Russia": {
            "prefixes": ["+7900", "+7911", "+7926", "+7937", "+7952", "+7965", "+7981"],
            "subscriber_len": 7,
        },
        # Kazakhstan: +7 + 3-digit operator code + 7-digit subscriber number (total 11 digits)
        "Kazakhstan": {
            "prefixes": ["+7701", "+7705", "+7707", "+7708", "+7712"],
            "subscriber_len": 7,
        },
        # Kyrgyzstan: +996 + 2-digit operator code + 6-digit subscriber number (total 12 digits)
        "Kyrgyzstan": {
            "prefixes": ["+99650", "+99655", "+99670", "+99677", "+99699"],
            "subscriber_len": 6,
        },
        # Uzbekistan: +998 + 2-digit operator code + 7-digit subscriber number (total 12 digits)
        "Uzbekistan": {
            "prefixes": ["+99890", "+99891", "+99893", "+99894", "+99895", "+99897", "+99899"],
            "subscriber_len": 7,
        },
    }

    cfg = operator_prefixes.get(country)
    if not cfg:
        return "+0000000000"  # fallback for unknown country

    prefix = random.choice(cfg["prefixes"])
    local_number = "".join(str(random.randint(0, 9)) for _ in range(cfg["subscriber_len"]))
    return prefix + local_number


# -------------------------------------------------------
# Main Endpoint
# -------------------------------------------------------

@router.post("/generate-consignee")
async def generate_consignee(data: dict):
    """
    Generate consignee record for a given country.
    """
    try:
        country = data.get("country")
        valid_countries = ["Russia", "Kazakhstan", "Kyrgyzstan", "Uzbekistan"]

        if country not in valid_countries:
            raise HTTPException(status_code=400, detail=f"Country must be one of {valid_countries}")

        # Seed random for each request (more reproducible but still random)
        random.seed(datetime.now().timestamp())

        # ✅ Strict JSON prompt
        prompt = f"""
        Generate one realistic consignee record for {country}.
        Requirements:
        - Output must be in **pure JSON** (no explanations, no markdown).
        - Use **only Latin alphabet** (no Cyrillic or special characters).
        - Fields: "consignee_name" and "consignee_address".
        - Name should look like a real full person name from {country}.
        - Address should look natural for {country} (include city and street).
        Example format:
        {{
          "consignee_name": "Aidar Nurlanov",
          "consignee_address": "45 Abai Avenue, Almaty"
        }}
        """

        # 🔮 OpenAI generation
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data generator producing clean JSON using Latin alphabet."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.9,
        )

        raw_output = response.choices[0].message.content.strip()

        # 🧹 Extract valid JSON safely
        try:
            start = raw_output.find("{")
            end = raw_output.rfind("}")
            if start != -1 and end != -1:
                data_json = json.loads(raw_output[start:end + 1])
            else:
                raise ValueError("No valid JSON found in model output.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON returned: {raw_output}")

        # ✅ Enrich with IIN and Phone
        data_json["consignee_iin"] = generate_iin(country)
        data_json["consignee_tel"] = generate_phone(country)

        return JSONResponse(
            content={
                "country": country,
                "data": data_json,
                "generated_at": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
