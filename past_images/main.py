"""
Modal deployment for SAM + face_recognition + LaMa inpainting pipeline.
Part of "Who Controls the Present" installation.

Pipeline (from commit 79e55bb):
1. SAM automatic mask generation
2. Face recognition to find target person
3. Select best mask containing face
4. LaMa inpainting to remove person
"""

import modal
import os

# Create Modal app
app = modal.App("past-images")

# Define the Modal image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git",
        "wget",
        "unzip",
        "cmake",
        "build-essential",
        "libglib2.0-0",
        "libsm6",
        "libxext6",
        "libxrender-dev",
        "libgomp1",
        "libgl1-mesa-glx",
        "ffmpeg",
    )
    # Install numpy FIRST to ensure version < 2.0 before other packages
    .pip_install("numpy<2.0,>=1.24.0")
    .pip_install_from_requirements("requirements.txt")
    # Install SAM from GitHub
    .pip_install("git+https://github.com/facebookresearch/segment-anything.git")
    .run_commands(
        # Force reinstall albumentations 0.5.2 to ensure DualIAATransform is available
        "pip install 'albumentations==0.5.2' --force-reinstall",
        # Verify and enforce NumPy < 2.0 after all dependencies
        "pip install 'numpy<2.0,>=1.24.0' --force-reinstall",
        "python -c 'import numpy; assert numpy.__version__.startswith(\"1.\"), f\"NumPy version {numpy.__version__} is not compatible\"; print(f\"✓ NumPy {numpy.__version__} installed\")'",
        # Download SAM ViT-H checkpoint
        "mkdir -p /models/sam",
        "wget -O /models/sam/sam_vit_h_4b8939.pth https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        # Clone LaMa repo
        "git clone https://github.com/advimman/lama.git /lama",
        # Download LaMa big-lama model and extract properly
        "wget -O /tmp/big-lama.zip https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip",
        "unzip /tmp/big-lama.zip -d /tmp/big-lama-extracted",
        # Move contents to correct location (handling nested directory structure)
        "mkdir -p /lama/big-lama",
        "if [ -d /tmp/big-lama-extracted/big-lama ]; then mv /tmp/big-lama-extracted/big-lama/* /lama/big-lama/; else mv /tmp/big-lama-extracted/* /lama/big-lama/; fi",
        "rm -rf /tmp/big-lama.zip /tmp/big-lama-extracted",
        # Verify config.yaml exists
        "ls -la /lama/big-lama/",
        "test -f /lama/big-lama/config.yaml && echo '✓ LaMa config.yaml found' || (echo '✗ LaMa config.yaml NOT FOUND' && exit 1)",
    )
    .add_local_dir("templates", remote_path="/root/templates")
    .add_local_dir("static", remote_path="/root/static")
)

# Create Modal volumes
uploads_volume = modal.Volume.from_name("uploads-past-images", create_if_missing=True)
outputs_volume = modal.Volume.from_name("outputs-past-images", create_if_missing=True)
masks_volume = modal.Volume.from_name("masks-past-images", create_if_missing=True)

@app.function(
    image=image,
    gpu="A100-80GB",
    timeout=1800,  # 30 minutes
    min_containers=1,  # Keep 1 container warm
    max_containers=4,  # Max 4 GPUs
    scaledown_window=300,
    volumes={
        "/app/uploads": uploads_volume,
        "/app/outputs": outputs_volume,
        "/app/masks": masks_volume,
    },
)
@modal.asgi_app(label="past-images-web")
def fastapi_app():
    """
    Person removal pipeline with SAM + face_recognition + LaMa.

    Pipeline steps:
    1. SEGMENTATION: SAM automatic mask generation
    2. FACE MATCHING: Find target person using face_recognition
    3. MASK SELECTION: Select best mask containing face
    4. INPAINTING: LaMa removes person
    """
    import io
    import uuid
    import json
    import shutil
    import subprocess
    import sys
    from pathlib import Path
    from typing import List
    import asyncio

    import cv2
    import numpy as np
    from fastapi import FastAPI, File, UploadFile, HTTPException, Request
    from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from starlette.middleware.cors import CORSMiddleware
    from PIL import Image

    from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
    import face_recognition

    # Initialize FastAPI
    web_app = FastAPI(title="Past Images - SAM+LaMa", version="4.0.0")
    web_app.mount("/static", StaticFiles(directory="/root/static"), name="static")
    templates = Jinja2Templates(directory="/root/templates")

    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configuration
    UPLOAD_DIR = Path("/app/uploads")
    OUTPUT_DIR = Path("/app/outputs")
    MASK_DIR = Path("/app/masks")
    for directory in [UPLOAD_DIR, OUTPUT_DIR, MASK_DIR]:
        directory.mkdir(exist_ok=True, parents=True)

    SAM_CHECKPOINT = "/models/sam/sam_vit_h_4b8939.pth"
    LAMA_DIR = Path("/lama")
    LAMA_MODEL_DIR = LAMA_DIR / "big-lama"

    # Model initialization
    import threading
    _model_lock = threading.Lock()
    _models_loaded = False
    sam_generator = None

    def initialize_models():
        """Initialize SAM model (lazy loading)."""
        nonlocal sam_generator, _models_loaded

        with _model_lock:
            if _models_loaded:
                return sam_generator

            print("[INIT] Loading SAM ViT-H...")
            sam = sam_model_registry["default"](checkpoint=SAM_CHECKPOINT)
            sam.to("cuda")
            sam_generator = SamAutomaticMaskGenerator(sam)
            print("[INIT] SAM loaded")

            _models_loaded = True
            return sam_generator

    # Startup event to warm up models
    @web_app.on_event("startup")
    def startup_event():
        """Warm up models when container starts."""
        print("[STARTUP] Warming up models...")
        try:
            initialize_models()
            print("[STARTUP] All models loaded successfully!")
        except Exception as e:
            print(f"[STARTUP] ERROR: Failed to warm up models: {e}")
            import traceback
            traceback.print_exc()

    # ============================================================================
    # STEP 1: SAM SEGMENTATION
    # ============================================================================

    def segment_image(image: Image.Image, session_id: str) -> List[dict]:
        """
        STEP 1: Segment image using SAM automatic mask generation.
        Returns: List of mask dictionaries
        """
        print(f"[STEP 1] Segmenting image with SAM...")

        # Ensure models are loaded
        generator = sam_generator if sam_generator else initialize_models()

        # Convert to RGB numpy array with explicit dtype and ensure contiguous memory
        image_rgb = np.ascontiguousarray(image.convert("RGB"), dtype=np.uint8)
        print(f"[STEP 1] Image array shape: {image_rgb.shape}, dtype: {image_rgb.dtype}, contiguous: {image_rgb.flags['C_CONTIGUOUS']}")

        # Generate masks
        masks = generator.generate(image_rgb)
        print(f"[STEP 1] Generated {len(masks)} masks")

        # Save masks to volume for debugging
        mask_session_dir = MASK_DIR / session_id
        mask_session_dir.mkdir(exist_ok=True, parents=True)

        for i, mask_data in enumerate(masks):
            # Save binary mask
            mask_uint8 = mask_data['segmentation'].astype(np.uint8) * 255
            mask_path = mask_session_dir / f"mask_{i}.png"
            cv2.imwrite(str(mask_path), mask_uint8)

        # Save metadata
        metadata_path = mask_session_dir / "mask_metadata.txt"
        with open(metadata_path, "w") as f:
            f.write("Mask Metadata:\n")
            f.write("=" * 50 + "\n")
            for i, mask_data in enumerate(masks):
                f.write(f"\nMask {i}:\n")
                f.write(f"  Area: {mask_data['area']} pixels\n")
                f.write(f"  Bbox (XYWH): {mask_data['bbox']}\n")
                f.write(f"  Predicted IoU: {mask_data['predicted_iou']:.4f}\n")
                f.write(f"  Stability Score: {mask_data['stability_score']:.4f}\n")

        masks_volume.commit()
        return masks

    # ============================================================================
    # STEP 2: FACE RECOGNITION
    # ============================================================================

    def find_matching_face(target_image: Image.Image, query_image: Image.Image) -> dict:
        """
        STEP 2: Find matching face in target image based on query face.
        Returns: Face bbox dict or None
        """
        print(f"[STEP 2] Finding matching face...")

        target_rgb = np.ascontiguousarray(target_image.convert("RGB"), dtype=np.uint8)
        query_rgb = np.ascontiguousarray(query_image.convert("RGB"), dtype=np.uint8)

        # Detect faces
        target_locations = face_recognition.face_locations(target_rgb, model="cnn")
        target_encodings = face_recognition.face_encodings(target_rgb, target_locations)

        query_locations = face_recognition.face_locations(query_rgb, model="cnn")
        if len(query_locations) == 0:
            raise ValueError("No faces found in query image")

        # Use largest face if multiple
        if len(query_locations) > 1:
            print(f"[STEP 2] Found {len(query_locations)} faces in query, using largest")
            face_areas = [
                ((bottom - top) * (right - left), idx)
                for idx, (top, right, bottom, left) in enumerate(query_locations)
            ]
            face_areas.sort(reverse=True)
            largest_idx = face_areas[0][1]
            query_locations = [query_locations[largest_idx]]

        query_encoding = face_recognition.face_encodings(query_rgb, query_locations)[0]

        # Compare faces
        distances = face_recognition.face_distance(target_encodings, query_encoding)
        threshold = 0.6
        matches = distances <= threshold

        # Find best match
        for i, ((top, right, bottom, left), is_match, dist) in enumerate(zip(target_locations, matches, distances)):
            if is_match:
                print(f"[STEP 2] Match found! Distance: {dist:.3f}")
                return {
                    'top': int(top),
                    'right': int(right),
                    'bottom': int(bottom),
                    'left': int(left),
                    'distance': float(dist)
                }

        print(f"[STEP 2] No matching face found (threshold={threshold})")
        return None

    # ============================================================================
    # STEP 3: SELECT BEST MASK
    # ============================================================================

    def select_best_mask(masks: List[dict], face_bbox: dict, session_id: str) -> int:
        """
        STEP 3: Select the largest mask that has overlap with the detected face.
        
        Strategy:
        1. Calculate overlap area between face bbox and each mask
        2. Filter masks with significant overlap (>10% of face area)
        3. Select the largest mask from those with overlap
        
        Returns: mask index
        """
        print(f"[STEP 3] Selecting best mask from {len(masks)} candidates...")

        # Calculate face area and bbox
        face_left = face_bbox['left']
        face_right = face_bbox['right']
        face_top = face_bbox['top']
        face_bottom = face_bbox['bottom']
        face_area = (face_right - face_left) * (face_bottom - face_top)
        
        print(f"[STEP 3] Face bbox: ({face_left}, {face_top}) to ({face_right}, {face_bottom}), area={face_area}")

        mask_session_dir = MASK_DIR / session_id
        overlapping_masks = []

        for i, mask_data in enumerate(masks):
            mask_path = mask_session_dir / f"mask_{i}.png"
            mask_image = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

            if mask_image is None:
                continue

            # Calculate overlap between face bbox and mask
            h, w = mask_image.shape
            
            # Crop mask to face bbox region
            crop_top = max(0, face_top)
            crop_bottom = min(h, face_bottom)
            crop_left = max(0, face_left)
            crop_right = min(w, face_right)
            
            if crop_top >= crop_bottom or crop_left >= crop_right:
                continue  # No overlap
            
            # Count pixels in the face region that are part of the mask
            face_region = mask_image[crop_top:crop_bottom, crop_left:crop_right]
            overlap_pixels = np.count_nonzero(face_region)
            overlap_percentage = (overlap_pixels / face_area) * 100 if face_area > 0 else 0
            
            # Only consider masks with at least 10% overlap with face
            if overlap_percentage >= 10:
                overlapping_masks.append({
                    'index': i,
                    'area': mask_data['area'],
                    'overlap_pixels': overlap_pixels,
                    'overlap_percentage': overlap_percentage
                })
                print(f"  Mask {i}: Overlap={overlap_percentage:.1f}%, Mask area={mask_data['area']}")

        if not overlapping_masks:
            print(f"[STEP 3] WARNING: No masks with >10% overlap. Trying with face center point...")
            # Fallback: just check if face center is in mask
            face_center_x = (face_left + face_right) // 2
            face_center_y = (face_top + face_bottom) // 2
            
            for i, mask_data in enumerate(masks):
                mask_path = mask_session_dir / f"mask_{i}.png"
                mask_image = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if mask_image is None:
                    continue
                h, w = mask_image.shape
                if 0 <= face_center_y < h and 0 <= face_center_x < w:
                    if mask_image[face_center_y, face_center_x] > 0:
                        overlapping_masks.append({
                            'index': i,
                            'area': mask_data['area'],
                            'overlap_pixels': 1,
                            'overlap_percentage': 0
                        })
            
            if not overlapping_masks:
                raise ValueError("No masks overlap with the detected face")

        # Select the mask with the LARGEST AREA that has overlap
        best = max(overlapping_masks, key=lambda x: x['area'])
        print(f"[STEP 3] ✓ Selected mask {best['index']}: area={best['area']}, overlap={best['overlap_percentage']:.1f}%")

        return best['index']

    # ============================================================================
    # STEP 4: LAMA INPAINTING
    # ============================================================================

    def inpaint_with_lama(image: Image.Image, mask: Image.Image, session_id: str, device: str = "cuda") -> Image.Image:
        """
        STEP 4: Inpaint using LaMa.
        Returns: Inpainted image
        """
        print(f"[STEP 4] Inpainting with LaMa...")

        # Create working directories
        work_dir = OUTPUT_DIR / f"{session_id}_lama_in"
        out_dir = OUTPUT_DIR / f"{session_id}_lama_out"
        work_dir.mkdir(exist_ok=True, parents=True)
        out_dir.mkdir(exist_ok=True, parents=True)

        # Save image and mask
        base_name = "image"
        image.save(work_dir / f"{base_name}.png")
        # Use cv2 to save mask to avoid PIL dtype issues
        mask_array = np.array(mask)
        print(f"[STEP 4] Mask array dtype: {mask_array.dtype}, shape: {mask_array.shape}")
        if mask_array.dtype != np.uint8:
            mask_array = mask_array.astype(np.uint8)
        # Ensure it's 2D grayscale
        if len(mask_array.shape) == 3:
            mask_array = mask_array[:, :, 0]
        success = cv2.imwrite(str(work_dir / f"{base_name}_mask001.png"), mask_array)
        if not success:
            raise RuntimeError(f"Failed to write mask file")
        print(f"[STEP 4] Mask saved successfully")

        # Run LaMa prediction
        predict_py = LAMA_DIR / "bin" / "predict.py"
        args = [
            sys.executable, str(predict_py),
            f"model.path={str(LAMA_MODEL_DIR)}",
            f"indir={str(work_dir)}",
            f"outdir={str(out_dir)}",
            f"device={device}"
        ]

        env = os.environ.copy()
        env["PYTHONPATH"] = str(LAMA_DIR)
        env["TORCH_HOME"] = str(LAMA_DIR)

        # Debug: List files in work_dir before LaMa
        print(f"[STEP 4] Files in work_dir before LaMa:")
        for f in work_dir.iterdir():
            print(f"  - {f.name} ({f.stat().st_size} bytes)")

        print(f"[STEP 4] Running LaMa...")
        print(f"[STEP 4] Command: {' '.join(args)}")
        proc = subprocess.run(args, env=env, capture_output=True, text=True)
        print(f"[STEP 4] LaMa return code: {proc.returncode}")
        print(f"[STEP 4] LaMa stdout: {proc.stdout}")
        if proc.stderr:
            print(f"[STEP 4] LaMa stderr: {proc.stderr}")
        
        # Debug: List files in out_dir after LaMa
        print(f"[STEP 4] Files in out_dir after LaMa:")
        if out_dir.exists():
            for f in out_dir.iterdir():
                print(f"  - {f.name} ({f.stat().st_size} bytes)")
        else:
            print(f"  - out_dir does not exist!")
        
        if proc.returncode != 0:
            raise RuntimeError(f"LaMa prediction failed with return code {proc.returncode}")

        # Load result - LaMa outputs with _mask suffix
        # Try both possible output names
        possible_outputs = [
            out_dir / f"{base_name}_mask001.png",
            out_dir / f"{base_name}.png",
        ]
        
        result_path = None
        for path in possible_outputs:
            if path.exists():
                result_path = path
                break
        
        if result_path is None:
            # List all possible output files for debugging
            print(f"[STEP 4] Expected outputs: {[str(p) for p in possible_outputs]}")
            print(f"[STEP 4] Available files in {out_dir}:")
            if out_dir.exists():
                for f in out_dir.rglob("*"):
                    if f.is_file():
                        print(f"  - {f.relative_to(out_dir)} ({f.stat().st_size} bytes)")
            raise FileNotFoundError(f"LaMa output not found in {out_dir}")

        print(f"[STEP 4] Loading result from: {result_path}")
        result = Image.open(result_path)
        
        # Verify image is valid
        result.verify()
        # Reopen after verify (verify closes the file)
        result = Image.open(result_path).convert("RGB")
        
        # Verify dimensions
        print(f"[STEP 4] Result image size: {result.size}, mode: {result.mode}")
        
        # Cleanup
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)

        print(f"[STEP 4] Inpainting complete")
        return result

    # ============================================================================
    # WEB ENDPOINTS
    # ============================================================================

    @web_app.get("/health")
    async def health():
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy" if _models_loaded else "initializing",
            "models_loaded": _models_loaded
        })

    @web_app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Serve the main upload page."""
        return templates.TemplateResponse("index.html", {"request": request})

    @web_app.post("/api/process")
    async def process_images(
        reference: UploadFile = File(...),
        targets: List[UploadFile] = File(...),
        session_id: str = None,
    ):
        """
        Process images using SAM + face_recognition + LaMa pipeline.

        Pipeline:
        1. Segment target image with SAM
        2. Match face from reference image
        3. Select best mask containing face
        4. Inpaint with LaMa
        """
        if len(targets) > 1:
            raise HTTPException(status_code=400, detail="Maximum 1 target image allowed")

        if session_id is None:
            session_id = str(uuid.uuid4())

        print(f"[API] Processing session {session_id}: 1 reference + {len(targets)} target{'s' if len(targets) != 1 else ''}")

        try:
            # Ensure models loaded
            initialize_models()

            # Load reference image - ensure proper format regardless of input
            ref_content = await reference.read()
            ref_pil = Image.open(io.BytesIO(ref_content))
            # Convert to RGB and create fresh copy to ensure clean memory layout
            ref_image = Image.frombytes('RGB', ref_pil.size, ref_pil.convert('RGB').tobytes())
            print(f"[API] Loaded reference image: {reference.filename}, size: {ref_image.size}")

            results = []

            for idx, target_file in enumerate(targets):
                try:
                    print(f"\n[API] Processing image {idx+1}/{len(targets)}: {target_file.filename}")

                    # Load target image - ensure proper format regardless of input
                    target_content = await target_file.read()
                    target_pil = Image.open(io.BytesIO(target_content))
                    # Convert to RGB and create fresh copy to ensure clean memory layout
                    target_image = Image.frombytes('RGB', target_pil.size, target_pil.convert('RGB').tobytes())
                    print(f"[API] Loaded target image: {target_file.filename}, size: {target_image.size}")

                    # STEP 1: Segment
                    masks = segment_image(target_image, f"{session_id}_{idx}")

                    # STEP 2: Find face
                    face_bbox = find_matching_face(target_image, ref_image)
                    if face_bbox is None:
                        raise ValueError("No matching face found")

                    # STEP 3: Select mask
                    mask_idx = select_best_mask(masks, face_bbox, f"{session_id}_{idx}")

                    # Load selected mask
                    mask_path = MASK_DIR / f"{session_id}_{idx}" / f"mask_{mask_idx}.png"
                    # Load mask using cv2 and convert to PIL to avoid dtype issues
                    mask_cv2 = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                    if mask_cv2 is None:
                        raise ValueError(f"Could not load mask from {mask_path}")
                    # Ensure array is contiguous and in correct format
                    mask_array = np.ascontiguousarray(mask_cv2, dtype=np.uint8)
                    mask_image = Image.fromarray(mask_array, mode='L')

                    # STEP 4: Inpaint
                    result_image = inpaint_with_lama(target_image, mask_image, f"{session_id}_{idx}")

                    # Save result with proper format
                    output_filename = f"{session_id}_{idx}_{uuid.uuid4()}.jpg"
                    output_path = OUTPUT_DIR / output_filename
                    
                    # Ensure result_image is in RGB mode
                    if result_image.mode != 'RGB':
                        result_image = result_image.convert('RGB')
                    
                    # Save with explicit JPEG format
                    result_image.save(output_path, format='JPEG', quality=95, optimize=False)
                    
                    # Verify file was saved and is valid
                    if not output_path.exists():
                        raise RuntimeError(f"Failed to save output file: {output_path}")
                    
                    file_size = output_path.stat().st_size
                    if file_size == 0:
                        raise RuntimeError(f"Output file is empty: {output_path}")
                    
                    # Verify the saved image can be opened
                    try:
                        verify_img = Image.open(output_path)
                        verify_img.verify()
                        verify_img = Image.open(output_path)  # Reopen after verify
                        print(f"[API] Saved result to {output_path} ({file_size} bytes, {verify_img.size})")
                    except Exception as e:
                        raise RuntimeError(f"Saved image is corrupted: {e}")
                    
                    # Commit outputs volume after each save to persist the file
                    outputs_volume.commit()
                    print(f"[API] Volume committed for {output_filename}")

                    results.append({
                        "original": target_file.filename,
                        "output": output_filename,
                        "url": f"/outputs/{output_filename}"
                    })

                    print(f"[API] ✓ Image {idx} processed successfully")

                except Exception as e:
                    print(f"[API] ✗ Image {idx} failed: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    results.append({
                        "original": target_file.filename,
                        "error": str(e)
                    })

            outputs_volume.commit()
            masks_volume.commit()

            return JSONResponse({
                "success": True,
                "session_id": session_id,
                "results": results,
                "processed": len([r for r in results if "url" in r]),
                "failed": len([r for r in results if "error" in r])
            })

        except Exception as e:
            print(f"[API] ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    @web_app.get("/outputs/{filename}")
    async def get_output(filename: str):
        """Serve processed images."""
        # Reload volume to ensure file is available
        outputs_volume.reload()
        
        file_path = OUTPUT_DIR / filename
        
        print(f"[DOWNLOAD] Attempting to serve: {file_path}")
        print(f"[DOWNLOAD] File exists: {file_path.exists()}")
        
        if not file_path.resolve().is_relative_to(OUTPUT_DIR.resolve()):
            print(f"[DOWNLOAD] Access denied - path not in OUTPUT_DIR")
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            # List available files for debugging
            print(f"[DOWNLOAD] File not found. Available files in {OUTPUT_DIR}:")
            if OUTPUT_DIR.exists():
                for f in OUTPUT_DIR.iterdir():
                    if f.is_file():
                        print(f"  - {f.name}")
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        print(f"[DOWNLOAD] Serving file: {filename}")
        return FileResponse(
            path=file_path, 
            media_type="image/jpeg",
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    return web_app
