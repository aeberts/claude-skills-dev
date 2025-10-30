#!/usr/bin/env python3
"""
Transcript Formatter Script

This script takes a wall-of-text transcript and formats it into readable
markdown with proper paragraphs, cleaned up filler words, and better structure.

Useful for cleaning up raw transcripts that don't have speaker labels or formatting.

Usage:
    python format_transcript.py <input_file> [--output <output_file>]
"""

import argparse
import re
import sys
from pathlib import Path


def clean_filler_words(text):
    """Remove excessive filler words and clean up text."""
    # Remove excessive um, uh, er, ah
    text = re.sub(r'\b(um|uh|er|ah)\b', '', text, flags=re.IGNORECASE)

    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)

    # Clean up punctuation spacing
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    text = re.sub(r'([.,!?])([A-Z])', r'\1 \2', text)

    return text.strip()


def detect_sentence_boundaries(text):
    """
    Split text into sentences, handling common abbreviations.
    """
    # Common abbreviations that shouldn't trigger sentence breaks
    text = re.sub(r'\bDr\.', 'Dr', text)
    text = re.sub(r'\bMr\.', 'Mr', text)
    text = re.sub(r'\bMrs\.', 'Mrs', text)
    text = re.sub(r'\bMs\.', 'Ms', text)
    text = re.sub(r'\bProf\.', 'Prof', text)

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    return sentences


def group_into_paragraphs(sentences, sentences_per_paragraph=5):
    """
    Group sentences into paragraphs for better readability.
    """
    paragraphs = []
    current_para = []

    for sentence in sentences:
        current_para.append(sentence)

        if len(current_para) >= sentences_per_paragraph:
            paragraphs.append(' '.join(current_para))
            current_para = []

    # Add remaining sentences
    if current_para:
        paragraphs.append(' '.join(current_para))

    return paragraphs


def format_transcript(text, input_file):
    """
    Format a wall-of-text transcript into readable markdown.
    """
    output = []

    # Add header
    filename = Path(input_file).name
    output.append("# Formatted Transcript\n")
    output.append(f"**Source:** {filename}\n")
    output.append("\n---\n\n")

    # Clean the text
    text = clean_filler_words(text)

    # Split into sentences
    sentences = detect_sentence_boundaries(text)

    # Group into paragraphs
    paragraphs = group_into_paragraphs(sentences, sentences_per_paragraph=5)

    # Write paragraphs
    for para in paragraphs:
        if para.strip():
            output.append(f"{para}\n\n")

    return ''.join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Format a wall-of-text transcript into readable markdown"
    )
    parser.add_argument("input_file", help="Path to input text file")
    parser.add_argument(
        "--output", "-o",
        help="Output markdown file (default: <input_file>_formatted.md)"
    )

    args = parser.parse_args()

    # Validate input file
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    # Read input
    with open(args.input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Set output file
    output_file = args.output
    if not output_file:
        input_path = Path(args.input_file)
        output_file = input_path.with_stem(input_path.stem + '_formatted').with_suffix('.md')

    print(f"Processing: {args.input_file}")
    print(f"Output will be saved to: {output_file}\n")

    # Format
    print("Formatting transcript...")
    formatted = format_transcript(text, args.input_file)

    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(formatted)

    print(f"✅ Formatted transcript saved to: {output_file}")


if __name__ == "__main__":
    main()
