# Podcast Transcriber Test Suite

Comprehensive pytest-based test suite for the podcast transcriber skill.

## Quick Start

```bash
# Install pytest (if not already installed)
uv pip install pytest

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_dependencies.py -v

# Run tests without slow/API tests
pytest -m "not slow and not api"
```

## Test Files

### test_dependencies.py
Tests the availability and proper installation of all required dependencies:
- Python version (3.8+)
- Required packages (openai, pyannote.audio, torch, pydub)
- PyTorch device availability (MPS, CUDA, CPU)
- ffmpeg installation
- API keys (OPENAI_API_KEY, HF_TOKEN)
- audio_processor module

**Run:**
```bash
pytest tests/test_dependencies.py -v
```

### test_audio_processing.py
Tests audio processing functionality to ensure sample alignment and prevent diarization errors:
- Sample rate consistency after compression
- Sample count alignment (fixes pyannote "ValueError: requested chunk resulted in X samples instead of expected Y")
- 10-second chunk alignment (pyannote processes in 10s windows)
- Duration calculation accuracy
- File size calculation
- Chunk splitting with overlap
- WAV format output verification

**Run:**
```bash
pytest tests/test_audio_processing.py -v
```

**Key Test:**
The `test_sample_count_alignment` test verifies the fix for the original diarization error by ensuring compressed audio has exact expected sample counts.

### test_integration.py
End-to-end integration tests:
- Transcription without diarization (--no-diarization flag)
- Compression format verification (WAV for exact alignment)
- Error handling for missing files
- Help output verification
- HF_TOKEN optional with --no-diarization
- CLI flag validation

**Run:**
```bash
# Skip slow/API tests
pytest tests/test_integration.py -m "not slow and not api"

# Run all integration tests (requires OPENAI_API_KEY)
pytest tests/test_integration.py -v
```

## Test Markers

Tests are marked with custom markers for selective execution:

### Available Markers

- `@pytest.mark.slow` - Tests that take significant time to run
- `@pytest.mark.api` - Tests that require API keys and make external API calls

### Using Markers

```bash
# Run only fast tests (skip slow tests)
pytest -m "not slow"

# Run only API tests
pytest -m api

# Skip both slow and API tests
pytest -m "not slow and not api"

# Run everything
pytest
```

## Fixtures

Shared fixtures are defined in [conftest.py](conftest.py):

- `temp_dir` - Temporary directory for test files (auto-cleanup)
- `test_audio(duration, frequency, sample_rate)` - Generate test audio with specified parameters
- `script_path` - Path to transcribe_podcast.py
- `sample_tolerance` - Tolerance for sample count variations (0.1%)

### Using Fixtures

```python
def test_example(temp_dir, test_audio):
    """Example test using fixtures."""
    # Create 10-second test audio at 16kHz
    audio = test_audio(duration_seconds=10, sample_rate=16000)

    # Save to temp directory (auto-cleaned up)
    audio_path = temp_dir / "test.wav"
    audio.export(str(audio_path), format="wav")
```

## What These Tests Fix

### Original Problem
```
ValueError: requested chunk [ 00:00:00.000 --> 00:00:10.000] from compressed_audio
file resulted in 158895 samples instead of the expected 160000 samples.
```

### Root Cause
- pyannote.audio requires exact sample alignment for 10-second processing windows
- MP3 compression introduces frame alignment issues
- Slight sample count variations cause diarization to fail

### Solutions Verified by Tests

1. **Audio Compression Fix** (test_audio_processing.py)
   - ✅ `test_compression_produces_wav` - Verifies WAV output format
   - ✅ `test_sample_rate_consistency` - Ensures 16kHz mono output
   - ✅ `test_sample_count_alignment` - Verifies exact sample counts
   - ✅ `test_10_second_chunk_alignment` - Tests pyannote's 10s windows

2. **Diarization Fallback** (test_integration.py)
   - ✅ `test_transcription_without_diarization` - Tests --no-diarization flag
   - ✅ `test_no_diarization_flag_skips_hf_token` - Verifies HF_TOKEN is optional

3. **Dependency Verification** (test_dependencies.py)
   - ✅ All package imports
   - ✅ ffmpeg availability
   - ✅ PyTorch device detection

## Common Test Commands

```bash
# Run all tests with coverage
pytest --cov=../podcast-transcriber/scripts

# Run tests and stop at first failure
pytest -x

# Run tests matching a pattern
pytest -k "sample_count"

# Show local variables on failure
pytest -l

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Generate HTML report
pytest --html=report.html --self-contained-html
```

## Test Output

### Verbose Output
```bash
pytest -v
```
Shows each test with ✓ PASSED or ✗ FAILED

### Short Output
```bash
pytest --tb=line
```
Shows minimal traceback on failures

### Detailed Output
```bash
pytest -vv --tb=long
```
Shows full details and complete tracebacks

## Continuous Testing

### Watch Mode (requires pytest-watch)
```bash
# Install pytest-watch
uv pip install pytest-watch

# Auto-run tests on file changes
ptw
```

### Pre-commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
pytest -m "not slow and not api"
```

## Requirements

Tests require the same dependencies as the main script:
```bash
uv pip install openai pyannote.audio torch pydub pytest
brew install ffmpeg  # macOS
```

## Interpreting Results

### All Tests Pass ✅
```
======================== 20 passed in 5.23s ========================
```
Your system is ready for podcast transcription.

### Some Tests Skipped ⚠
```
=================== 18 passed, 2 skipped in 4.12s ===================
```
Normal if OPENAI_API_KEY or HF_TOKEN not set. Tests can be provided via CLI flags.

### Tests Fail ✗
```
=================== 2 failed, 18 passed in 5.45s ====================
```
Review failure messages for specific issues:
- **Dependency failures**: Install missing packages
- **Audio processing failures**: Check ffmpeg/pydub configuration
- **Integration failures**: Verify API keys or use --no-diarization

## Troubleshooting

### ImportError: No module named 'pytest'
```bash
uv pip install pytest
```

### Tests can't find audio_processor module
The conftest.py automatically adds the scripts directory to sys.path. If still failing:
```bash
cd transcribe-podcast
pytest tests/
```

### API tests fail with authentication errors
Set environment variables or use flags:
```bash
export OPENAI_API_KEY="your-key"
export HF_TOKEN="your-token"
pytest
```

Or skip API tests:
```bash
pytest -m "not api"
```

## Writing New Tests

### Example Test
```python
def test_my_feature(temp_dir, test_audio):
    """Test description."""
    # Arrange
    audio = test_audio(duration_seconds=5)
    audio_path = temp_dir / "test.wav"
    audio.export(str(audio_path), format="wav")

    # Act
    result = my_function(str(audio_path))

    # Assert
    assert result is not None
    assert result.duration == 5.0
```

### Using Markers
```python
@pytest.mark.slow
@pytest.mark.api
def test_full_transcription():
    """This test is marked as slow and requires API."""
    pass
```

### Parametrized Tests
```python
@pytest.mark.parametrize("duration,expected", [
    (10, 160000),
    (20, 320000),
    (30, 480000),
])
def test_sample_counts(duration, expected):
    """Test multiple scenarios."""
    assert duration * 16000 == expected
```

## Next Steps

After tests pass:
1. Process your podcast: `python podcast-transcriber/scripts/transcribe_podcast.py audio.mp3`
2. Run tests after any code changes
3. Add new tests for new features
