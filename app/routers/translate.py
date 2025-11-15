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

