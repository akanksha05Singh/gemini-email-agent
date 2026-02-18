import google.generativeai as genai
import logging
import json
import typing_extensions as typing
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Define the schema using TypedDict for clear structure if using response_schema (future proof)
# For now, we rely on the prompt + JSON validation as requested.

class GeminiAgent:
    """
    Interface for Google's Gemini 2.5 Flash model.
    Enforces strict JSON structured output.
    """
    def __init__(self, api_key: str, model_name: str, system_prompt_path: str):
        if not api_key:
            raise ValueError("API Key required for GeminiAgent")
            
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.system_instruction = self._load_prompt(system_prompt_path)
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_instruction
        )
        
        # Generation config to encourage JSON
        self.generation_config = genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=1024,
            response_mime_type="application/json"
        )

    def _load_prompt(self, path: str) -> str:
        try:
            with open(path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"System prompt file not found: {path}")
            return "You are a helpful assistant. Output valid JSON."

    def analyze_email(self, email_text: str, sender: str, subject: str) -> Dict[str, Any]:
        """
        Analyze email and return structured data.
        """
        user_prompt = f"""
Input Email:
[Sender]: {sender}
[Subject]: {subject}
[Body]:
{email_text}
"""
        try:
            response = self.model.generate_content(
                user_prompt,
                generation_config=self.generation_config
            )
            
            # Parse JSON
            # Gemini typically returns the JSON text directly when response_mime_type is set
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3].strip()
                
            data = json.loads(clean_text)
            
            # Basic schema validation
            required_keys = ["intent", "priority", "confidence_score", "reasoning"]
            for key in required_keys:
                if key not in data:
                    logger.warning(f"Missing key in AI response: {key}")
                    # We could raise error or fill defaults
            
            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {e}. Raw response: {response.text}")
            return self._get_fallback_response("JSON Error")
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return self._get_fallback_response("API Error")

    def _get_fallback_response(self, reasoning: str) -> Dict[str, Any]:
        return {
            "intent": "Other",
            "priority": "Low",
            "confidence_score": 0.0,
            "entities": {},
            "suggested_response": "",
            "reasoning": reasoning
        }
