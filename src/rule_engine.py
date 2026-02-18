from typing import Dict, Any, List
import logging
from src.config_manager import RuleConfig # Import validation model if needed

logger = logging.getLogger(__name__)

class RuleEngine:
    def __init__(self, rules: List[Any]):
        """
        Initialize with a list of RuleConfig objects or dicts.
        """
        self.rules = rules

    def evaluate(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate the AI analysis against the rules.
        Returns a list of actions to take.
        """
        matched_actions = []
        
        intent = analysis.get("intent")
        priority = analysis.get("priority")
        
        for rule in self.rules:
            # Handle both Pydantic model and Dict
            if hasattr(rule, 'condition'):
                condition = rule.condition
                actions = [a.model_dump() for a in rule.actions]
                rule_name = rule.name
            else:
                condition = rule.get("condition", {})
                actions = rule.get("actions", [])
                rule_name = rule.get("name")
            
            # Simple Exact Match Logic
            match = True
            if "intent" in condition and condition["intent"] != intent:
                match = False
            if "priority" in condition and condition["priority"] != priority:
                match = False
            
            if match:
                logger.info(f"Rule Matched: {rule_name}")
                matched_actions.extend(actions)
        
        return matched_actions
