#!/usr/bin/env python3
"""
Test if a Python package can be imported and used.

This script attempts to:
1. Import the package
2. Get version information
3. Get package file location
4. Perform basic usage test if applicable

Usage:
    python test_package.py package_name [import_name]

If import_name is not provided, it defaults to package_name.
Some packages have different import names (e.g., 'pillow' installs as 'PIL').

Returns JSON with test results.
"""

import json
import sys
import traceback


def test_package(package_name, import_name=None):
    """
    Test if a package can be imported and used.

    Args:
        package_name: Name of the package (e.g., 'pandas')
        import_name: Import name if different from package name (e.g., 'PIL' for 'pillow')

    Returns:
        Dictionary with test results
    """
    if import_name is None:
        import_name = package_name

    result = {
        'package': package_name,
        'import_name': import_name,
        'import_success': False,
        'version': None,
        'file_location': None,
        'error': None,
        'api_key_required': False,
    }

    try:
        # Try to import the package
        module = __import__(import_name)
        result['import_success'] = True

        # Try to get version
        if hasattr(module, '__version__'):
            result['version'] = module.__version__
        elif hasattr(module, 'VERSION'):
            result['version'] = str(module.VERSION)
        elif hasattr(module, 'version'):
            result['version'] = str(module.version)

        # Get file location
        if hasattr(module, '__file__'):
            result['file_location'] = module.__file__

        # Check for common API key requirements
        api_key_indicators = ['api_key', 'API_KEY', 'openai', 'anthropic', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY']
        error_lower = str(result.get('error', '')).lower()
        if any(indicator.lower() in error_lower for indicator in api_key_indicators):
            result['api_key_required'] = True

    except ImportError as e:
        result['error'] = f'ImportError: {str(e)}'
        result['error_type'] = 'ImportError'
        result['traceback'] = traceback.format_exc()
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {str(e)}'
        result['error_type'] = type(e).__name__
        result['traceback'] = traceback.format_exc()

        # Check if error message suggests API key is needed
        if 'api' in str(e).lower() or 'key' in str(e).lower() or 'auth' in str(e).lower():
            result['api_key_required'] = True

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'No package name provided',
            'usage': 'python test_package.py package_name [import_name]'
        }), file=sys.stderr)
        return 1

    package_name = sys.argv[1]
    import_name = sys.argv[2] if len(sys.argv) > 2 else None

    result = test_package(package_name, import_name)
    print(json.dumps(result, indent=2))

    return 0 if result['import_success'] else 1


if __name__ == '__main__':
    sys.exit(main())
