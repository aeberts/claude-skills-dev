#!/usr/bin/env python3
"""
Test suite for audio processing functions.

Tests sample alignment, compression, chunking, and other audio operations
to prevent pyannote diarization errors.

Run with: pytest tests/test_audio_processing.py -v
"""

import os
import pytest
from pydub import AudioSegment

from audio_processor import (
    compress_audio,
    get_audio_duration,
    get_file_size_mb,
    split_audio_to_chunks
)


def test_sample_rate_consistency(temp_dir, test_audio):
    """Test that compressed audio maintains exact sample rate."""
    # Create test audio at 44100 Hz
    audio = test_audio(duration_seconds=10, sample_rate=44100)
    input_path = temp_dir / "test_input.wav"
    audio.export(str(input_path), format="wav")

    # Compress to 16kHz
    output_path = temp_dir / "test_output.wav"
    compressed_path = compress_audio(str(input_path), str(output_path), sample_rate=16000)

    # Load compressed audio and verify
    compressed = AudioSegment.from_file(compressed_path)

    assert compressed.frame_rate == 16000, (
        f"Sample rate mismatch: expected 16000, got {compressed.frame_rate}"
    )
    assert compressed.channels == 1, (
        f"Channel mismatch: expected 1 (mono), got {compressed.channels}"
    )


def test_sample_count_alignment(temp_dir, test_audio, sample_tolerance):
    """
    Test that compressed audio has exact expected sample count.

    This verifies the fix for: "ValueError: requested chunk resulted in
    X samples instead of expected Y samples"
    """
    duration_seconds = 10
    target_sample_rate = 16000
    expected_samples = duration_seconds * target_sample_rate

    # Create test audio at different sample rate to test resampling
    audio = test_audio(duration_seconds=duration_seconds, sample_rate=44100)
    input_path = temp_dir / "test_input.wav"
    audio.export(str(input_path), format="wav")

    # Compress to target sample rate
    output_path = temp_dir / "test_output.wav"
    compressed_path = compress_audio(
        str(input_path),
        str(output_path),
        sample_rate=target_sample_rate
    )

    # Load compressed audio and check sample count
    compressed = AudioSegment.from_file(compressed_path)
    actual_samples = len(compressed.raw_data) // (compressed.sample_width * compressed.channels)

    # Allow small tolerance for edge effects
    tolerance = int(expected_samples * sample_tolerance)
    difference = abs(actual_samples - expected_samples)

    assert difference <= tolerance, (
        f"Sample count mismatch: expected {expected_samples}, "
        f"got {actual_samples} (diff: {difference})"
    )


@pytest.mark.parametrize("chunk_start,chunk_duration", [
    (0, 10),   # First 10 seconds
    (10, 10),  # Second 10 seconds
    (20, 10),  # Third 10 seconds
])
def test_10_second_chunk_alignment(temp_dir, test_audio, sample_tolerance, chunk_start, chunk_duration):
    """
    Test sample alignment for 10-second chunks.

    pyannote.audio processes in 10-second windows, so we need exact sample counts.
    """
    target_sample_rate = 16000

    # Create 30-second test audio
    audio = test_audio(duration_seconds=30, sample_rate=44100)
    input_path = temp_dir / "test_input.wav"
    audio.export(str(input_path), format="wav")

    # Compress
    output_path = temp_dir / "test_output.wav"
    compressed_path = compress_audio(
        str(input_path),
        str(output_path),
        sample_rate=target_sample_rate
    )

    # Load compressed audio
    compressed = AudioSegment.from_file(compressed_path)

    # Extract chunk
    start_ms = chunk_start * 1000
    end_ms = (chunk_start + chunk_duration) * 1000
    chunk = compressed[start_ms:end_ms]

    # Calculate sample count
    chunk_samples = len(chunk.raw_data) // (chunk.sample_width * chunk.channels)
    expected_samples = chunk_duration * target_sample_rate

    tolerance = int(expected_samples * sample_tolerance)
    difference = abs(chunk_samples - expected_samples)

    assert difference <= tolerance, (
        f"Chunk [{chunk_start}s - {chunk_start + chunk_duration}s] sample mismatch: "
        f"expected {expected_samples}, got {chunk_samples} (diff: {difference})"
    )


def test_duration_calculation(temp_dir, test_audio):
    """Test accurate duration calculation."""
    expected_duration = 15.0
    audio = test_audio(duration_seconds=expected_duration)

    input_path = temp_dir / "test_audio.wav"
    audio.export(str(input_path), format="wav")

    calculated_duration = get_audio_duration(str(input_path))

    # Check accuracy (within 0.1 seconds)
    assert abs(calculated_duration - expected_duration) < 0.1, (
        f"Duration mismatch: expected {expected_duration}s, got {calculated_duration:.2f}s"
    )


def test_file_size_calculation(temp_dir, test_audio):
    """Test file size calculation accuracy."""
    audio = test_audio(duration_seconds=5)
    input_path = temp_dir / "test_audio.wav"
    audio.export(str(input_path), format="wav")

    calculated_size = get_file_size_mb(str(input_path))
    actual_size = os.path.getsize(str(input_path)) / (1024 * 1024)

    assert abs(calculated_size - actual_size) < 0.01, (
        f"File size mismatch: calculated={calculated_size:.3f}, actual={actual_size:.3f}"
    )


def test_chunk_splitting(temp_dir, test_audio):
    """Test audio chunk splitting with overlap."""
    # Create 60-second test audio
    duration_seconds = 60
    audio = test_audio(duration_seconds=duration_seconds)

    input_path = temp_dir / "test_audio.wav"
    audio.export(str(input_path), format="wav")

    # Compress first
    compressed_path = temp_dir / "compressed.wav"
    compressed_path = compress_audio(str(input_path), str(compressed_path))

    # Split into chunks
    chunks_dir = temp_dir / "chunks"
    chunks_dir.mkdir()

    chunk_info = split_audio_to_chunks(
        compressed_path,
        str(chunks_dir),
        overlap_seconds=5,
        target_size_mb=0.5  # Small chunks for testing
    )

    # Verify chunks were created
    assert len(chunk_info) > 0, "No chunks were created"

    total_coverage = 0
    for idx, (chunk_path, start_time, duration) in enumerate(chunk_info, 1):
        # Verify chunk exists
        assert os.path.exists(chunk_path), f"Chunk {idx} file not found: {chunk_path}"

        # Verify chunk duration
        actual_duration = get_audio_duration(chunk_path)
        assert abs(actual_duration - duration) < 0.5, (
            f"Chunk {idx} duration mismatch: expected {duration:.1f}s, got {actual_duration:.1f}s"
        )

        total_coverage = max(total_coverage, start_time + duration)

    # Verify total coverage (allow 1% tolerance)
    assert total_coverage >= duration_seconds * 0.99, (
        f"Incomplete coverage: {total_coverage:.1f}s / {duration_seconds}s"
    )


def test_compression_produces_wav(temp_dir, test_audio):
    """Test that compression produces WAV files for exact sample alignment."""
    audio = test_audio(duration_seconds=5)
    input_path = temp_dir / "test_input.mp3"
    audio.export(str(input_path), format="mp3", bitrate="128k")

    # Compress (even though we pass .mp3 extension, it should output .wav)
    output_path = temp_dir / "compressed_output.mp3"
    compressed_path = compress_audio(str(input_path), str(output_path))

    # Verify output is WAV
    assert compressed_path.endswith('.wav'), (
        f"Compression should produce WAV file, got {compressed_path}"
    )

    # Verify it's a valid WAV file
    audio = AudioSegment.from_wav(compressed_path)
    assert audio.frame_rate == 16000, f"Expected 16000 Hz, got {audio.frame_rate}"
    assert audio.channels == 1, f"Expected mono, got {audio.channels} channels"
