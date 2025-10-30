# Special Package Handling

This document contains information about Python packages that require special handling during installation or testing.

## Packages with Different Import Names

Some packages have different names when installing vs importing:

| Package Name (pip) | Import Name | Notes |
|-------------------|-------------|-------|
| pillow | PIL | Image processing library |
| beautifulsoup4 | bs4 | HTML/XML parsing |
| python-dateutil | dateutil | Date utilities |
| PyYAML | yaml | YAML parser |
| opencv-python | cv2 | Computer vision |
| scikit-learn | sklearn | Machine learning |
| python-dotenv | dotenv | Environment variables |

## Packages Requiring API Keys

These packages require API keys or authentication to function:

### OpenAI
- **Package:** `openai`
- **Import:** `openai`
- **Environment Variable:** `OPENAI_API_KEY`
- **Test Command:** `python -c "import openai; print(openai.__version__)"`
- **Notes:** Import works without API key, but usage requires it

### Anthropic
- **Package:** `anthropic`
- **Import:** `anthropic`
- **Environment Variable:** `ANTHROPIC_API_KEY`
- **Test Command:** `python -c "import anthropic; print(anthropic.__version__)"`
- **Notes:** Import works without API key, but usage requires it

### Google Cloud Libraries
- **Packages:** `google-cloud-*`
- **Environment Variable:** `GOOGLE_APPLICATION_CREDENTIALS` (path to JSON key file)
- **Notes:** May require additional setup beyond just API key

### AWS Libraries (boto3)
- **Package:** `boto3`
- **Import:** `boto3`
- **Environment Variables:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- **Notes:** Import works without credentials, but AWS operations require them

## Packages with Build Requirements

Some packages require system dependencies or build tools:

### Packages Requiring Compilation
- **psycopg2**: PostgreSQL adapter (may need PostgreSQL dev libraries)
- **mysqlclient**: MySQL adapter (may need MySQL dev libraries)
- **lxml**: XML parser (may need libxml2/libxslt)
- **cryptography**: Cryptographic libraries (may need OpenSSL dev)
- **numpy**, **scipy**, **pandas**: May require compilation on some systems

**Note:** Using `uv` typically handles these better than pip, but system dependencies may still be needed.

## Common Installation Issues

### macOS Specific
- **ARM64 (M1/M2) Compatibility**: Some older packages may not have ARM64 wheels
- **System Python vs pyenv**: Ensure using pyenv python, not system python
- **Command Line Tools**: May need Xcode Command Line Tools for packages with C extensions

### Platform-Specific Wheels
Some packages have platform-specific behavior:
- **torch**: Different installation commands for CPU vs GPU
- **tensorflow**: Different packages for different platforms
- **jax**: Requires specific installation for GPU support

## Testing Recommendations

### Import-Only Test
For most packages, a simple import test is sufficient:
```bash
python -c "import package_name; print(package_name.__version__)"
```

### API Key Test
For packages requiring API keys, test with environment variable:
```bash
PACKAGE_API_KEY=test_key python -c "import package_name; client = package_name.Client()"
```

### Basic Functionality Test
For critical packages, test basic functionality:
```python
# pandas
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3]})
print(df)

# numpy
import numpy as np
arr = np.array([1, 2, 3])
print(arr.sum())

# requests
import requests
# Don't actually make a request in test, just check it's importable
print(requests.__version__)
```
