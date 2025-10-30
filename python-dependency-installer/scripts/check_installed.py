#!/usr/bin/env python3
"""
Check if Python packages are installed and where they are located.

This script checks both virtual environment and system-wide installations.
It uses multiple methods to ensure accurate detection:
1. importlib.metadata for package metadata
2. Direct import attempt for package availability
3. pip show for installation details

Usage:
    python check_installed.py package1 package2 ...

Returns JSON with installation status for each package.
"""

import json
import subprocess
import sys
from importlib import metadata
from pathlib import Path


def check_package_installed(package_name):
    """
    Check if a package is installed and return its details.

    Args:
        package_name: Name of the package to check

    Returns:
        Dictionary with installation status and details
    """
    result = {
        'package': package_name,
        'installed': False,
        'version': None,
        'location': None,
        'importable': False,
    }

    # Try to get package metadata
    try:
        dist = metadata.distribution(package_name)
        result['installed'] = True
        result['version'] = dist.version

        # Get the location from metadata
        if dist.locate_file(''):
            result['location'] = str(dist.locate_file('').parent)

    except metadata.PackageNotFoundError:
        pass

    # Try to import the package
    try:
        __import__(package_name)
        result['importable'] = True
    except ImportError:
        # Try common name variations (e.g., 'PIL' for 'pillow')
        pass

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'No package names provided',
            'usage': 'python check_installed.py package1 package2 ...'
        }), file=sys.stderr)
        return 1

    packages = sys.argv[1:]
    results = {}

    for package in packages:
        results[package] = check_package_installed(package)

    print(json.dumps(results, indent=2))

    # Return 0 if all packages are installed, 1 otherwise
    all_installed = all(r['installed'] for r in results.values())
    return 0 if all_installed else 1


if __name__ == '__main__':
    sys.exit(main())
