import yaml
import os
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# --- Pydantic Models for Configuration ---

class CredentialsConfig(BaseModel):
    gmail_email: str = Field(..., description="Gmail email address")
    gmail_app_password: Optional[str] = Field(None, description="App password (prefer env var)")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API key (prefer env var)")

class AgentSettingsConfig(BaseModel):
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.2
    max_output_tokens: int = 1024
    system_prompt_path: str = "prompts/system_instruction.txt"

class RateLimitConfig(BaseModel):
    enabled: bool = True
    max_emails_per_hour: int = 50

class SafetyConfig(BaseModel):
    min_confidence_for_auto_action: float = 0.85
    min_confidence_for_draft: float = 0.60
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    allowed_domains_for_reply: List[str] = Field(default_factory=lambda: ["*"])
    human_in_the_loop_label: str = "AI_REVIEW_NEEDED"

class ActionConfig(BaseModel):
    type: str
    value: Optional[str] = None
    template: Optional[str] = None

class RuleConfig(BaseModel):
    name: str
    condition: Dict[str, Any]
    actions: List[ActionConfig]

class AppConfig(BaseModel):
    credentials: CredentialsConfig
    agent_settings: AgentSettingsConfig
    safety: SafetyConfig
    rules: List[RuleConfig] = Field(default_factory=list)

# --- Config Manager Class ---

class ConfigManager:
    """
    Manages loading and validating configuration.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config: Optional[AppConfig] = None
        self.reload()

    def reload(self):
        """Load and validate the configuration file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Validate with Pydantic
            self.config = AppConfig(**raw_config)
            logger.info("Configuration loaded and validated successfully.")
            
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML: {e}")
            raise

    def get_config(self) -> AppConfig:
        if not self.config:
            self.reload()
        return self.config

    def get_credentials_from_env(self) -> Dict[str, str]:
        """
        Helper to resolve credentials from Config OR Environment variables.
        Env vars take precedence for security.
        """
        if not self.config:
            self.reload()
        
        creds = self.config.credentials
        
        return {
            "email": creds.gmail_email,
            "password": os.environ.get("GMAIL_APP_PASSWORD") or creds.gmail_app_password,
            "gemini_key": os.environ.get("GEMINI_API_KEY") or creds.gemini_api_key
        }
