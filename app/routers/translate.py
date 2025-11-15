from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
import os
import json

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Valid language codes
VALID_LANGUAGES = ["ru", "en", "uz", "kz", "ko"]

@router.post("/translate")
async def translate_text(data: dict):
    """
    Translate text from source language to multiple target languages using OpenAI.
    
    Request body:
    {
        "source": "ru",
        "text": "Мерседес",
        "targets": ["en", "uz", "kz", "ko"]
    }
    
    Response:
    {
        "translations": {
            "en": "Mercedes",
            "uz": "Mercedes",
            "kz": "Мерседес",
            "ko": "메르세데스"
        }
    }
    """
    try:
        # Validate input
        source = data.get("source")
        text = data.get("text")
        targets = data.get("targets")
        
        if not source:
            raise HTTPException(status_code=400, detail="'source' field is required")
        if not text:
            raise HTTPException(status_code=400, detail="'text' field is required")
        if not targets or not isinstance(targets, list):
            raise HTTPException(status_code=400, detail="'targets' must be a non-empty array")
        
        # Validate language codes
        if source not in VALID_LANGUAGES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid source language code. Must be one of: {VALID_LANGUAGES}"
            )
        
        for target in targets:
            if target not in VALID_LANGUAGES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid target language code '{target}'. Must be one of: {VALID_LANGUAGES}"
                )
        
        # Remove source from targets if present (no need to translate to itself)
        targets = [t for t in targets if t != source]
        
        if not targets:
            # If only source language in targets, return source text
            return JSONResponse(content={"translations": {source: text}})
        
        # Create structured prompt for OpenAI
        language_names = {
            "ru": "Russian",
            "en": "English",
            "uz": "Uzbek",
            "kz": "Kazakh",
            "ko": "Korean"
        }
        
        target_languages_str = ", ".join([f"{code} ({language_names[code]})" for code in targets])
        
        prompt = f"""
Translate the following text from {language_names.get(source, source)} to the specified target languages.

Source text: "{text}"
Source language: {source} ({language_names.get(source, source)})
Target languages: {target_languages_str}

Requirements:
- Output must be in **pure JSON format** (no explanations, no markdown, no code blocks).
- Return a JSON object where keys are language codes and values are the translated text.
- Ensure translations are accurate and natural for each target language.
- Preserve proper names and brand names when appropriate (e.g., "Mercedes" may remain "Mercedes" in some languages).
- For languages that use different scripts (Cyrillic, Latin, Hangul), use the appropriate script.

Example output format:
{{
  "en": "Mercedes",
  "uz": "Mercedes",
  "kz": "Мерседес",
  "ko": "메르세데스"
}}

Return ONLY the JSON object, nothing else.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Always return valid JSON with language codes as keys and translated text as values. Do not include any explanations or markdown formatting."
                },
                {"role": "user", "content": prompt.strip()},
            ],
            max_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent translations
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks if present)
        try:
            # Remove markdown code blocks if present
            cleaned = raw_output.replace("```json", "").replace("```", "").strip()
            
            # Find JSON object
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            
            if start == -1 or end == -1:
                raise ValueError("No valid JSON object found in response")
            
            translations_json = json.loads(cleaned[start:end + 1])
            
            # Validate that all target languages are present
            missing_targets = [t for t in targets if t not in translations_json]
            if missing_targets:
                raise ValueError(f"Missing translations for: {missing_targets}")
            
            # Return in the required format
            return JSONResponse(content={"translations": translations_json})
            
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse translation response as JSON: {str(e)}. Raw response: {raw_output[:200]}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing translation response: {str(e)}. Raw response: {raw_output[:200]}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")


@router.post("/generate-listing")
async def generate_listing(data: dict):
    """
    Generate structured car listing with multilingual content from car description text.
    
    Request body:
    {
        "text": "Mercedes-Benz E-Class 2022\nAutomatic transmission, Gasoline engine\n..."
    }
    
    Response: Complete car listing structure with all 5 languages (ru, en, uz, kz, ko)
    """
    try:
        # Validate input
        text = data.get("text")
        
        if not text or not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=400, detail="'text' field is required and must be a non-empty string")
        
        # Language names for reference
        language_names = {
            "ru": "Russian",
            "en": "English",
            "uz": "Uzbek",
            "kz": "Kazakh",
            "ko": "Korean"
        }
        
        # Create comprehensive prompt for OpenAI
        prompt = f"""
You are an expert car listing data extractor and multilingual content generator. Analyze the following car description text and generate a complete structured car listing.

INPUT TEXT:
{text}

TASK:
1. Extract all available information from the input text (make, model, year, specs, features, etc.)
2. Research and fill in any missing information about the car model (use your knowledge to complete gaps)
3. Generate multilingual content in ALL 5 languages: Russian (ru), English (en), Uzbek (uz), Kazakh (kz), Korean (ko)
4. Create short, informative descriptions in all languages
5. Reference the original input text extensively when generating descriptions

REQUIRED OUTPUT STRUCTURE (pure JSON, no markdown):
{{
  "listingId": "optional_string_or_null",
  "specs": {{
    "year": 2022,
    "mileageKm": 15000,
    "fuelType": "gasoline" | "diesel" | "hybrid" | "electric",
    "transmission": "automatic" | "manual" | "cvt",
    "engineDisplacementCc": 2000,
    "priceKRW": 35000000,
    "currency": "KRW"
  }},
  "text": {{
    "make": {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }},
    "model": {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }},
    "trim": {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }},
    "color": {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }},
    "interiorColor": {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }},
    "description": {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }}
  }},
  "additionalOptions": [
    {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }}
  ],
  "inspectionHistory": {{
    "accidents": false,
    "maintenanceHistory": {{ "ru": "...", "en": "...", "uz": "...", "kz": "...", "ko": "..." }}
  }}
}}

CRITICAL REQUIREMENTS:
- Extract ALL specs from the input text (year, mileage, fuel type, transmission, engine size, price if mentioned)
- If information is missing, use your knowledge to fill reasonable defaults based on the car model
- ALL multilingual fields MUST include all 5 languages: ru, en, uz, kz, ko
- Descriptions should be short (2-4 sentences) but informative
- Reference specific details from the input text in descriptions
- Use appropriate scripts: Cyrillic for ru/kz, Latin for en/uz, Hangul for ko
- Preserve brand names appropriately (e.g., "Mercedes-Benz" may stay as-is in some languages)
- Generate realistic additional options based on the car model and input text
- If accidents are mentioned, set accidents to true, otherwise false
- Generate maintenance history descriptions in all languages

Return ONLY the JSON object, no explanations, no markdown formatting, no code blocks.
        """
        
        # Call OpenAI API with higher token limit for comprehensive response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert car data extractor and multilingual content generator. Always return valid JSON in the exact structure specified. Extract all information from input text, fill gaps with your knowledge, and generate accurate translations in all 5 languages (ru, en, uz, kz, ko)."
                },
                {"role": "user", "content": prompt.strip()},
            ],
            max_tokens=3000,
            temperature=0.4,  # Balanced creativity and consistency
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Extract and parse JSON
        try:
            # Remove markdown code blocks if present
            cleaned = raw_output.replace("```json", "").replace("```", "").strip()
            
            # Find JSON object
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            
            if start == -1 or end == -1:
                raise ValueError("No valid JSON object found in response")
            
            listing_json = json.loads(cleaned[start:end + 1])
            
            # Validate structure and ensure all required multilingual fields have all 5 languages
            required_text_fields = ["make", "model", "trim", "color", "interiorColor", "description"]
            required_languages = VALID_LANGUAGES
            
            # Validate text fields
            if "text" not in listing_json:
                raise ValueError("Missing 'text' field in response")
            
            for field in required_text_fields:
                if field not in listing_json["text"]:
                    raise ValueError(f"Missing 'text.{field}' field in response")
                
                field_data = listing_json["text"][field]
                if not isinstance(field_data, dict):
                    raise ValueError(f"'text.{field}' must be an object with language codes")
                
                missing_langs = [lang for lang in required_languages if lang not in field_data]
                if missing_langs:
                    raise ValueError(f"'text.{field}' missing languages: {missing_langs}")
            
            # Validate additionalOptions
            if "additionalOptions" not in listing_json:
                listing_json["additionalOptions"] = []
            elif not isinstance(listing_json["additionalOptions"], list):
                raise ValueError("'additionalOptions' must be an array")
            else:
                for i, option in enumerate(listing_json["additionalOptions"]):
                    if not isinstance(option, dict):
                        raise ValueError(f"'additionalOptions[{i}]' must be an object")
                    missing_langs = [lang for lang in required_languages if lang not in option]
                    if missing_langs:
                        raise ValueError(f"'additionalOptions[{i}]' missing languages: {missing_langs}")
            
            # Validate inspectionHistory
            if "inspectionHistory" not in listing_json:
                listing_json["inspectionHistory"] = {
                    "accidents": False,
                    "maintenanceHistory": {lang: "" for lang in required_languages}
                }
            else:
                if "maintenanceHistory" not in listing_json["inspectionHistory"]:
                    listing_json["inspectionHistory"]["maintenanceHistory"] = {lang: "" for lang in required_languages}
                else:
                    maint_history = listing_json["inspectionHistory"]["maintenanceHistory"]
                    missing_langs = [lang for lang in required_languages if lang not in maint_history]
                    if missing_langs:
                        # Fill missing languages
                        for lang in missing_langs:
                            maint_history[lang] = ""
            
            # Ensure specs object exists
            if "specs" not in listing_json:
                listing_json["specs"] = {}
            
            # Return the validated listing
            return JSONResponse(content=listing_json)
            
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse listing response as JSON: {str(e)}. Raw response: {raw_output[:500]}"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid listing structure: {str(e)}. Raw response: {raw_output[:500]}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing listing response: {str(e)}. Raw response: {raw_output[:500]}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Listing generation error: {str(e)}")

