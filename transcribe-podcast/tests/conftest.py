#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for podcast transcriber tests.
"""

import sys
import os
import tempfile
from pathlib import Path
import pytest

# Add scripts directory to path for all tests
script_dir = Path(__file__).parent.parent / "podcast-transcriber" / "scripts"
sys.path.insert(0, str(script_dir))

# Import pydub dependencies
try:
    from pydub import AudioSegment
    from pydub.generators import Sine
except ImportError:
    AudioSegment = None
    Sine = None


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_audio():
    """
    Create a test audio file with known properties.

    Returns a function that creates audio with specified parameters.
    """
    if AudioSegment is None or Sine is None:
        pytest.skip("pydub not installed. Run: uv pip install pydub")

    # Capture the imports in the closure
    _AudioSegment = AudioSegment
    _Sine = Sine

    def _create_audio(duration_seconds=10, frequency=440, sample_rate=16000):
        """
        Create test audio with specified parameters.

        Args:
            duration_seconds: Duration in seconds
            frequency: Tone frequency in Hz
            sample_rate: Sample rate in Hz

        Returns:
            AudioSegment object
        """
        # Generate a sine wave
        audio = _Sine(frequency).to_audio_segment(
            duration=duration_seconds * 1000,  # pydub uses milliseconds
            volume=-20.0  # Reduce volume to avoid clipping
        )

        # Set sample rate and channels
        audio = audio.set_frame_rate(sample_rate)
        audio = audio.set_channels(1)  # Mono

        return audio

    return _create_audio


@pytest.fixture
def script_path():
    """Path to the transcribe_podcast.py script."""
    return Path(__file__).parent.parent / "podcast-transcriber" / "scripts" / "transcribe_podcast.py"


@pytest.fixture
def sample_tolerance():
    """Tolerance for sample count variations (0.1%)."""
    return 0.001


# Configure pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require API keys"
    )
