import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AuditLogger:
    def __init__(self, log_file: str = "audit_log.jsonl"):
        self.log_file = log_file

    def log_event(self, email_id: str, subject: str, analysis: Dict[str, Any], actions: list, status: str):
        """
        Log an event to the audit log file (JSONL format).
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "email_id": email_id,
            "subject": subject,
            "ai_analysis": analysis,
            "actions_triggered": actions,
            "status": status
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")
