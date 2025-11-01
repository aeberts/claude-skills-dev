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
4. Groups content into readable paragraphs and five-minute sections
5. Generates optional table of contents, anchor links, and content markers
6. Cleans up filler words (um, uh, etc.) for readability
7. Adds metadata header (duration, speaker count)

**Output format:**
```markdown
# Podcast Transcript

**File:** episode_123.mp3
**Duration:** [01:23:45]
**Speakers:** 2
**Speakers identified via diarization.**

---

## Table of Contents

- [00:00 Introduction](#00-00-introduction)
- [05:00 Sponsor: Heart And Soil](#05-00-sponsor-heart-and-soil)
- [12:00 Hypertension Discussion](#12-00-hypertension-discussion)

---

## <a id="00-00-introduction"></a>[00:00:00] Introduction

**[00:00:15]** Welcome to the show. Today we're discussing the latest research on metabolic health and why it matters.

## <a id="05-00-sponsor-heart-and-soil"></a>[00:05:02] Sponsor: Heart And Soil

**[00:05:05]** This episode is brought to you by Heart and Soil. Use code PAUL for a discount on nose-to-tail supplements.

## <a id="12-00-hypertension-discussion"></a>[00:12:18] Hypertension Discussion

**[00:12:20]** Let's dive into what causes high blood pressure and how to reverse it with nutrition, sunlight, and movement.
```

**Advanced options:**
```bash
# Specify custom output file
python scripts/transcribe_podcast.py audio.mp3 --output transcript.md

# Skip automatic name detection (use generic Speaker 1, Speaker 2, etc.)
python scripts/transcribe_podcast.py audio.mp3 --no-name-detection

# Provide API keys directly (instead of env vars)
python scripts/transcribe_podcast.py audio.mp3 --openai-key sk-... --hf-token hf_...

# Tune readability
python scripts/transcribe_podcast.py audio.mp3 --paragraph-duration 45 --section-duration 240

# Generate navigation aids
python scripts/transcribe_podcast.py audio.mp3 --generate-toc --content-markers

# Produce summaries (requires OPENAI_API_KEY permissions)
python scripts/transcribe_podcast.py audio.mp3 --add-summaries
```

**Readability flags:**
- `--paragraph-duration`: control paragraph length (seconds per paragraph)
- `--section-duration`: control section length (seconds per major topic)
- `--generate-toc`: add a linked table of contents to the output
- `--minimal-timestamps`: hide per-paragraph timestamps (show section timestamps only)
- `--content-markers`: display emoji markers for sponsor segments, Q&A, etc.
- `--add-summaries`: create AI-written section summaries (requires OpenAI access)

**Handling Large Files (>25MB):**

For audio files exceeding the Whisper API's 25MB limit, the script automatically:
1. Compresses audio to 16kHz stereo, 128kbps (typically 60-70% size reduction)
2. Splits into ~20MB chunks with 5-second overlap if still needed
3. Transcribes each chunk separately with timestamp offset calculation
4. Runs diarization on full compressed audio (ensures consistent speaker labels)
5. Merges transcripts using timestamp-based deduplication

Working files are saved to `<audio_name>_chunks/` directory:
```
podcast_episode_chunks/
├── compressed_audio.mp3      # Compressed version for diarization
├── chunk_001.mp3             # First chunk (if needed)
├── chunk_002.mp3             # Second chunk
└── chunk_003.mp3             # Etc.
```

By default, working files are **kept for debugging**. Use `--delete-temp-files` to clean up:

```bash
# Keep working files (default)
python scripts/transcribe_podcast.py large_podcast.mp3

# Clean up after successful completion
python scripts/transcribe_podcast.py large_podcast.mp3 --delete-temp-files

# Force chunking for testing (even if <25MB)
python scripts/transcribe_podcast.py small_file.mp3 --force-chunking

# Customize chunk parameters (advanced)
python scripts/transcribe_podcast.py huge_file.mp3 --chunk-size 15 --overlap-seconds 10
```

**Note:** If transcription fails, working files are always preserved for debugging, regardless of the `--delete-temp-files` flag.

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
> Use this utility when the source material has **no timestamps** and just needs sentence detection and paragraph regrouping. It does not produce the section/TOC hierarchy provided by the new formatter.

**Example:**
```bash
# Input: wall_of_text.txt (one long paragraph)
python scripts/format_transcript.py wall_of_text.txt

# Output: wall_of_text_formatted.md (readable paragraphs)
```

#### Reformat Timestamped Markdown

Use `scripts/reformat_transcript.py` to convert existing `[HH:MM:SS]` style transcripts into the improved readable layout:

```bash
python scripts/reformat_transcript.py fragmented.md readable.md --generate-toc --content-markers
```

**What it does:**
1. Parses timestamp fragments (`[HH:MM:SS]` blocks) from an existing markdown file
2. Groups fragments into paragraphs using silence gaps and sentence endings
3. Bundles paragraphs into 5-minute sections with generated titles and anchors
4. Produces the same improved markdown output as the live transcription path

The reformatter refuses to overwrite the source file—always provide a different output path. You can reuse the same readability flags (`--paragraph-duration`, `--section-duration`, `--generate-toc`, `--content-markers`) to match the live transcription behavior.

> Use this utility exclusively for **legacy, timestamp-heavy markdown** files. You do not need to run `format_transcript.py` beforehand, and the two scripts are not chained together.

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
- Diarization runs on the compressed audio (smaller than original)
- Process on a machine with more RAM (16GB+ recommended for very long files)

**"File exceeds 25MB limit" / Large file errors**
- The script automatically handles this - it will compress and chunk the audio
- Check that `pydub` is installed: `uv pip install pydub`
- Verify ffmpeg is available: `ffmpeg -version`
- If compression isn't enough, the script will automatically chunk the file
- Working files are kept in `<audio_name>_chunks/` for debugging

**Chunk transcription failures**
- Check the error message for which chunk failed and why
- Working files in `<audio_name>_chunks/` are preserved for debugging
- Verify chunk size with: `ls -lh <audio_name>_chunks/`
- Try reducing chunk size: `--chunk-size 15` (instead of default 20MB)
- Check OpenAI API rate limits if multiple chunks fail

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
