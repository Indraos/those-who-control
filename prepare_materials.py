#!/usr/bin/env python3
"""
Print Materials - Fading Memory Aesthetic

Generates PDFs of project documentation with partially erased features to reflect
the theme of changing memory and the malleability of the past.

Usage: python print_materials.py [--output-dir DIR] [--send-to-printer]
    --output-dir: Directory to save PDFs (default: print_output/)
    --send-to-printer: Send PDFs to default printer after generation
"""

import os
import sys
import re
import random
import argparse
import subprocess
import json
import requests
from pathlib import Path
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Flowable, Image
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
except ImportError:
    print("ERROR: ReportLab not found. Install with: pip install reportlab")
    sys.exit(1)

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class FadingMemoryStyle:
    """Configuration for the fading memory aesthetic"""

    # Probability that a word will be partially/fully erased
    FADE_PROBABILITY = 0.15

    # Different levels of fading (level_name, probability, hex_color)
    FADE_LEVELS = [
        ('full', 0.35, '#000000'),      # Full opacity - black
        ('medium', 0.35, '#666666'),    # Medium fade - gray
        ('light', 0.20, '#AAAAAA'),     # Light fade - light gray
        ('erased', 0.10, '#DDDDDD'),    # Almost gone - very light gray
    ]

    # Words that have thematic significance - more likely to fade
    THEMATIC_WORDS = {
        'memory', 'past', 'future', 'present', 'remember', 'forget',
        'identity', 'change', 'transformation', 'control', 'history',
        'authentic', 'truth', 'real', 'alter', 'edit', 'rewrite',
        'malleable', 'narrative', 'reconstruct', 'erase', 'preserve',
        'orwell', 'stalin', 'trotsky', 'ai', 'algorithm'
    }

    # Increase fade probability for thematic words
    THEMATIC_FADE_BOOST = 0.25


def should_fade_word(word):
    """Determine if a word should fade based on probability"""
    # Clean word for checking
    clean_word = word.lower().strip('.,!?;:"\'()[]{}')

    base_prob = FadingMemoryStyle.FADE_PROBABILITY

    # Boost probability for thematic words
    if clean_word in FadingMemoryStyle.THEMATIC_WORDS:
        base_prob += FadingMemoryStyle.THEMATIC_FADE_BOOST

    return random.random() < base_prob


def get_fade_level():
    """Randomly select a fade level based on weighted probabilities"""
    roll = random.random()
    cumulative = 0

    for level, probability, color in FadingMemoryStyle.FADE_LEVELS:
        cumulative += probability
        if roll < cumulative:
            return level, color

    # Default to full opacity
    return 'full', '#000000'


def escape_xml(text):
    """Escape XML special characters for ReportLab"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def process_inline_formatting(text):
    """
    Convert markdown inline formatting to ReportLab tags.
    Handles: **bold**, *italic*, _italic_, `code`
    Returns list of (type, content) tuples.
    """
    import re

    # Pattern to match inline formatting
    # Order matters: code first (to protect it), then bold, then italic
    pattern = r'(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)'

    parts = []
    last_end = 0

    for match in re.finditer(pattern, text):
        # Add any text before this match
        if match.start() > last_end:
            parts.append(('text', text[last_end:match.start()]))

        matched_text = match.group(1)

        # Determine type and extract content
        if matched_text.startswith('`') and matched_text.endswith('`'):
            # Inline code
            parts.append(('code', escape_xml(matched_text[1:-1])))
        elif matched_text.startswith('**') and matched_text.endswith('**'):
            # Bold
            parts.append(('bold', matched_text[2:-2]))
        elif matched_text.startswith('*') and matched_text.endswith('*'):
            # Italic (asterisk)
            parts.append(('italic', matched_text[1:-1]))
        elif matched_text.startswith('_') and matched_text.endswith('_'):
            # Italic (underscore)
            parts.append(('italic', matched_text[1:-1]))
        else:
            # Shouldn't happen, but treat as text
            parts.append(('text', matched_text))

        last_end = match.end()

    # Add any remaining text
    if last_end < len(text):
        parts.append(('text', text[last_end:]))

    # If no formatting was found, return as plain text
    if not parts:
        parts.append(('text', text))

    return parts


def apply_fading_to_text_segment(text):
    """
    Apply fading to a plain text segment (no formatting).
    Returns text with color font tags.
    """
    words = text.split(' ')
    faded_words = []

    for word in words:
        if not word:
            faded_words.append(word)
            continue

        # Decide if this word should have fading
        if should_fade_word(word):
            level, color = get_fade_level()
            escaped_word = escape_xml(word)
            faded_word = f'<font color="{color}">{escaped_word}</font>'
            faded_words.append(faded_word)
        else:
            faded_words.append(escape_xml(word))

    return ' '.join(faded_words)


def apply_fading_to_paragraph(text, is_heading=False):
    """
    Apply fading effect to text using ReportLab's inline color tags.
    Returns text with formatting tags: <b>, <i>, <font>.
    Handles: **bold**, *italic*, _italic_, `code`
    """
    if not text.strip():
        return text

    # Process inline formatting (bold, italic, code)
    parts = process_inline_formatting(text)

    result = []
    for part_type, part_text in parts:
        if part_type == 'code':
            # Code - already escaped, don't fade
            result.append(f'<font name="Courier" size="9">{part_text}</font>')

        elif part_type == 'bold':
            # Bold - apply fading to content, then wrap in <b>
            if is_heading and random.random() > 0.3:
                # Don't fade headings as much
                result.append(f'<b>{escape_xml(part_text)}</b>')
            else:
                faded_content = apply_fading_to_text_segment(part_text)
                result.append(f'<b>{faded_content}</b>')

        elif part_type == 'italic':
            # Italic - apply fading to content, then wrap in <i>
            if is_heading and random.random() > 0.3:
                result.append(f'<i>{escape_xml(part_text)}</i>')
            else:
                faded_content = apply_fading_to_text_segment(part_text)
                result.append(f'<i>{faded_content}</i>')

        else:  # 'text'
            # Regular text - apply fading
            if is_heading and random.random() > 0.3:
                # Don't fade headings as much
                result.append(escape_xml(part_text))
            else:
                result.append(apply_fading_to_text_segment(part_text))

    return ''.join(result)


class FadedLine(Flowable):
    """Custom flowable for horizontal rules with fading effect"""

    def __init__(self, width):
        Flowable.__init__(self)
        self.width = width
        self.height = 1

    def draw(self):
        self.canv.setStrokeColor(HexColor('#CCCCCC'))
        self.canv.setLineWidth(0.5)
        self.canv.line(0, 0, self.width, 0)


def parse_markdown_to_story(content, styles):
    """
    Parse markdown content and convert to ReportLab story elements.
    Applies fading effect to text.
    """
    lines = content.split('\n')
    story = []
    in_code_block = False
    in_list = False

    for line in lines:
        # Handle code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            if not in_code_block:
                story.append(Spacer(1, 0.1*inch))
            continue

        if in_code_block:
            # Apply light fading to code
            faded_line = apply_fading_to_paragraph(line, is_heading=False)
            story.append(Paragraph(faded_line, styles['Code']))
            continue

        # Empty lines
        if not line.strip():
            if in_list:
                in_list = False
            story.append(Spacer(1, 0.08*inch))
            continue

        # Headers
        if line.startswith('# '):
            text = apply_fading_to_paragraph(line[2:], is_heading=True)
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph(text, styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))
        elif line.startswith('## '):
            text = apply_fading_to_paragraph(line[3:], is_heading=True)
            story.append(Spacer(1, 0.12*inch))
            story.append(Paragraph(text, styles['Heading2']))
            story.append(Spacer(1, 0.08*inch))
        elif line.startswith('### '):
            text = apply_fading_to_paragraph(line[4:], is_heading=True)
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(text, styles['Heading3']))
            story.append(Spacer(1, 0.06*inch))
        # Blockquote
        elif line.startswith('> '):
            text = apply_fading_to_paragraph(line[2:])
            story.append(Paragraph(text, styles['Quote']))
        # Unordered list
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            in_list = True
            text = apply_fading_to_paragraph(line.strip()[2:])
            story.append(Paragraph(f'• {text}', styles['Bullet']))
        # Horizontal rule
        elif line.strip() in ['---', '***', '___']:
            story.append(Spacer(1, 0.1*inch))
            story.append(FadedLine(6*inch))
            story.append(Spacer(1, 0.1*inch))
        # Regular paragraph
        else:
            text = apply_fading_to_paragraph(line)
            if text.strip():
                story.append(Paragraph(text, styles['Body']))

    return story


def create_pdf_document(input_file, output_file):
    """Create a PDF with fading memory aesthetic from a markdown file"""

    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = Path(input_file).name
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Create PDF
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title=f"{filename} - Fading Memory",
    )

    # Define styles
    # Using Times-Roman/Times-Bold for headings (serif, similar to Garamond)
    # Using Helvetica for body text (sans-serif, similar to Inter)
    styles = {
        'Title': ParagraphStyle(
            'Title',
            fontName='Times-Bold',  # Garamond-like serif
            fontSize=18,
            textColor=HexColor('#222222'),
            spaceAfter=6,
            alignment=TA_CENTER,
        ),
        'Metadata': ParagraphStyle(
            'Metadata',
            fontName='Helvetica-Oblique',  # Inter-like sans-serif
            fontSize=8,
            textColor=HexColor('#888888'),
            spaceAfter=0.2*inch,
            alignment=TA_CENTER,
        ),
        'Heading1': ParagraphStyle(
            'Heading1',
            fontName='Times-Bold',  # Garamond-like serif
            fontSize=16,
            textColor=HexColor('#222222'),
            spaceAfter=8,
        ),
        'Heading2': ParagraphStyle(
            'Heading2',
            fontName='Times-Bold',  # Garamond-like serif
            fontSize=14,
            textColor=HexColor('#333333'),
            spaceAfter=6,
        ),
        'Heading3': ParagraphStyle(
            'Heading3',
            fontName='Times-Bold',  # Garamond-like serif
            fontSize=12,
            textColor=HexColor('#444444'),
            spaceAfter=4,
        ),
        'Body': ParagraphStyle(
            'Body',
            fontName='Helvetica',  # Inter-like sans-serif
            fontSize=10,
            textColor=HexColor('#000000'),
            spaceAfter=6,
            leading=14,
        ),
        'Code': ParagraphStyle(
            'Code',
            fontName='Courier',
            fontSize=8,
            textColor=HexColor('#444444'),
            leftIndent=20,
            spaceAfter=2,
            leading=10,
        ),
        'Quote': ParagraphStyle(
            'Quote',
            fontName='Helvetica-Oblique',  # Inter-like sans-serif
            fontSize=10,
            textColor=HexColor('#555555'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=6,
            leading=14,
        ),
        'Bullet': ParagraphStyle(
            'Bullet',
            fontName='Helvetica',  # Inter-like sans-serif
            fontSize=10,
            textColor=HexColor('#000000'),
            leftIndent=20,
            spaceAfter=4,
            leading=13,
        ),
    }

    # Build story
    story = []

    # Title
    story.append(Paragraph(f'<b>{filename}</b>', styles['Title']))
    story.append(Paragraph(f'Generated: {timestamp}', styles['Metadata']))
    story.append(Spacer(1, 0.1*inch))

    # Parse markdown content and add to story
    story.extend(parse_markdown_to_story(content, styles))

    # Build PDF
    doc.build(story)
    print(f"  Created: {output_file}")


def get_modal_workspace():
    """Get current Modal workspace name from CLI"""
    try:
        result = subprocess.run(
            ['modal', 'profile', 'current'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def extract_modal_url(main_py_path):
    """
    Extract Modal app URL from main.py file.
    Looks for @modal.asgi_app(label="...") decorator.
    Returns URL or None if not found.
    """
    try:
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find label in @modal.asgi_app decorator
        match = re.search(r'@modal\.asgi_app\(label="([^"]+)"\)', content)
        if not match:
            return None

        label = match.group(1)

        # Get workspace
        workspace = get_modal_workspace()
        if not workspace:
            return None

        # Construct URL
        return f"https://{workspace}--{label}.modal.run"

    except Exception as e:
        print(f"  Warning: Could not extract URL from {main_py_path}: {e}")
        return None


def generate_qr_code_image(url, size=10):
    """
    Generate QR code image for a URL.
    Returns PIL Image object.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return img


def create_qr_codes_pdf(output_file, project_root):
    """
    Create a PDF with QR codes for Modal apps.
    """
    if not QRCODE_AVAILABLE:
        print("  Warning: qrcode library not installed. Skipping QR code generation.")
        print("  Install with: pip install qrcode[pil]")
        return False

    # Find Modal apps and extract URLs
    modal_apps = [
        {
            'name': 'Past Messages',
            'path': project_root / 'past_messages' / 'main.py',
        },
        {
            'name': 'Past Images',
            'path': project_root / 'past_images' / 'main.py',
        },
    ]

    # Extract URLs
    qr_data = []
    for app in modal_apps:
        if app['path'].exists():
            url = extract_modal_url(app['path'])
            if url:
                qr_data.append({
                    'name': app['name'],
                    'url': url,
                })

    if not qr_data:
        print("  Warning: No Modal app URLs found. Skipping QR code generation.")
        return False

    # Create PDF
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title="Modal App QR Codes",
    )

    # Styles
    title_style = ParagraphStyle(
        'Title',
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=HexColor('#222222'),
        spaceAfter=0.3*inch,
        alignment=TA_CENTER,
    )

    app_name_style = ParagraphStyle(
        'AppName',
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=HexColor('#333333'),
        spaceAfter=0.1*inch,
        alignment=TA_CENTER,
    )

    url_style = ParagraphStyle(
        'URL',
        fontName='Courier',
        fontSize=9,
        textColor=HexColor('#666666'),
        spaceAfter=0.4*inch,
        alignment=TA_CENTER,
    )

    metadata_style = ParagraphStyle(
        'Metadata',
        fontName='Helvetica-Oblique',
        fontSize=8,
        textColor=HexColor('#888888'),
        spaceAfter=0.3*inch,
        alignment=TA_CENTER,
    )

    # Build story
    story = []

    # Title
    story.append(Paragraph('<b>Modal App QR Codes</b>', title_style))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Paragraph(f'Generated: {timestamp}', metadata_style))
    story.append(Spacer(1, 0.2*inch))

    # Add QR codes
    for data in qr_data:
        # Generate QR code
        qr_img = generate_qr_code_image(data['url'], size=10)

        # Convert PIL image to ReportLab Image
        img_buffer = BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        # Add to PDF
        story.append(Paragraph(data['name'], app_name_style))
        story.append(Spacer(1, 0.1*inch))

        # QR code image (centered)
        qr_reportlab_img = Image(img_buffer, width=3*inch, height=3*inch)
        qr_reportlab_img.hAlign = 'CENTER'
        story.append(qr_reportlab_img)

        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph(data['url'], url_style))

        # Add spacing between QR codes
        if data != qr_data[-1]:
            story.append(Spacer(1, 0.5*inch))

    # Build PDF
    doc.build(story)
    print(f"  Created: {output_file}")
    return True


def create_landscape_title_pages(output_file):
    """
    Create a PDF with 5 landscape title pages.
    First page: "those who control" in very large font (96pt)
    Other pages: Future, Past Images, Past Messages, Present (72pt)
    Each title is large and centered with fading effect applied.
    Uses Garamond font (falls back to Times-Roman if not available).
    """
    from reportlab.pdfgen.canvas import Canvas

    # Create canvas with landscape orientation
    c = Canvas(str(output_file), pagesize=landscape(letter))
    page_width, page_height = landscape(letter)

    # Try to use Garamond, fall back to Times-Roman (serif alternative)
    # Note: Garamond may not be available on all systems
    heading_font = "Times-Bold"  # Built-in ReportLab font (serif, similar to Garamond)

    # First page: "those who control" - very large
    title = "those who control"
    words = title.split()

    font_size = 96  # Even larger font
    c.setFont(heading_font, font_size)

    # Calculate positions for centered text
    total_width = sum([c.stringWidth(word + " ", heading_font, font_size) for word in words])

    # Start position (centered horizontally and vertically)
    x_start = (page_width - total_width) / 2
    y_position = page_height / 2

    # Draw each word with potential fading
    current_x = x_start
    for word in words:
        # Decide if this word should fade
        random.seed(word + title)  # Consistent fading per word

        if should_fade_word(word):
            level, color = get_fade_level()
            c.setFillColor(HexColor(color))
        else:
            c.setFillColor(HexColor('#000000'))

        # Draw the word
        c.drawString(current_x, y_position, word)

        # Move to next word position
        word_width = c.stringWidth(word + " ", heading_font, font_size)
        current_x += word_width

    c.showPage()  # New page after "those who control"

    # Remaining titles
    titles = [
        "Future",
        "Past Images",
        "Past Messages",
        "Present"
    ]

    for title in titles:
        # Apply fading to title - each word can fade independently
        words = title.split()

        # Calculate total width needed for all words
        font_size = 72
        c.setFont(heading_font, font_size)

        # Calculate positions for centered text
        total_width = sum([c.stringWidth(word + " ", heading_font, font_size) for word in words])

        # Start position (centered horizontally and vertically)
        x_start = (page_width - total_width) / 2
        y_position = page_height / 2

        # Draw each word with potential fading
        current_x = x_start
        for word in words:
            # Decide if this word should fade
            random.seed(word + title)  # Consistent fading per word

            if should_fade_word(word):
                level, color = get_fade_level()
                c.setFillColor(HexColor(color))
            else:
                c.setFillColor(HexColor('#000000'))

            # Draw the word
            c.drawString(current_x, y_position, word)

            # Move to next word position
            word_width = c.stringWidth(word + " ", heading_font, font_size)
            current_x += word_width

        # New page (except after last title)
        if title != titles[-1]:
            c.showPage()

    # Save PDF
    c.save()
    print(f"  Created: {output_file}")
    return True


def create_typeform_feedback():
    """
    Create a Typeform feedback form for the art installation.
    Questions about memories, life changes, and general feedback.
    Returns the form URL or None if creation failed.
    """
    # Load environment variables
    load_dotenv()
    typeform_token = os.getenv('TYPEFORM_TOKEN')

    if not typeform_token:
        print("  Warning: TYPEFORM_TOKEN not found in .env file")
        print("  Skipping Typeform creation. Add token to .env to enable.")
        return None

    # Typeform Create API endpoint
    url = "https://api.typeform.com/forms"
    headers = {
        "Authorization": f"Bearer {typeform_token}",
        "Content-Type": "application/json"
    }

    # Define the form structure
    form_data = {
        "title": "Who Controls the Present - Feedback",
        "type": "form",
        "theme": {
            "href": "https://api.typeform.com/themes/qHWOQ7"  # Default dark theme
        },
        "settings": {
            "is_public": True,
            "show_progress_bar": True,
            # "show_typeform_branding": False,  # Premium feature - removed for free tier
            "meta": {
                "allow_indexing": False
            }
        },
        "fields": [
            # Opening statement
            {
                "title": "Thank you for experiencing \"Who Controls the Present.\" Your reflections help us understand how we collectively navigate memory, identity, and transformation.",
                "type": "statement"
            },

            # Memory change questions
            {
                "title": "If you could erase one memory from your past, what would it be and why?",
                "type": "long_text",
                "properties": {
                    "description": "Optional - share as much or as little as you'd like"
                },
                "validations": {
                    "required": False
                }
            },
            {
                "title": "If you could create a new memory that never happened, what would it be?",
                "type": "long_text",
                "properties": {
                    "description": "Optional"
                },
                "validations": {
                    "required": False
                }
            },
            {
                "title": "What is one concrete change you want to make in your life after this experience?",
                "type": "long_text",
                "properties": {
                    "description": "Be specific if possible"
                },
                "validations": {
                    "required": False
                }
            },

            # Experience feedback
            {
                "title": "Which part of the installation resonated most with you?",
                "type": "multiple_choice",
                "properties": {
                    "choices": [
                        {"label": "Past Images (person removal)"},
                        {"label": "Past Messages (conversation continuation)"},
                        {"label": "Present (transformative dialogue)"},
                        {"label": "Future (alternate reality photobooth)"}
                    ],
                    "allow_multiple_selection": False,
                    "randomize": False
                },
                "validations": {
                    "required": False
                }
            },
            {
                "title": "How did this experience make you feel about your own memories?",
                "type": "opinion_scale",
                "properties": {
                    "labels": {
                        "left": "More uncertain",
                        "right": "More empowered"
                    },
                    "steps": 5
                },
                "validations": {
                    "required": False
                }
            },
            {
                "title": "Do you feel you have control over your past, present, and future?",
                "type": "opinion_scale",
                "properties": {
                    "labels": {
                        "left": "No control",
                        "right": "Full control"
                    },
                    "steps": 7
                },
                "validations": {
                    "required": False
                }
            },

            # General feedback
            {
                "title": "Any other thoughts, reflections, or feedback?",
                "type": "long_text",
                "properties": {
                    "description": "We welcome all perspectives"
                },
                "validations": {
                    "required": False
                }
            },

            # Optional contact
            {
                "title": "Would you like to be notified about future projects? (optional)",
                "type": "email",
                "validations": {
                    "required": False
                }
            },

            # Closing statement
            {
                "title": "Thank you for sharing your reflections. Remember: you control who you become.",
                "type": "statement"
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=form_data)
        response.raise_for_status()

        result = response.json()
        form_id = result.get('id')
        form_url = f"https://form.typeform.com/to/{form_id}"

        print(f"  Created Typeform: {form_url}")
        print(f"  Form ID: {form_id}")

        return form_url

    except requests.exceptions.RequestException as e:
        print(f"  Warning: Failed to create Typeform: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def create_participant_contexts_pdf(output_file, yaml_path):
    """
    Create a single-page PDF listing all the keys from the context: section of participant_background.yaml.
    """
    import yaml

    # Load the YAML file
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"  Warning: Could not load {yaml_path}: {e}")
        return False

    # Extract context keys
    context_keys = list(data.get('context', {}).keys())

    if not context_keys:
        print(f"  Warning: No context keys found in {yaml_path}")
        return False

    print(f"  Found {len(context_keys)} participant context keys")

    # Create PDF using SimpleDocTemplate
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title="Participant Contexts",
    )

    # Styles
    title_style = ParagraphStyle(
        'Title',
        fontName='Times-Bold',
        fontSize=18,
        textColor=HexColor('#222222'),
        spaceAfter=0.3*inch,
        alignment=TA_CENTER,
    )

    metadata_style = ParagraphStyle(
        'Metadata',
        fontName='Helvetica-Oblique',
        fontSize=8,
        textColor=HexColor('#888888'),
        spaceAfter=0.2*inch,
        alignment=TA_CENTER,
    )

    item_style = ParagraphStyle(
        'Item',
        fontName='Helvetica',
        fontSize=11,
        textColor=HexColor('#000000'),
        spaceAfter=6,
        leading=16,
    )

    # Build story
    story = []

    # Title
    story.append(Paragraph('<b>Participant Contexts</b>', title_style))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Paragraph(f'Generated: {timestamp}', metadata_style))
    story.append(Spacer(1, 0.2*inch))

    # Add sorted context keys as a list
    for key in sorted(context_keys):
        story.append(Paragraph(f'• {key}', item_style))

    # Build PDF
    doc.build(story)
    print(f"  Created: {output_file}")
    return True


def create_typeform_qr_pdf(output_file, typeform_url):
    """
    Create a PDF with QR code for the Typeform feedback form.
    Similar format to Modal QR codes.
    """
    if not QRCODE_AVAILABLE:
        print("  Warning: qrcode library not installed. Skipping Typeform QR code generation.")
        return False

    # Create PDF
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title="Typeform Feedback QR Code",
    )

    # Styles
    title_style = ParagraphStyle(
        'Title',
        fontName='Times-Bold',
        fontSize=20,
        textColor=HexColor('#222222'),
        spaceAfter=0.3*inch,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        'Heading',
        fontName='Times-Bold',
        fontSize=16,
        textColor=HexColor('#333333'),
        spaceAfter=0.1*inch,
        alignment=TA_CENTER,
    )

    url_style = ParagraphStyle(
        'URL',
        fontName='Courier',
        fontSize=9,
        textColor=HexColor('#666666'),
        spaceAfter=0.4*inch,
        alignment=TA_CENTER,
    )

    metadata_style = ParagraphStyle(
        'Metadata',
        fontName='Helvetica-Oblique',
        fontSize=8,
        textColor=HexColor('#888888'),
        spaceAfter=0.3*inch,
        alignment=TA_CENTER,
    )

    description_style = ParagraphStyle(
        'Description',
        fontName='Helvetica',
        fontSize=11,
        textColor=HexColor('#444444'),
        spaceAfter=0.3*inch,
        alignment=TA_CENTER,
    )

    # Build story
    story = []

    # Title
    story.append(Paragraph('<b>Feedback Form</b>', title_style))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Paragraph(f'Generated: {timestamp}', metadata_style))
    story.append(Spacer(1, 0.2*inch))

    # Description
    story.append(Paragraph('Share your reflections on memory, identity, and transformation', description_style))
    story.append(Spacer(1, 0.1*inch))

    # Generate QR code
    qr_img = generate_qr_code_image(typeform_url, size=10)

    # Convert PIL image to ReportLab Image
    img_buffer = BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    # Add heading
    story.append(Paragraph('Who Controls the Present', heading_style))
    story.append(Spacer(1, 0.1*inch))

    # QR code image (centered)
    qr_reportlab_img = Image(img_buffer, width=4*inch, height=4*inch)
    qr_reportlab_img.hAlign = 'CENTER'
    story.append(qr_reportlab_img)

    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(typeform_url, url_style))

    # Build PDF
    doc.build(story)
    print(f"  Created: {output_file}")
    return True


def send_to_printer(pdf_file):
    """Send PDF to default printer using lp command"""
    try:
        subprocess.run(['lp', str(pdf_file)], check=True)
        print(f"  Sent to printer: {pdf_file.name}")
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Failed to print {pdf_file.name}: {e}")
    except FileNotFoundError:
        print(f"  ERROR: 'lp' command not found. Printing requires CUPS.")


def main():
    parser = argparse.ArgumentParser(
        description='Generate PDF materials with fading memory aesthetic'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='print_output',
        help='Directory to save PDF files (default: print_output/)'
    )
    parser.add_argument(
        '--send-to-printer',
        action='store_true',
        help='Send PDFs to default printer after generation'
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Find project root
    project_root = Path(__file__).parent

    # Collect all .md files except README.md and CLAUDE.md
    files_to_print = []
    for md_file in project_root.rglob('*.md'):
        if md_file.name not in ['README.md', 'CLAUDE.md'] and 'node_modules' not in str(md_file):
            files_to_print.append(md_file)

    # Sort for consistent ordering
    files_to_print.sort()

    if not files_to_print:
        print("No files found to print.")
        return

    print(f"\n{'='*60}")
    print(f"  GENERATING PRINT MATERIALS - FADING MEMORY AESTHETIC")
    print(f"{'='*60}\n")
    print(f"Found {len(files_to_print)} files to process:\n")

    for f in files_to_print:
        print(f"  - {f.relative_to(project_root)}")

    print(f"\n{'='*60}\n")

    # Process each file
    generated_pdfs = []
    for input_file in files_to_print:
        rel_path = input_file.relative_to(project_root)
        print(f"Processing: {rel_path}")

        # Create output filename
        output_filename = str(rel_path).replace('/', '_').replace('.md', '.pdf')
        output_file = output_dir / output_filename

        # Set random seed based on filename for consistent fading pattern
        random.seed(str(input_file))

        # Create PDF with fading
        create_pdf_document(input_file, output_file)
        generated_pdfs.append(output_file)
        print()

    # Generate landscape title pages
    print(f"{'='*60}")
    print(f"  GENERATING LANDSCAPE TITLE PAGES")
    print(f"{'='*60}\n")

    title_output_file = output_dir / 'title_pages.pdf'
    create_landscape_title_pages(title_output_file)
    generated_pdfs.append(title_output_file)
    print()

    # Generate QR codes for Modal apps
    print(f"{'='*60}")
    print(f"  GENERATING MODAL APP QR CODES")
    print(f"{'='*60}\n")

    qr_output_file = output_dir / 'modal_qr_codes.pdf'
    qr_success = create_qr_codes_pdf(qr_output_file, project_root)

    if qr_success:
        generated_pdfs.append(qr_output_file)
        print()

    # Create participant contexts PDF
    print(f"{'='*60}")
    print(f"  GENERATING PARTICIPANT CONTEXTS PDF")
    print(f"{'='*60}\n")

    participant_yaml_path = project_root / 'present' / 'participant_background.yaml'
    participant_contexts_file = output_dir / 'participant_contexts.pdf'
    participant_contexts_success = False
    if participant_yaml_path.exists():
        participant_contexts_success = create_participant_contexts_pdf(
            participant_contexts_file, participant_yaml_path
        )
        if participant_contexts_success:
            generated_pdfs.append(participant_contexts_file)
        print()
    else:
        print(f"  Warning: {participant_yaml_path} not found")
        print()

    # Create Typeform feedback form
    print(f"{'='*60}")
    print(f"  CREATING TYPEFORM FEEDBACK FORM")
    print(f"{'='*60}\n")

    typeform_url = create_typeform_feedback()
    typeform_qr_success = False
    if typeform_url:
        # Create QR code PDF for Typeform
        typeform_qr_file = output_dir / 'typeform_qr_code.pdf'
        typeform_qr_success = create_typeform_qr_pdf(typeform_qr_file, typeform_url)
        if typeform_qr_success:
            generated_pdfs.append(typeform_qr_file)
        print()

    # Send to printer if requested
    if args.send_to_printer:
        print(f"{'='*60}")
        print(f"  SENDING TO PRINTER")
        print(f"{'='*60}\n")
        for pdf_file in generated_pdfs:
            send_to_printer(pdf_file)
        print()

    print(f"{'='*60}")
    print(f"  PDF files saved to: {output_dir}/")
    print(f"  Includes landscape title pages: title_pages.pdf")
    if qr_success:
        print(f"  Includes Modal QR codes: modal_qr_codes.pdf")
    if participant_contexts_success:
        print(f"  Includes participant contexts: participant_contexts.pdf")
    if typeform_qr_success:
        print(f"  Includes Typeform QR code: typeform_qr_code.pdf")
    if args.send_to_printer:
        print(f"  All PDFs sent to printer!")
    else:
        print(f"  Use --send-to-printer to print automatically")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
