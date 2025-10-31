#!/usr/bin/env python3
"""
Integration tests for the podcast transcriber.

Tests end-to-end functionality, error handling, and CLI interface.

Run with: pytest tests/test_integration.py -v
"""

import sys
import os
import subprocess
import pytest
from pydub import AudioSegment
from pydub.generators import Sine


@pytest.fixture
def create_test_mp3(temp_dir):
    """Create a test MP3 audio file."""
    def _create(duration_seconds=30):
        audio = Sine(440).to_audio_segment(duration=duration_seconds * 1000, volume=-20.0)
        audio = audio.set_frame_rate(44100)
        audio = audio.set_channels(2)

        output_path = temp_dir / "test_podcast.mp3"
        audio.export(str(output_path), format="mp3", bitrate="128k")
        return str(output_path)

    return _create


@pytest.mark.api
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
def test_transcription_without_diarization(temp_dir, create_test_mp3, script_path):
    """
    Test transcription with --no-diarization flag.

    This ensures the fallback works and doesn't require HF_TOKEN.
    """
    # Create test audio
    audio_path = create_test_mp3(duration_seconds=10)  # Short for quick test
    output_path = temp_dir / "transcript.md"

    cmd = [
        sys.executable,
        str(script_path),
        audio_path,
        "--output", str(output_path),
        "--no-diarization"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120  # 2 minute timeout
    )

    assert result.returncode == 0, f"Transcription failed: {result.stderr}"
    assert output_path.exists(), "Transcript file not created"

    content = output_path.read_text()
    assert len(content) > 0, "Transcript file is empty"
    assert "Speaker diarization was not available" in content, (
        "Transcript should indicate diarization was skipped"
    )


def test_compression_format(temp_dir, test_audio):
    """Test that compression produces WAV files instead of MP3."""
    from audio_processor import compress_audio

    # Create test audio
    audio = test_audio(duration_seconds=5)
    audio_path = temp_dir / "test_input.mp3"
    audio.export(str(audio_path), format="mp3")

    # Compress
    output_path = temp_dir / "compressed_output.mp3"
    compressed_path = compress_audio(str(audio_path), str(output_path))

    # Verify it's WAV
    assert compressed_path.endswith('.wav'), (
        f"Compression should produce WAV, got {compressed_path}"
    )

    # Verify it's valid WAV
    audio = AudioSegment.from_wav(compressed_path)
    assert audio.frame_rate == 16000
    assert audio.channels == 1


def test_error_handling_missing_file(script_path):
    """Test error handling for non-existent audio file."""
    cmd = [
        sys.executable,
        str(script_path),
        "/nonexistent/audio/file.mp3"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode != 0, "Should fail for non-existent file"
    assert "not found" in result.stdout.lower() or "not found" in result.stderr.lower()


def test_help_output(script_path):
    """Test that help message includes all expected flags."""
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, "Help command should succeed"

    help_text = result.stdout

    # Check for key flags
    expected_flags = [
        "--output",
        "--openai-key",
        "--hf-token",
        "--no-diarization",
        "--force-chunking",
        "--delete-temp-files",
        "--chunk-size",
        "--overlap-seconds",
    ]

    for flag in expected_flags:
        assert flag in help_text, f"Help message missing flag: {flag}"


def test_no_diarization_flag_skips_hf_token(script_path, create_test_mp3, temp_dir):
    """Test that --no-diarization allows script to run without HF_TOKEN."""
    # Temporarily remove HF_TOKEN from environment
    original_hf_token = os.environ.pop("HF_TOKEN", None)

    try:
        # This should not fail due to missing HF_TOKEN
        audio_path = create_test_mp3(duration_seconds=5)

        cmd = [
            sys.executable,
            str(script_path),
            audio_path,
            "--no-diarization",
        ]

        # Without OPENAI_API_KEY, it should fail with that error, not HF_TOKEN error
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should fail due to missing OPENAI_API_KEY, not HF_TOKEN
        if result.returncode != 0:
            output = result.stdout + result.stderr
            # Should NOT mention HF_TOKEN when using --no-diarization
            assert "HuggingFace" not in output or "optional" in output.lower()

    finally:
        # Restore HF_TOKEN
        if original_hf_token:
            os.environ["HF_TOKEN"] = original_hf_token


@pytest.mark.parametrize("flag", ["--no-name-detection", "--force-chunking", "--delete-temp-files"])
def test_optional_flags_accepted(script_path, flag):
    """Test that optional flags are recognized."""
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert flag in result.stdout, f"Flag {flag} not in help output"
