"""
Modal deployment for Past Messages AI Continuation.
Part of "Who Controls the Present" installation.

Uploads message exports from various platforms and uses GPT-5.1 to
continue the conversation with transformative guidance.
"""

import modal
import os

# Create Modal app
app = modal.App("past-messages")

# Define the Modal image (no GPU needed)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir("templates", remote_path="/root/templates")
    .add_local_dir("static", remote_path="/root/static")
    .add_local_file("parsers.py", remote_path="/root/parsers.py")
    .add_local_file("config.yml", remote_path="/root/config.yml")
)

# Create Modal volume for generated HTML files
generated_volume = modal.Volume.from_name("past-messages-generated", create_if_missing=True)

# Define secrets
secrets = [
    modal.Secret.from_name("openai-secret"),  # Must contain OPENAI_API_KEY
]


@app.function(
    image=image,
    timeout=300,
    min_containers=0,
    gpu="A10G",
    max_containers=1,
    scaledown_window=300,
    volumes={
        "/app/generated": generated_volume,
    },
    secrets=secrets,
)
@modal.asgi_app(label="past-messages-web")
def fastapi_app():
    """
    Create and return the FastAPI application.
    This function is called by Modal to create the ASGI app.
    """
    import io
    import uuid
    import json
    import yaml
    from pathlib import Path
    from datetime import datetime
    from typing import Dict, List

    from fastapi import FastAPI, File, UploadFile, HTTPException, Request
    from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from starlette.middleware.cors import CORSMiddleware
    from openai import OpenAI

    import parsers

    # Initialize FastAPI
    web_app = FastAPI(title="Past Messages - AI Continuation", version="1.0.0")

    # Mount static files
    web_app.mount("/static", StaticFiles(directory="/root/static"), name="static")

    # Initialize Jinja2 templates
    templates = Jinja2Templates(directory="/root/templates")

    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configuration
    GENERATED_DIR = Path("/app/generated")
    GENERATED_DIR.mkdir(exist_ok=True, parents=True)

    # Session storage (using volume for persistence across requests)
    SESSION_DIR = GENERATED_DIR / "sessions"
    SESSION_DIR.mkdir(exist_ok=True, parents=True)

    # Load config
    with open("/root/config.yml", "r") as f:
        config = yaml.safe_load(f)

    # Initialize OpenAI client
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def save_session(session_id: str, data: dict):
        """Save session data to disk with file locking."""
        import fcntl
        session_file = SESSION_DIR / f"{session_id}.json"
        temp_file = SESSION_DIR / f"{session_id}.tmp"
        print(f"[SESSION] Attempting to save to: {session_file}")
        print(f"[SESSION] Session dir exists: {SESSION_DIR.exists()}")
        print(f"[SESSION] Session dir is writable: {os.access(SESSION_DIR, os.W_OK)}")

        try:
            # Write to temp file with exclusive lock
            with open(temp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
                json.dump(data, f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock

            # Atomic rename
            temp_file.rename(session_file)
            print(f"[SESSION] Wrote session file, size: {session_file.stat().st_size} bytes")

            # Commit volume changes
            print(f"[SESSION] Committing volume...")
            generated_volume.commit()
            print(f"[SESSION] Volume committed successfully")

            # Verify file exists after commit
            if session_file.exists():
                print(f"[SESSION] ✓ Session {session_id} saved and verified at {session_file}")
            else:
                print(f"[SESSION] ✗ WARNING: Session file disappeared after commit!")

        except Exception as e:
            print(f"[SESSION] ERROR saving session: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def load_session(session_id: str) -> dict:
        """Load session data from disk."""
        # Reload volume to get latest data
        print(f"[SESSION] Reloading volume to get latest data...")
        try:
            generated_volume.reload()
            print(f"[SESSION] Volume reloaded successfully")
        except Exception as e:
            print(f"[SESSION] Warning: Volume reload failed: {e}")

        session_file = SESSION_DIR / f"{session_id}.json"
        print(f"[SESSION] Attempting to load from: {session_file}")
        print(f"[SESSION] Session dir exists: {SESSION_DIR.exists()}")
        print(f"[SESSION] Session dir contents: {list(SESSION_DIR.glob('*.json'))}")

        if not session_file.exists():
            print(f"[SESSION] ✗ Session file not found: {session_file}")
            print(f"[SESSION] Available session files: {[f.name for f in SESSION_DIR.glob('*.json')]}")
            return None

        try:
            with open(session_file, "r") as f:
                data = json.load(f)
            print(f"[SESSION] ✓ Loaded session {session_id}, message count: {data.get('message_count', 0)}")
            return data
        except Exception as e:
            print(f"[SESSION] ERROR loading session: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    @web_app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Serve the main upload page."""
        return templates.TemplateResponse("index.html", {"request": request})

    @web_app.post("/api/upload")
    async def upload_messages(file: UploadFile = File(...)):
        """
        Upload and parse message file.
        Returns parsed message data and session ID.
        """
        print(f"[API] Upload request received for file: {file.filename}")
        print(f"[API] Content type: {file.content_type}")

        try:
            # Read file content
            content = await file.read()
            print(f"[API] File size: {len(content)} bytes")

            # Check if this is a PDF file
            is_pdf = content[:4] == b'%PDF' or file.filename.lower().endswith('.pdf')

            if is_pdf:
                print("[API] Detected PDF file, passing bytes to parser")
                content_str = ""  # Will be extracted by parser
            else:
                content_str = content.decode('utf-8', errors='ignore')
                print(f"[API] Decoded to {len(content_str)} characters")

            # Parse messages
            print("[API] Calling parser...")
            result = parsers.parse_messages(content_str, file.filename, content_bytes=content)
            print(f"[API] Parser returned format: {result.get('format')}, messages: {result.get('message_count')}")

            if result["format"] == "unknown":
                error_detail = result.get("error", "Could not detect message format")
                print(f"[API] ERROR: Format unknown - {error_detail}")
                raise HTTPException(
                    status_code=400,
                    detail=f"{error_detail}. Supported: WhatsApp, iMessage (PDF), Facebook Messenger (JSON)"
                )

            if result["message_count"] == 0:
                error_detail = result.get("error", "No messages found in file")
                print(f"[API] ERROR: No messages - {error_detail}")
                raise HTTPException(
                    status_code=400,
                    detail=error_detail
                )

            # Generate session ID
            session_id = str(uuid.uuid4())
            print(f"[API] Generated session ID: {session_id}")

            # Store parsed messages persistently
            save_session(session_id, result)
            print(f"[API] Stored messages for session {session_id}")

            # Also return the full data in response for immediate use
            # This avoids volume reload timing issues
            response_data = {
                "session_id": session_id,
                "format": result["format"],
                "message_count": result["message_count"],
                "participants": result["participants"],
                "messages": result["messages"]  # Include full message data
            }
            print(f"[API] Returning success response with {len(result['messages'])} messages")

            return JSONResponse(response_data)

        except UnicodeDecodeError as e:
            print(f"[API] ERROR: Unicode decode failed: {str(e)}")
            raise HTTPException(status_code=400, detail="File encoding not supported")
        except HTTPException:
            # Re-raise HTTP exceptions without wrapping
            raise
        except Exception as e:
            print(f"[API] ERROR: Unexpected exception: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

    @web_app.post("/api/generate/{session_id}")
    async def generate_continuation(session_id: str, request: Request):
        """
        Generate AI continuation for the uploaded messages.
        Accepts session data in request body to avoid volume persistence issues.
        Returns HTML file path for download.
        """
        print(f"[API] Generate request for session: {session_id}")

        # Try to get session data from request body first (preferred method)
        try:
            body = await request.body()
            if body:
                result = json.loads(body)
                print(f"[API] Using session data from request body: {result.get('message_count')} messages")
            else:
                # Fall back to loading from volume
                print(f"[API] No body data, loading from volume...")
                result = load_session(session_id)
        except Exception as e:
            print(f"[API] Error parsing request body: {e}, falling back to volume")
            result = load_session(session_id)

        if result is None:
            print(f"[API] ERROR: Session {session_id} not found")
            raise HTTPException(status_code=404, detail=f"Session not found. Please upload the file again.")

        try:
            messages = result["messages"]
            participants = result["participants"]

            if len(participants) < 2:
                raise HTTPException(
                    status_code=400,
                    detail="Need at least 2 participants for continuation"
                )

            # Build conversation context for GPT
            conversation_context = build_conversation_context(messages, participants)

            # Call GPT-5.1 for continuation
            print(f"[INFO] Generating continuation with GPT-5.1...")
            system_prompt = config["system_prompt"]
            temperature = config.get("temperature", 0.8)
            max_tokens = config.get("max_tokens", 2000)

            response = client.chat.completions.create(
                model="gpt-4.1",  # GPT-5.1
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_context}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            continuation_text = response.choices[0].message.content

            # Parse generated messages
            ai_messages = parse_generated_messages(continuation_text, participants)

            # Generate HTML
            html_filename = f"conversation_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            html_path = GENERATED_DIR / html_filename

            html_content = generate_html(messages, ai_messages, participants, result["format"])

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Commit volume changes
            generated_volume.commit()

            return JSONResponse({
                "success": True,
                "filename": html_filename,
                "download_url": f"/generated/{html_filename}",
                "original_count": len(messages),
                "generated_count": len(ai_messages)
            })

        except Exception as e:
            print(f"[ERROR] Generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating continuation: {str(e)}")

    @web_app.get("/generated/{filename}")
    async def download_html(filename: str):
        """Serve generated HTML file for download."""
        import time

        # Security: prevent directory traversal
        file_path = GENERATED_DIR / filename
        if not file_path.resolve().is_relative_to(GENERATED_DIR.resolve()):
            print(f"[DOWNLOAD] ERROR: Directory traversal attempt blocked")
            raise HTTPException(status_code=403, detail="Access denied")

        # Retry logic to handle volume sync latency
        max_retries = 3
        for attempt in range(max_retries):
            print(f"[DOWNLOAD] Attempt {attempt + 1}/{max_retries} for file: {filename}")

            # Reload volume to get latest files
            try:
                generated_volume.reload()
                print(f"[DOWNLOAD] Volume reloaded successfully")
            except Exception as e:
                print(f"[DOWNLOAD] Warning: Volume reload failed: {e}")

            print(f"[DOWNLOAD] Looking for file at: {file_path}")
            print(f"[DOWNLOAD] File exists: {file_path.exists()}")

            if file_path.exists():
                print(f"[DOWNLOAD] ✓ Found file: {filename} ({file_path.stat().st_size} bytes)")
                return FileResponse(
                    path=file_path,
                    filename=filename,
                    media_type="text/html"
                )

            # If not found, wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                print(f"[DOWNLOAD] File not found, waiting 2 seconds before retry...")
                time.sleep(2)

        # All retries exhausted
        print(f"[DOWNLOAD] ERROR: File not found after {max_retries} attempts: {filename}")
        print(f"[DOWNLOAD] Directory contents: {list(GENERATED_DIR.glob('*.html'))}")
        print(f"[DOWNLOAD] Available files: {[f.name for f in GENERATED_DIR.glob('*.html')]}")
        raise HTTPException(
            status_code=404,
            detail=f"File not found on server after {max_retries} attempts. The file may not have been generated successfully. Please try generating again."
        )

    def build_conversation_context(messages: List[Dict], participants: List[str]) -> str:
        """Build context string for GPT from message history."""

        # Count messages per participant to understand conversation dynamics
        message_counts = {}
        for msg in messages:
            sender = msg["sender"]
            message_counts[sender] = message_counts.get(sender, 0) + 1

        # Determine who speaks next (person who spoke last)
        last_sender = messages[-1]["sender"] if messages else participants[0]

        context = f"CONVERSATION PARTICIPANTS: {' and '.join(participants)}\n\n"
        context += f"YOU ARE SPEAKING AS: {last_sender}\n"
        context += f"You are continuing this conversation from {last_sender}'s perspective.\n\n"

        context += "CONVERSATION HISTORY:\n\n"

        for msg in messages[-50:]:  # Use last 50 messages for context
            sender = msg["sender"]
            message = msg["message"]
            context += f"{sender}: {message}\n\n"

        context += f"\n---\n\n"
        context += f"As {last_sender}, continue this conversation naturally for 5-7 exchanges (10-14 messages total), "
        context += f"alternating with {[p for p in participants if p != last_sender][0]}. "
        context += f"Surface past challenges and unresolved tensions in your relationship. "
        context += f"Maintain {last_sender}'s exact voice, tone, and communication style from the conversation above."

        return context

    def parse_generated_messages(text: str, participants: List[str]) -> List[Dict]:
        """Parse GPT output into message structure."""
        messages = []
        lines = text.strip().split('\n')

        current_message = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with participant name
            matched = False
            for participant in participants:
                if line.startswith(f"{participant}:"):
                    # Save previous message
                    if current_message:
                        messages.append(current_message)

                    # Start new message
                    message_text = line[len(participant)+1:].strip()
                    current_message = {
                        "sender": participant,
                        "message": message_text,
                        "timestamp": "AI Generated",
                        "ai_generated": True
                    }
                    matched = True
                    break

            # If no match, append to current message (multi-line)
            if not matched and current_message:
                current_message["message"] += "\n" + line

        # Add last message
        if current_message:
            messages.append(current_message)

        return messages

    def generate_html(original_messages: List[Dict], ai_messages: List[Dict],
                     participants: List[str], format_type: str) -> str:
        """Generate self-contained HTML with original + AI messages."""

        # Read CSS
        with open("/root/static/style.css", "r") as f:
            css = f.read()

        # Determine which participant is "left" vs "right"
        left_participant = participants[0]
        right_participant = participants[1] if len(participants) > 1 else participants[0]

        def render_message(msg: Dict, is_ai: bool = False) -> str:
            sender = msg["sender"]
            message = msg["message"]
            timestamp = msg.get("timestamp", "")

            side = "left" if sender == left_participant else "right"
            ai_class = " ai-generated" if is_ai else ""

            html = f'<div class="message {side}{ai_class}">\n'
            html += f'  <div class="message-sender">{sender}</div>\n'
            html += f'  <div class="message-bubble">{message}'

            if is_ai:
                html += '<span class="ai-indicator">AI</span>'

            html += '</div>\n'

            if timestamp and timestamp != "AI Generated":
                html += f'  <div class="message-timestamp">{timestamp}</div>\n'

            html += '</div>\n'

            return html

        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Past Messages - AI Continuation</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>Past Messages - AI Continuation</h1>
        <p style="color: #666; margin-bottom: 30px;">
            Original conversation ({format_type.title()}) with AI-generated continuation<br>
            Between: {' and '.join(participants)}
        </p>

        <!-- Original Messages -->
"""

        for msg in original_messages:
            html += render_message(msg)

        html += """
        <!-- AI Continuation Divider -->
        <div class="section-divider">
            AI-Generated Continuation
        </div>

"""

        # AI Messages
        for msg in ai_messages:
            html += render_message(msg, is_ai=True)

        html += """
    </div>
</body>
</html>
"""

        return html

    return web_app
