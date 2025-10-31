# Setup Instructions

This document provides setup instructions for the podcast transcriber skill.

## Prerequisites

### Required Accounts and Tokens

1. **OpenAI API Key**
   - Required for Whisper transcription
   - Get your key at: https://platform.openai.com/api-keys
   - Set as environment variable: `export OPENAI_API_KEY="sk-..."`

2. **HuggingFace Token**
   - Required for pyannote.audio speaker diarization
   - Steps to get your token:
     1. Create account at https://huggingface.co
     2. Go to Settings → Access Tokens
     3. Create a new token (read permission is sufficient)
     4. Accept pyannote model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1
   - Set as environment variable: `export HF_TOKEN="hf_..."`

## Installation

### For Mac M1/M2/M3 (Apple Silicon)

The skill requires Python dependencies. Install them using uv:

```bash
# Install core dependencies
uv pip install openai pyannote.audio

# Install PyTorch with Metal (MPS) support for Mac M1
# Use the standard install - it automatically includes MPS support
uv pip install torch torchvision torchaudio

# Install audio processing dependencies (for large file handling)
uv pip install pydub
```

**Note on pydub and ffmpeg:**
- `pydub` requires `ffmpeg` for audio processing
- On Mac, ffmpeg is usually pre-installed or available via Homebrew
- Verify ffmpeg: `ffmpeg -version`
- If needed, install via Homebrew: `brew install ffmpeg`

**Note:** Do NOT use the CUDA (`--index-url https://download.pytorch.org/whl/cu121`) or CPU-only versions of PyTorch on Mac M1. The default installation automatically uses Apple's Metal Performance Shaders (MPS) for GPU acceleration.

### For Other Platforms

**Linux/Windows with NVIDIA GPU:**
```bash
uv pip install openai pyannote.audio pydub
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**CPU-only (any platform):**
```bash
uv pip install openai pyannote.audio pydub
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

## Environment Variables

Create a `.env` file or export these variables:

```bash
export OPENAI_API_KEY="sk-..."
export HF_TOKEN="hf_..."
```

## Verifying Installation

Test that everything is installed correctly:

```bash
# Test imports
python -c "import openai; import torch; from pyannote.audio import Pipeline; from pydub import AudioSegment; print('✅ All dependencies installed')"

# Check PyTorch device availability (Mac M1)
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"

# Verify ffmpeg is available
ffmpeg -version
```

## Troubleshooting

### pyannote.audio Issues

If you get authentication errors with pyannote.audio:
1. Make sure you've accepted the model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1
2. Verify your HF token is set correctly: `echo $HF_TOKEN`
3. Check your token has read permissions on HuggingFace

### OpenAI API Issues

If transcription fails:
1. Verify your API key: `echo $OPENAI_API_KEY`
2. Check your OpenAI account has credits/billing set up
3. Ensure the audio file is in a supported format (mp3, wav, m4a, etc.)

### PyTorch/MPS Issues (Mac M1)

If you get MPS-related errors:
1. Make sure you have macOS 12.3 or later
2. Try updating PyTorch: `uv pip install --upgrade torch torchvision torchaudio`
3. If MPS fails, the script will automatically fall back to CPU

### Memory Issues

For very large audio files (>2 hours):
- The diarization step may consume significant RAM (10-15GB)
- The script now automatically compresses and chunks large files (>25MB)
- Diarization runs on compressed audio (reduces memory usage)
- Close other applications to free up memory

### pydub/ffmpeg Issues

If you get errors about ffmpeg not found:
```bash
# Check if ffmpeg is installed
ffmpeg -version

# Mac: Install via Homebrew
brew install ffmpeg

# Linux: Install via package manager
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg      # CentOS/RHEL
```

If pydub cannot find ffmpeg even when it's installed:
- Ensure ffmpeg is in your PATH: `which ffmpeg`
- Try reinstalling pydub: `uv pip install --force-reinstall pydub`

## Audio File Format Support

The scripts support common audio formats:
- MP3 (recommended for podcasts)
- WAV
- M4A
- FLAC
- OGG

For best results with very long files, use compressed formats like MP3 or M4A.
