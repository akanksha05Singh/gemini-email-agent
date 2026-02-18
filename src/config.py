import yaml
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {config_path}")
            return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        raise

def get_agent_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get('agent_settings', {})

def get_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get('credentials', {})

def get_rules(config: Dict[str, Any]) -> list:
    return config.get('rules', [])

def get_safety_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get('safety', {})
