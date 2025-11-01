#!/usr/bin/env python3
"""
Reformat existing fragmented podcast transcripts into the improved readable format.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from utils.formatting import (
    format_improved_transcript,
    format_timestamp,
    fragments_to_paragraphs,
    group_into_sections,
)


def parse_fragmented_transcript(file_path: Path):
    """
    Parse fragmented transcript files that contain one sentence per timestamp block.

    Returns a list of fragment dictionaries with `timestamp` and `text` keys.
    """
    content = file_path.read_text(encoding="utf-8")
    pattern = r"\[(\d{2}:\d{2}:\d{2})\]"
    parts = re.split(pattern, content)

    fragments = []
    for idx in range(1, len(parts), 2):
        timestamp = parts[idx]
        text = parts[idx + 1].strip() if idx + 1 < len(parts) else ""
        if not text:
            continue
        hours, minutes, seconds = (int(value) for value in timestamp.split(":"))
        total_seconds = hours * 3600 + minutes * 60 + seconds
        fragments.append({"timestamp": float(total_seconds), "text": text})

    return fragments


def reformat_transcript(
    input_file: Path,
    output_file: Path,
    *,
    paragraph_duration: int,
    section_duration: int,
    generate_toc: bool,
    content_markers: bool,
):
    if input_file.resolve() == output_file.resolve():
        raise ValueError("Output file must differ from input file to prevent overwriting.")

    fragments = parse_fragmented_transcript(input_file)
    if not fragments:
        raise ValueError("No timestamped fragments found in the input file.")

    paragraphs = fragments_to_paragraphs(
        fragments,
        max_paragraph_seconds=paragraph_duration,
    )
    sections = group_into_sections(paragraphs, section_duration=section_duration)

    metadata_lines = []
    if paragraphs:
        metadata_lines.append(f"**Duration:** {format_timestamp(paragraphs[-1]['end'])}")
        metadata_lines.append(f"**Paragraphs:** {len(paragraphs)}")

    output = format_improved_transcript(
        sections,
        audio_name=input_file.name,
        generate_toc=generate_toc,
        minimal_timestamps=False,
        content_markers=content_markers,
        diarization_available=False,
        metadata_lines=metadata_lines,
    )

    output_file.write_text(output, encoding="utf-8")
    print(f"✓ Reformatted transcript saved to: {output_file}")
    print(f"  Reduced from {len(fragments)} fragments to {len(paragraphs)} paragraphs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reformat fragmented podcast transcripts into the improved layout."
    )
    parser.add_argument("input", help="Input transcript markdown file with frequent timestamps.")
    parser.add_argument("output", help="Destination file path for the reformatted transcript.")
    parser.add_argument(
        "--paragraph-duration",
        type=int,
        default=30,
        help="Maximum paragraph duration in seconds (default: 30).",
    )
    parser.add_argument(
        "--section-duration",
        type=int,
        default=300,
        help="Maximum section duration in seconds (default: 300).",
    )
    parser.add_argument(
        "--generate-toc",
        action="store_true",
        help="Include a table of contents in the output.",
    )
    parser.add_argument(
        "--content-markers",
        action="store_true",
        help="Add emoji markers to indicate section content types.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        parser.error(f"Input file not found: {input_path}")

    try:
        reformat_transcript(
            input_path,
            output_path,
            paragraph_duration=args.paragraph_duration,
            section_duration=args.section_duration,
            generate_toc=args.generate_toc,
            content_markers=args.content_markers,
        )
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main(sys.argv[1:])
