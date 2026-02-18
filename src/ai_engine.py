import google.generativeai as genai
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash", system_prompt_path: str = "prompts/system_instruction.txt"):
        """
        Initialize the AI Engine with Gemini API key and model settings.
        """
        if not api_key:
            raise ValueError("Gemini API Key is required.")
        
        genai.configure(api_key=api_key)
        
        self.model_name = model_name
        self.system_instruction = self._load_system_prompt(system_prompt_path)
        
        # Define the generation config with JSON schema enforcement if supported or standard JSON mode
        self.generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
            "response_mime_type": "application/json",
        }
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=self.system_instruction
        )

    def _load_system_prompt(self, path: str) -> str:
        try:
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            return "You are a helpful email assistant."

    def analyze_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email content to Gemini and get structured analysis.
        """
        prompt = self._construct_prompt(email_data)
        
        try:
            response = self.model.generate_content(prompt)
            return json.loads(response.text)
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from Gemini response.")
            # Return a fallback safe structure
            return {
                "intent": "Other",
                "priority": "Low",
                "entities": {"dates": [], "names": [], "action_items": []},
                "suggested_response": "",
                "confidence_score": 0.0,
                "reasoning": "JSON Parsing Error"
            }
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            raise

    def _construct_prompt(self, email_data: Dict[str, Any]) -> str:
        """
        Format the email data into a user prompt.
        """
        return f"""
Please analyze the following email:

From: {email_data.get('sender')}
Subject: {email_data.get('subject')}
Date: {email_data.get('date')}

Body:
{email_data.get('body')}
"""
