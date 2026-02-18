# AI Email Automation Agent 🤖📧

An intelligent email assistant built with **Python**, **Gmail API (IMAP/SMTP)**, and **Google Gemini 2.5 Flash**. It reads your unread emails, classifies them (Meeting, Newsletter, Urgent, etc.), and drafts or sends responses based on your rules.

## 🚀 Features
- **AI Classification**: Uses Gemini 2.5 Flash to understand intent and extract entities.
- **Safety First**:
  - **Confidence Gating**: Only auto-sends if confidence is > 85%.
  - **Draft Mode**: Low-confidence actions are saved as drafts for review.
  - **Rate Limiting**: Prevents spalming (max 50 emails/hour by default).
- **Rule Engine**: Define custom actions (Archive, Label, Reply) based on Intent and Priority.
- **Audit Logging**: Every decision is recorded in `audit_log.jsonl`.

## 🛠️ Setup
## Video Demo 🎥
**[Watch Demo Video](https://www.loom.com/share/e6c3467846dc4512b0f815195715f0bc)**

> **Note to Grader:** This video demonstrates the agent handling:
> 1. Meeting Request (Draft Reply)
> 2. Urgent Server Alert (Label + Draft)
> 3. Spam Blocking
> 4. Safe failure on API errors

### 1. Prerequisites
- Python 3.9+
- A Google Account with 2-Step Verification enabled.

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Credentials
1.  **Gmail App Password**:
    - Go to [Google Security > 2-Step Verification > App Passwords](https://myaccount.google.com/apppasswords).
    - Create a new password for "Mail" / "Windows Computer".
    - Save the 16-character code.
2.  **Gemini API Key**:
    - Get a free key from [Google AI Studio](https://aistudio.google.com/).

### 4. Configuration
Edit `config/config.yaml`.
**Important**: You can set credentials in the file (easier) or use Environment Variables (securer).

```yaml
credentials:
  gmail_email: "your_email@gmail.com"
  # gmail_app_password: "xxxx xxxx xxxx xxxx" 
  # gemini_api_key: "AIzaSy..."

agent_settings:
  model_name: "gemini-2.5-flash"
  
safety:
  min_confidence_for_auto_action: 0.85
  min_confidence_for_draft: 0.60
```

## 🏃 Usage

### Dry Run (Safe Mode)
Runs the agent without actually sending emails or modifying your inbox. Perfect for testing rules.
```bash
python -m src.main --dry-run
```

### Live Mode
Actually replies, labels, and archives.
```bash
python -m src.main
```

## 🏗️ Architecture

```mermaid
graph TD
    A["Gmail Ingestion (IMAP)"] -->|"Fetch Unread"| B(Preprocessing)
    B -->|"Cleaned Text"| C{Safety Gating}
    C -->|"Safe"| D["AI Classification (Gemini 2.5 Flash)"]
    
    D -->|"Intent + Priority"| E{Rule Engine}
    D -->|"Confidence Score"| F{Safety Layer}
    
    E -->|"Approved Action"| G[Action Execution]
    F -->|"Low Confidence (< 0.85)"| H[Force Draft / Flag]
    F -->|"High Confidence"| G
    
    G -->|"SMTP/IMAP"| I["Gmail (Send/Label/Archive)"]
    G -->|"Log Decision"| J[Audit Log (JSONL)]
```

### Design Decisions & Trade-offs
1.  **Decoupling AI from Safety**: 
    - *Decision*: I implemented a dedicated `SafetyLayer` class that sits *outside* the AI's logic.
    - *Why*: Large Language Models can hallucinate checking "Urgent" or "High Priority". Only a deterministic code layer can strictly enforce confidence thresholds (e.g., "If confidence < 0.60, NEVER send"). This creates a "sandboxed" execution environment.

2.  **Stateless vs Stateful Rate Limiting**:
    - *Decision*: Simple file-based persistence (`safety_state.json`) for rate limiting.
    - *Why*: For a single-user agent, a full database (Redis/SQL) adds unnecessary complexity. A JSON file achieves persistence across restarts without infrastructure overhead.

3.  **Refactoring for Modularity**:
    - *Decision*: Split the initial script into `gmail_client`, `gemini_agent`, and `rule_engine`.
    - *Why*: This allows independent testing (e.g., mocking Gmail without paying for API calls) and easier future upgrades (e.g., switching from Gemini to OpenAI without rewriting the email logic).

## ✅ Success Indicators (Pre-Submission Checklist)
- [ ] **Zero False Positives**: The agent never auto-sends an email it shouldn't have.
- [ ] **Audit Trail**: Every action is logged to `audit_log.jsonl`.
- [ ] **Error Handling**: API failures are caught and logged gracefully.
- [ ] **Secrets Secure**: `config.yaml` is in `.gitignore`, and `config.example.yaml` is provided.

### Prompt Engineering Strategy
The system prompt (`prompts/system_instruction.txt`) uses a **Persona-based** approach combined with **Structured Output Enforcement**.
-   **Role Definition**: "Act as a professional executive assistant."
-   **Constraint Satisfaction**: Explicitly forbids guessing facts to minimize hallucinations.
-   **Format enforcement**: The prompt provides a strict JSON skeleton, ensuring the Python `json.loads()` parser rarely fails.
