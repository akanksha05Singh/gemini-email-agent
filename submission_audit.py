import os
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# --- Configuration ---
REQUIRED_STRUCTURE = {
    "src": ["main.py", "gmail_client.py", "gemini_agent.py", "safety_layer.py"],
    "tests": ["test_scenarios.py"], 
    ".": ["config.yaml", "requirements.txt", "README.md", "Dockerfile", ".gitignore"]
}

README_CHECKLIST = [
    ("Video Demo", ["loom.com", "youtube.com", "drive.google.com", ".mp4", ".gif"]),
    ("Architecture Diagram", ["Architecture", "Diagram", "Flow"]),
    ("Setup Section", ["## Setup", "Installation"]),
    ("Configuration Section", ["## Configuration", "Config"]),
    ("Design Trade-offs", ["Trade-offs", "Design Decisions", "Why Gemini"])
]

SENSITIVE_KEYWORDS = ["password", "secret", "key", "token"]
SAFE_PLACEHOLDERS = ["your_", "enter_", "placeholder", "env_var"]

def print_result(msg, passed):
    tag = "[PASS]" if passed else "[FAIL]"
    print(f"{tag} {msg}")

def check_files():
    print("\n--- FILE CHECK ---")
    all_passed = True
    for folder, files in REQUIRED_STRUCTURE.items():
        if folder != ".":
            if not os.path.exists(folder):
                print_result(f"Missing Dir: {folder}", False)
                all_passed = False
                continue
        
        for file in files:
            path = os.path.join(folder, file) if folder != "." else file
            if os.path.exists(path):
                print_result(f"Found: {path}", True)
            else:
                if file in ["Dockerfile", ".gitignore"]:
                     print(f"[WARN] Missing bonus file: {file}")
                else:
                    print_result(f"MISSING: {file}", False)
                    all_passed = False
    return all_passed

def check_config_safety():
    print("\n--- SAFETY CHECK ---")
    if not os.path.exists("config.yaml"):
        return False
    
    with open("config.yaml", "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split('\n')
    leaks_found = False
    
    for i, line in enumerate(lines):
        lower_line = line.lower()
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in lower_line and ":" in line:
                val = line.split(":", 1)[1].strip()
                if not val or any(safe in val.lower() for safe in SAFE_PLACEHOLDERS):
                    continue
                if len(val) > 8 and " " not in val:
                    print(f"[FAIL] Potential Leak line {i+1}: {line.strip()}")
                    leaks_found = True

    if not leaks_found:
        print_result("Config matches safety standards", True)
    return not leaks_found

def check_readme():
    print("\n--- DOCS CHECK ---")
    if not os.path.exists("README.md"):
        print_result("README.md missing", False)
        return False

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    score = 0
    for section, keywords in README_CHECKLIST:
        found = any(k.lower() in content.lower() for k in keywords)
        print_result(f"README has '{section}'", found)
        if found: score += 1
        
    print(f"\nScore: {score}/{len(README_CHECKLIST)}")
    return score == len(README_CHECKLIST)

if __name__ == "__main__":
    print("STARTING AUDIT...")
    f_ok = check_files()
    s_ok = check_config_safety()
    r_ok = check_readme()
    
    if f_ok and s_ok and r_ok:
        print("\nRESULT: READY FOR SUBMISSION")
    else:
        print("\nRESULT: FIX ERRORS")
