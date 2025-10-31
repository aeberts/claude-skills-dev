#!/usr/bin/env python3
"""
Audio Processing Module

This module provides utilities for compressing and chunking audio files
to prepare them for transcription via OpenAI's Whisper API.

Functions:
    - compress_audio: Compress audio to reduce file size
    - get_audio_duration: Get audio duration in seconds
    - get_file_size_mb: Get file size in megabytes
    - split_audio_to_chunks: Split audio into overlapping chunks
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub not installed. Run: uv pip install pydub")
    sys.exit(1)


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to file

    Returns:
        float: File size in MB
    """
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return size_mb


def get_audio_duration(audio_path: str) -> float:
    """
    Get audio duration in seconds.

    Args:
        audio_path: Path to audio file

    Returns:
        float: Duration in seconds
    """
    audio = AudioSegment.from_file(audio_path)
    duration_seconds = len(audio) / 1000.0  # pydub works in milliseconds
    return duration_seconds


def compress_audio(
    input_path: str,
    output_path: str,
    target_bitrate: str = "128k",
    sample_rate: int = 16000
) -> str:
    """
    Compress audio to reduce file size while maintaining transcription quality.

    Converts audio to:
    - 16kHz sample rate (sufficient for speech recognition)
    - 128kbps bitrate
    - Mono channel (for consistent diarization)
    - WAV format (uncompressed for exact sample alignment)

    Args:
        input_path: Original audio file path
        output_path: Compressed output file path
        target_bitrate: Target bitrate (default: "128k")
        sample_rate: Target sample rate in Hz (default: 16000)

    Returns:
        str: Path to compressed file
    """
    print(f"  Loading audio from {input_path}...")
    audio = AudioSegment.from_file(input_path)

    # Convert to mono for consistent processing
    if audio.channels > 1:
        print(f"  Converting to mono...")
        audio = audio.set_channels(1)

    # Set sample rate
    print(f"  Resampling to {sample_rate}Hz...")
    audio = audio.set_frame_rate(sample_rate)

    # Change output to WAV for exact sample alignment
    # WAV is uncompressed and ensures exact sample counts
    output_path_wav = str(Path(output_path).with_suffix('.wav'))

    # Export as WAV with specific parameters for exact alignment
    print(f"  Exporting to WAV for precise sample alignment...")
    audio.export(
        output_path_wav,
        format="wav",
        parameters=["-ar", str(sample_rate), "-ac", "1"]
    )

    original_size = get_file_size_mb(input_path)
    compressed_size = get_file_size_mb(output_path_wav)

    print(f"  Conversion complete: {original_size:.2f}MB → {compressed_size:.2f}MB")
    print(f"  Sample rate: {sample_rate}Hz, Channels: 1 (mono)")

    return output_path_wav


def split_audio_to_chunks(
    audio_path: str,
    output_dir: str,
    overlap_seconds: int = 5,
    target_size_mb: int = 20
) -> List[Tuple[str, float, float]]:
    """
    Split audio file into chunks with overlap, targeting specific file size.

    Args:
        audio_path: Path to audio file to split
        output_dir: Directory to save chunks
        overlap_seconds: Overlap duration between chunks (default: 5)
        target_size_mb: Target size per chunk in MB (default: 20)

    Returns:
        List of tuples (chunk_path, start_time_seconds, duration_seconds)
        where start_time_seconds is absolute time from original audio start

    Algorithm:
        1. Calculate bytes per second from file size and duration
        2. Calculate target duration per chunk
        3. Create overlapping chunks
        4. Save each chunk as chunk_001.mp3, chunk_002.mp3, etc.
    """
    print(f"\n  Loading audio for chunking...")
    audio = AudioSegment.from_file(audio_path)
    total_duration = len(audio) / 1000.0  # Convert ms to seconds
    file_size_mb = get_file_size_mb(audio_path)

    print(f"  Audio duration: {total_duration:.2f}s ({total_duration/60:.2f} minutes)")
    print(f"  File size: {file_size_mb:.2f}MB")

    # Calculate bytes per second
    bytes_per_second = (file_size_mb * 1024 * 1024) / total_duration

    # Calculate target duration per chunk
    target_duration = (target_size_mb * 1024 * 1024) / bytes_per_second
    print(f"  Target duration per chunk: {target_duration:.2f}s")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    chunks_info = []
    chunk_number = 1
    current_start = 0.0

    while current_start < total_duration:
        # Calculate end time for this chunk
        current_end = min(current_start + target_duration, total_duration)

        # Extract chunk (pydub works in milliseconds)
        start_ms = int(current_start * 1000)
        end_ms = int(current_end * 1000)
        chunk_audio = audio[start_ms:end_ms]

        # Save chunk
        chunk_filename = f"chunk_{chunk_number:03d}.mp3"
        chunk_path = os.path.join(output_dir, chunk_filename)

        chunk_audio.export(chunk_path, format="mp3")
        chunk_size = get_file_size_mb(chunk_path)
        chunk_duration = (current_end - current_start)

        print(f"  Created {chunk_filename}: {chunk_duration:.2f}s, {chunk_size:.2f}MB, time range [{current_start:.2f}s - {current_end:.2f}s]")

        chunks_info.append((chunk_path, current_start, chunk_duration))

        # Move to next chunk start (with overlap)
        # Next chunk starts (target_duration - overlap) seconds after this one
        current_start += (target_duration - overlap_seconds)
        chunk_number += 1

        # If we're close to the end, break to avoid tiny final chunk
        if current_start >= total_duration:
            break

    print(f"\n  Total chunks created: {len(chunks_info)}")
    return chunks_info
