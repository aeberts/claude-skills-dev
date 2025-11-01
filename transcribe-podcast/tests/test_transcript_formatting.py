import sys
from pathlib import Path
from types import SimpleNamespace

PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "podcast-transcriber"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from utils import formatting as fmt


def test_extract_words_from_transcript_handles_duplicates_and_resets():
    transcript = SimpleNamespace(
        words=[
            {"word": "Intro", "start": 0.0, "end": 1.0},
            {"word": "world", "start": 1.2, "end": 2.0},
            {"word": "Intro", "start": 0.0, "end": 1.0},  # duplicate should be ignored
            {"word": "Later", "start": 12.0, "end": 12.5},
            {"word": "Reset", "start": 1.0, "end": 1.5},  # triggers reset
            {"word": "Fresh", "start": 2.0, "end": 2.5},
        ]
    )

    words = fmt.extract_words_from_transcript(transcript, reset_threshold=8.0)
    assert [entry["word"] for entry in words] == ["Reset", "Fresh"]


def test_group_into_paragraphs_breaks_on_pause():
    words = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world.", "start": 0.6, "end": 1.0},
        {"word": "Next", "start": 5.0, "end": 5.5},
        {"word": "sentence.", "start": 5.7, "end": 6.0},
    ]

    paragraphs = fmt.group_into_paragraphs(
        words,
        max_paragraph_seconds=30,
        pause_threshold=2.0,
        max_words=50,
        min_words=2,
    )

    assert len(paragraphs) == 2
    assert paragraphs[0]["text"].startswith("Hello")
    assert paragraphs[0]["text"].endswith("Next")
    assert paragraphs[1]["text"] == "sentence."


def test_group_into_sections_generates_titles():
    paragraphs = [
        {"start": 0.0, "end": 5.0, "text": "This episode is brought to you by Heart and Soil."},
        {"start": 15.0, "end": 20.0, "text": "Use code PAUL for a discount."},
        {"start": 340.0, "end": 350.0, "text": "We cover hypertension and blood pressure basics."},
    ]

    sections = fmt.group_into_sections(paragraphs, section_duration=300)
    assert len(sections) == 2
    assert sections[0]["title"].startswith("Sponsor")
    assert sections[1]["title"] == "Hypertension Discussion"


def test_format_improved_transcript_produces_toc_and_anchors():
    sections = [
        {
            "start": 0.0,
            "title": "Introduction",
            "paragraphs": [{"start": 0.0, "end": 5.0, "text": "Welcome to the show."}],
        },
        {
            "start": 120.0,
            "title": "Main Topic",
            "paragraphs": [{"start": 120.0, "end": 180.0, "text": "Deep dive into ideas."}],
        },
    ]

    output = fmt.format_improved_transcript(
        sections,
        audio_name="episode.mp3",
        generate_toc=True,
        minimal_timestamps=False,
        content_markers=False,
        diarization_available=True,
        metadata_lines=["**Duration:** [00:05:00]"],
    )

    assert "## Table of Contents" in output
    assert "- [00:00 Introduction](#00-00-introduction)" in output
    assert '## <a id="02-00-main-topic"></a' in output
