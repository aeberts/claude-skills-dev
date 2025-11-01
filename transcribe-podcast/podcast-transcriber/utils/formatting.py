"""Shared helpers for improving podcast transcript readability."""

from __future__ import annotations

import os
import re
from datetime import timedelta
from typing import Callable, Dict, List, Optional, Sequence

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


# ---------------------------------------------------------------------------
# Timestamp Helpers
# ---------------------------------------------------------------------------

def format_timestamp(seconds: float) -> str:
    """Return HH:MM:SS timestamp string for a floating-point second value."""
    total_seconds = max(0, int(round(seconds)))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"


def format_timestamp_short(seconds: float) -> str:
    """Return MM:SS for durations <1 hour, otherwise HH:MM:SS."""
    total_seconds = max(0, int(round(seconds)))
    if total_seconds < 3600:
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def create_anchor_id(timestamp: float, title: str) -> str:
    """Convert timestamp and title into a markdown anchor slug."""
    base = f"{format_timestamp_short(timestamp)} {title}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return slug or "section"


# ---------------------------------------------------------------------------
# Text Normalisation Utilities
# ---------------------------------------------------------------------------

def clean_filler_words(text: str) -> str:
    """Normalize whitespace and remove simple filler tokens."""
    cleaned = re.sub(r"\b(um|uh|er|ah)\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([.,!?])", r"\1", cleaned)
    return cleaned.strip()


def extract_section_text(section: Dict) -> str:
    """Concatenate paragraph text for a section."""
    paragraphs = section.get("paragraphs", [])
    return " ".join(para.get("text", "").strip() for para in paragraphs if para.get("text")).strip()


def extract_sponsor_name(paragraph_text: str) -> str:
    """Detect sponsor or brand mentions from introductory paragraphs."""
    sponsor_patterns = [
        r"(?:sponsor(?:ed)? by|brought to you by)\s+([A-Za-z0-9 &'-]+)",
        r"use code\s+([A-Za-z0-9]+)",
        r"visit\s+([A-Za-z0-9\.-]+)\.com",
        r"heart and soil",
        r"white oak",
        r"eight sleep",
        r"eight-sleep",
    ]

    lowered = paragraph_text.lower()
    for pattern in sponsor_patterns:
        match = re.search(pattern, lowered)
        if match:
            brand = match.group(match.lastindex or 0) if match.lastindex else match.group(0)
            brand = re.sub(r"[^a-z0-9 &'-]", " ", brand).strip()
            if brand:
                return f"Sponsor: {brand.title()}"

    return "Sponsor Segment"


# ---------------------------------------------------------------------------
# Transcript Extraction
# ---------------------------------------------------------------------------

def extract_words_from_transcript(transcript, reset_threshold: float = 8.0) -> List[Dict]:
    """Extract word-level timestamps, normalising duplicates and resets."""
    words: List[Dict] = []
    seen_tokens = set()
    last_end: Optional[float] = None

    def append_word(word_data):
        nonlocal last_end
        token = ""
        start = None
        end = None

        if isinstance(word_data, dict):
            token = word_data.get("word") or word_data.get("text") or ""
            start = word_data.get("start")
            end = word_data.get("end")
        else:
            token = getattr(word_data, "word", "") or getattr(word_data, "text", "")
            start = getattr(word_data, "start", None)
            end = getattr(word_data, "end", None)

        if not token:
            return
        if start is None and end is None:
            return

        if start is None:
            start = end
        if end is None:
            end = start

        try:
            start_f = float(start)
            end_f = float(end)
        except (TypeError, ValueError):
            return

        dedupe_key = (round(start_f, 3), round(end_f, 3), token.strip())
        if dedupe_key in seen_tokens:
            return

        if last_end is not None and start_f + 1e-3 < last_end - reset_threshold:
            words.clear()
            seen_tokens.clear()

        seen_tokens.add(dedupe_key)
        last_end = end_f
        words.append({"word": token, "start": start_f, "end": end_f})

    if hasattr(transcript, "words") and getattr(transcript, "words"):
        for word_data in transcript.words:
            append_word(word_data)

    segments = []
    if hasattr(transcript, "segments") and getattr(transcript, "segments"):
        segments = transcript.segments
    elif isinstance(transcript, dict) and transcript.get("segments"):
        segments = transcript["segments"]

    use_segments = not words
    if use_segments:
        for segment in segments or []:
            segment_words = None
            segment_text = None
            start = None
            end = None

            if isinstance(segment, dict):
                segment_words = segment.get("words")
                segment_text = segment.get("text")
                start = segment.get("start")
                end = segment.get("end")
            else:
                segment_words = getattr(segment, "words", None)
                segment_text = getattr(segment, "text", None)
                start = getattr(segment, "start", None)
                end = getattr(segment, "end", None)

            if segment_words:
                for word_data in segment_words:
                    append_word(word_data)
            elif segment_text:
                append_word({"word": segment_text.strip(), "start": start, "end": end})

    if not words and hasattr(transcript, "text"):
        text = getattr(transcript, "text", "")
        if text:
            append_word({"word": text.strip(), "start": 0.0, "end": 0.0})

    words.sort(key=lambda item: item["start"])
    return words


# ---------------------------------------------------------------------------
# Paragraph & Section Grouping
# ---------------------------------------------------------------------------

def group_into_paragraphs(
    words: Sequence[Dict],
    max_paragraph_seconds: int = 30,
    pause_threshold: float = 2.5,
    max_words: int = 140,
    min_words: int = 12,
) -> List[Dict]:
    """Group words into paragraphs using timing and sentence heuristics."""
    if not words:
        return []

    paragraphs: List[Dict] = []
    current_tokens: List[str] = []
    paragraph_start = words[0]["start"]
    last_end = words[0]["end"]

    def flush(final_timestamp):
        if not current_tokens:
            return
        text = " ".join(token.strip() for token in current_tokens if token.strip())
        if not text:
            return
        paragraphs.append(
            {
                "start": paragraph_start,
                "end": final_timestamp,
                "text": text,
            }
        )

    for idx, word in enumerate(words):
        token = word["word"]
        start = word["start"]
        end = word["end"]

        if not current_tokens:
            paragraph_start = start

        current_tokens.append(token)
        duration = end - paragraph_start
        pause = start - last_end if idx > 0 else 0.0

        sentence_end = token.strip().endswith((".", "!", "?"))
        hit_hard_cap = duration >= max_paragraph_seconds
        hit_pause = pause >= pause_threshold
        hit_soft_cap = duration >= (max_paragraph_seconds * 0.5) and len(current_tokens) >= max_words

        should_break = False
        if hit_hard_cap or hit_soft_cap:
            should_break = True
        elif sentence_end and duration >= 6 and len(current_tokens) >= min_words:
            should_break = True
        elif hit_pause and len(current_tokens) >= min_words:
            should_break = True

        if should_break:
            flush(end)
            current_tokens = []

        last_end = end

    if current_tokens:
        flush(words[-1]["end"])

    return paragraphs


def build_paragraphs_from_segments(
    segments: Sequence[Dict],
    *,
    speaker_names: Optional[Dict[str, str]] = None,
    max_duration: int = 30,
) -> List[Dict]:
    """Convert diarized segments into paragraphs with speaker metadata."""
    paragraphs: List[Dict] = []
    current_speaker: Optional[str] = None
    current_label = ""
    current_text: List[str] = []
    paragraph_start: Optional[float] = None
    paragraph_end: Optional[float] = None

    def speaker_label(raw_speaker: str) -> str:
        if speaker_names and raw_speaker in speaker_names:
            return speaker_names[raw_speaker]
        match = re.search(r"(\d+)", raw_speaker or "")
        if match:
            return f"Speaker {int(match.group(1)) + 1}"
        return raw_speaker or "Speaker"

    def flush():
        if not current_text or paragraph_start is None or paragraph_end is None:
            return
        text = " ".join(current_text).strip()
        if not text:
            return
        paragraphs.append(
            {
                "start": paragraph_start,
                "end": paragraph_end,
                "text": f"**{current_label}:** {text}",
            }
        )

    for seg in segments:
        speaker = seg.get("speaker") if isinstance(seg, dict) else getattr(seg, "speaker", None)
        text = seg.get("text") if isinstance(seg, dict) else getattr(seg, "text", "")
        start = seg.get("start") if isinstance(seg, dict) else getattr(seg, "start", 0.0)
        end = seg.get("end") if isinstance(seg, dict) else getattr(seg, "end", start)

        if speaker is None:
            speaker = "UNKNOWN"

        label = speaker_label(speaker)

        if current_speaker is None:
            current_speaker = speaker
            current_label = label
            paragraph_start = start
            paragraph_end = end
            current_text = [text]
            continue

        duration = end - (paragraph_start or 0.0)
        speaker_changed = speaker != current_speaker

        if speaker_changed or duration >= max_duration:
            flush()
            current_speaker = speaker
            current_label = label
            paragraph_start = start
            paragraph_end = end
            current_text = [text]
        else:
            current_text.append(text)
            paragraph_end = end

    flush()
    return paragraphs


def fragments_to_paragraphs(
    fragments: Sequence[Dict],
    *,
    max_paragraph_seconds: int = 30,
    pause_threshold: float = 2.5,
    min_fragments: int = 2,
) -> List[Dict]:
    """Convert timestamped markdown fragments into paragraph dictionaries."""
    if not fragments:
        return []

    paragraphs: List[Dict] = []
    current_text: List[str] = []
    paragraph_start = fragments[0]["timestamp"]
    last_timestamp = paragraph_start

    def flush(final_timestamp: float):
        if not current_text:
            return
        text = " ".join(fragment.strip() for fragment in current_text if fragment.strip())
        if not text:
            return
        paragraphs.append({"start": paragraph_start, "end": final_timestamp, "text": text})

    for idx, fragment in enumerate(fragments):
        start = fragment["timestamp"]
        text = fragment["text"]
        duration = start - paragraph_start
        pause = start - last_timestamp if current_text else 0.0

        current_text.append(text)
        last_timestamp = start

        is_sentence_end = text.rstrip().endswith((".", "!", "?"))
        hit_hard_cap = duration >= max_paragraph_seconds
        hit_pause = pause >= pause_threshold
        enough_content = len(current_text) >= min_fragments

        should_break = False
        if hit_hard_cap:
            should_break = True
        elif is_sentence_end and duration >= 6 and enough_content:
            should_break = True
        elif hit_pause and enough_content:
            should_break = True

        if should_break:
            flush(start)
            current_text = []
            if idx + 1 < len(fragments):
                paragraph_start = fragments[idx + 1]["timestamp"]

    if current_text:
        flush(last_timestamp)

    return paragraphs


def group_into_sections(paragraphs: Sequence[Dict], section_duration: int = 300) -> List[Dict]:
    """Group paragraphs into larger sections using duration-based cuts."""
    if not paragraphs:
        return []

    sections: List[Dict] = []
    current_section = {
        "paragraphs": [],
        "start": paragraphs[0]["start"],
        "timestamp": paragraphs[0]["start"],
        "title": None,
    }

    for para in paragraphs:
        if current_section["paragraphs"]:
            first_start = current_section["start"]
            if para["start"] - first_start >= section_duration:
                sections.append(current_section)
                current_section = {
                    "paragraphs": [para],
                    "start": para["start"],
                    "timestamp": para["start"],
                    "title": None,
                }
                continue

        current_section["paragraphs"].append(para)

    if current_section["paragraphs"]:
        current_section.setdefault("timestamp", current_section["start"])
        sections.append(current_section)

    return generate_section_titles(sections)


def generate_section_titles(sections: Sequence[Dict]) -> List[Dict]:
    """Generate human-friendly section titles using simple heuristics."""
    for index, section in enumerate(sections):
        paragraphs = section.get("paragraphs", [])
        if not paragraphs:
            section["title"] = f"Section at {format_timestamp(section.get('start', 0))}"
            section["type"] = "general"
            continue

        first_para_text = paragraphs[0]["text"]
        lowered = first_para_text.lower()

        sponsor_keywords = [
            "sponsor",
            "brought to you by",
            "promo code",
            "heart and soil",
            "white oak",
            "8sleep",
            "eight sleep",
            "primal pastures",
        ]
        hypertension_keywords = ["hypertension", "blood pressure"]

        if any(keyword in lowered for keyword in sponsor_keywords):
            section["title"] = extract_sponsor_name(first_para_text)
            section["type"] = "sponsor"
            continue

        if index == 0:
            section["title"] = "Introduction"
            section["type"] = "intro"
            continue

        if any(keyword in lowered for keyword in hypertension_keywords):
            section["title"] = "Hypertension Discussion"
            section["type"] = "main_content"
            continue

        section["title"] = f"Section at {format_timestamp(section['start'])}"
        section["type"] = section.get("type", "general")

    return list(sections)


# ---------------------------------------------------------------------------
# Content Markers & Summaries
# ---------------------------------------------------------------------------

def detect_content_types(sections: Sequence[Dict]) -> List[Dict]:
    """Enrich sections with coarse content markers."""
    type_markers = {
        "intro": "🎙️",
        "sponsor": "💡",
        "main_content": "🧠",
        "qa": "❓",
        "closing": "🏁",
        "general": "📝",
    }

    qa_keywords = ["q&a", "question", "listener"]
    closing_keywords = ["thanks for listening", "see you next", "wrap up", "closing"]

    for section in sections:
        paragraphs = section.get("paragraphs", [])
        combined = " ".join(para.get("text", "") for para in paragraphs).lower()

        if any(keyword in combined for keyword in qa_keywords):
            section["type"] = "qa"
        elif any(keyword in combined for keyword in closing_keywords):
            section["type"] = "closing"

        section["marker"] = type_markers.get(section.get("type", "general"), "📝")

    return list(sections)


def add_section_summaries(
    sections: Sequence[Dict],
    summary_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> List[Dict]:
    """Attach summaries to sections using the provided summary function."""
    summary_callable = summary_fn
    if summary_callable is None and os.environ.get("OPENAI_API_KEY"):
        summary_callable = generate_summary_with_openai

    if summary_callable is None:
        return list(sections)

    for section in sections:
        section_text = extract_section_text(section)
        if not section_text:
            continue
        summary = summary_callable(section_text)
        if summary:
            section["summary"] = summary.strip()

    return list(sections)


def generate_summary_with_openai(section_text: str, *, model: str = "gpt-4o-mini") -> Optional[str]:
    """Generate a short summary using OpenAI if available."""
    if OpenAI is None:
        return None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    prompt = (
        "Summarize this podcast transcript section in 2 concise sentences. "
        "Focus on the key ideas and avoid marketing fluff.\n\n"
        f"Section:\n{section_text}"
    )

    try:  # pragma: no cover - network path
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        choice = response.choices[0].message.content.strip()
        return choice
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Markdown Rendering
# ---------------------------------------------------------------------------

def generate_table_of_contents(sections: Sequence[Dict]) -> str:
    """Build a markdown table of contents with anchor links."""
    if not sections:
        return ""

    lines = ["## Table of Contents", ""]
    for section in sections:
        title = section.get("title") or "Section"
        anchor_id = section.get("anchor_id") or create_anchor_id(section.get("start", 0.0), title)
        section["anchor_id"] = anchor_id
        timestamp = format_timestamp_short(section.get("start", 0.0))
        lines.append(f"- [{timestamp} {title}](#{anchor_id})")

    return "\n".join(lines)


def format_section(section: Dict, *, minimal_timestamps: bool, show_markers: bool) -> str:
    """Render a section into markdown."""
    title = section.get("title") or "Section"
    timestamp = format_timestamp(section.get("start", 0.0))
    anchor_id = section.get("anchor_id") or create_anchor_id(section.get("start", 0.0), title)
    section["anchor_id"] = anchor_id

    marker = section.get("marker") if show_markers else ""
    marker_prefix = f"{marker} " if marker else ""

    lines: List[str] = [f"## <a id=\"{anchor_id}\"></a>{timestamp} {marker_prefix}{title}", ""]

    summary = section.get("summary")
    if summary:
        lines.append(f"> **Summary:** {summary}")
        lines.append("")

    for para in section.get("paragraphs", []):
        text = clean_filler_words(para.get("text", ""))
        if not text:
            continue
        if minimal_timestamps:
            lines.append(text)
        else:
            para_ts = format_timestamp(para.get("start", 0.0))
            lines.append(f"**{para_ts}** {text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n\n"


def format_improved_transcript(
    sections: Sequence[Dict],
    *,
    audio_name: str,
    generate_toc: bool,
    minimal_timestamps: bool,
    content_markers: bool,
    diarization_available: bool,
    metadata_lines: Optional[Sequence[str]] = None,
) -> str:
    """Compose the full improved transcript markdown."""
    note_line = (
        "**Speakers identified via diarization.**"
        if diarization_available
        else "**Note:** Speaker diarization was not available for this transcript."
    )

    header_lines = ["# Podcast Transcript", f"**File:** {audio_name}"]

    if metadata_lines:
        header_lines.extend(metadata_lines)

    header_lines.extend(
        [
            note_line,
            "",
            "---",
            "",
        ]
    )

    toc_block: List[str] = []
    if generate_toc:
        toc = generate_table_of_contents(sections)
        if toc:
            toc_block = [toc, "", "---", ""]

    body_lines: List[str] = []
    for section in sections:
        body_lines.append(
            format_section(
                section,
                minimal_timestamps=minimal_timestamps,
                show_markers=content_markers,
            ).rstrip()
        )
    body = "\n\n".join(line for line in body_lines if line)

    components = header_lines + toc_block
    if body:
        components.append(body)

    return "\n".join(components).strip() + "\n"
