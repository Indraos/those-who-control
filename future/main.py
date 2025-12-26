#!/usr/bin/env python3
"""
Photo booth web app using OpenAI gpt-image-1 for image transformations.
Supports USB webcam capture and USB printer output.
"""

import base64
import io
import os
import re
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from PIL import Image, ImageOps
from openai import OpenAI
import dotenv

# Load environment variables
load_dotenv(override=True)

# Paths
APP_ROOT = Path(__file__).resolve().parent
GEN_DIR = APP_ROOT / "generated"
TEMPLATES_DIR = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"
GEN_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Configuration from environment
PRINTER_NAME = os.getenv("PRINTER_NAME", "")
MEDIA_SIZE = os.getenv("MEDIA_SIZE", "Custom.4x6in")
LP_OPTIONS = [o for o in os.getenv("LP_OPTIONS", "fit-to-page").split() if o]
BIND_HOST = os.getenv("BIND_HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

# Initialize
app = FastAPI()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Mount static files - must be before route definitions
app.mount("/static", StaticFiles(directory=str(STATIC_DIR.resolve())), name="static")
app.mount("/generated", StaticFiles(directory=str(GEN_DIR.resolve())), name="generated")


# Pydantic models
class GeneratedImage(BaseModel):
    label: str
    url: str
    path: str


class GenerateResponse(BaseModel):
    images: List[GeneratedImage]


class PrintRequest(BaseModel):
    paths: List[str]


def process_image(image_bytes: bytes, dest: Path) -> bytes:
    """Auto-orient and save image as JPEG. Returns processed bytes.

    Args:
        image_bytes: Raw image bytes.
        dest: Destination path for saved JPEG.

    Returns:
        bytes: Processed image bytes.
    """
    with Image.open(io.BytesIO(image_bytes)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, format="JPEG", quality=94, optimize=True)

        # Return processed bytes
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=94, optimize=True)
        return buf.getvalue()


async def transform_image(image_bytes: bytes, prompt: str) -> bytes:
    """Edit the input image with gpt-image-1 via the Images API and return JPEG bytes."""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        file_obj = io.BytesIO(image_bytes)
        file_obj.name = "input.jpg"
        # Generate an edit (image-to-image). You can also call images.generate for text->image.
        result = openai_client.images.edit(
            model="gpt-image-1",
            image=file_obj,
            prompt=prompt,
            size="1024x1024"
        )
        b64 = result.data[0].b64_json
        return base64.b64decode(b64)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API failed: {exc}")


@app.get("/")
async def index(request: Request):
    """Serve the HTML UI."""
    return templates.TemplateResponse("index.html", {"request": request})


# Session storage for progressive generation
generation_sessions = {}

@app.post("/api/generate/start")
async def generate_start(background_tasks: BackgroundTasks, image: UploadFile = File(...)):
    """Start image generation and return session ID."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] GENERATE START request received", flush=True)

    # Process and save original
    uid = uuid.uuid4().hex[:8]
    session_id = uid
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    original_path = GEN_DIR / f"original-{timestamp}-{uid}.jpg"

    try:
        raw_bytes = await image.read()
        image_bytes = process_image(raw_bytes, original_path)
    except Exception as exc:
        print(f"[{ts}] Image processing error: {exc}", flush=True)
        raise HTTPException(status_code=400, detail=str(exc))

    print(f"[{ts}] Processed {len(image_bytes)} bytes", flush=True)

    # Build initial response with original
    rel_path = original_path.relative_to(GEN_DIR).as_posix()
    images = [GeneratedImage(
        label="original",
        url=f"{BASE_URL}/generated/{rel_path}",
        path=str(original_path)
    )]

    # Store session state
    generation_sessions[session_id] = {
        "images": images,
        "status": "processing",
        "total": 0,
        "completed": 1
    }

    # Load scene prompts
    config_path = APP_ROOT / "config.yml"
    if not config_path.exists():
        raise HTTPException(status_code=500, detail="Missing config.yml")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    scenes = config.get("scenes", [])
    if not scenes or not isinstance(scenes, list):
        raise HTTPException(status_code=500, detail="Invalid config.yml")

    generation_sessions[session_id]["total"] = len(scenes) + 1  # +1 for original

    print(f"[{ts}] Processing {len(scenes)} scenes for session {session_id}", flush=True)

    # Add background task to generate scenes
    background_tasks.add_task(generate_scenes_background, session_id, image_bytes, scenes, timestamp, uid)

    print(f"[{ts}] Returning session {session_id} with 1 image", flush=True)

    return JSONResponse({
        "session_id": session_id,
        "images": [img.model_dump() for img in images]
    })

async def generate_scenes_background(session_id: str, image_bytes: bytes, scenes: list, timestamp: str, uid: str):
    """Background task to generate scene variants."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for scene in scenes:
        label = str(scene.get("label", "unnamed"))
        prompt = str(scene.get("prompt", "")).strip()

        if not prompt:
            continue

        try:
            print(f"[{ts}] START {label}", flush=True)
            transformed = await transform_image(image_bytes, prompt)

            scene_path = GEN_DIR / f"{label}-{timestamp}-{uid}.jpg"
            with open(scene_path, "wb") as f:
                f.write(transformed)

            rel_path = scene_path.relative_to(GEN_DIR).as_posix()
            new_image = GeneratedImage(
                label=label,
                url=f"{BASE_URL}/generated/{rel_path}",
                path=str(scene_path)
            )

            # Add to session
            if session_id in generation_sessions:
                generation_sessions[session_id]["images"].append(new_image)
                generation_sessions[session_id]["completed"] += 1
                print(f"[{ts}] Session {session_id} now has {len(generation_sessions[session_id]['images'])} images", flush=True)

            print(f"[{ts}] DONE {label}", flush=True)
        except Exception as exc:
            print(f"[{ts}] ERROR {label}: {exc}", flush=True)

    # Mark as complete
    if session_id in generation_sessions:
        generation_sessions[session_id]["status"] = "completed"
        print(f"[{ts}] Session {session_id} completed with {len(generation_sessions[session_id]['images'])} images", flush=True)

@app.get("/api/generate/status/{session_id}")
async def generate_status(session_id: str):
    """Get current status of generation session."""
    if session_id not in generation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = generation_sessions[session_id]

    # Print debug info
    print(f"[STATUS] Session {session_id}: {session['completed']}/{session['total']}, images={len(session['images'])}", flush=True)

    return JSONResponse(
        {
            "status": session["status"],
            "completed": session["completed"],
            "total": session["total"],
            "images": [img.model_dump() for img in session["images"]]
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


def create_composite_image(image_paths: List[str]) -> Path:
    """Create a composite image with all images arranged on a single page."""
    # Validate all paths
    valid_paths = []
    for path_str in image_paths:
        p = Path(path_str).resolve()
        if not str(p).startswith(str(GEN_DIR.resolve())):
            continue
        if not p.exists():
            continue
        valid_paths.append(p)

    if not valid_paths:
        raise ValueError("No valid images to print")

    # Load all images
    images = []
    for img_path in valid_paths:
        img = Image.open(img_path)
        images.append(img)

    # Determine layout (5 images: 2 rows, top row has 3, bottom row has 2)
    # For 4x6 inch photo paper at 300 DPI: 1200x1800 pixels
    # Adjust based on actual paper size
    if len(images) <= 2:
        # Single row
        cols = len(images)
        rows = 1
    elif len(images) <= 4:
        # 2x2 grid
        cols = 2
        rows = 2
    else:
        # 5 images: 3 on top, 2 on bottom
        cols = 3
        rows = 2

    # Calculate dimensions for each thumbnail
    # Target composite size for 4x6 paper (landscape): 1800x1200 pixels at 300 DPI
    composite_width = 1800
    composite_height = 1200

    thumb_width = composite_width // cols
    thumb_height = composite_height // rows

    # Create composite canvas
    composite = Image.new('RGB', (composite_width, composite_height), (255, 255, 255))

    # Paste images into grid
    for idx, img in enumerate(images):
        # Resize image to fit thumbnail while maintaining aspect ratio
        img.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)

        # Calculate position in grid
        x_offset = 0
        if len(images) == 5:
            # Special layout: 3 on top row, 2 on bottom row (centered)
            if idx < 3:
                row = 0
                col = idx
            else:
                row = 1
                col = idx - 3
                # Center the bottom row
                x_offset = thumb_width // 2
        else:
            row = idx // cols
            col = idx % cols

        # Calculate paste position (centered within cell)
        x = col * thumb_width + (thumb_width - img.width) // 2 + x_offset
        y = row * thumb_height + (thumb_height - img.height) // 2

        composite.paste(img, (x, y))

    # Save composite
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    uid = uuid.uuid4().hex[:8]
    composite_path = GEN_DIR / f"composite-{timestamp}-{uid}.jpg"
    composite.save(composite_path, format="JPEG", quality=95, optimize=True)

    return composite_path

@app.post("/api/print")
async def print_images(req: PrintRequest):
    """Create composite image and print via CUPS."""
    if not PRINTER_NAME:
        raise HTTPException(status_code=500, detail="PRINTER_NAME not configured")

    try:
        # Create composite image from all provided images
        composite_path = create_composite_image(req.paths)

        # Print composite via lp
        cmd = ["lp", "-d", PRINTER_NAME, "-o", f"media={MEDIA_SIZE}"]
        for opt in LP_OPTIONS:
            cmd.extend(["-o", opt])
        cmd.append(str(composite_path))

        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        m = re.search(r"(\S+-\d+)", out)
        job_id = m.group(1) if m else out or "submitted"

        return JSONResponse({
            "jobs": [job_id],
            "composite": str(composite_path.relative_to(GEN_DIR))
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Print failed: {str(exc)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BIND_HOST, port=PORT)
