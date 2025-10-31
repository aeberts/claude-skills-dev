# Podcast Transcriber Fixes - Summary

## What Was Fixed

### Original Error
Your 70-minute podcast transcription failed during speaker diarization with:
```
ValueError: requested chunk resulted in 158895 samples instead of the expected 160000 samples
```

### Root Cause
- pyannote.audio requires exact sample alignment for 10-second processing windows
- MP3 compression caused frame alignment issues and sample count mismatches

### Solutions Implemented

✅ **1. Audio Compression Fix** ([audio_processor.py](podcast-transcriber/scripts/audio_processor.py:57-111))
- Changed output format from MP3 to WAV (uncompressed = exact sample alignment)
- Convert to mono channel for consistency
- Maintain 16kHz sample rate for optimal speech recognition

✅ **2. Diarization Fallback** ([transcribe_podcast.py](podcast-transcriber/scripts/transcribe_podcast.py:390-454))
- Added `--no-diarization` flag to skip speaker identification
- Script saves transcript even if diarization fails
- Made HF_TOKEN optional when using `--no-diarization`

✅ **3. Comprehensive Test Suite** (pytest-based)
- **test_dependencies.py** - Verify all dependencies are installed
- **test_audio_processing.py** - Ensure sample alignment (prevents the original error)
- **test_integration.py** - End-to-end functionality tests
- **conftest.py** - Shared pytest fixtures
- **pytest.ini** - pytest configuration

## Quick Start

### Install Dependencies
```bash
# Install packages
uv pip install openai pyannote.audio torch pydub pytest

# Install ffmpeg
brew install ffmpeg  # macOS
```

### Run Tests
```bash
# Run all tests
pytest

# Skip slow/API tests (recommended for quick check)
pytest -m "not slow and not api"
```

### Transcribe Your Podcast

**With speaker diarization:**
```bash
python podcast-transcriber/scripts/transcribe_podcast.py \
  "Paul Saladino MD 181 How to Reverse High Blood Pressure.mp3" \
  --openai-key YOUR_KEY \
  --hf-token YOUR_TOKEN
```

**Without speaker diarization (faster, no HF_TOKEN needed):**
```bash
python podcast-transcriber/scripts/transcribe_podcast.py \
  "Paul Saladino MD 181 How to Reverse High Blood Pressure.mp3" \
  --openai-key YOUR_KEY \
  --no-diarization
```

## New Features

### Command-Line Flags
- `--no-diarization` - Skip speaker identification (faster, no HF_TOKEN needed)
- `--force-chunking` - Force chunked processing even for small files
- `--delete-temp-files` - Auto-cleanup working directory after completion
- `--chunk-size MB` - Set target chunk size (default: 20MB)
- `--overlap-seconds N` - Set chunk overlap duration (default: 5s)

### Automatic Handling
- ✅ Compresses large files to WAV at 16kHz
- ✅ Automatically chunks files >25MB
- ✅ Merges transcripts with deduplication
- ✅ Falls back gracefully if diarization fails
- ✅ Preserves working files for debugging

## Test Suite Benefits

### Why pytest?
For your personal use, pytest provides:
- **Concise tests** - Less boilerplate code
- **Powerful fixtures** - Shared test setup/teardown
- **Parametrized tests** - Test multiple scenarios easily
- **Selective execution** - Skip slow/API tests with markers
- **Better output** - Clear pass/fail indicators

### Test Markers
```bash
# Fast tests only
pytest -m "not slow"

# Skip API tests (no API key needed)
pytest -m "not api"

# Run specific test
pytest tests/test_dependencies.py::test_ffmpeg_installed -v
```

### Coverage
```bash
# Run with coverage report
pytest --cov=podcast-transcriber/scripts

# Generate HTML coverage report
pytest --cov=podcast-transcriber/scripts --cov-report=html
```

## Files Changed

### Modified
1. **[audio_processor.py](podcast-transcriber/scripts/audio_processor.py)** - WAV compression for exact sample alignment
2. **[transcribe_podcast.py](podcast-transcriber/scripts/transcribe_podcast.py)** - Diarization fallback and error handling

### Created
1. **[tests/test_dependencies.py](tests/test_dependencies.py)** - Dependency verification tests
2. **[tests/test_audio_processing.py](tests/test_audio_processing.py)** - Audio processing and sample alignment tests
3. **[tests/test_integration.py](tests/test_integration.py)** - End-to-end integration tests
4. **[tests/conftest.py](tests/conftest.py)** - pytest fixtures and configuration
5. **[pytest.ini](pytest.ini)** - pytest configuration
6. **[tests/README.md](tests/README.md)** - Comprehensive test documentation
7. **[FIXES.md](FIXES.md)** - Detailed technical documentation
8. **[SUMMARY.md](SUMMARY.md)** - This file

## Next Steps

1. **Verify setup:**
   ```bash
   pytest -m "not slow and not api"
   ```

2. **Process your failed podcast:**
   ```bash
   # Try with diarization (should work now)
   python podcast-transcriber/scripts/transcribe_podcast.py \
     "Paul Saladino MD 181 How to Reverse High Blood Pressure.mp3"

   # Or without diarization (guaranteed to work)
   python podcast-transcriber/scripts/transcribe_podcast.py \
     "Paul Saladino MD 181 How to Reverse High Blood Pressure.mp3" \
     --no-diarization
   ```

3. **Review output:**
   - Transcript saved as `.md` file
   - Working files in `*_chunks/` directory (preserved for debugging)
   - Add `--delete-temp-files` to auto-cleanup

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Compression** | MP3 (lossy, alignment issues) | WAV (lossless, exact alignment) |
| **Reliability** | Failed on sample mismatch | Graceful fallback on error |
| **Flexibility** | Required HF_TOKEN | Optional with `--no-diarization` |
| **Testing** | None | Comprehensive pytest suite |
| **Error Handling** | Complete failure | Saves transcript without speakers |

## Documentation

- **[FIXES.md](FIXES.md)** - Technical details about all fixes
- **[tests/README.md](tests/README.md)** - Complete pytest guide with examples
- **[SUMMARY.md](SUMMARY.md)** - This quick reference

## Questions?

### Why WAV instead of MP3?
WAV is uncompressed, ensuring exact sample counts that pyannote.audio requires for its 10-second processing windows. MP3's lossy compression introduces frame alignment variations.

### Will this make files larger?
Yes, WAV files are larger than MP3. However, they're still smaller than the original due to lower sample rate (16kHz vs 44.1kHz). The working files are temporary and can be deleted with `--delete-temp-files`.

### Can I still get speaker labels?
Yes! The fix should allow diarization to work properly. If it fails for any reason, the script now saves the transcript without speaker labels instead of failing completely.

### Do I need both API keys?
- **OPENAI_API_KEY**: Always required for transcription
- **HF_TOKEN**: Only required for speaker diarization (optional with `--no-diarization`)

## Success Criteria

After running `pytest -m "not slow and not api"`, you should see:
```
======================== XX passed in X.XXs ========================
```

Your system is then ready to process the 70-minute podcast that previously failed!
