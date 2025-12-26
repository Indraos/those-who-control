"""
Message parsers for different messenger platforms.
Converts various export formats into a unified JSON structure.

Supported formats:
- WhatsApp: Text exports with [date, time] Sender: Message format
- iMessage: PDF exports from macOS Messages app (layout-aware extraction)
- Facebook Messenger: JSON exports (not yet implemented)
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

def detect_format(content: str, filename: str, is_pdf: bool = False) -> Optional[str]:
    """Auto-detect messenger format from file extension.

    Supported formats:
    - iMessage (PDF exports from macOS Messages app) - .pdf
    - WhatsApp (text exports) - .txt
    - Facebook Messenger (JSON exports) - .json
    """

    print(f"[PARSER] Detecting format for file: {filename}")
    print(f"[PARSER] Content length: {len(content)} characters")
    print(f"[PARSER] Is PDF: {is_pdf}")

    # Simple extension-based detection
    filename_lower = filename.lower()

    if filename_lower.endswith('.json'):
        print("[PARSER] Detected format: Facebook Messenger (JSON)")
        return "facebook"
    elif filename_lower.endswith('.pdf') or is_pdf:
        print("[PARSER] Detected format: iMessage (PDF)")
        return "imessage"
    elif filename_lower.endswith('.txt'):
        print("[PARSER] Detected format: WhatsApp (TXT)")
        return "whatsapp"
    else:
        print(f"[PARSER] ERROR: Unknown file extension for {filename}")
        return None

# PDF library imports
PDF_LIBRARY = None

try:
    import fitz  # PyMuPDF
    PDF_LIBRARY = "pymupdf"
except ImportError:
    pass

if PDF_LIBRARY is None:
    try:
        import pdfplumber
        PDF_LIBRARY = "pdfplumber"
    except ImportError:
        pass

if PDF_LIBRARY is None:
    try:
        from PyPDF2 import PdfReader
        PDF_LIBRARY = "pypdf2"
    except ImportError:
        pass


# ==================== PDF Extraction Functions ====================

def extract_text_from_pdf_pymupdf(pdf_path):
    """Extract text using PyMuPDF (fitz) - fastest and most accurate."""
    doc = fitz.open(pdf_path)
    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()
    return text


def extract_text_from_pdf_pdfplumber(pdf_path):
    """Extract text using pdfplumber - good for complex layouts."""
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

    return text


def extract_text_from_pdf_pypdf2(pdf_path):
    """Extract text using PyPDF2 - fallback option."""
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text

    return text


def extract_imessage_from_pdf_pymupdf(
    pdf_path,
    right_label="You",
    left_label="Them",
    vertical_merge_threshold=15.0
):
    """
    Extract an iMessage-style conversation using layout (left/right bubbles).
    Requires PyMuPDF. Returns a list of message dicts.

    Args:
        pdf_path: Path to PDF file
        right_label: Label for messages on the right side (default: "You")
        left_label: Label for messages on the left side (default: "Them")
        vertical_merge_threshold: Max vertical distance to merge text blocks (default: 15.0)
    """
    if PDF_LIBRARY != "pymupdf":
        raise RuntimeError(
            "iMessage PDF extraction requires PyMuPDF (fitz). "
            "Install with: pip install PyMuPDF"
        )

    doc = fitz.open(pdf_path)
    messages = []
    current_timestamp = "N/A"

    # Timestamp patterns to detect centered date/time headers
    timestamp_patterns = [
        r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\w+\s+\d+\s+at\s+\d{1,2}:\d{2}',  # Mon, Oct 27 at 10:36
        r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d+\.\s+\w+\s+at\s+\d{1,2}:\d{2}',  # Fri 19. Sep at 23:55
        r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}:\d{2}',  # Wednesday 15:15
        r'^(Yesterday|Today)\s+\d{1,2}:\d{2}',  # Today 14:18
    ]

    for page_index, page in enumerate(doc):
        width = page.rect.width
        blocks = page.get_text("blocks")
        blocks_sorted = sorted(blocks, key=lambda b: (b[1], b[0]))
        current_msg = None

        for b in blocks_sorted:
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4].strip()
            if not text:
                continue

            # Filter block-level artifacts
            if text.strip().lower() == "imessage":
                continue

            # Check if any line in this block is a timestamp
            has_timestamp = False
            filtered_lines = []
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # Check skip phrases
                lower = line.lower()
                skip_phrases = ["delivered quietly", "notifications silenced", "notify anyway", "delivered", "imessage"]
                if lower in skip_phrases:
                    continue

                # Skip "Edited" labels
                if line.strip().lower() == "edited":
                    continue

                # Check if timestamp
                is_timestamp_line = False
                for pattern in timestamp_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        current_timestamp = line
                        is_timestamp_line = True
                        print(f"[PARSER] Detected timestamp: {current_timestamp}")
                        break

                if not is_timestamp_line:
                    filtered_lines.append(line)

            # Skip this block if it only contained timestamps or filtered content
            if not filtered_lines:
                continue

            # Rejoin filtered lines into message text
            message_text = '\n'.join(filtered_lines)

            # Decide which side the bubble is on
            # Use left edge position for more reliable detection
            margin_threshold = width * 0.3  # If x0 > 30% of width, it's on the right
            side = "right" if x0 > margin_threshold else "left"
            speaker = right_label if side == "right" else left_label

            # Merge into current message if same speaker & close vertically
            if (
                current_msg is not None
                and current_msg["speaker"] == speaker
                and current_msg["page"] == page_index
                and abs(y0 - current_msg["last_y"]) <= vertical_merge_threshold
            ):
                # Merge continuation text
                current_msg["text"] += " " + message_text
                current_msg["last_y"] = y1
            else:
                # Save previous message
                if current_msg is not None:
                    messages.append(current_msg)

                # Start new message
                current_msg = {
                    "page": page_index,
                    "y": y0,
                    "last_y": y1,
                    "speaker": speaker,
                    "text": message_text,
                    "timestamp": current_timestamp,
                }

        # Save last message on page
        if current_msg is not None:
            messages.append(current_msg)
            current_msg = None

    doc.close()
    messages = sorted(messages, key=lambda m: (m["page"], m["y"]))

    # Handle cross-page duplicates/continuations
    # When text spans pages, PyMuPDF sometimes duplicates the last line of page N
    # at the start of page N+1. Merge these duplicates.
    deduplicated = []
    i = 0
    while i < len(messages):
        current = messages[i]

        # Check if there's a next message that might be a continuation
        if i + 1 < len(messages):
            next_msg = messages[i + 1]

            # If same speaker and next message starts with current message's text
            if (current["speaker"] == next_msg["speaker"] and
                current["page"] + 1 == next_msg["page"] and
                next_msg["text"].startswith(current["text"])):
                # Skip current, keep next (which has the full text)
                i += 1
                continue

        deduplicated.append(current)
        i += 1

    return deduplicated


def extract_text_from_pdf(pdf_bytes, filename: str) -> str:
    """
    Extract text from PDF bytes.
    Detects if it's an iMessage PDF (print from desktop app) and uses
    layout-aware extraction, otherwise falls back to standard text extraction.

    Args:
        pdf_bytes: PDF file content as bytes
        filename: Original filename for format detection

    Returns:
        Extracted text as string
    """
    if PDF_LIBRARY is None:
        raise RuntimeError(
            "No PDF library installed! Install one:\n"
            "  pip install PyMuPDF  (recommended)\n"
            "  pip install pdfplumber\n"
            "  pip install PyPDF2"
        )

    # Save bytes to temporary file for PDF libraries
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        # Check if this looks like an iMessage PDF (use layout-aware extraction)
        if "imessage" in filename.lower() or "message" in filename.lower():
            if PDF_LIBRARY == "pymupdf":
                print("[PARSER] Detected iMessage PDF, using layout-aware extraction")
                messages = extract_imessage_from_pdf_pymupdf(tmp_path)
                if messages:
                    # Convert to text format
                    text_lines = []
                    for msg in messages:
                        sender = msg.get("speaker", "Unknown")
                        message = msg.get("text", "")
                        timestamp = msg.get("timestamp", "N/A")
                        text_lines.append(f"[{timestamp}] {sender}: {message}")
                    return "\n".join(text_lines)

        # Standard text extraction for other PDFs
        print(f"[PARSER] Extracting text from PDF using {PDF_LIBRARY}")
        if PDF_LIBRARY == "pymupdf":
            text = extract_text_from_pdf_pymupdf(tmp_path)
        elif PDF_LIBRARY == "pdfplumber":
            text = extract_text_from_pdf_pdfplumber(tmp_path)
        elif PDF_LIBRARY == "pypdf2":
            text = extract_text_from_pdf_pypdf2(tmp_path)
        else:
            raise ValueError(f"Unknown PDF library: {PDF_LIBRARY}")

        return text

    finally:
        # Clean up temp file
        import os
        try:
            os.unlink(tmp_path)
        except:
            pass


def parse_whatsapp(content: str) -> List[Dict]:
    """Parse WhatsApp chat export format."""
    print("[PARSER] Starting WhatsApp parsing...")
    messages = []

    # Patterns for both US and European date formats
    # US: [12/31/23, 10:30:45 PM] John: Hello there
    # EU: [08.06.24, 15:21:25] John: Hello there
    # Pattern supports with/without seconds and with/without AM/PM
    pattern_us = r'\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?)\]\s+([^:]+):\s*(.+)'
    pattern_eu = r'\[(\d{1,2}\.\d{1,2}\.\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?)\]\s+([^:]+):\s*(.+)'

    lines = content.split('\n')
    print(f"[PARSER] Total lines to process: {len(lines)}")
    current_message = None
    skipped_lines = 0
    matched_lines = 0

    for line_num, line in enumerate(lines, 1):
        # Skip WhatsApp system messages (encryption notice, media omitted, etc.)
        if ("end-to-end encrypted" in line.lower() or
            "‎messages and calls" in line.lower() or
            "image omitted" in line.lower() or
            "video omitted" in line.lower() or
            "audio omitted" in line.lower() or
            "sticker omitted" in line.lower() or
            "gif omitted" in line.lower() or
            "document omitted" in line.lower()):
            skipped_lines += 1
            continue
        # Try US format first
        match = re.match(pattern_us, line)
        if not match:
            # Try EU format
            match = re.match(pattern_eu, line)

        if match:
            matched_lines += 1
            date_str, time_str, sender, message = match.groups()

            # Save previous message if exists
            if current_message:
                messages.append(current_message)

            # Create new message
            timestamp = f"{date_str} {time_str}"
            current_message = {
                "sender": sender.strip(),
                "message": message.strip(),
                "timestamp": timestamp
            }
        elif current_message:
            # Continuation of previous message
            current_message["message"] += "\n" + line

    # Add last message
    if current_message:
        messages.append(current_message)

    print(f"[PARSER] WhatsApp parsing complete: {len(messages)} messages parsed")
    print(f"[PARSER] Matched lines: {matched_lines}, Skipped system messages: {skipped_lines}")

    return messages


def parse_imessage(content: str) -> List[Dict]:
    """Parse iMessage export format from PDF text extraction.

    iMessage PDFs from macOS Messages app are parsed using layout-aware extraction.
    The text format here is: [timestamp] sender: message
    This function handles the text output from extract_imessage_from_pdf_pymupdf.
    """
    messages = []

    # Pattern: [timestamp] Sender: Message
    # Example: [Mon, Oct 27 at 10:36] You: Cool
    pattern = r'\[([^\]]+)\]\s*([^:]+):\s*(.+)'

    lines = content.split('\n')
    current_message = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            if current_message:
                messages.append(current_message)

            timestamp, sender, message = match.groups()
            current_message = {
                "sender": sender.strip(),
                "message": message.strip(),
                "timestamp": timestamp.strip()
            }
        elif current_message:
            # Continuation of previous message
            current_message["message"] += "\n" + line

    if current_message:
        messages.append(current_message)

    return messages




def parse_facebook(content: str) -> List[Dict]:
    """Parse Facebook Messenger JSON export.

    Facebook Messenger exports are JSON files with:
    - participants: list of conversation participants
    - messages: list of message objects with sender_name, timestamp_ms, content

    Returns messages in chronological order (oldest first).
    """
    print("[PARSER] Starting Facebook Messenger parsing...")
    messages = []

    try:
        data = json.loads(content)

        if not isinstance(data, dict):
            print("[PARSER] ERROR: Expected JSON object at root")
            return []

        if "messages" not in data:
            print("[PARSER] ERROR: No 'messages' field in JSON")
            return []

        raw_messages = data["messages"]
        print(f"[PARSER] Found {len(raw_messages)} raw messages")

        for msg in raw_messages:
            # Skip messages without content (reactions, call logs, etc.)
            if "content" not in msg:
                continue

            # Skip reaction messages
            content = msg.get("content", "")
            if "reagiert" in content or "reacted" in content.lower():
                continue

            sender = msg.get("sender_name", "Unknown")
            timestamp_ms = msg.get("timestamp_ms", 0)

            # Convert timestamp from milliseconds to readable format
            if timestamp_ms:
                from datetime import datetime
                dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp = "Unknown"

            messages.append({
                "sender": sender,
                "message": content,
                "timestamp": timestamp
            })

        # Facebook exports are in reverse chronological order, so reverse them
        messages.reverse()

        print(f"[PARSER] Facebook parsing complete: {len(messages)} messages parsed")
        return messages

    except json.JSONDecodeError as e:
        print(f"[PARSER] ERROR: Failed to parse JSON: {e}")
        return []
    except Exception as e:
        print(f"[PARSER] ERROR: Unexpected error during Facebook parsing: {e}")
        return []


def parse_messages(content: str, filename: str = "", content_bytes: bytes = None) -> Dict:
    """
    Main parser function that auto-detects format and returns parsed messages.

    Args:
        content: Text content (or empty string if PDF)
        filename: Original filename
        content_bytes: Optional raw bytes (for PDF detection)

    Returns:
        {
            "format": str,
            "messages": List[Dict],
            "participants": List[str],
            "message_count": int
        }
    """
    print(f"[PARSER] parse_messages called for file: {filename}")

    # Check if this is a PDF file
    is_pdf = False
    if content_bytes and content_bytes[:4] == b'%PDF':
        print("[PARSER] Detected PDF file by magic bytes")
        is_pdf = True
        try:
            content = extract_text_from_pdf(content_bytes, filename)
            print(f"[PARSER] Extracted {len(content)} characters from PDF")
        except Exception as e:
            print(f"[PARSER] ERROR extracting PDF text: {type(e).__name__}: {str(e)}")
            return {
                "format": "unknown",
                "messages": [],
                "participants": [],
                "message_count": 0,
                "error": f"Failed to extract text from PDF: {str(e)}"
            }
    elif filename.lower().endswith('.pdf'):
        print("[PARSER] Detected PDF file by extension")
        is_pdf = True
        if content_bytes:
            try:
                content = extract_text_from_pdf(content_bytes, filename)
                print(f"[PARSER] Extracted {len(content)} characters from PDF")
            except Exception as e:
                print(f"[PARSER] ERROR extracting PDF text: {type(e).__name__}: {str(e)}")
                return {
                    "format": "unknown",
                    "messages": [],
                    "participants": [],
                    "message_count": 0,
                    "error": f"Failed to extract text from PDF: {str(e)}"
                }

    format_type = detect_format(content, filename, is_pdf=is_pdf)

    if not format_type:
        print("[PARSER] ERROR: Format detection failed")
        return {
            "format": "unknown",
            "messages": [],
            "participants": [],
            "message_count": 0,
            "error": "Could not detect message format"
        }

    print(f"[PARSER] Format detected: {format_type}")

    # Parse based on detected format
    parsers = {
        "whatsapp": parse_whatsapp,
        "imessage": parse_imessage,
        "facebook": parse_facebook
    }

    try:
        messages = parsers[format_type](content)
        print(f"[PARSER] Parser returned {len(messages)} messages")
    except Exception as e:
        print(f"[PARSER] ERROR during parsing: {type(e).__name__}: {str(e)}")
        return {
            "format": format_type,
            "messages": [],
            "participants": [],
            "message_count": 0,
            "error": f"Parsing failed: {str(e)}"
        }

    # Extract unique participants
    participants = list(set(msg["sender"] for msg in messages))
    print(f"[PARSER] Extracted {len(participants)} participants: {participants}")

    result = {
        "format": format_type,
        "messages": messages,
        "participants": participants,
        "message_count": len(messages)
    }

    print(f"[PARSER] parse_messages complete: {result['message_count']} messages, {len(result['participants'])} participants")

    return result
