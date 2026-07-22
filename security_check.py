#!/usr/bin/env python3
"""
Pre-commit hook to prevent accidental commits of sensitive files.

Usage:
  1. Copy this file to .git/hooks/pre-commit
  2. Make it executable: chmod +x .git/hooks/pre-commit
  3. Or run manually: python security_check.py

This prevents committing:
  - .env files
  - .streamlit/secrets.toml
  - API keys in code
"""

import os
import sys
import re
import subprocess
from pathlib import Path

# Files that should NEVER be committed
FORBIDDEN_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".streamlit/secrets.toml",
    "secrets.json",
}

# Patterns that might indicate exposed keys
SENSITIVE_PATTERNS = [
    r"sk-ant-[a-zA-Z0-9\-]{20,}",  # Anthropic keys
    r"ANTHROPIC_API_KEY\s*=\s*['\"]sk-ant",
    r"password\s*=\s*['\"][^'\"]{5,}['\"]",  # Any password assignment
    r"api.?key\s*=\s*['\"][^'\"]{10,}['\"]",  # Any API key assignment
]


def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd()
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1


def check_forbidden_files():
    """Check if any forbidden files are staged for commit."""
    stdout, _, _ = run_command("git diff --cached --name-only")
    staged_files = stdout.strip().split("\n")
    
    violations = []
    for file in staged_files:
        if file in FORBIDDEN_FILES or any(forbidden in file for forbidden in FORBIDDEN_FILES):
            violations.append(f"  ❌ {file}")
    
    return violations


def check_sensitive_content():
    """Check for sensitive patterns in staged changes."""
    stdout, _, _ = run_command("git diff --cached")
    violations = []
    
    for i, line in enumerate(stdout.split("\n"), 1):
        # Only check added lines (starting with +)
        if line.startswith("+") and not line.startswith("+++"):
            for pattern in SENSITIVE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(f"  ❌ Line {i}: Possible API key or secret detected")
                    violations.append(f"     {line[:80]}...")
                    break
    
    return violations


def main():
    """Run security checks."""
    print("\n🔒 Running pre-commit security checks...\n")
    
    all_violations = []
    
    # Check forbidden files
    print("📋 Checking for forbidden files...")
    file_violations = check_forbidden_files()
    if file_violations:
        print("\n⚠️  FORBIDDEN FILES DETECTED:\n" + "\n".join(file_violations))
        all_violations.extend(file_violations)
    else:
        print("✅ No forbidden files detected")
    
    # Check sensitive content
    print("\n📝 Checking for sensitive content (API keys, passwords)...")
    content_violations = check_sensitive_content()
    if content_violations:
        print("\n⚠️  POSSIBLE SECRETS DETECTED:\n" + "\n".join(content_violations))
        all_violations.extend(content_violations)
    else:
        print("✅ No sensitive content detected")
    
    # Summary
    print("\n" + "=" * 60)
    if all_violations:
        print(f"\n❌ Security check FAILED - {len(all_violations)} violation(s)\n")
        print("DO NOT COMMIT FILES CONTAINING SECRETS!\n")
        print("If you need to commit:", "- Remove the secrets")
        print("- Or use: git reset HEAD <file>")
        print("\n" + "=" * 60)
        return 1  # Fail the commit
    else:
        print("\n✅ Security check PASSED - Safe to commit\n")
        return 0  # Allow the commit


if __name__ == "__main__":
    sys.exit(main())
