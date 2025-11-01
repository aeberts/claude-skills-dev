#!/usr/bin/env python3
"""
Podcast Transcription Script

This script transcribes podcast audio files using OpenAI's Whisper API for transcription
and pyannote.audio for speaker diarization. It produces a formatted markdown transcript
with speaker identification, timestamps, and cleaned up text.

Usage:
    python transcribe_podcast.py <audio_file> [--output <output_file>] [--openai-key <key>] [--hf-token <token>]

Requirements:
    - OpenAI API key (via --openai-key flag or OPENAI_API_KEY environment variable)
    - HuggingFace token (via --hf-token flag or HF_TOKEN environment variable)
    - See references/setup.md for installation instructions
"""

import argparse
import os
import sys
import re
import shutil
from pathlib import Path
import json

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: uv pip install openai")
    sys.exit(1)

try:
    from pyannote.audio import Pipeline
except ImportError:
    print("Error: pyannote.audio not installed. Run: uv pip install pyannote.audio")
    sys.exit(1)

try:
    import torch
except ImportError:
    print("Error: torch not installed. Run: uv pip install torch torchvision torchaudio")
    sys.exit(1)

# Import audio processing utilities
try:
    from audio_processor import (
        compress_audio,
        get_audio_duration,
        get_file_size_mb,
        split_audio_to_chunks
    )
except ImportError:
    print("Error: audio_processor module not found. Ensure audio_processor.py is in the same directory.")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from utils.formatting import (
    add_section_summaries,
    build_paragraphs_from_segments,
    clean_filler_words,
    detect_content_types,
    extract_words_from_transcript,
    format_improved_transcript,
    format_timestamp,
    group_into_paragraphs,
    group_into_sections,
)


def identify_speaker_names(transcript_text, num_speakers):
    """
    Try to identify speaker names from the transcript content.
    Uses OpenAI API to analyze the transcript and extract speaker names.

    Returns a dict mapping speaker labels (SPEAKER_00, etc.) to names,
    or None if identification fails.
    """
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        prompt = f"""Analyze this podcast transcript and identify the speakers by name. There are {num_speakers} speakers.
Look for introductions, name mentions, or contextual clues about who is speaking.

Return ONLY a JSON object mapping speaker numbers to names, like:
{{"1": "John Smith", "2": "Jane Doe"}}

If you cannot identify a speaker's name, use "Speaker N" for that person.

Transcript excerpt:
{transcript_text[:3000]}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        result = response.choices[0].message.content.strip()
        # Try to parse JSON
        result = re.search(r'\{[^}]+\}', result)
        if result:
            speaker_map = json.loads(result.group())
            return speaker_map
    except Exception as e:
        print(f"Warning: Could not identify speaker names: {e}")

    return None


def transcribe_audio(audio_path, openai_key):
    """Transcribe audio using OpenAI Whisper API."""
    print("Transcribing audio with Whisper API...")
    client = OpenAI(api_key=openai_key)

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json"
        )

    print("✓ Transcription complete")
    return transcript


def diarize_audio(audio_path, hf_token):
    """Perform speaker diarization using pyannote.audio."""
    print("Performing speaker diarization...")

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token
    )

    # Use MPS (Metal Performance Shaders) on Mac M1, or CPU if not available
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    if device == "cpu" and torch.cuda.is_available():
        device = "cuda"

    pipeline = pipeline.to(torch.device(device))
    print(f"Using device: {device}")

    diarization = pipeline(audio_path)

    print("✓ Diarization complete")
    return diarization


def deduplicate_overlap_words(words_list):
    """
    Remove duplicate words from overlapping regions using timestamp-based approach.

    This function implements Option A: Pure timestamp-based deduplication.
    Words are already tagged with absolute timestamps before calling this function.

    Args:
        words_list: List of word lists, one per chunk (already with absolute timestamps)
                   Each word has: {'word': str, 'start': float, 'end': float}

    Returns:
        List of deduplicated words with absolute timestamps, sorted by start time

    Algorithm:
        1. Keep all words from chunk 1
        2. For each subsequent chunk N:
           - Find the end time of chunk N-1
           - Skip words from chunk N where start_time < end_time of chunk N-1
           - Keep remaining words from chunk N
        3. Sort final word list by start timestamp
    """
    if not words_list:
        return []

    if len(words_list) == 1:
        return words_list[0]

    deduplicated = []

    # Keep all words from first chunk
    deduplicated.extend(words_list[0])
    previous_end_time = words_list[0][-1]['end'] if words_list[0] else 0.0

    # Process subsequent chunks
    for chunk_idx, chunk_words in enumerate(words_list[1:], start=1):
        if not chunk_words:
            continue

        # Find where overlap ends: skip words that start before previous chunk ended
        kept_words = []
        skipped_count = 0

        for word in chunk_words:
            if word['start'] >= previous_end_time:
                # Word is past the overlap region, keep it
                kept_words.append(word)
            else:
                # Word is in overlap region, skip it
                skipped_count += 1

        print(f"  Chunk {chunk_idx + 1}: Skipped {skipped_count} overlapping words, kept {len(kept_words)} words")

        deduplicated.extend(kept_words)

        # Update previous end time
        if kept_words:
            previous_end_time = kept_words[-1]['end']

    # Sort by start time to ensure proper ordering
    deduplicated.sort(key=lambda w: w['start'])

    return deduplicated


def transcribe_chunked_audio(chunk_info, openai_key):
    """
    Transcribe multiple audio chunks and merge with absolute timestamps.

    Args:
        chunk_info: List of tuples (chunk_path, start_time_seconds, duration_seconds)
                   start_time_seconds is absolute time from original audio start
        openai_key: OpenAI API key

    Returns:
        Combined transcript object with absolute timestamps

    Algorithm:
        1. Transcribe each chunk via Whisper API (timestamps are chunk-relative, starting at 0)
        2. For each chunk's words, apply time offset to convert to absolute timestamps:
           - word.start += start_time_seconds
           - word.end += start_time_seconds
        3. Deduplicate overlaps using deduplicate_overlap_words()
        4. Create a combined transcript-like object
    """
    print(f"\nTranscribing {len(chunk_info)} chunks...")

    all_chunks_words = []
    all_segments = []

    for idx, (chunk_path, start_time, duration) in enumerate(chunk_info, start=1):
        print(f"\n  Transcribing chunk {idx}/{len(chunk_info)}: {Path(chunk_path).name}")
        print(f"  Time range: [{start_time:.2f}s - {start_time + duration:.2f}s]")

        try:
            # Transcribe this chunk (timestamps will be relative to chunk start, i.e., 0.0)
            transcript = transcribe_audio(chunk_path, openai_key)

            # Extract words from transcript
            chunk_words = []
            if hasattr(transcript, 'words') and transcript.words:
                for word_data in transcript.words:
                    if isinstance(word_data, dict):
                        word = word_data['word']
                        word_start = word_data['start']
                        word_end = word_data['end']
                    else:
                        word = word_data.word
                        word_start = word_data.start
                        word_end = word_data.end

                    # Apply time offset to convert to absolute timestamps
                    chunk_words.append({
                        'word': word,
                        'start': word_start + start_time,
                        'end': word_end + start_time
                    })
            else:
                # Fallback: use segments if words not available
                for segment in transcript.segments:
                    chunk_words.append({
                        'word': segment.text,
                        'start': segment.start + start_time,
                        'end': segment.end + start_time
                    })

            print(f"  Transcribed {len(chunk_words)} words with timestamps adjusted to absolute time")
            all_chunks_words.append(chunk_words)

            # Also collect segments for potential fallback
            if hasattr(transcript, 'segments'):
                for segment in transcript.segments:
                    all_segments.append(segment)

        except Exception as e:
            # Detailed error reporting
            chunk_size_mb = get_file_size_mb(chunk_path)
            print(f"\n❌ Error: Transcription failed for chunk {idx}/{len(chunk_info)}")
            print(f"   Chunk file: {chunk_path}")
            print(f"   Chunk size: {chunk_size_mb:.2f} MB")
            print(f"   Time range: {start_time:.2f}s - {start_time + duration:.2f}s")
            print(f"   API Error: {str(e)}")
            print(f"\nTemporary files have been preserved for debugging.")
            raise

    # Deduplicate overlapping words
    print(f"\nDeduplicating overlapping regions...")
    merged_words = deduplicate_overlap_words(all_chunks_words)
    print(f"✓ Final transcript contains {len(merged_words)} words")

    # Create a transcript-like object to return
    # This mimics the structure returned by transcribe_audio()
    class ChunkedTranscript:
        def __init__(self, words, segments):
            self.words = words
            self.segments = segments

    return ChunkedTranscript(merged_words, all_segments)


def merge_transcription_and_diarization(transcript, diarization):
    """
    Merge word-level transcription with speaker diarization.
    Returns a list of segments with speaker, text, start, and end times.
    """
    segments = []

    # Get words from transcript
    words = []
    if hasattr(transcript, 'words') and transcript.words:
        words = transcript.words
    else:
        # Fallback: use segments if words not available
        for segment in transcript.segments:
            words.append({
                'word': segment.text,
                'start': segment.start,
                'end': segment.end
            })

    # Convert diarization to list of (start, end, speaker) tuples
    diar_segments = []
    # Handle both old Annotation and new DiarizeOutput formats
    if hasattr(diarization, 'itertracks'):
        # Old pyannote format (Annotation object)
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            diar_segments.append((turn.start, turn.end, speaker))
    elif hasattr(diarization, 'speaker_diarization'):
        # New pyannote.audio v4+ format (DiarizeOutput dataclass)
        for segment, _, speaker in diarization.speaker_diarization.itertracks(yield_label=True):
            diar_segments.append((segment.start, segment.end, speaker))
    else:
        raise ValueError(f"Unknown diarization format: {type(diarization)}")

    # Assign speakers to words
    for word_data in words:
        if isinstance(word_data, dict):
            word = word_data['word']
            start = word_data['start']
            end = word_data['end']
        else:
            word = word_data.word
            start = word_data.start
            end = word_data.end

        # Find which speaker is talking at this time
        word_mid = (start + end) / 2
        speaker = None
        for diar_start, diar_end, diar_speaker in diar_segments:
            if diar_start <= word_mid <= diar_end:
                speaker = diar_speaker
                break

        if speaker is None:
            speaker = "UNKNOWN"

        # Add to segments
        if segments and segments[-1]['speaker'] == speaker:
            # Continue previous segment
            segments[-1]['text'] += ' ' + word
            segments[-1]['end'] = end
        else:
            # Start new segment
            segments.append({
                'speaker': speaker,
                'text': word,
                'start': start,
                'end': end
            })

    return segments


def format_transcript_without_diarization(
    transcript,
    audio_path,
    paragraph_duration=30,
    section_duration=300,
    generate_toc=True,
    minimal_timestamps=False,
    content_markers=False,
    add_summaries=False,
    diarization_available=False,
):
    """
    Format transcript without speaker diarization.
    Enhanced for readability with hierarchical structure.
    """
    audio_name = Path(audio_path).name

    words = extract_words_from_transcript(transcript)
    total_duration = words[-1]["end"] if words else 0.0
    paragraphs = group_into_paragraphs(
        words,
        max_paragraph_seconds=paragraph_duration,
    )
    sections = group_into_sections(paragraphs, section_duration)

    if content_markers:
        sections = detect_content_types(sections)

    if add_summaries:
        sections = add_section_summaries(sections)

    metadata_lines = []
    if total_duration:
        metadata_lines.append(f"**Duration:** {format_timestamp(total_duration)}")

    return format_improved_transcript(
        sections,
        audio_name=audio_name,
        generate_toc=generate_toc,
        minimal_timestamps=minimal_timestamps,
        content_markers=content_markers,
        diarization_available=diarization_available,
        metadata_lines=metadata_lines,
    )


def format_transcript(
    segments,
    audio_path,
    speaker_names=None,
    paragraph_duration=30,
    section_duration=300,
    generate_toc=True,
    minimal_timestamps=False,
    content_markers=False,
    add_summaries=False,
    diarization_available=True,
):
    """
    Format diarized segments into readable markdown with hierarchical structure.
    """
    audio_name = Path(audio_path).name

    total_duration = segments[-1]["end"] if segments else 0.0
    speaker_ids = {seg["speaker"] for seg in segments} if segments else set()

    paragraphs = build_paragraphs_from_segments(
        segments,
        speaker_names=speaker_names,
        max_duration=paragraph_duration,
    )
    sections = group_into_sections(paragraphs, section_duration)

    if content_markers:
        sections = detect_content_types(sections)

    if add_summaries:
        sections = add_section_summaries(sections)

    metadata_lines = []
    if total_duration:
        metadata_lines.append(f"**Duration:** {format_timestamp(total_duration)}")
    if speaker_ids:
        metadata_lines.append(f"**Speakers:** {len(speaker_ids)}")

    return format_improved_transcript(
        sections,
        audio_name=audio_name,
        generate_toc=generate_toc,
        minimal_timestamps=minimal_timestamps,
        content_markers=content_markers,
        diarization_available=diarization_available,
        metadata_lines=metadata_lines,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe podcast audio with speaker diarization"
    )
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument(
        "--output", "-o",
        help="Output markdown file (default: <audio_file>.md)"
    )
    parser.add_argument(
        "--openai-key",
        help="OpenAI API key (default: OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--hf-token",
        help="HuggingFace token (default: HF_TOKEN env var)"
    )
    parser.add_argument(
        "--no-name-detection",
        action="store_true",
        help="Skip automatic speaker name detection"
    )
    parser.add_argument(
        "--force-chunking",
        action="store_true",
        help="Force chunked processing even if file <25MB (for testing)"
    )
    parser.add_argument(
        "--delete-temp-files",
        action="store_true",
        help="Delete working directory after successful completion (default: keep files)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=20,
        help="Target chunk size in MB (default: 20)"
    )
    parser.add_argument(
        "--overlap-seconds",
        type=int,
        default=5,
        help="Overlap duration between chunks in seconds (default: 5)"
    )
    parser.add_argument(
        "--no-diarization",
        action="store_true",
        help="Skip speaker diarization and only transcribe (faster, no speaker labels)"
    )
    parser.add_argument(
        "--paragraph-duration",
        type=int,
        default=30,
        help="Target duration for paragraphs in seconds (default: 30)"
    )
    parser.add_argument(
        "--section-duration",
        type=int,
        default=300,
        help="Target duration for major sections in seconds (default: 300)"
    )
    parser.add_argument(
        "--generate-toc",
        action="store_true",
        help="Generate table of contents with anchor links"
    )
    parser.add_argument(
        "--minimal-timestamps",
        action="store_true",
        help="Only show section-level timestamps"
    )
    parser.add_argument(
        "--content-markers",
        action="store_true",
        help="Add emoji markers for section content types"
    )
    parser.add_argument(
        "--add-summaries",
        action="store_true",
        help="Generate AI summaries for each section (requires OpenAI API access)"
    )

    args = parser.parse_args()

    # Validate audio file exists
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found: {args.audio_file}")
        sys.exit(1)

    # Get API keys
    openai_key = args.openai_key or os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("Error: OpenAI API key required. Provide via --openai-key or OPENAI_API_KEY env var")
        sys.exit(1)

    hf_token = args.hf_token or os.environ.get("HF_TOKEN")
    if not hf_token and not args.no_diarization:
        print("Error: HuggingFace token required for speaker diarization.")
        print("Provide via --hf-token or HF_TOKEN env var, or use --no-diarization to skip speaker identification")
        sys.exit(1)

    # Set output file
    output_file = args.output
    if not output_file:
        audio_path = Path(args.audio_file)
        output_file = audio_path.with_suffix('.md')

    print(f"Processing: {args.audio_file}")
    print(f"Output will be saved to: {output_file}\n")

    # Check file size to determine processing strategy
    file_size_mb = get_file_size_mb(args.audio_file)
    print(f"Audio file size: {file_size_mb:.2f} MB")

    # Determine if chunking is needed
    needs_chunking = file_size_mb > 25 or args.force_chunking
    work_dir = None

    if needs_chunking:
        print(f"\nFile exceeds 25MB limit or --force-chunking flag set. Using chunked processing...\n")

        # Create working directory
        audio_path = Path(args.audio_file)
        work_dir = audio_path.parent / f"{audio_path.stem}_chunks"
        work_dir.mkdir(exist_ok=True)
        print(f"Working directory: {work_dir}\n")

        # Step 1: Compress audio
        compressed_path = work_dir / "compressed_audio.mp3"
        print(f"Step 1: Compressing audio...")
        compress_audio(args.audio_file, str(compressed_path))
        compressed_size = get_file_size_mb(str(compressed_path))
        print(f"Compressed size: {compressed_size:.2f} MB\n")

        # Step 2: Check if still needs chunking after compression
        if compressed_size > 25:
            print(f"Step 2: Compressed file still exceeds 25MB. Splitting into chunks...")
            chunk_info = split_audio_to_chunks(
                str(compressed_path),
                str(work_dir),
                overlap_seconds=args.overlap_seconds,
                target_size_mb=args.chunk_size
            )
            print(f"Created {len(chunk_info)} chunks\n")

            # Step 3: Transcribe chunks
            print(f"Step 3: Transcribing chunks...")
            transcript = transcribe_chunked_audio(chunk_info, openai_key)
            audio_for_diarization = str(compressed_path)
        else:
            # Compressed file fits in one API call
            print(f"Step 2: Compressed file fits in single API call. Skipping chunking.\n")
            print(f"Step 3: Transcribing audio...")
            transcript = transcribe_audio(str(compressed_path), openai_key)
            audio_for_diarization = str(compressed_path)

        # Step 4: Diarize using compressed audio (not chunks)
        if not args.no_diarization:
            print(f"\nStep 4: Performing speaker diarization on full audio...")
            try:
                diarization = diarize_audio(audio_for_diarization, hf_token)
            except Exception as e:
                print(f"\n⚠ Warning: Speaker diarization failed: {e}")
                print("Saving transcript without speaker labels...")
                diarization = None
        else:
            print(f"\nStep 4: Skipping speaker diarization (--no-diarization flag set)")
            diarization = None

    else:
        # Original workflow for files < 25MB
        print(f"File size OK for direct processing (no compression/chunking needed)\n")

        # Step 1: Transcribe
        transcript = transcribe_audio(args.audio_file, openai_key)

        # Step 2: Diarize
        if not args.no_diarization:
            try:
                diarization = diarize_audio(args.audio_file, hf_token)
            except Exception as e:
                print(f"\n⚠ Warning: Speaker diarization failed: {e}")
                print("Saving transcript without speaker labels...")
                diarization = None
        else:
            print("Skipping speaker diarization (--no-diarization flag set)")
            diarization = None

    formatting_options = dict(
        paragraph_duration=args.paragraph_duration,
        section_duration=args.section_duration,
        generate_toc=args.generate_toc,
        minimal_timestamps=args.minimal_timestamps,
        content_markers=args.content_markers,
        add_summaries=args.add_summaries,
    )

    # Format and save based on whether diarization succeeded
    if diarization is not None:
        # Merge transcription and diarization
        print("\nMerging transcription with speaker labels...")
        segments = merge_transcription_and_diarization(transcript, diarization)
        print("✓ Merge complete")

        # Try to identify speaker names
        speaker_names = None
        if not args.no_name_detection:
            print("Attempting to identify speaker names...")
            full_text = ' '.join(seg['text'] for seg in segments[:100])  # First 100 segments
            num_speakers = len(set(seg['speaker'] for seg in segments))
            speaker_names = identify_speaker_names(full_text, num_speakers)
            if speaker_names:
                print(f"✓ Identified speakers: {speaker_names}")
            else:
                print("⚠ Could not identify speaker names, using generic labels")

        # Format and save
        print("\nFormatting transcript...")
        formatted = format_transcript(
            segments,
            args.audio_file,
            speaker_names=speaker_names,
            **dict(formatting_options, diarization_available=True),
        )
    else:
        # Diarization failed or was skipped, save transcript without speaker labels
        print("\nFormatting transcript without speaker labels...")
        formatted = format_transcript_without_diarization(
            transcript,
            args.audio_file,
            **dict(formatting_options, diarization_available=False),
        )

    with open(output_file, 'w') as f:
        f.write(formatted)

    print(f"\n✅ Transcript saved to: {output_file}")

    # Handle cleanup of temporary files
    if work_dir and args.delete_temp_files:
        print(f"\nCleaning up temporary files...")
        shutil.rmtree(work_dir)
        print(f"✓ Deleted {work_dir}")
    elif work_dir:
        print(f"\nTemporary files preserved in: {work_dir}")
        print(f"Use --delete-temp-files flag to auto-cleanup on next run")


if __name__ == "__main__":
    main()
