import time
import json
import os
import logging
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SafetyLayer:
    """
    Enforces safety policies:
    1. Confidence Thresholds (Auto-Send vs Draft).
    2. Rate Limiting (Emails per hour).
    """
    def __init__(self, config: Any):
        self.config = config
        self.state_file = "safety_state.json"
        self._load_state()

    def _load_state(self):
        """Load rate limit counters from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            except:
                self.state = {"sent_log": []}
        else:
            self.state = {"sent_log": []}

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error(f"Failed to save safety state: {e}")

    def check_rate_limit(self) -> bool:
        """
        Check if we are within the hourly rate limit.
        """
        if not self.config.rate_limit.enabled:
            return True

        limit = self.config.rate_limit.max_emails_per_hour
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        # Filter logs generally
        valid_logs = [ts for ts in self.state.get("sent_log", []) 
                      if datetime.fromisoformat(ts) > one_hour_ago]
        
        self.state["sent_log"] = valid_logs
        self._save_state()

        if len(valid_logs) >= limit:
            logger.warning("Rate limit exceeded.")
            return False
        return True

    def record_action(self):
        """Record an action (email sent) for rate limiting."""
        self.state["sent_log"].append(datetime.now().isoformat())
        self._save_state()

    def determine_execution_mode(self, confidence: float) -> str:
        """
        Decide between 'send' and 'draft' based on confidence.
        """
        if confidence >= self.config.min_confidence_for_auto_action:
            return "send"
        elif confidence >= self.config.min_confidence_for_draft:
            return "draft"
        else:
            return "manual" # Meaning just label/log, don't even draft

    def validate_action(self, proposed_mode: str, confidence: float) -> str:
        """
        Final safety gate. 
        If proposed is 'send' but safety checks fail, downgrade to 'draft'.
        """
        # 1. Check Rate Limit
        if proposed_mode == "send":
            if not self.check_rate_limit():
                logger.warning("Downgrading to DRAFT due to rate limit.")
                return "draft"

        # 2. Check Confidence (Double check)
        # If the code logic elsewhere proposed 'send' but confidence is actually low
        safe_mode = self.determine_execution_mode(confidence)
        
        if proposed_mode == "send" and safe_mode != "send":
            logger.warning(f"Downgrading to {safe_mode.upper()} due to confidence {confidence}.")
            return safe_mode
            
        return proposed_mode
