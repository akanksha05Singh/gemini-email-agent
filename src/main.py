import logging
import argparse
import time
from typing import List, Dict, Any

from src.config_manager import ConfigManager
from src.gmail_client import GmailClient
from src.gemini_agent import GeminiAgent
from src.safety_layer import SafetyLayer
from src.rule_engine import RuleEngine
from src.audit import AuditLogger

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainOrchestrator")

def main():
    parser = argparse.ArgumentParser(description="Email Automation Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run without performing any actions on Gmail")
    args = parser.parse_args()

    logger.info(f"Starting Agent. Dry Run: {args.dry_run}")

    # 1. Load Config
    try:
        cfg_mgr = ConfigManager()
        config = cfg_mgr.get_config()
        secrets = cfg_mgr.get_credentials_from_env()
    except Exception as e:
        logger.critical(f"Config load failed: {e}")
        return

    # 2. Initialize Components
    if not secrets["password"] or not secrets["gemini_key"]:
        logger.critical("Missing Secrets (GMAIL_APP_PASSWORD or GEMINI_API_KEY).")
        return

    gmail_client = GmailClient(secrets["email"], secrets["password"])
    gemini_agent = GeminiAgent(
        api_key=secrets["gemini_key"],
        model_name=config.agent_settings.model_name,
        system_prompt_path=config.agent_settings.system_prompt_path
    )
    safety_layer = SafetyLayer(config.safety)
    rule_engine = RuleEngine(config.rules) # We can reuse the simple rule engine we built or enhance it
    audit_log = AuditLogger()

    # 3. Execution Flow
    try:
        # Fetch
        emails = gmail_client.fetch_unread_emails(limit=10)
        logger.info(f"Fetched {len(emails)} unread emails.")

        for email_data in emails:
            email_id = email_data['message_id']
            subject = email_data['subject']
            
            logger.info(f"Processing: {subject}")

            # Classify
            analysis = gemini_agent.analyze_email(
                email_text=email_data['body'], 
                sender=email_data['sender'],
                subject=subject
            )
            
            # Decisions
            confidence = analysis.get("confidence_score", 0.0)
            
            # Determine Matches
            rule_actions = rule_engine.evaluate(analysis) 
            logger.info(f"Rule Actions identified: {[a['type'] for a in rule_actions]}")
            
            executed_actions = []

            # By default, if rule engine says "reply", we check safety
            for action in rule_actions:
                act_type = action.get('type')
                
                # Handling Reply/Draft
                if act_type == 'draft_reply' or act_type == 'reply':
                    mode = "draft" if act_type == 'draft_reply' else "send"
                    
                    # Safety Gate
                    safe_mode = safety_layer.validate_action(mode, confidence)
                    
                    if safe_mode != "manual":
                        if args.dry_run:
                            logger.info(f"[DRY RUN] Would execute: {safe_mode.upper()} reply.")
                            executed_actions.append(f"DRY_RUN_{safe_mode}")
                        else:
                            # Use template text or AI text
                            response_text = analysis.get("suggested_response", "")
                            if not response_text:
                                logger.warning("No suggested response from AI, skipping reply.")
                                continue

                            # Execute
                            success = gmail_client.send_email(
                                to_email=email_data['sender'],
                                subject=f"Re: {subject}",
                                body=response_text,
                                reference_msg_id=email_data['message_id'],
                                reference_chain=email_data['references'],
                                mode=safe_mode
                            )
                            if success:
                                executed_actions.append(safe_mode)
                                if safe_mode == "send":
                                    safety_layer.record_action()

                # Handling Labels
                elif act_type == 'label':
                    label_val = action.get('value')
                    if args.dry_run:
                        logger.info(f"[DRY RUN] Would label: {label_val}")
                        executed_actions.append(f"DRY_RUN_LABEL_{label_val}")
                    else:
                        gmail_client.add_label(email_data["id"], label_val) # id is UID for imap
                        executed_actions.append(f"LABEL_{label_val}")

                # Handling Archive
                elif act_type == 'archive':
                    if args.dry_run:
                         logger.info(f"[DRY RUN] Would archive.")
                         executed_actions.append("DRY_RUN_ARCHIVE")
                    else:
                        gmail_client.archive_email(email_data["id"])
                        executed_actions.append("ARCHIVE")

            # Fallback for Low Confidence if no actions taken
            if confidence < config.safety.min_confidence_for_draft and not executed_actions:
                 logger.info("Low confidence, applying review label.")
                 review_label = config.safety.human_in_the_loop_label
                 if not args.dry_run:
                     gmail_client.add_label(email_data["id"], review_label)
                 executed_actions.append(f"LABEL_{review_label}")

            # Log
            audit_log.log_event(
                email_id=email_id,
                subject=subject,
                analysis=analysis,
                actions=executed_actions,
                status="Completed"
            )

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    except Exception as e:
        logger.exception(f"Fatal Error: {e}")
    finally:
        gmail_client.close()
        logger.info("Agent Shutdown.")

if __name__ == "__main__":
    main()
