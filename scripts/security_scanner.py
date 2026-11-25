import subprocess
import re
import os
import sys

def scan_tracked_files():
    print("=== SECURITY CHECK: Scanning Git-Tracked Files ===")
    
    # 1. Get all git tracked files
    res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    print(f"Total tracked files: {len(files)}")
    
    # Patterns to detect secrets
    patterns = {
        "Private Key": re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA|PGP|PRIVATE) KEY-----"),
        "Groq API Key": re.compile(r"gsk_[a-zA-Z0-9]{20,}"),
        "OpenAI API Key": re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        "Google API Key": re.compile(r"AIza[a-zA-Z0-9_-]{35}"),
        "GitHub Token": re.compile(r"(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}"),
        "Generic Secret Assignment": re.compile(r"(?i)(api_key|secret_key|private_key|auth_token)\s*=\s*['\"][a-zA-Z0-9_\-]{16,}['\"]"),
        "Password Assignment": re.compile(r"(?i)(password|passwd)\s*=\s*['\"][^'\"]{8,}['\"]"),
    }
    
    findings = []
    
    for f in files:
        # Check forbidden files
        if f.endswith(".env") or f == ".env" or "/.env" in f:
            findings.append((f, 0, "CRITICAL: .env file is tracked in git!"))
            continue
            
        if not os.path.exists(f):
            continue
            
        # Skip binary files
        if f.endswith(('.pth', '.db', '.sqlite3', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip')):
            continue
            
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, start=1):
                    # Skip common test/placeholder strings
                    if any(dummy in line for dummy in ["your_api_key_here", "dummy", "placeholder", "None", "os.getenv", "request.args"]):
                        continue
                    for name, pat in patterns.items():
                        if pat.search(line):
                            findings.append((f, line_no, f"Potential secret ({name}): {line.strip()[:60]}..."))
        except Exception as e:
            pass

    print(f"\nScan complete. Findings count: {len(findings)}")
    if findings:
        for f, line, desc in findings:
            print(f"  [!] {f}:{line} - {desc}")
        return False
    else:
        print("  [✓] No hardcoded API keys, private keys, or passwords found in tracked files.")
        print("  [✓] No .env files tracked in git.")
        return True

if __name__ == "__main__":
    success = scan_tracked_files()
    if not success:
        sys.exit(1)
