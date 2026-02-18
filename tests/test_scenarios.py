import unittest
from unittest.mock import MagicMock
from src.rule_engine import RuleEngine
from src.safety_layer import SafetyLayer
from src.config_manager import SafetyConfig, AppConfig

class TestScenarios(unittest.TestCase):
    def setUp(self):
        # Mock Config: Match config.yaml rules
        self.rules = [
            {"name": "Urgent Meeting Request", "condition": {"intent": "Meeting", "priority": "High"}, "actions": [{"type": "label", "value": "Urgent-Meeting"}, {"type": "draft_reply", "template": "response_templates/meeting_confirm.txt"}]},
            {"name": "Newsletter Archive", "condition": {"intent": "Newsletter"}, "actions": [{"type": "label", "value": "Newsletters"}, {"type": "archive"}]},
            {"name": "Spam Block", "condition": {"intent": "Spam"}, "actions": [{"type": "label", "value": "Potential-Spam"}]}
        ]
        self.rule_engine = RuleEngine(self.rules)
        self.safety_layer = SafetyLayer(SafetyConfig(min_confidence_for_auto_action=0.85, min_confidence_for_draft=0.60))

    def test_scenario_a_meeting_request_high_conf(self):
        """Scenario A: 'Can we meet tomorrow?' -> Drafts a reply (High Confidence)."""
        ai_output = {
            "intent": "Meeting",
            "priority": "High",
            "entities": {"time": "tomorrow 10 AM"},
            "suggested_response": "Sure, let's meet.",
            "confidence_score": 0.95,
            "reasoning": "Sender requested a meeting unambiguously."
        }
        
        # Rule Engine check
        actions = self.rule_engine.evaluate(ai_output)
        self.assertTrue(any(a['type'] == 'draft_reply' for a in actions), "Should trigger draft_reply")
        
        # Safety Check (High Confidence -> Send allowed, but rule only asks for Draft anyway)
        mode = self.safety_layer.determine_execution_mode(ai_output['confidence_score'])
        self.assertEqual(mode, "send") # AI is confident enough to send if asked
        
        # But since the rule is 'draft_reply', the final result is a Draft.
        safe_action = self.safety_layer.validate_action("draft_reply", ai_output['confidence_score'])
        self.assertEqual(safe_action, "draft_reply")

    def test_scenario_b_newsletter(self):
        """Scenario B: 'Weekly Newsletter' -> Archives (High Confidence)."""
        ai_output = {
            "intent": "Newsletter",
            "priority": "Low",
            "entities": {},
            "suggested_response": "",
            "confidence_score": 0.99,
            "reasoning": "Contains unsubscribe link and weekly digest pattern."
        }
        
        actions = self.rule_engine.evaluate(ai_output)
        self.assertTrue(any(a['type'] == 'archive' for a in actions), "Should trigger archive")
        
        mode = self.safety_layer.determine_execution_mode(ai_output['confidence_score'])
        self.assertEqual(mode, "send") # Confident enough to execute 'archive' without review

    def test_scenario_c_urgent_server_down_low_conf(self):
        """Scenario C: 'URGENT: Server Down' (Low Confidence) -> Human Review."""
        ai_output = {
            "intent": "Urgent", # Maybe misclassified?
            "priority": "High",
            "entities": {"server": "Prod DB"},
            "suggested_response": "I am looking into it.",
            "confidence_score": 0.55, # VERY LOW
            "reasoning": "Unclear if sender is authorized."
        }
        
        # Rule Engine might match 'Urgent' rules, or fallback
        # Let's say it matches a hypothetical urgent rule
        # But Safety Layer MUST block it.
        
        mode = self.safety_layer.determine_execution_mode(ai_output['confidence_score'])
        self.assertEqual(mode, "manual", "Low confidence must force manual review")

    def test_scenario_d_lottery_scam(self):
        """Scenario D: 'You won a lottery!' -> Spam/Ignore."""
        ai_output = {
            "intent": "Spam",
            "priority": "Low",
            "entities": {},
            "confidence_score": 0.98,
            "reasoning": "classic lottery scam pattern"
        }
        
        actions = self.rule_engine.evaluate(ai_output)
        self.assertTrue(any(a['value'] == 'Potential-Spam' for a in actions), "Should label as Potential-Spam")

if __name__ == '__main__':
    unittest.main()
