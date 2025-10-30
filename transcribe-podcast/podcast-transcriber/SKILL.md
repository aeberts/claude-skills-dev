---
name: podcast-transcriber
description: Transcribe podcast audio files into readable markdown transcripts with speaker identification and timestamps. This skill should be used when working with audio files (mp3, wav, m4a) that need to be converted to text, when transcribing podcast episodes, interviews, or recorded conversations, or when formatting existing wall-of-text transcripts into readable documents.
---

# Podcast Transcriber

## Overview

This skill enables transcription of podcast audio files into formatted markdown documents with speaker identification, timestamps, paragraph breaks, and cleaned text. It uses OpenAI's Whisper API for accurate transcription and pyannote.audio for speaker diarization (identifying who is speaking when).

## Quick Start

Before using this skill, ensure dependencies are installed and API keys are configured. See `references/setup.md` for detailed setup instructions.

**Required:**
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)
- HuggingFace token (set as `HF_TOKEN` environment variable)
- Python packages: `openai`, `pyannote.audio`, `torch`

## Core Tasks

### Transcribe Audio with Speaker Identification

Use `scripts/transcribe_podcast.py` to transcribe audio files with full speaker diarization:

```bash
python scripts/transcribe_podcast.py <audio_file.mp3>
```

**What it does:**
1. Transcribes audio using OpenAI Whisper API (accurate, fast, multi-language)
2. Identifies speakers using pyannote.audio diarization
3. Attempts to detect speaker names from transcript context
4. Formats output with timestamps, speaker labels, and paragraph breaks
5. Cleans up filler words (um, uh, etc.) for readability
6. Adds metadata header (duration, speaker count)

**Output format:**
```markdown
# Podcast Transcript

**File:** episode_123.mp3
**Duration:** [01:23:45]
**Speakers:** 2

---

**John Smith** [00:00:15]

Welcome to the show. Today we're discussing...

**Jane Doe** [00:01:30]

Thanks for having me. I'm excited to talk about...
```

**Advanced options:**
```bash
# Specify custom output file
python scripts/transcribe_podcast.py audio.mp3 --output transcript.md

# Skip automatic name detection (use generic Speaker 1, Speaker 2, etc.)
python scripts/transcribe_podcast.py audio.mp3 --no-name-detection

# Provide API keys directly (instead of env vars)
python scripts/transcribe_podcast.py audio.mp3 --openai-key sk-... --hf-token hf_...
```

**When to use:**
- User provides an audio file and asks to transcribe it
- User requests "transcribe this podcast"
- User asks to "identify speakers" in an audio recording
- User needs a readable transcript from an interview or conversation

### Format Existing Transcripts

Use `scripts/format_transcript.py` to clean up wall-of-text transcripts:

```bash
python scripts/format_transcript.py <transcript.txt>
```

**What it does:**
1. Removes excessive filler words (um, uh, er, ah)
2. Detects sentence boundaries
3. Groups sentences into readable paragraphs
4. Fixes punctuation spacing
5. Adds markdown header with source info

**When to use:**
- User has a raw transcript that's difficult to read
- User asks to "format this transcript"
- User provides a text file that's one long paragraph
- User needs to clean up an auto-generated transcript

**Example:**
```bash
# Input: wall_of_text.txt (one long paragraph)
python scripts/format_transcript.py wall_of_text.txt

# Output: wall_of_text_formatted.md (readable paragraphs)
```

## Workflow Guidance

### For Full Audio Transcription

1. **Verify prerequisites**: Check that OPENAI_API_KEY and HF_TOKEN are set
2. **Run transcription**: Execute `scripts/transcribe_podcast.py` with the audio file path
3. **Review output**: Open the generated markdown file to verify quality
4. **Manual edits if needed**:
   - If speaker names weren't detected correctly, edit the markdown to replace generic labels
   - Verify timestamps align with content
   - Add any missing context or corrections

### For Transcript Formatting Only

1. **Run formatter**: Execute `scripts/format_transcript.py` with the text file
2. **Review output**: Check that paragraphing makes sense
3. **Iterate if needed**: The formatter is quick, so can be run multiple times with adjustments

## Technical Details

### Supported Audio Formats
- MP3 (recommended for podcasts)
- WAV
- M4A
- FLAC
- OGG

### Processing Time
- **Transcription**: Usually 1-2 minutes per hour of audio (depends on API speed)
- **Diarization**: 10-20% of audio length on Mac M1 with MPS acceleration (2-4 minutes per hour)

### Resource Requirements
- **Disk space**: Minimal (outputs are text files)
- **Memory**:
  - Transcription: ~500MB (API-based)
  - Diarization: 10-15GB RAM for long files (2+ hours)
- **Network**: Required for OpenAI API calls

### Device Acceleration
- Mac M1/M2/M3: Uses Metal Performance Shaders (MPS) automatically
- NVIDIA GPU: Uses CUDA if properly configured
- CPU fallback: Works on any system but slower for diarization

## Troubleshooting

### Common Issues

**"OpenAI API key required"**
- Set environment variable: `export OPENAI_API_KEY="sk-..."`
- Or pass directly: `--openai-key sk-...`

**"HuggingFace token required"**
- Set environment variable: `export HF_TOKEN="hf_..."`
- Ensure you've accepted pyannote model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1

**"pyannote.audio not installed"**
- Run: `uv pip install pyannote.audio`
- See `references/setup.md` for complete installation guide

**Poor speaker diarization accuracy**
- Try shorter audio segments (split long files)
- Ensure audio quality is good (clear voices, minimal background noise)
- Consider manually editing speaker labels in output

**Memory errors during diarization**
- Close other applications to free RAM
- Split large files into smaller chunks (e.g., 30-minute segments)
- Process on a machine with more RAM (16GB+ recommended for long files)

## Example Usage Patterns

### Pattern 1: Quick Podcast Episode Transcription
```
User: "Transcribe this podcast episode: episode_42.mp3"
Claude: Runs python scripts/transcribe_podcast.py episode_42.mp3
```

### Pattern 2: Format Existing Raw Transcript
```
User: "This transcript is unreadable. Can you format it? [provides transcript.txt]"
Claude: Runs python scripts/format_transcript.py transcript.txt
```

### Pattern 3: Transcribe with Custom Output Location
```
User: "Transcribe interview.mp3 and save it as docs/interview_transcript.md"
Claude: Runs python scripts/transcribe_podcast.py interview.mp3 --output docs/interview_transcript.md
```

## Resources

### scripts/
- `transcribe_podcast.py`: Main transcription script with speaker diarization
- `format_transcript.py`: Utility to format wall-of-text transcripts

### references/
- `setup.md`: Complete installation and setup instructions for all dependencies and API keys