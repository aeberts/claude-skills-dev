# Podcast Transcript Readability Improvement Plan

**Created:** 2025-10-31
**Status:** Planning phase - ready for implementation
**Reference File:** Paul Saladino MD 181 How to Reverse High Blood Pressure part 1.md

---

## Executive Summary

The current transcript format creates **severe readability issues** with timecodes every 1-4 seconds, resulting in 2,462 lines of fragmented text for a 70-minute podcast. This plan outlines improvements to create readable, navigable transcripts that serve as useful reference documents.

### Key Metrics
- **Current:** ~700 timecodes, 2,462 lines, impossible to read as prose
- **Target:** ~50 major sections, ~200 paragraphs, readable and navigable
- **Improvement:** 92% reduction in visual clutter

---

## Critical Problems Identified

### 1. **Excessive Timecode Granularity** 🔴 CRITICAL
- Average 1 timecode every 1.7 seconds
- Creates extreme visual fragmentation
- Example: Lines 40-57 break a single testimonial into 9 fragments
- **Should be:** 1 paragraph with 1 timecode

**Current Format:**
```markdown
[00:00:40]

She says, I'm two weeks into animal base

[00:00:42]

with Heart and Soil Supplements

[00:00:43]

and it's difficult to articulate just how excited
```

**Should Be:**
```markdown
**[00:00:40]** She says, I'm two weeks into animal base with Heart and Soil Supplements and it's difficult to articulate just how excited and relieved I am to have finally found a healthy lifestyle of eating and movement.
```

### 2. **No Paragraph Structure** 🔴 CRITICAL
- Each sentence/fragment isolated on its own line
- No logical grouping of related thoughts
- Reader must mentally reconstruct the conversation
- Impossible to skim or scan for key points

### 3. **Duplicate Content Bug** 🟡 MEDIUM
- Lines 1738-1741 show same content with different timecodes
- Timestamp appears to reset at [00:00:00] mid-transcript
- Indicates processing error in transcription
- **Fix plan:** normalize the word stream before paragraph grouping. Prefer `transcript.words` when available, fall back to segment text only when needed, and drop monotonically-decreasing timestamp windows so duplicate paragraphs never enter the formatter.

### 4. **No Content Hierarchy** 🔴 CRITICAL
- No sections, chapters, or topic markers
- 70-minute podcast = flat wall of text
- Can't jump to specific topics
- No table of contents

### 5. **Poor Skimmability** 🟡 MEDIUM
- Can't identify main points quickly
- No visual hierarchy beyond timestamps
- Promotional content mixed with educational content
- No way to distinguish content types

---

## Reader Pain Points

| Pain Point | Current Experience | Desired Experience |
|------------|-------------------|-------------------|
| **"Where am I?"** | No sense of progress | Section markers show position |
| **"What's the main point?"** | Must read everything | Can scan section summaries |
| **"I want to reference this later"** | Hard to bookmark | Named sections with anchors |
| **"This is hard to read"** | Visual fatigue | Flowing prose with clear structure |
| **"I want the part about X"** | Manual search/scroll | Table of contents with links |

---

## Improvement Plan

## Phase 1: Immediate Formatting Improvements

### A. Intelligent Paragraph Grouping

**Implementation:**
```python
def group_into_paragraphs(
    words,
    max_paragraph_seconds=30,
    pause_threshold=2.5,
    max_words=140,
    min_words=12,
):
    """
    Turn word-level timestamps into grouped paragraphs.

    Break triggers:
      - Hard cap: paragraph duration >= max_paragraph_seconds
      - Long pause: silence >= pause_threshold seconds after the last word
      - Sentence boundary: paragraph ends with . ! ? and is at least min_words long
      - Soft cap: duration >= 50% of max + word count >= max_words

    Returns:
        List[dict]: [{'start': float, 'end': float, 'text': str}, ...]
    """
    paragraphs = []
    if not words:
        return paragraphs

    current_tokens = []
    paragraph_start = words[0]['start']
    last_end = words[0]['start']

    def flush(last_timestamp):
        if not current_tokens:
            return
        paragraphs.append({
            'start': paragraph_start,
            'end': last_timestamp,
            'text': ' '.join(current_tokens)
        })
        current_tokens.clear()

    for idx, token_data in enumerate(words):
        token = token_data['word']
        token_start = token_data['start']
        token_end = token_data['end']
        pause = token_start - last_end if current_tokens else 0.0

        current_tokens.append(token)
        last_end = token_end

        duration = token_end - paragraph_start
        ended_sentence = token.rstrip().endswith(('.', '!', '?'))
        hit_pause = pause >= pause_threshold
        hit_hard_cap = duration >= max_paragraph_seconds
        hit_soft_cap = duration >= max_paragraph_seconds * 0.5 and len(current_tokens) >= max_words

        should_break = False
        if hit_hard_cap:
            should_break = True
        elif ended_sentence and duration >= 6 and len(current_tokens) >= min_words:
            should_break = True
        elif hit_pause and len(current_tokens) >= min_words:
            should_break = True
        elif hit_soft_cap:
            should_break = True

        if should_break:
            flush(token_end)
            if idx + 1 < len(words):
                paragraph_start = words[idx + 1]['start']

    flush(last_end)
    return paragraphs
```

**Benefits:**
- Guaranteed hard cap on paragraph length
- Breaks on real pauses even without punctuation
- Smarter handling when Whisper omits sentence-ending tokens
- Maintains chronological order and precise start/end timestamps

### B. Hierarchical Timecode System

**Three-Level Hierarchy:**

1. **Major Sections** (every 5-10 minutes)
   ```markdown
   ## [00:00:00] Introduction & Sponsors
   ```

2. **Subsections** (every 2-3 minutes or topic change)
   ```markdown
   ### [00:02:32] Weekly Podcast Topic
   ```

3. **Paragraph Timestamps** (every 30-60 seconds)
   ```markdown
   **[00:03:15]** Paragraph text begins here...
   ```

**Example Output:**
```markdown
## [00:00:00] Introduction & Sponsors

**[00:00:00]** You do not have high blood pressure or high cholesterol because you are getting older. You have high blood pressure and high cholesterol because you are living in an evolutionarily inconsistent way and Western medicine fails to realize this.

### [00:00:17] Customer Testimonial - Frances L.

**[00:00:17]** This is the first hope I've had in 30 years. Check out this review on gut and digestion from Heart and Soil Supplements from Frances L. She says, I'm two weeks into animal base with Heart and Soil Supplements and it's difficult to articulate just how excited and relieved I am to have finally found a healthy lifestyle of eating and movement.

**[00:00:41]** An animal-based diet coupled with Heart and Soil Supplements and gut and digestion has drastically improved the quality of my life. Overall, inflammation is decreasing. Energy is increasing. Cognition and sleep are improving. As a sufferer of Crohn's disease for almost 30 years, this is the first hope I've had of existing without discomfort or pharmaceuticals.

### [00:01:43] Sponsor: Heart and Soil

**[00:01:43]** Our mission at Heart and Soil is to help you reclaim your birthright to optimal health. Find us at heartandsoil.co. We have a whole host of different types of desiccated organ supplements so you can get more organs in your life and start thriving, get back to your real life.
```

---

## Phase 2: Content Enhancement

### C. Auto-Generated Table of Contents

Add at the top of every transcript:

```markdown
# Podcast Transcript

**File:** Paul Saladino MD 181 How to Reverse High Blood Pressure part 1.mp3
**Duration:** ~70 minutes
**Note:** Speaker diarization was not available for this transcript.

---

## Table of Contents

1. [Introduction & Opening Statement](#000000-introduction--opening-statement) - 0:00
2. [Sponsors](#000117-sponsors) - 0:17
   - Heart and Soil Supplements - 0:17
   - Kale is Bullshit Merch - 1:49
   - White Oak Pastures - 3:17
   - 8sleep - 4:05
   - Primal Pastures - 5:39
   - Higher Dose - 6:49
3. [Main Topic: Hypertension](#000816-main-topic-hypertension) - 8:16
4. [Current Burden of Hypertension](#001035-current-burden-of-hypertension) - 10:35
   - US Statistics (116M Americans) - 10:35
   - Global Epidemiology (1.39B people) - 12:40
5. [Primary vs Secondary Hypertension](#001418-primary-vs-secondary-hypertension) - 14:18
6. [Western Medicine's View](#001854-western-medicines-view) - 18:54
   - Age as Risk Factor - 21:26
   - Family History Myth - 21:26
7. [Hunter-Gatherer Evidence (Hadza Study)](#002151-hunter-gatherer-study) - 21:51
8. [Physician Health & Counseling Quality](#000535-physician-health) - 5:35
9. [Medications for Hypertension](#000930-medications-for-hypertension) - 9:30
   - ACE Inhibitors - 9:39
   - ARBs & Diuretics - 9:44
   - Side Effects - 10:44

---
```

**Implementation:**
```python
def generate_table_of_contents(sections):
    """
    Generate markdown TOC with anchor links.

    Args:
        sections: List of section dicts with title, timestamp, subsections

    Returns:
        Markdown string for TOC
    """
    toc = ["## Table of Contents\n"]

    for i, section in enumerate(sections, 1):
        anchor = create_anchor_id(section['timestamp'], section['title'])
        time_str = format_timestamp_short(section['timestamp'])

        toc.append(f"{i}. [{section['title']}](#{anchor}) - {time_str}")

        # Add subsections
        if section.get('subsections'):
            for subsection in section['subsections']:
                sub_anchor = create_anchor_id(subsection['timestamp'], subsection['title'])
                sub_time = format_timestamp_short(subsection['timestamp'])
                toc.append(f"   - {subsection['title']} - {sub_time}")

        toc.append("")

    return '\n'.join(toc)

> **Anchor guarantee:** Because Markdown engines generate their own heading slugs, `format_section()` injects an explicit `<a id="...">` tag using the same `create_anchor_id()` helper so every TOC link resolves.

def create_anchor_id(timestamp, title):
    """Convert timestamp and title to markdown anchor ID."""
    # Format: 000000-introduction--opening-statement
    time_str = f"{int(timestamp):06d}"
    title_slug = title.lower().replace(' ', '-').replace('&', '').replace(',', '')
    return f"{time_str}-{title_slug}"
```

### D. Section Summaries (Optional - AI Enhancement)

**Format:**
```markdown
## [00:08:16] Main Topic: Hypertension Overview

> **Summary:** Introduction to hypertension epidemic affecting 116 million Americans (47.3% of population). Discusses Western medicine's view of hypertension as age-related and irreversible, contrasted with evidence from hunter-gatherer populations showing no age-related blood pressure increase.
>
> **Key Points:**
> - 116M Americans have hypertension
> - Western medicine considers it irreversible
> - Hadza hunter-gatherers show no age-related BP increase
> - Root cause vs symptom management debate

**[00:08:18]** Many of you may not have high blood pressure, but I am betting that you know someone who has high blood pressure...
```

**Implementation (Optional):**
```python
def add_section_summaries(sections, summary_fn=None):
    """
    Add AI-generated summaries to each major section.

    `summary_fn` defaults to `generate_summary_with_openai`, but tests can
    inject a stub. When the helper returns None, we skip adding a summary.
    """
    if summary_fn is None:
        summary_fn = generate_summary_with_openai  # Local helper defined in this module

    for section in sections:
        # Extract section text
        section_text = extract_section_text(section)

        # Generate summary via OpenAI
        summary = summary_fn(section_text)

        if summary:
            section['summary'] = summary

    return sections
```

> **Implementation note:** Keep the `'timestamp'` key in sync anywhere sections are built (diarized formatter, reformatter utility, tests) so `generate_table_of_contents()` can consume the shared structure without triggering a `KeyError`.

When `generate_summary_with_openai` is used, it should:
- Read `OPENAI_API_KEY` from the environment and return `None` if unavailable.
- Handle API failures gracefully (log + return `None`).
- Allow tests to supply a fake `summary_fn` so no network calls are required.

### E. Visual Content Type Markers

Distinguish different types of content with icons/emoji:

```markdown
### 💊 [00:09:30] Medications for Hypertension
_Discussion of pharmaceutical interventions and their side effects_

### 📊 [00:10:35] Statistics: Hypertension Burden in America
_Data from NHANES 2015-2018 study showing 47.3% prevalence_

### 🎙️ [00:00:17] Sponsor: Heart and Soil Supplements
_Commercial content - customer testimonial_

### 🔬 [00:21:51] Research: Hadza Hunter-Gatherer Blood Pressure Study
_Scientific study from Herman Ponser showing no age-related BP increase_

### 🏥 [00:05:35] Clinical Practice: Physician Health Statistics
_Discussion of obesity rates among physicians and impact on counseling_

### 💡 [00:01:00] Key Insight: Age is Not the Cause
_Main thesis: BP increase is lifestyle-related, not age-related_
```

**Content Type Categories:**
- 🎙️ Sponsor/Advertisement
- 📊 Statistics/Data
- 🔬 Research/Study
- 💊 Medications/Treatments
- 🏥 Clinical Practice
- 💡 Key Insights/Thesis
- ❓ FAQ/Common Questions
- ⚠️ Warnings/Cautions
- ✅ Actionable Advice

---

## Phase 3: Implementation Details

### Shared Formatting Utilities

Create `podcast-transcriber/utils/formatting.py` to host shared helpers consumed by both the CLI script and the standalone reformatter.

**Helper Catalog:**
```python
def format_timestamp(seconds: float) -> str:
    """Return HH:MM:SS (existing helper moves here)."""

def format_timestamp_short(seconds: float) -> str:
    """Return MM:SS when duration < 1 hour, else HH:MM:SS."""

def create_anchor_id(timestamp: float, title: str) -> str:
    """Convert timestamp + title -> slug used in markdown anchors."""

def extract_section_text(section: dict) -> str:
    """Concatenate a section's paragraph text for summary generation."""

def extract_sponsor_name(paragraph_text: str) -> str:
    """Detect sponsor/brand names from intro paragraphs."""

def clean_filler_words(text: str) -> str:
    """Shared text normalizer (migrated from transcribe_podcast.py)."""

def fragments_to_paragraphs(fragments: list, *, max_paragraph_seconds: int = 30) -> list:
    """Convert timestamped markdown fragments into paragraph dicts (reformatter entry point)."""

def build_paragraphs_from_segments(
    segments: list,
    *,
    speaker_names: dict | None,
    max_duration: int = 30,
) -> list:
    """Convert diarized segments into paragraph dicts with speaker metadata."""

def format_section(section: dict, *, minimal_timestamps: bool, show_markers: bool) -> str:
    """Shared section formatter (migrated from transcribe_podcast.py)."""

def format_improved_transcript(
    sections: list,
    *,
    audio_name: str,
    generate_toc: bool,
    minimal_timestamps: bool,
    content_markers: bool,
    diarization_available: bool,
) -> str:
    """Compose metadata header, optional TOC, and section bodies into markdown."""

def generate_summary_with_openai(section_text: str, *, model: str = "gpt-4o-mini") -> str | None:
    """Optional AI summary helper; reads OPENAI_API_KEY and returns None on failure."""
```

`format_improved_transcript` serves as the single entry point for building the final markdown output. Both the CLI path and the reformat utility feed `sections` and formatting options into this helper, ensuring the rendered structure stays consistent across tools. Existing helpers such as `group_into_sections` and `clean_filler_words` move into this module so there is one source of truth.

**Formatting Workflow Example:**
```python
def format_improved_transcript(
    sections,
    *,
    audio_name,
    generate_toc,
    minimal_timestamps,
    content_markers,
    diarization_available,
):
    note_line = (
        "**Speakers identified via diarization.**"
        if diarization_available
        else "**Note:** Speaker diarization was not available for this transcript."
    )

    header = [
        "# Podcast Transcript",
        f"**File:** {audio_name}",
        note_line,
        "",
        "---",
        "",
    ]

    toc_block = [generate_table_of_contents(sections), "", "---", ""] if generate_toc else []

    body = [
        format_section(
            section,
            minimal_timestamps=minimal_timestamps,
            show_markers=content_markers,
        )
        for section in sections
    ]

    return "\n".join(header + toc_block + body)
```

> **Callers:** Pass `diarization_available=True` when speaker diarization succeeded so the header note reflects the correct state; fallback utilities pass `False`.

**Testing Targets:**
- Timestamp helpers (`format_timestamp_short`, `create_anchor_id`) unit tests.
- `extract_sponsor_name` coverage for common sponsor keyword variants.
- `extract_words_from_transcript` fixtures covering segment-level words, top-level words, deduplication of overlapping token streams, and timestamp reset handling.
- `format_improved_transcript` snapshot tests (with/without TOC, markers, summaries).
- `generate_summary_with_openai` wrapped via injectable `summary_fn` to stub API in tests.

### Modifications to `transcribe_podcast.py`

**New Command-Line Flags:**
```python
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
    help="Target duration for major sections in seconds (default: 300/5min)"
)

parser.add_argument(
    "--generate-toc",
    action="store_true",
    help="Generate table of contents with anchor links"
)

parser.add_argument(
    "--minimal-timestamps",
    action="store_true",
    help="Only show major section timestamps, hide paragraph timestamps"
)

parser.add_argument(
    "--content-markers",
    action="store_true",
    help="Add emoji/icons to distinguish content types (ads, research, etc)"
)

parser.add_argument(
    "--add-summaries",
    action="store_true",
    help="Generate AI summaries for each major section (requires OpenAI API)"
)
```

**Updated `format_transcript_without_diarization()` Function:**

```python
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

    Args:
        transcript: Transcript object from Whisper API
        audio_path: Path to audio file
        paragraph_duration: Max duration for paragraphs (seconds)
        section_duration: Duration for major sections (seconds)
        generate_toc: Generate table of contents
        minimal_timestamps: Only show section-level timestamps
        content_markers: Add emoji icons for content types
        add_summaries: Generate AI summaries (requires API)

    Returns:
        Formatted markdown string
    """
    output = []

    # Add metadata header
    audio_name = Path(audio_path).name
    output.append("# Podcast Transcript\n")
    output.append(f"**File:** {audio_name}\n")
    note_line = (
        "**Speakers identified via diarization.**\n"
        if diarization_available
        else "**Note:** Speaker diarization was not available for this transcript.\n"
    )
    output.append(note_line)
    output.append("\n---\n\n")

    # Get words from transcript
    words = extract_words_from_transcript(transcript)

    # Group into paragraphs
    paragraphs = group_into_paragraphs(words, paragraph_duration)

    # Group paragraphs into sections
    sections = group_into_sections(paragraphs, section_duration)

    # Optionally detect content types
    if content_markers:
        sections = detect_content_types(sections)

    # Optionally add AI summaries
    if add_summaries:
        sections = add_section_summaries(sections)

    # Generate table of contents
    if generate_toc:
        toc = generate_table_of_contents(sections)
        output.append(toc)
        output.append("\n---\n\n")

    # Format sections
    for section in sections:
        output.append(format_section(
            section,
            minimal_timestamps=minimal_timestamps,
            show_markers=content_markers
        ))

    return ''.join(output)
```

```python
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
    Speaker-aware version that feeds the same section/paragraph pipeline.
    """
    output = []
    audio_name = Path(audio_path).name
    output.append("# Podcast Transcript\n")
    output.append(f"**File:** {audio_name}\n")

    total_duration = segments[-1]['end'] if segments else 0
    output.append(f"**Duration:** {format_timestamp(total_duration)}\n")
    output.append(f"**Speakers:** {len(set(seg['speaker'] for seg in segments))}\n")
    if not diarization_available:
        output.append("**Note:** Speaker diarization was not available for this transcript.\n")
    output.append("\n---\n\n")

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

    if generate_toc:
        toc = generate_table_of_contents(sections)
        output.append(toc)
        output.append("\n---\n\n")

    for section in sections:
        output.append(format_section(
            section,
            minimal_timestamps=minimal_timestamps,
            show_markers=content_markers
        ))

    return ''.join(output)
```

**Helper Functions:**

```python
def extract_words_from_transcript(transcript):
    """Extract words with timestamps from transcript object."""
    words = []
    seen_tokens = set()
    last_end = None
    reset_threshold = 2.0  # seconds; treat larger backwards jumps as a reset

    def append_word(word_data):
        """Normalize heterogenous word payloads into dicts."""
        nonlocal last_end
        if word_data is None:
            return

        if isinstance(word_data, dict):
            token = word_data.get('word') or word_data.get('text')
            start = word_data.get('start')
            end = word_data.get('end')
        else:
            token = getattr(word_data, 'word', None) or getattr(word_data, 'text', None)
            start = getattr(word_data, 'start', None) or getattr(word_data, 'start_time', None)
            end = getattr(word_data, 'end', None) or getattr(word_data, 'end_time', None)

        if token is None or start is None or end is None:
            return

        try:
            start_f = float(start)
            end_f = float(end)
        except (TypeError, ValueError):
            return

        dedupe_key = (round(start_f, 3), round(end_f, 3), token)
        if dedupe_key in seen_tokens:
            return

        # Guard against timestamp resets: if we suddenly jump backwards by more than
        # `reset_threshold`, clear the collected stream so downstream grouping does not
        # produce duplicated paragraphs.
        if last_end is not None and start_f + 1e-3 < last_end - reset_threshold:
            words.clear()
            seen_tokens.clear()

        # Record this token now that we know the stream is monotonic.
        seen_tokens.add(dedupe_key)

        last_end = end_f

        words.append({
            'word': token,
            'start': start_f,
            'end': end_f,
        })

    if hasattr(transcript, 'words') and transcript.words:
        for word_data in transcript.words:
            append_word(word_data)

    # Only fall back to segment-level text when word-level timing is unavailable.
    use_segments = not words
    segments = []
    if hasattr(transcript, 'segments') and transcript.segments:
        segments = transcript.segments
    elif isinstance(transcript, dict) and transcript.get('segments'):
        segments = transcript['segments']

    for segment in segments or []:
        if isinstance(segment, dict):
            segment_words = segment.get('words')
            segment_text = segment.get('text')
            start = segment.get('start')
            end = segment.get('end')
        else:
            segment_words = getattr(segment, 'words', None)
            segment_text = getattr(segment, 'text', None)
            start = getattr(segment, 'start', None)
            end = getattr(segment, 'end', None)

        if segment_words and use_segments:
            for word_data in segment_words:
                append_word(word_data)
        elif segment_text and use_segments:
            # Fallback: ensure segments without word-level timestamps still produce content
            append_word({
                'word': segment_text.strip(),
                'start': start,
                'end': end,
            })

    words.sort(key=lambda w: w['start'])
    return words

> **Implementation detail:** `seen_tokens` deduplicates Whisper outputs that supply both `transcript.words` and per-segment `words`, and the `reset_threshold` guard prevents non-monotonic timestamp resets (e.g., the mid-transcript `[00:00:00]` bug) from leaking duplicate paragraphs into downstream formatting.

def group_into_sections(paragraphs, section_duration=300):
    """Group paragraphs into major sections."""
    sections = []
    current_section = {
        'paragraphs': [],
        'start': paragraphs[0]['start'] if paragraphs else 0,
        'timestamp': paragraphs[0]['start'] if paragraphs else 0,  # Alias used by TOC builder
        'title': None  # Will be auto-generated or left generic
    }

    for para in paragraphs:
        # Check if we should start a new section
        if para['start'] - current_section['start'] >= section_duration:
            # Finalize current section
            if current_section['paragraphs']:
                sections.append(current_section)

            # Start new section
            current_section = {
                'paragraphs': [para],
                'start': para['start'],
                'timestamp': para['start'],  # Keep timestamp key in sync with TOC expectations
                'title': None
            }
        else:
            current_section['paragraphs'].append(para)

    # Add final section
    if current_section['paragraphs']:
        current_section.setdefault('timestamp', current_section['start'])
        sections.append(current_section)

    # Generate section titles
    sections = generate_section_titles(sections)

    return sections

def generate_section_titles(sections):
    """
    Generate descriptive titles for sections.

    Strategies:
    1. Detect sponsor mentions → "Sponsor: [Brand]"
    2. Detect topic keywords → "Topic: [Keyword]"
    3. Fallback to time-based → "Section at [timestamp]"
    """
    for i, section in enumerate(sections):
        # Extract first paragraph text for analysis
        first_para = section['paragraphs'][0]['text']

        # Strategy 1: Detect sponsors
        sponsor_keywords = [
            'sponsor', 'brought to you', 'check out', 'promo code',
            'heartandsoil', 'white oak', '8sleep', 'primal pastures'
        ]
        if any(kw in first_para.lower() for kw in sponsor_keywords):
            section['title'] = extract_sponsor_name(first_para)
            section['type'] = 'sponsor'
            continue

        # Strategy 2: Detect main topics
        if i == 0:
            section['title'] = "Introduction"
            section['type'] = 'intro'
        elif 'hypertension' in first_para.lower() or 'blood pressure' in first_para.lower():
            section['title'] = "Hypertension Discussion"
            section['type'] = 'main_content'
        else:
            # Fallback
            time_str = format_timestamp(section['start'])
            section['title'] = f"Section at {time_str}"
            section['type'] = 'general'

    return sections

def build_paragraphs_from_segments(segments, speaker_names=None, max_duration=30):
    """Convert diarized segments into paragraphs with speaker labels."""
    paragraphs = []
    current_speaker = None
    current_label = ""
    current_text = []
    paragraph_start = None
    paragraph_end = None

    def speaker_label(raw_speaker):
        if speaker_names and raw_speaker in speaker_names:
            return speaker_names[raw_speaker]
        match = re.search(r'(\d+)', raw_speaker)
        if match:
            return f"Speaker {int(match.group(1)) + 1}"
        return raw_speaker

    def flush():
        if not current_text:
            return
        paragraphs.append({
            'start': paragraph_start,
            'end': paragraph_end,
            'text': f"**{current_label}:** {' '.join(current_text)}"
        })

    for seg in segments:
        speaker = seg['speaker']
        label = speaker_label(speaker)

        if current_speaker is None:
            current_speaker = speaker
            current_label = label
            paragraph_start = seg['start']
            current_text = [seg['text']]
            paragraph_end = seg['end']
            continue

        duration = seg['end'] - paragraph_start
        speaker_changed = speaker != current_speaker
        if speaker_changed or duration >= max_duration:
            flush()
            current_speaker = speaker
            current_label = label
            paragraph_start = seg['start']
            current_text = [seg['text']]
        else:
            current_text.append(seg['text'])

        paragraph_end = seg['end']

    flush()
    return paragraphs

def fragments_to_paragraphs(
    fragments,
    max_paragraph_seconds=30,
    pause_threshold=2.5,
    min_fragments=2,
):
    """Convert timestamped markdown fragments into paragraph dicts."""
    if not fragments:
        return []

    paragraphs = []
    current_text = []
    paragraph_start = fragments[0]['timestamp']
    last_timestamp = paragraph_start

    def flush(final_timestamp):
        if not current_text:
            return
        paragraphs.append({
            'start': paragraph_start,
            'end': final_timestamp,
            'text': ' '.join(current_text)
        })

    for idx, frag in enumerate(fragments):
        start = frag['timestamp']
        text = frag['text']
        duration = start - paragraph_start
        pause = start - last_timestamp if current_text else 0.0

        current_text.append(text)
        last_timestamp = start

        is_sentence_end = text.rstrip().endswith(('.', '!', '?'))
        hit_hard_cap = duration >= max_paragraph_seconds
        hit_pause = pause >= pause_threshold

        should_break = False
        if hit_hard_cap:
            should_break = True
        elif is_sentence_end and duration >= 6 and len(current_text) >= min_fragments:
            should_break = True
        elif hit_pause and len(current_text) >= min_fragments:
            should_break = True

        if should_break:
            flush(start)
            current_text = []
            if idx + 1 < len(fragments):
                paragraph_start = fragments[idx + 1]['timestamp']

    if current_text:
        flush(last_timestamp)

    return paragraphs

def detect_content_types(sections):
    """Add content type markers (emoji) to sections."""
    type_markers = {
        'sponsor': '🎙️',
        'research': '🔬',
        'statistics': '📊',
        'medication': '💊',
        'clinical': '🏥',
        'key_insight': '💡',
        'intro': '👋',
        'general': ''
    }

    for section in sections:
        # Analyze section content
        text = ' '.join([p['text'] for p in section['paragraphs']]).lower()

        # Assign type based on keywords
        if 'study' in text or 'research' in text or 'paper' in text:
            section['type'] = 'research'
        elif any(word in text for word in ['statistic', 'million', 'percent', 'data']):
            section['type'] = 'statistics'
        elif any(word in text for word in ['medication', 'drug', 'prescription', 'ace inhibitor']):
            section['type'] = 'medication'

        # Add marker
        section['marker'] = type_markers.get(section['type'], '')

    return sections

def format_section(section, minimal_timestamps=False, show_markers=False):
    """Format a section into markdown."""
    output = []

    # Section header
    timestamp = format_timestamp(section['start'])
    anchor_id = create_anchor_id(
        section['timestamp'],
        section.get('title', 'section')
    )
    marker = section.get('marker', '') if show_markers else ''
    title = section.get('title', 'Section')

    output.append(f'\n<a id="{anchor_id}"></a>\n')
    output.append(f"## {marker} [{timestamp}] {title}\n\n")

    # Optional summary
    if section.get('summary'):
        output.append(f"> **Summary:** {section['summary']}\n\n")

    # Paragraphs
    for para in section['paragraphs']:
        if not minimal_timestamps:
            para_time = format_timestamp(para['start'])
            output.append(f"**[{para_time}]** ")

        # Clean text
        text = clean_filler_words(para['text'])
        output.append(f"{text}\n\n")

    return ''.join(output)
```

### Main Flow Integration

Thread the new CLI options directly into the formatting calls so both diarized and non-diarized paths stay in sync:

```python
    formatting_options = dict(
        paragraph_duration=args.paragraph_duration,
        section_duration=args.section_duration,
        generate_toc=args.generate_toc,
        minimal_timestamps=args.minimal_timestamps,
        content_markers=args.content_markers,
        add_summaries=args.add_summaries,
        diarization_available=diarization is not None,
    )

    if diarization is not None:
        formatted = format_transcript(
            segments,
            args.audio_file,
            speaker_names=speaker_names,
            **formatting_options,
        )
    else:
        formatted = format_transcript_without_diarization(
            transcript,
            args.audio_file,
            **formatting_options,
        )
```

`format_transcript` receives the same keyword arguments so that diarized transcripts run through the identical section/paragraph pipeline (with speaker metadata layered on top).

---

## Phase 4: Post-Processing Utility

### Create `scripts/reformat_transcript.py`

For reformatting existing fragmented transcripts:

```python
#!/usr/bin/env python3
"""
Reformat existing fragmented transcripts into readable format.

Usage:
    python scripts/reformat_transcript.py input.md output.md [options]

Options:
    --paragraph-duration SECONDS    Group into paragraphs (default: 30)
    --generate-toc                  Add table of contents
    --content-markers               Add emoji content type markers
    --section-duration SECONDS      Group paragraphs into sections (default: 300)
"""

import argparse
import re
from pathlib import Path

from podcast_transcriber.utils.formatting import (
    format_improved_transcript,
    fragments_to_paragraphs,
    group_into_sections,
)

def parse_fragmented_transcript(file_path):
    """
    Parse existing fragmented transcript.

    Expected format:
        [00:00:00]

        Text content

        [00:00:03]

        More text

    Returns:
        List of {timestamp, text} dicts
    """
    with open(file_path, 'r') as f:
        content = f.read()

    # Split by timestamp pattern
    pattern = r'\[(\d{2}:\d{2}:\d{2})\]'
    parts = re.split(pattern, content)

    fragments = []
    for i in range(1, len(parts), 2):
        timestamp = parts[i]
        text = parts[i+1].strip() if i+1 < len(parts) else ''

        if text:
            # Convert timestamp to seconds
            h, m, s = map(int, timestamp.split(':'))
            seconds = h * 3600 + m * 60 + s

            fragments.append({
                'timestamp': seconds,
                'text': text
            })

    return fragments

def reformat_transcript(input_file, output_file, **options):
    """Main reformatting function."""
    # Parse existing file
    fragments = parse_fragmented_transcript(input_file)

    # Merge into paragraphs
    paragraphs = fragments_to_paragraphs(
        fragments,
        max_paragraph_seconds=options.get('paragraph_duration', 30)
    )

    # Group into sections
    sections = group_into_sections(
        paragraphs,
        section_duration=options.get('section_duration', 300)
    )

    # Generate output
    output = format_improved_transcript(
        sections,
        audio_name=Path(input_file).name,
        generate_toc=options.get('generate_toc', False),
        minimal_timestamps=False,
        content_markers=options.get('content_markers', False),
        diarization_available=False,
    )

    # Write to file
    with open(output_file, 'w') as f:
        f.write(output)

    print(f"✓ Reformatted transcript saved to: {output_file}")
    print(f"  Reduced from {len(fragments)} fragments to {len(paragraphs)} paragraphs")

def main():
    parser = argparse.ArgumentParser(
        description="Reformat fragmented transcripts into readable format"
    )
    parser.add_argument("input", help="Input transcript file")
    parser.add_argument("output", help="Output file path")
    parser.add_argument(
        "--paragraph-duration",
        type=int,
        default=30,
        help="Maximum paragraph duration in seconds"
    )
    parser.add_argument(
        "--generate-toc",
        action="store_true",
        help="Generate table of contents"
    )
    parser.add_argument(
        "--content-markers",
        action="store_true",
        help="Add emoji content type markers"
    )
    parser.add_argument(
        "--section-duration",
        type=int,
        default=300,
        help="Maximum section duration in seconds"
    )

    args = parser.parse_args()

    reformat_transcript(
        args.input,
        args.output,
        paragraph_duration=args.paragraph_duration,
        section_duration=args.section_duration,
        generate_toc=args.generate_toc,
        content_markers=args.content_markers
    )

if __name__ == "__main__":
    main()
```

---

## Benefits Summary

### Quantitative Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total Lines** | 2,462 | ~200 | 92% reduction |
| **Timecodes Shown** | ~700 | ~50 major + ~100 paragraph | 85% reduction |
| **Visual Clutter** | Extreme | Minimal | Dramatic improvement |
| **Paragraphs** | 0 (all fragments) | ~100-150 | Readable prose |
| **Sections** | 0 | ~15-20 major | Easy navigation |
| **Reading Time** | Impossible (fragmented) | Normal prose speed | Readable |

### Qualitative Improvements

✅ **Readability**
- Flows like natural text
- Can be read continuously
- Professional document appearance

✅ **Navigation**
- Table of contents for instant topic access
- Section headers show progress
- Anchor links for deep linking

✅ **Skimmability**
- Can quickly scan section titles
- Summaries provide overview
- Content markers show type

✅ **Reference**
- Named sections easy to cite
- Timestamps preserved for audio sync
- Professional documentation format

✅ **Sharing**
- Looks professional when shared
- Not embarrassing to send to others
- Actually useful as reference material

---

## Implementation Priority

### Phase 1: Essential (Do First) ⚡
1. ✅ Paragraph grouping (30-second intervals)
2. ✅ Section headers (5-minute intervals)
3. ✅ Clean up duplicate timestamps bug

### Phase 2: High Value 🎯
4. ✅ Table of contents generation
5. ✅ Anchor link system
6. ✅ Format cleanup (remove extra blank lines)

### Phase 3: Enhancement 💎
7. ⚠️ Content type detection
8. ⚠️ Emoji/icon markers
9. ⚠️ Reformat script for existing files

### Phase 4: Optional/Future 💡
10. 🔮 AI-generated section summaries
11. 🔮 Auto-detect topic changes
12. 🔮 Key point extraction
13. 🔮 Cross-reference links between sections

---

## Testing Strategy

### Test Cases

1. **Short Transcript (5 minutes)**
   - Test basic paragraph grouping
   - Verify no errors on small files
   - Check TOC generation

2. **Medium Transcript (30 minutes)**
   - Test section detection
   - Verify section boundaries
   - Check anchor links work

3. **Long Transcript (70 minutes)**
   - Full feature test
   - Performance check
   - Memory usage monitoring

4. **Edge Cases**
   - No timestamps
   - Duplicate timestamps / timestamp resets (verify dedupe & reset guard)
   - Very long paragraphs
   - Very short audio

### Success Criteria

✅ **Functional Requirements**
- Script runs without errors
- Output is valid markdown
- All timestamps preserved
- No content lost

✅ **Quality Requirements**
- Paragraphs <60 seconds
- Sections clearly delineated
- TOC links work
- Readable as continuous prose

✅ **Performance Requirements**
- Processes 70-min transcript in <5 seconds
- Memory usage <500MB
- No regression in transcription quality

---

## Example Output Comparison

### Before (Fragment of Current Output)
```markdown
[00:08:18]

Many of you may not have high blood pressure, but I am betting that you know someone who

[00:08:26]

has high blood pressure, whether this is a parent, a grandparent, a brother, a sister,

[00:08:31]

someone you know likely has high blood pressure.

[00:08:34]

The epidemiology of high blood pressure is astounding.

[00:08:38]

There are millions, millions of people who have high blood pressure in the world, in

[00:08:44]

the United States.
```

### After (Improved Output)
```markdown
## [00:08:16] Main Topic: Hypertension Epidemic

**[00:08:18]** Many of you may not have high blood pressure, but I am betting that you know someone who has high blood pressure, whether this is a parent, a grandparent, a brother, a sister, someone you know likely has high blood pressure. The epidemiology of high blood pressure is astounding. There are millions, millions of people who have high blood pressure in the world, in the United States.

**[00:08:45]** And I will show you there are really hundreds of millions of people who have high blood pressure even in the United States. I will show you some graphics that discuss the actual profound burden of this condition in Americans and in the world.
```

---

## Files to Create/Modify

### New Files
1. `/scripts/reformat_transcript.py` - Utility to reformat existing transcripts
2. `/podcast-transcriber/utils/formatting.py` - Shared formatting helpers for transcripts
3. `/tests/test_transcript_formatting.py` - Tests for new formatting functions

### Modified Files
1. `/podcast-transcriber/scripts/transcribe_podcast.py`
   - Update `format_transcript_without_diarization()`
   - Add new command-line arguments
   - Import helpers from `utils/formatting.py`

### Documentation Updates
1. `/podcast-transcriber/SKILL.md` - Document new flags
2. `/transcribe-podcast/README.md` - Update usage examples
3. `/podcast-transcriber/utils/formatting.py` - Inline docstrings describing helper responsibilities

---

## Next Steps

1. **Review this plan** - Confirm approach before implementation
2. **Implement Phase 1** - Core paragraph/section grouping
3. **Test with existing transcript** - Verify improvements
4. **Iterate** - Adjust based on results
5. **Implement Phase 2** - TOC and navigation
6. **Document** - Update all documentation
7. **Create reformat utility** - For existing files

---

## Notes

- This plan focuses on **readability first**, timestamps second
- Timestamps are preserved but de-emphasized for better reading flow
- All original information is retained, just reformatted
- Can be applied to future transcripts AND existing ones
- Optional features (AI summaries) can be added incrementally

---

**Status:** Ready for implementation
**Last Updated:** 2025-10-31
