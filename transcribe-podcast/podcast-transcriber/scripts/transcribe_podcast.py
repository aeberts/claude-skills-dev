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
from pathlib import Path
from datetime import timedelta
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


def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS format."""
    td = timedelta(seconds=seconds)
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    secs = td.seconds % 60
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"


def clean_filler_words(text):
    """Remove excessive filler words and clean up text."""
    # Remove excessive um, uh, etc.
    text = re.sub(r'\b(um|uh|er|ah)\b', '', text, flags=re.IGNORECASE)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Clean up punctuation spacing
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    return text.strip()


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


def format_transcript(segments, audio_path, speaker_names=None):
    """
    Format segments into readable markdown with paragraphs,
    timestamps, and speaker labels.
    """
    output = []

    # Add metadata header
    audio_name = Path(audio_path).name
    total_duration = segments[-1]['end'] if segments else 0
    speakers = set(seg['speaker'] for seg in segments)
    num_speakers = len(speakers)

    output.append("# Podcast Transcript\n")
    output.append(f"**File:** {audio_name}\n")
    output.append(f"**Duration:** {format_timestamp(total_duration)}\n")
    output.append(f"**Speakers:** {num_speakers}\n")
    output.append("\n---\n\n")

    # Group segments into paragraphs (every ~30 seconds or speaker change)
    current_speaker = None
    current_paragraph = []
    paragraph_start = None

    for seg in segments:
        speaker = seg['speaker']

        # Convert speaker label to readable format
        if speaker_names and speaker in speaker_names:
            speaker_label = speaker_names[speaker]
        else:
            # Extract number from SPEAKER_XX format
            match = re.search(r'(\d+)', speaker)
            if match:
                num = int(match.group(1))
                speaker_label = f"Speaker {num + 1}"
            else:
                speaker_label = speaker

        # Start new paragraph on speaker change
        if speaker != current_speaker:
            # Write out previous paragraph
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                para_text = clean_filler_words(para_text)
                if para_text:
                    timestamp = format_timestamp(paragraph_start)
                    output.append(f"**{current_speaker_label}** {timestamp}\n\n")
                    output.append(f"{para_text}\n\n")

            # Start new paragraph
            current_speaker = speaker
            current_speaker_label = speaker_label
            current_paragraph = [seg['text']]
            paragraph_start = seg['start']
        else:
            current_paragraph.append(seg['text'])

            # Also break into paragraphs every ~30 seconds for readability
            if seg['end'] - paragraph_start > 30:
                para_text = ' '.join(current_paragraph)
                para_text = clean_filler_words(para_text)
                if para_text:
                    timestamp = format_timestamp(paragraph_start)
                    output.append(f"**{speaker_label}** {timestamp}\n\n")
                    output.append(f"{para_text}\n\n")

                current_paragraph = []
                paragraph_start = seg['end']

    # Write final paragraph
    if current_paragraph:
        para_text = ' '.join(current_paragraph)
        para_text = clean_filler_words(para_text)
        if para_text:
            timestamp = format_timestamp(paragraph_start)
            output.append(f"**{current_speaker_label}** {timestamp}\n\n")
            output.append(f"{para_text}\n\n")

    return ''.join(output)


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
    if not hf_token:
        print("Error: HuggingFace token required. Provide via --hf-token or HF_TOKEN env var")
        sys.exit(1)

    # Set output file
    output_file = args.output
    if not output_file:
        audio_path = Path(args.audio_file)
        output_file = audio_path.with_suffix('.md')

    print(f"Processing: {args.audio_file}")
    print(f"Output will be saved to: {output_file}\n")

    # Step 1: Transcribe
    transcript = transcribe_audio(args.audio_file, openai_key)

    # Step 2: Diarize
    diarization = diarize_audio(args.audio_file, hf_token)

    # Step 3: Merge transcription and diarization
    print("Merging transcription with speaker labels...")
    segments = merge_transcription_and_diarization(transcript, diarization)
    print("✓ Merge complete")

    # Step 4: Try to identify speaker names
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

    # Step 5: Format and save
    print("Formatting transcript...")
    formatted = format_transcript(segments, args.audio_file, speaker_names)

    with open(output_file, 'w') as f:
        f.write(formatted)

    print(f"\n✅ Transcript saved to: {output_file}")


if __name__ == "__main__":
    main()
