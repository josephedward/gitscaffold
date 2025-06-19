#!/usr/bin/env python3
"""
Alias script to auto-generate GitHub milestones and issues from ROADMAP.md.
Wrapper around github_setup_from_roadmap.py for convenient invocation.
"""
import os
import sys

# Ensure scripts/ directory is on sys.path for imports
script_dir = os.path.dirname(__file__)
sys.path.insert(0, script_dir)

try:
    from github_setup import main
except ImportError:
    sys.stderr.write("Error: cannot import github_setup from github_setup.py.\n")
    sys.exit(1)

if __name__ == '__main__':
    main()