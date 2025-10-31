#!/usr/bin/env python3
"""
Test suite for verifying podcast transcriber dependencies.

Run with: pytest tests/test_dependencies.py -v
"""

import sys
import os
import subprocess
from pathlib import Path
import pytest


def test_python_version():
    """Test that Python version is 3.8 or higher."""
    version = sys.version_info
    min_version = (3, 8)

    assert (version.major, version.minor) >= min_version, (
        f"Python {min_version[0]}.{min_version[1]}+ required, "
        f"got {version.major}.{version.minor}.{version.micro}"
    )


@pytest.mark.parametrize("package_name,import_name", [
    ("openai", "openai"),
    ("pyannote.audio", "pyannote.audio"),
    ("torch", "torch"),
    ("pydub", "pydub"),
])
def test_package_import(package_name, import_name):
    """Test if required packages can be imported."""
    try:
        __import__(import_name)
    except ImportError:
        pytest.fail(f"{package_name} is not installed. Run: uv pip install {package_name}")


def test_torch_devices():
    """Test available torch devices (MPS, CUDA, CPU)."""
    import torch

    # At least one device should be available
    has_device = False

    if torch.backends.mps.is_available():
        has_device = True

    if torch.cuda.is_available():
        has_device = True

    # CPU is always available
    has_device = True

    assert has_device, "No torch device available"


def test_ffmpeg_installed():
    """Test if ffmpeg is available (required by pydub)."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, "ffmpeg is not working properly"
    except FileNotFoundError:
        pytest.fail(
            "ffmpeg is not installed. "
            "Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
        )


def test_openai_api_key():
    """Test if OPENAI_API_KEY is available (can be set via env or CLI)."""
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not openai_key:
        pytest.skip("OPENAI_API_KEY not set (can be provided via --openai-key flag)")

    assert len(openai_key) > 0, "OPENAI_API_KEY is empty"


def test_hf_token():
    """Test if HF_TOKEN is available (optional with --no-diarization)."""
    hf_token = os.environ.get("HF_TOKEN")

    if not hf_token:
        pytest.skip("HF_TOKEN not set (optional with --no-diarization flag)")

    assert len(hf_token) > 0, "HF_TOKEN is empty"


def test_audio_processor_module():
    """Test if audio_processor module can be imported."""
    # Add the scripts directory to the path
    script_dir = Path(__file__).parent.parent / "podcast-transcriber" / "scripts"
    sys.path.insert(0, str(script_dir))

    from audio_processor import (
        compress_audio,
        get_audio_duration,
        get_file_size_mb,
        split_audio_to_chunks
    )

    # Verify functions are callable
    assert callable(compress_audio)
    assert callable(get_audio_duration)
    assert callable(get_file_size_mb)
    assert callable(split_audio_to_chunks)
