#!/usr/bin/env python3
"""
Check for technical jargon in user‑facing strings.
"""

import os
import re
import sys

# List of forbidden words (jargon)
FORBIDDEN = [
    "department", "worker", "registry", "pipeline", "scheduler",
    "capability", "execution", "engine", "planner", "board",
    "chief of staff", "event bus", "eventbus", "tool registry",
    "knowledge librarian", "secure memory", "synapse interface",
    "security module", "user manager", "model manager",
]

# Paths to scan
SCAN_PATHS = [
    "src/executive/mind.py",
    "src/templates.py",
    "src/core/constitution.py",
    "src/gui.py",
    "src/api.py",      # only strings in responses
]

def scan_file(filepath):
    errors = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments and docstrings
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        # Skip code lines (def, class, import, etc.)
        if re.match(r'^(def|class|import|from|return|if|else|elif|for|while|try|except|with|async|await|@)', stripped):
            continue
        for word in FORBIDDEN:
            if word.lower() in line.lower():
                errors.append((filepath, i, line.strip(), word))
    return errors

def main():
    found = False
    for path in SCAN_PATHS:
        if not os.path.exists(path):
            print(f"Warning: {path} not found, skipping.")
            continue
        errors = scan_file(path)
        for filepath, line_num, content, word in errors:
            print(f"❌ Jargon found: {filepath}:{line_num}: '{content}'")
            print(f"   Contains forbidden word: '{word}'")
            found = True
    if found:
        sys.exit(1)
    else:
        print("✅ No jargon found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
