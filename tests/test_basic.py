import unittest
from unittest.mock import MagicMock
from src.safety_layer import SafetyLayer
from src.config_manager import SafetyConfig, AppConfig

class TestSafetyLayer(unittest.TestCase):
    def setUp(self):
        # Mock configuration
        self.mock_config = SafetyConfig(
            min_confidence_for_auto_action=0.85,
            min_confidence_for_draft=0.60
        )
        self.safety_layer = SafetyLayer(self.mock_config)
        # Mock state saving to avoid file I/O
        self.safety_layer._save_state = MagicMock()
        self.safety_layer._load_state = MagicMock()
        self.safety_layer.state = {"sent_log": []}

    def test_high_confidence_allows_send(self):
        """Test that high confidence (>= 0.85) allows 'send' mode."""
        mode = self.safety_layer.determine_execution_mode(0.90)
        self.assertEqual(mode, "send")

    def test_medium_confidence_forces_draft(self):
        """Test that medium confidence (0.60 - 0.84) forces 'draft' mode."""
        mode = self.safety_layer.determine_execution_mode(0.75)
        self.assertEqual(mode, "draft")

    def test_low_confidence_forces_manual(self):
        """Test that low confidence (< 0.60) forces 'manual' mode."""
        mode = self.safety_layer.determine_execution_mode(0.40)
        self.assertEqual(mode, "manual")

    def test_validate_action_downgrades_send(self):
        """Test that 'send' is downgraded to 'draft' if confidence logic disagrees."""
        # Scenario: Rule engine says "Send", but confidence is only 0.70
        safe_mode = self.safety_layer.validate_action("send", 0.70)
        self.assertEqual(safe_mode, "draft")

    def test_validate_action_allows_send(self):
        """Test that 'send' is allowed if confidence is high."""
        # Scenario: Rule engine says "Send", confidence is 0.90
        safe_mode = self.safety_layer.validate_action("send", 0.90)
        self.assertEqual(safe_mode, "send")

if __name__ == '__main__':
    unittest.main()
