#!/usr/bin/env python3
"""
Detect if the current environment is using a virtual environment.

This script checks for:
1. VIRTUAL_ENV environment variable (activated venv)
2. Common venv directory patterns (.venv, venv, env)

Returns JSON with venv status and path if found.
"""

import json
import os
import sys
from pathlib import Path


def detect_venv():
    """Detect if we're in a virtual environment and return its details."""

    # Check if a venv is currently activated
    venv_path = os.environ.get('VIRTUAL_ENV')
    if venv_path:
        return {
            'has_venv': True,
            'venv_path': venv_path,
            'is_activated': True,
            'detection_method': 'VIRTUAL_ENV environment variable'
        }

    # Check for common venv directory patterns in current working directory
    cwd = Path.cwd()
    common_venv_names = ['.venv', 'venv', 'env']

    for venv_name in common_venv_names:
        venv_dir = cwd / venv_name
        if venv_dir.exists() and venv_dir.is_dir():
            # Verify it looks like a venv (has bin/python or Scripts/python.exe)
            python_paths = [
                venv_dir / 'bin' / 'python',
                venv_dir / 'bin' / 'python3',
                venv_dir / 'Scripts' / 'python.exe',  # Windows
            ]

            if any(p.exists() for p in python_paths):
                return {
                    'has_venv': True,
                    'venv_path': str(venv_dir.absolute()),
                    'is_activated': False,
                    'detection_method': f'Found {venv_name} directory'
                }

    # No venv detected
    return {
        'has_venv': False,
        'venv_path': None,
        'is_activated': False,
        'detection_method': 'No venv detected'
    }


def main():
    result = detect_venv()
    print(json.dumps(result, indent=2))
    return 0 if result['has_venv'] else 1


if __name__ == '__main__':
    sys.exit(main())
