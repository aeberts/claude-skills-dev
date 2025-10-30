---
name: python-dependency-installer
description: Automatically install missing Python dependencies when import errors occur or when explicitly requested by the user. Handle both virtual environment and system-wide installations using uv. This skill should be used when Python code fails with ImportError or ModuleNotFoundError, or when the user explicitly requests package installation (e.g., "install pandas").
---

# Python Dependency Installer

## Overview

Automatically install missing Python packages when import errors occur or when explicitly requested. Handle both virtual environment (.venv, venv, env) and system-wide installations (via pyenv) using the `uv` package manager. Verify installations with import and usage tests, and gracefully handle packages requiring API keys or special configuration.

## Trigger Conditions

This skill activates in two scenarios:

1. **Automatic Trigger**: When Python code execution results in an ImportError or ModuleNotFoundError
2. **Manual Trigger**: When the user explicitly requests package installation (e.g., "install pandas", "I need numpy installed")

## Workflow

### Step 1: Detect Environment

Before any installation, determine the target installation location:

1. Run `scripts/detect_env.py` to detect virtual environment:
   - Checks `VIRTUAL_ENV` environment variable (if venv is activated)
   - Checks for `.venv/`, `venv/`, or `env/` directories in current working directory
   - Returns JSON with venv status and path

2. Determine installation strategy:
   - **If venv detected**: Target virtual environment installation
   - **If no venv**: Target system-wide installation (pyenv-managed Python)

### Step 2: Check If Already Installed

Before installing, verify the package isn't already available:

1. Run `scripts/check_installed.py <package_name>` to check installation status
2. The script returns JSON with installation details including version and location

3. Handle different scenarios:
   - **Package not found anywhere**: Proceed to installation
   - **Package in system but working in venv**: Inform user and present options:
     - Option A: Install in venv as well
     - Option B: Skip installation
   - **Package already installed in target location**: Skip installation and inform user

**Note**: Always check installation status BEFORE asking for user confirmation to install.

### Step 3: Confirm Installation (Automatic Trigger Only)

For automatic triggers (import errors), ask user for confirmation before installing:

- Clearly state which package(s) will be installed
- Specify the installation location (venv or system-wide)
- Show the command that will be executed

For manual triggers, the user has already requested installation, so skip confirmation.

### Step 4: Install Package(s)

Install the package using `uv`:

**Virtual Environment Installation:**
```bash
uv pip install <package_name>
```

**System-Wide Installation (pyenv):**
```bash
uv pip install --system <package_name>
```

**Multiple Packages:**
```bash
uv pip install <package1> <package2> <package3>
```

Notes:
- `uv` automatically detects activated virtual environments
- For system-wide installs, `uv --system` targets the active Python version managed by pyenv
- Installation goes to `~/.pyenv/versions/<python_version>/lib/python<version>/site-packages/`
- Display installation progress and output to the user

### Step 5: Verify Installation

After installation, verify the package is available and functional:

1. **Basic Verification** - Run `uv pip show <package_name>` to confirm installation

2. **Import Test** - Run `scripts/test_package.py <package_name>` to:
   - Attempt to import the package
   - Get version information
   - Get installation file path
   - Detect if API keys are required

3. **Handle Import Name Differences**:
   - Some packages have different pip names vs import names
   - Consult `references/special_packages.md` for known cases
   - Examples: `pillow` → `PIL`, `beautifulsoup4` → `bs4`
   - Use: `scripts/test_package.py <package_name> <import_name>`

### Step 6: Handle API Key Requirements

If the test indicates an API key is required:

1. Inform the user that the package requires authentication
2. Ask the user to provide the API key or credentials
3. Test with the provided credentials:
   ```bash
   PACKAGE_API_KEY=user_provided_key python -c "import package; client = package.Client()"
   ```
4. If test succeeds, inform user the package is ready to use
5. If test fails, troubleshoot the issue (wrong key format, additional setup needed, etc.)

### Step 7: Provide Installation Summary

After successful installation and verification, provide a concise summary:

```
✅ Successfully installed <package_name> <version>
📍 Location: <installation_path>
✓ Import test: Passed
✓ Version: <version>
```

For failed installations:
```
❌ Failed to install <package_name>
Error: <error_message>
Troubleshooting: <suggestions>
```

### Step 8: Offer to Re-run Failed Command (Automatic Trigger Only)

For automatic triggers where a Python script failed due to missing imports:

1. Offer to re-run the original command that failed
2. If user confirms, execute the command again
3. If the command succeeds, return control to the calling task/skill
4. If the command still fails, troubleshoot remaining issues

For manual triggers, skip this step.

## Special Cases

### Packages with Different Import Names

Consult `references/special_packages.md` for packages with different pip/import names:
- pillow (pip) → PIL (import)
- beautifulsoup4 (pip) → bs4 (import)
- python-dateutil (pip) → dateutil (import)
- scikit-learn (pip) → sklearn (import)
- And more...

### Packages Requiring Build Tools

Some packages need compilation (numpy, scipy, cryptography, etc.):
- `uv` handles most build requirements automatically
- If installation fails with build errors, inform user they may need system dependencies
- Suggest installing via system package manager (brew on macOS)

### Platform-Specific Issues

**macOS ARM64 (M1/M2):**
- Some older packages may not have ARM64 wheels
- May require Rosetta or compilation from source
- Inform user if ARM64 compatibility is suspected issue

## Error Handling

Common installation failures and responses:

1. **Network/Download Error**: Retry once, then inform user of connectivity issue
2. **Permission Error**: Check if correct installation mode (venv vs system)
3. **Version Conflict**: Show conflict details, suggest resolution (upgrade/downgrade)
4. **Build Failure**: Suggest system dependency installation
5. **API Key Error**: Guide user through credential setup

## Resources

### scripts/detect_env.py
Detects virtual environment presence and location. Returns JSON with venv status, path, and detection method.

### scripts/check_installed.py
Checks if packages are installed and where. Takes package names as arguments, returns JSON with installation status for each.

### scripts/test_package.py
Tests if a package can be imported and provides diagnostic information. Handles different import names and detects API key requirements.

### references/special_packages.md
Comprehensive reference for packages requiring special handling:
- Packages with different import names
- Packages requiring API keys (OpenAI, Anthropic, AWS, etc.)
- Packages with build requirements
- Platform-specific considerations
- Testing recommendations

Load this reference when dealing with unfamiliar packages or when installation/testing issues arise.
